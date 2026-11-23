"""Lost NAT regression: no real nftables, USB, modem or network operations."""
import json
import re
from types import SimpleNamespace

import pytest

from uz801_manager.ap_sharing import ApSharing,ERROR,OWNER,TABLE
from test_quick_settings import quick
from uz801_manager.hotspot import AP_UUID,CELL_UUID
from uz801_manager.quick_intent import save_intent


class Nft:
    def __init__(self):self.table=None;self.writes=[];self.calls=[];self.fail_check=False;self.fail_read=False
    def run(self,args,**kw):
        self.calls.append(args)
        code=0;out=''
        if args==['nft','-j','list','tables']:
            code=int(self.fail_read)
            out=json.dumps({'nftables':[{'table':{'family':'inet','name':TABLE}}] if self.table else []})
        elif args==['nft','-j','list','table','inet',TABLE]:out=json.dumps({'nftables':self.table})
        elif args==['nft','--check','-f','-']:code=int(self.fail_check)
        elif args==['nft','-f','-']:
            rules=kw['input'];self.writes.append(rules)
            match=re.search(r'oifname "([^"]+)"',rules)
            self.table=table(match[1]) if match else None
        else:raise AssertionError('Unexpected command')
        return SimpleNamespace(returncode=code,stdout=out,stderr='')


def table(interface):
    return [
        {'metainfo':{'json_schema_version':1}},
        {'table':{'family':'inet','name':TABLE,'handle':10,'comment':OWNER}},
        {'chain':{'family':'inet','table':TABLE,'name':'srcnat','handle':1,
                  'type':'nat','hook':'postrouting','prio':99,'policy':'accept'}},
        {'rule':{'family':'inet','table':TABLE,'chain':'srcnat','handle':2,'expr':[
            {'match':{'op':'==','left':{'payload':{'protocol':'ip','field':'saddr'}},
                      'right':{'prefix':{'addr':'192.168.8.0','len':24}}}},
            {'match':{'op':'==','left':{'meta':{'key':'oifname'}},'right':interface}},
            {'masquerade':None},
        ]}},
    ]


def test_missing_nat_recreated_without_resetting_ap_modem_or_other_firewalls():
    n=Nft();sharing=ApSharing(n)
    assert sharing.current() is None and not n.writes
    assert sharing.reconcile('wwan0') and sharing.current()=='wwan0'
    assert len(n.writes)==1
    rules=n.writes[0]
    assert 'ip saddr 192.168.8.0/24 oifname "wwan0" masquerade' in rules
    assert 'priority 99' in rules and OWNER in rules
    assert not any(x in rules for x in ['flush','usb0','hook input','hook forward','nm-shared','table inet filter'])
    n.writes.clear()
    assert not sharing.reconcile('wwan0') and not n.writes
    # Simulate dynamic firewall loss while the existing AP/bearer remain up.
    n.table=None
    assert sharing.reconcile('wwan0') and len(n.writes)==1


def test_uplink_change_is_atomic_and_off_removes_only_owned_nat():
    n=Nft();n.table=table('wwan0');sharing=ApSharing(n)
    sharing.reconcile('rmnet1')
    assert n.writes[-1].startswith('delete table inet '+TABLE+'\ntable inet '+TABLE)
    assert sharing.current()=='rmnet1'
    sharing.reconcile(None)
    assert n.writes[-1]=='delete table inet '+TABLE+'\n' and n.table is None
    assert not sharing.reconcile(None)


@pytest.mark.parametrize('value',['usb0','wlan0','lo','wwan0"; flush ruleset','wwan'+'x'*28,''])
def test_invalid_or_non_cellular_interface_never_mutates(value):
    n=Nft()
    with pytest.raises(RuntimeError,match=ERROR):ApSharing(n).reconcile(value)
    assert not n.writes


@pytest.mark.parametrize('corruption',['owner','chain','subnet','extra_rule','interface'])
def test_foreign_or_modified_table_never_overwritten_even_on_off(corruption):
    n=Nft();n.table=table('wwan0')
    if corruption=='owner':n.table[1]['table']['comment']='foreign'
    if corruption=='chain':n.table[2]['chain']['hook']='input'
    if corruption=='subnet':n.table[3]['rule']['expr'][0]['match']['right']['prefix']['len']=0
    if corruption=='extra_rule':n.table.append(n.table[-1])
    if corruption=='interface':n.table[3]['rule']['expr'][1]['match']['right']='usb0'
    for target in [None,'wwan0']:
        with pytest.raises(RuntimeError,match=ERROR):ApSharing(n).reconcile(target)
    assert not n.writes


def test_read_or_syntax_check_failure_never_applies_rules():
    n=Nft();sharing=ApSharing(n)
    n.fail_read=True
    with pytest.raises(RuntimeError,match=ERROR):sharing.reconcile('wwan0')
    n.fail_read=False;n.fail_check=True
    with pytest.raises(RuntimeError,match=ERROR):sharing.reconcile('wwan0')
    assert not n.writes


def actual_forwarding(quick):
    q,n,_,_=quick;nft=Nft();guard=[False]
    n.active_profiles={'wlan0':AP_UUID,'cell':CELL_UUID}
    n.cellular_interface=lambda _:'wwan0'
    original=n.nm
    n.nm=lambda *args,**kw:'shared\n192.168.8.1/24' if args[:2]==('-g','ipv4.method,ipv4.addresses') else original(*args,**kw)
    def run(args,**kw):
        if args==['nft','list','table','inet','openstick_quick_ap']:
            return SimpleNamespace(returncode=0 if guard[0] else 1)
        if args==['nft','-f','-'] and 'openstick_quick_ap' in kw['input']:
            guard[0]=True;return SimpleNamespace(returncode=0)
        return nft.run(args,**kw)
    def command(args,**kw):
        assert args==['nft','delete','table','inet','openstick_quick_ap'];guard[0]=False
    n.run=run;n.command=command
    return q,n,nft,guard


@pytest.mark.parametrize('veto',['missing_intent','data_off','airplane','no_bearer'])
def test_forwarding_never_installs_nat_without_positive_saved_consent_and_bearer(quick,veto):
    q,n,nft,guard=actual_forwarding(quick)
    if veto!='missing_intent':save_intent(q.directory,airplane=veto=='airplane',data_allowed=veto not in ('airplane','data_off'))
    if veto=='no_bearer':n.active_profiles['cell']=None
    q._ap_forwarding(True)
    assert not nft.writes and guard[0]


def test_nat_readback_precedes_unblocking_and_off_retains_ap_and_cellular_identity(quick):
    q,n,nft,guard=actual_forwarding(quick)
    save_intent(q.directory,airplane=False,data_allowed=True);guard[0]=True
    q._ap_forwarding(True)
    assert nft.table and not guard[0]
    q._ap_forwarding(False)
    assert not nft.table and guard[0]
    assert n.active('wlan0')==AP_UUID and n.active('cell')==CELL_UUID


def test_nat_failure_leaves_closed_guard_and_no_wrong_subnet_nat(quick):
    q,n,nft,guard=actual_forwarding(quick)
    save_intent(q.directory,airplane=False,data_allowed=True);guard[0]=True;nft.fail_check=True
    with pytest.raises(RuntimeError,match=ERROR):q._ap_forwarding(True)
    assert guard[0] and not nft.writes
    n.nm=lambda *args,**kw:'shared\n192.0.2.1/24'
    with pytest.raises(RuntimeError,match=ERROR):q._ap_forwarding(True)
    assert guard[0] and not nft.writes

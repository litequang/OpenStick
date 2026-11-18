"""AP client fixtures. No USB, modem, system firewall or real MACs."""
from contextlib import nullcontext
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import uuid

import pytest

from uz801_manager.ap_clients import ApClients, TABLE, stations, mac, validate
from uz801_manager.hotspot import AP_UUID
from uz801_manager.hosting import create_hosting_app

A='02:00:00:00:00:01'
B='02:00:00:00:00:02'
DRIVER=f'''Station {A} (on wlan0)
\trx bytes:\t123456
\ttx bytes:\t654321
\tsignal:\t-51 [-51] dBm
\trx bitrate:\t72.2 MBit/s MCS 7
\ttx bitrate:\t65.0 MBit/s
\tconnected time:\t61 seconds
Station {B} (on wlan0)
\trx bytes:\t9
'''


class Network:
    def __init__(self):
        self.identity=AP_UUID;self.calls=[];self.table=None;self.base='table inet preserved { }'
        self.driver=DRIVER;self.fail=None
        self.neighbors=[{'dev':'wlan0','dst':'192.168.8.21','lladdr':A,'state':['REACHABLE']},
                        {'dev':'wlan0','dst':'2001:db8::21','lladdr':A,'state':['STALE']}]
    def active(self, interface):assert interface=='wlan0';return self.identity
    def run(self,args,**kw):
        assert kw.get('shell') is False and kw['timeout']==8
        self.calls.append((args,kw.get('input')))
        if self.fail=='disconnect':raise OSError('private data')
        result='';error='';code=0
        if args==['iw','dev','wlan0','station','dump']:
            result=self.driver
            if self.fail=='inventory':code=1;error='private identifier'
        elif args==['ip','-j','neigh','show','dev','wlan0']:result=json.dumps(self.neighbors)
        elif args==['nft','list','ruleset']:result=self.base+(self.table or '')
        elif args==['nft','list','table','inet',TABLE]:
            result=self.table or ''
            if self.table is None:code=1;error='No such file or directory'
        elif args==['nft','--check','-f','-']:
            if self.fail=='check':code=1;error='private nft details'
        elif args==['nft','-f','-']:
            if self.fail=='apply':self.fail=None;code=1;error='private nft details'
            else:self.table=kw['input']
        elif args==['nft','delete','table','inet',TABLE]:self.table=None
        else:raise AssertionError(args)
        return subprocess.CompletedProcess(args,code,result,error)


@pytest.fixture
def clients(tmp_path,monkeypatch):
    network=Network();lease=tmp_path/'leases'
    lease.write_text(f'2000 {A} 192.168.8.20 fixture-phone *\n2000 02:00:00:00:00:03 192.168.8.22 stale-only *\n')
    backend=ApClients(tmp_path/'private',network=network,lock_factory=nullcontext,
                      leases=[lease],clock=lambda:1000,available=lambda _:True)
    if os.name=='nt':monkeypatch.setattr(backend.journal,'_sync_directory',lambda:None)
    return backend,network,lease


def act(backend,action='block',address=A,operation=None):
    return backend.call(action,mac=address,operation=operation or str(uuid.uuid4()),confirm=True)


def test_driver_is_authority_not_dhcp_and_status_does_not_write(clients):
    backend,network,_=clients
    state=backend.status()
    assert state['count']==2 and state['inventory_available'] and not state['association_block_supported']
    assert [v['mac'] for v in state['clients']]==[A,B]
    first=state['clients'][0]
    assert first['name']=='fixture-phone' and first['ip']=='192.168.8.21'
    assert first['signal_dbm']==-51 and first['rx_mbps']==72.2 and first['tx_bytes']==654321
    assert first['connected_seconds']==61
    assert not backend.directory.exists()
    assert not any(args[0]=='nft' and args[1]!='list' for args,_ in network.calls)


@pytest.mark.parametrize('value',['', '00:00:00:00:00:00','ff:ff:ff:ff:ff:ff','01:00:00:00:00:01',
    '02:00:00:00:00:01;drop',None,'$(secret)','02-00-00-00-00-01'])
def test_bad_mac_rejected_before_transport_or_state(clients,value):
    backend,network,_=clients
    with pytest.raises(ValueError):act(backend,address=value)
    assert not network.calls and not backend.directory.exists()


def test_action_contract_confirmation_operation_and_unknown_fields():
    value={'action':'block','mac':A,'operation':str(uuid.uuid4()),'confirm':True}
    assert validate(value)=='block' and mac(A.upper())==A
    for extra in [{'confirm':False},{'operation':'../bad'},{'action':'kick'},{'command':'reset'}]:
        with pytest.raises(ValueError):validate({**value,**extra})


def test_block_apply_receipt_restore_on_boot_and_unblock_preserves_base(clients):
    backend,network,_=clients;base=network.base;identity=str(uuid.uuid4())
    result=act(backend,operation=identity)
    assert result['saved'] and result['filter_applied'] and backend.config()==[A]
    assert 'iifname "wlan0" ether saddr @blocked counter drop' in network.table
    assert 'oifname "wlan0" ip daddr @blocked4 counter drop' in network.table
    assert '192.168.8.21' in network.table and '2001:db8::21' in network.table
    assert 'hook forward priority -15' in network.table
    assert not any(v in network.table for v in ['usb0','masquerade','flush ruleset','hook input','hook output'])
    assert backend.status()['clients'][0]['internet_blocked'] and backend.status()['filter_applied']
    with pytest.raises(RuntimeError,match='ALREADY_ATTEMPTED'):act(backend,operation=identity)
    receipt=json.loads((backend.journal.directory/(identity+'.json')).read_text())
    assert receipt['state']=='COMPLETED' and A not in json.dumps(receipt)
    # New worker/boot has no in-memory rules or lease assumption.
    network.table=None
    replacement=ApClients(backend.directory,network=network,lock_factory=nullcontext)
    replacement.tick();assert network.table
    old=len([1 for args,_ in network.calls if args==['nft','-f','-']])
    replacement.tick();assert len([1 for args,_ in network.calls if args==['nft','-f','-']])==old
    act(backend,'unblock');assert backend.config()==[] and network.table is None and network.base==base


def test_neighbor_change_refresh_and_station_mode_removes_only_owned_filter(clients):
    backend,network,_=clients;act(backend)
    network.neighbors=[{'dst':'192.168.8.30','lladdr':A,'state':['STALE']}]
    backend.tick();assert '192.168.8.30' in network.table and '192.168.8.21' not in network.table
    network.identity='saved-station';backend.tick()
    assert network.table is None and backend.config()==[A]
    state=backend.status();assert not state['ap_active'] and not state['filter_applied'] and state['count'] is None
    network.identity=AP_UUID;backend.prepare_ap();assert network.table


@pytest.mark.parametrize('fail',['check','apply'])
def test_failed_firewall_transaction_restores_private_policy_without_raw_errors(clients,fail):
    backend,network,_=clients;act(backend);before=backend.path.read_bytes();table=network.table
    network.fail=fail
    with pytest.raises(RuntimeError,match='^AP_CLIENTS_FIREWALL_FAILED$'):act(backend,address=B)
    assert backend.path.read_bytes()==before and network.table==table
    assert all('private' not in p.read_text() for p in backend.journal.directory.glob('*.json'))


def test_uncertain_save_after_replace_is_rolled_back_and_config_corruption_is_not_ignored(clients,monkeypatch):
    backend,network,_=clients
    from uz801_manager.hotspot import Hotspot
    normal=Hotspot.atomic;counter=[0]
    def fail_after_replace(path,text):
        normal(path,text);counter[0]+=1
        if counter[0]==1:raise OSError('directory sync failed')
    monkeypatch.setattr(Hotspot,'atomic',fail_after_replace)
    with pytest.raises(RuntimeError,match='^AP_CLIENTS_SAVE_FAILED$'):act(backend)
    assert backend.config() is None and network.table is None
    backend.path.write_text('{corrupt')
    before=list(backend.journal.directory.glob('*'))
    with pytest.raises(RuntimeError,match='^AP_CLIENTS_INVALID$'):act(backend)
    assert list(backend.journal.directory.glob('*'))==before


def test_offload_or_foreign_table_are_rejected_without_flushing_them(clients):
    backend,network,_=clients
    network.base='table inet preserved { flowtable other {} }'
    with pytest.raises(RuntimeError,match='AP_CLIENTS_OFFLOAD_UNSUPPORTED'):act(backend)
    assert network.table is None and 'flowtable' in network.base
    network.base='table inet preserved {}';network.table='table inet '+TABLE+' { comment "foreign"; }'
    with pytest.raises(RuntimeError):act(backend)
    assert 'foreign' in network.table


def test_inventory_disconnect_empty_and_malformed_are_distinguished(clients):
    backend,network,_=clients;network.driver=''
    state=backend.status();assert state['count']==0 and state['inventory_available']
    network.fail='inventory';state=backend.status()
    assert state['count'] is None and not state['inventory_available'] and state['error']=='AP_CLIENTS_UNAVAILABLE'
    network.fail='disconnect'
    state=backend.status();assert state['count'] is None and 'private' not in json.dumps(state)
    for text in ['private error', 'Station invalid (on wlan0)', 'x'*131073]:
        with pytest.raises(RuntimeError):stations(text)


def test_readonly_leases_are_bounded_expired_not_client_identity(clients):
    backend,network,lease=clients
    network.neighbors=[]
    lease.write_text(f'2 {A} 192.168.8.30 expired *\n2000 {B} 203.0.113.2 outside *\n')
    state=backend.status();assert all(v['ip'] is None and v['name'] is None for v in state['clients'])
    lease.write_text('x'*65537);assert backend.status()['count']==2


def test_pending_network_operation_blocks_writes_and_capacity_is_bounded(clients):
    backend,network,_=clients
    backend.directory.mkdir();pending=backend.directory/'setup-pending.json';pending.write_text('{}')
    with pytest.raises(RuntimeError,match='NETWORK_BUSY'):act(backend)
    assert not network.calls and not backend.path.exists();pending.unlink()
    values=[f'02:00:00:01:00:{v:02x}' for v in range(128)]
    backend.path.write_text(json.dumps({'version':1,'blocked':values}))
    with pytest.raises(RuntimeError,match='AP_CLIENTS_LIST_FULL'):act(backend)
    assert backend.config()==values


def test_api_auth_origin_token_input_and_read_only_get(clients):
    backend,network,_=clients
    setup=SimpleNamespace(clients=backend)
    app=create_hosting_app(usb_portal=True,backend=object(),setup_backend=setup,token='fixture')
    client=app.test_client();base='http://172.16.42.1';headers={'X-OpenStick-Token':'fixture','Origin':base}
    assert client.get('/api/ap/clients',base_url=base).status_code==403
    assert client.get('/api/ap/clients',base_url=base,headers=headers).json['count']==2
    assert not backend.directory.exists()
    data={'action':'block','mac':A,'operation':str(uuid.uuid4()),'confirm':True}
    assert client.post('/api/ap/clients',base_url=base,json=data).status_code==403
    assert client.post('/api/ap/clients',base_url=base,headers={**headers,'Origin':'https://evil.invalid'},json=data).status_code==403
    assert client.post('/api/ap/clients',base_url=base,headers=headers,json={**data,'confirm':False}).status_code==400
    assert not backend.directory.exists()
    assert client.post('/api/ap/clients',base_url=base,headers=headers,json=data).json['saved']
    result=client.get('/api/ap/clients',base_url=base,headers=headers).json
    assert result['blocked']==[A] and not result['association_block_supported']


def test_orphaned_filter_is_not_reported_as_an_empty_successful_policy(clients):
    backend,network,_=clients
    network.table=ApClients.rules([A])
    state=backend.status()
    assert state['blocked']==[] and not state['filter_applied']
    assert state['error']=='AP_CLIENTS_FIREWALL_FAILED' and network.table is not None


def test_saved_filter_is_installed_before_owned_ap_activation(clients):
    from uz801_manager.ap_options import activate
    backend,network,_=clients
    act(backend);network.identity='saved-station';backend.suspend()
    events=[]
    def up(identity):
        assert network.table and A in network.table
        events.append(identity);network.identity=identity
    network.up=up
    wrapper=SimpleNamespace(directory=backend.directory,network=network,read=lambda _: {},profiles=Path('unused'))
    activate(wrapper,AP_UUID)
    assert events==[AP_UUID]


@pytest.mark.parametrize('text',['unexpected-output','Station invalid (on wlan0)', 'x'*131073])
def test_malformed_inventory_is_not_zero_clients(text):
    with pytest.raises(RuntimeError,match='AP_CLIENTS_UNAVAILABLE'):stations(text)


def test_busybox_ip_without_json_uses_fixed_plain_neighbor_listing(clients):
    backend,network,_=clients;normal=network.run
    def busybox(args,**kw):
        if args==['ip','-j','neigh','show','dev','wlan0']:
            return subprocess.CompletedProcess(args,1,'','ip: invalid option -- j')
        if args==['ip','neigh','show','dev','wlan0']:
            return subprocess.CompletedProcess(args,0,
                f'192.168.8.21 dev wlan0 lladdr {A} REACHABLE\n'
                f'2001:db8::21 lladdr {A} STALE\n'
                f'192.168.8.22 dev usb0 lladdr {A} REACHABLE\n'
                '192.168.8.23 FAILED\ninvalid data\n','')
        return normal(args,**kw)
    network.run=busybox
    assert backend.status()['clients'][0]['ip']=='192.168.8.21'
    result=act(backend)
    assert result['saved'] and result['filter_applied']
    assert '192.168.8.21' in network.table and '2001:db8::21' in network.table
    assert '192.168.8.22' not in network.table

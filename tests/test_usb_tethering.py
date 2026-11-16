"""Tethering ownership/rollback tests; no host networking or USB operations."""
from pathlib import Path
from contextlib import nullcontext
import uuid
from types import SimpleNamespace

import pytest

from uz801_manager.usb_tethering import MANAGEMENT, UsbTethering


class Network:
    def __init__(self):
        self.calls=[];self.table=None;self.daemon=False;self.fail_start=False;self.internet_ok=True
    def devices(self):return ['modem']
    def active(self, interface):return {'usb0':'management','wlan0':'station'}.get(interface)
    def cellular_interface(self, control):return None
    def internet(self, interface, control):return self.internet_ok
    def nm(self,*args):return 'manual' if args[1]=='ipv4.method' else 'wwan0'
    def run(self,args,**kw):
        self.calls.append((args,kw))
        if args[:3]==['nft','list','table']:return SimpleNamespace(returncode=0 if self.table else 1,stdout=self.table or '')
        if args==['nft','-f','-']:self.table=kw['input']
        if args[:2]==['rc-service','openstick-usb-dhcp'] and args[-1]=='stop':self.daemon=False
        return SimpleNamespace(returncode=0,stdout='')
    def command(self,args,timeout=12):
        self.calls.append((args,{}))
        if args[:3]==['ip','-4','route']:return '1.1.1.1 via 192.0.2.1 dev wlan0'
        if args==['rc-service','openstick-usb-dhcp','start']:
            if self.fail_start:raise RuntimeError('SERVICE_FAILED')
            self.daemon=True
        if args==['rc-service','openstick-usb-dhcp','stop']:self.daemon=False
        return ''


@pytest.fixture
def tether(tmp_path):
    network=Network()
    service=tmp_path/'service';service.touch()
    sysctl=tmp_path/'forward';sysctl.write_text('0\n')
    boot=tmp_path/'proc/sys/kernel/random/boot_id';boot.parent.mkdir(parents=True);boot.write_text('fixture-boot')
    backend=UsbTethering(tmp_path/'state',network=network,proc=tmp_path/'proc',service=service,sysctl=sysctl,supported=lambda:True)
    backend.boot=lambda:'fixture-boot'
    sysctl.write_text('0\n')
    backend.running=lambda:network.daemon
    management=[True]
    backend._management_processes=lambda:[(10,'fixture-start')] if management[0] else []
    backend._stop_management=lambda:management.__setitem__(0,False)
    backend._restore_management=lambda:management.__setitem__(0,True)
    return backend,network,management


def test_status_is_read_only_and_old_boot_does_not_replay(tether):
    backend,network,_=tether
    backend.status()
    assert not backend.path.exists() and not network.calls
    backend.write({'enabled':True,'boot':'previous-boot'})
    network.daemon=True
    assert not backend.status()['enabled']


def test_no_internet_never_replaces_management_dhcp(tether):
    backend,network,management=tether;network.internet_ok=False
    with pytest.raises(RuntimeError,match='USB_NO_INTERNET'):backend.enable()
    assert management==[True] and not network.daemon and backend.sysctl.read_text().strip()=='0'
    assert not any(args[0]=='rc-service' for args,_ in network.calls)


def test_dhcp_failure_restores_management_and_closes_usb_forwarding(tether):
    backend,network,management=tether;network.fail_start=True
    with pytest.raises(RuntimeError,match='SERVICE_FAILED'):backend.enable()
    assert management==[True] and not network.daemon
    assert 'iifname "usb0" drop' in network.table and 'masquerade' not in network.table
    assert backend.sysctl.read_text().strip()=='0' and not backend.path.exists()


def test_persistence_failure_also_rolls_back_dhcp_nat_and_forwarding(tether):
    backend,network,management=tether
    backend.write=lambda value:(_ for _ in ()).throw(OSError('fixture failure'))
    with pytest.raises(OSError):backend.enable()
    assert management==[True] and not network.daemon
    assert 'masquerade' not in network.table and backend.sysctl.read_text().strip()=='0'


@pytest.mark.parametrize('prior',['0','1'])
def test_enable_disable_preserves_usb_profile_and_existing_forwarding_owner(tether,prior):
    backend,network,management=tether;backend.sysctl.write_text(prior+'\n')
    backend.enable()
    assert not management[0] and network.daemon
    assert backend.read()['enabled'] and backend.sysctl.read_text().strip()=='1'
    assert 'ip saddr 172.16.42.0/24' in network.table and 'masquerade' in network.table
    backend.disable()
    assert management[0] and not network.daemon and backend.read()['enabled'] is False
    assert backend.sysctl.read_text().strip()==prior
    assert all(args[0] in ('ip','nft','rc-service') for args,_ in network.calls)
    assert all('nmcli' not in args and 'reboot' not in args for args,_ in network.calls)


def test_unknown_management_dhcp_arguments_are_rejected_without_signalling(tmp_path):
    proc=tmp_path/'proc/11';proc.mkdir(parents=True)
    (proc/'comm').write_text('unudhcpd\n')
    (proc/'cmdline').write_bytes(b'\0'.join(a.encode() for a in MANAGEMENT+['--unknown'])+b'\0')
    backend=UsbTethering(tmp_path/'state',proc=tmp_path/'proc')
    with pytest.raises(RuntimeError,match='USB_DHCP_CONFLICT'):backend._management_processes()


def test_usb_dns_dhcp_is_scoped_and_does_not_claim_loopback_or_gadget():
    service=(Path(__file__).parents[1]/'scripts/openrc/openstick-usb-dhcp').read_text()
    assert '--interface=usb0' in service and '--except-interface=lo' in service
    assert '--dhcp-option=3,172.16.42.1' in service and '--dhcp-option=6,172.16.42.1' in service
    assert 'UDC' not in service and 'nmcli' not in service and '--quiet-dhcp' in service


def test_saved_request_never_changes_live_network_and_reboots_exactly_once(tether):
    backend,network,management=tether
    now=[0];backend.clock=lambda:now[0];backend.lock_factory=nullcontext;backend.modem_lock_factory=nullcontext
    backend.readiness=lambda:{'ussd_state':1}
    operation=str(uuid.uuid4());backend.request(True,operation)
    assert not network.calls and management[0] and backend.status()['reboot_pending']
    backend.tick();assert not network.calls
    now[0]=6;backend.tick();backend.tick()
    assert [args for args,_ in network.calls]==[['/sbin/reboot']]
    now[0]=60;backend.tick();backend.tick()
    assert backend.status()['apply_state']=='REBOOT_FAILED'
    assert len(network.calls)==1


def test_reboot_waits_for_modem_idle_without_cancelling_session(tether):
    backend,network,_=tether
    backend.clock=lambda:10;backend.lock_factory=nullcontext;backend.modem_lock_factory=nullcontext
    backend.readiness=lambda:{'ussd_state':3}
    backend.request(True,str(uuid.uuid4()));backend.clock=lambda:20
    backend.tick();backend.tick()
    assert not network.calls and backend.status()['apply_state']=='WAITING_MODEM'


@pytest.mark.parametrize('enabled',[True,False])
def test_new_boot_applies_saved_mode_without_another_reboot_or_cell_activation(tether,enabled):
    backend,network,management=tether
    backend.lock_factory=nullcontext
    backend.request(enabled,str(uuid.uuid4()))
    backend.boot=lambda:'new-boot'
    backend.tick();backend.tick()
    assert backend.status()['apply_state']=='APPLIED'
    assert backend.status()['enabled']==enabled
    assert not any(args[0] in ('nmcli','/sbin/reboot') for args,_ in network.calls)
    assert management[0] is not enabled


def test_boot_accepts_its_already_running_dhcp_without_an_upstream(tether):
    backend,network,management=tether
    backend.lock_factory=nullcontext
    backend.request(True,str(uuid.uuid4()));backend.boot=lambda:'new-boot'
    management[0]=False;network.daemon=True;network.internet_ok=False
    backend.tick()
    assert backend.status()['enabled'] and backend.status()['apply_state']=='APPLIED'
    assert not any(args[:3]==['ip','-4','route'] for args,_ in network.calls)


def test_boot_failure_retries_with_a_deadline_and_never_reboots(tether):
    backend,network,_=tether
    now=[0];backend.clock=lambda:now[0];backend.lock_factory=nullcontext
    backend.request(True,str(uuid.uuid4()));backend.boot=lambda:'new-boot';network.fail_start=True
    backend.tick();assert backend.status()['apply_state']=='APPLYING'
    now[0]=121;backend.tick();assert backend.status()['apply_state']=='APPLY_FAILED'
    count=len(network.calls);backend.tick();assert len(network.calls)==count
    assert not any(args[0]=='/sbin/reboot' for args,_ in network.calls)


def test_dispatcher_hook_uses_only_saved_boolean_and_retains_management_fallback():
    text=(Path(__file__).parents[1]/'scripts/unudhcpd-openstick.conf').read_text()
    assert 'v.get("desired") is True' in text and 'disable_dhcpd=false' in text
    assert 'UDC' not in text and 'nmcli' not in text and 'reboot' not in text
    assert 'openstick-usb-dhcp start' in text

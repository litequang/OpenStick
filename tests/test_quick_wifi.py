"""Role rollback, secret preservation and read-only listing; no real networking."""
from contextlib import nullcontext
import hashlib
from types import SimpleNamespace
import uuid

import pytest

from uz801_manager.hotspot import AP_UUID, CELL_UUID
from uz801_manager.quick_intent import save_intent
from uz801_manager.quick_settings import validate_quick
from uz801_manager.quick_wifi import QuickWifi
from uz801_manager.setup_ap import SETUP_UUID, SetupAP


class Network:
    def __init__(self):
        self.links={'wlan0':AP_UUID,'modem':CELL_UUID};self.calls=[];self.auto='yes';self.fail=set()
        self.scan_fail=False
    def active(self, device):return self.links.get(device)
    def devices(self):return ['modem']
    def cellular_interface(self, device):return 'cell-data' if self.links.get(device)==CELL_UUID else None
    def nm(self,*args):
        if args[:2]==('-g','GENERAL.AUTOCONNECT'):return self.auto
        self.calls.append(('nm',args))
        if args[:4]==('device','set','wlan0','autoconnect'):self.auto=args[-1]
        return ''
    def up(self, identity):
        self.calls.append(('up',identity))
        if identity in self.fail:raise RuntimeError('private driver failure')
        self.links['wlan0']=identity
    def down(self, identity):
        self.calls.append(('down',identity))
        if self.links['wlan0']==identity:self.links['wlan0']=None
    def load(self, path):self.calls.append(('load',path.name))
    def ready(self):return bool(self.links['wlan0'])
    def local_services(self, enabled):self.calls.append(('ap_services',enabled))
    def scan(self, refresh):
        self.calls.append(('scan',refresh))
        if self.scan_fail:raise RuntimeError('private scan failure')
        return [{'ssid':'fixture-home','signal':80,'security':'WPA2'}]
    def saved_wifi(self):return [{'ssid':'fixture-home','uuid':'saved','priority':10,'hidden':False}]
    def try_station(self, identity):self.up(identity)


@pytest.fixture
def wifi(tmp_path):
    network=Network()
    setup=SetupAP(tmp_path/'state',profiles=tmp_path/'profiles',runtime=tmp_path/'run',network=network,
                  boot=lambda:'fixture-boot',lock_factory=nullcontext,modem_lock_factory=nullcontext)
    setup.profiles.mkdir()
    setup.write('setup-ap.json',{'ssid':'fixture-ap','enabled':False})
    save_intent(setup.directory,airplane=False,data_allowed=True)
    quick=SimpleNamespace(network=network,setup=setup,directory=setup.directory,
        _read=setup.read,_stop_automation=lambda:network.calls.append(('stop_automation',)),
        ap_forwarding=lambda allowed:network.calls.append(('ap_forwarding',allowed)),
        tethering=SimpleNamespace(update_uplinks=lambda:network.calls.append(('tether_update',))))
    backend=QuickWifi(quick,connect=lambda ssid,password:network.up('new'))
    backend.profiles=lambda:[{'uuid':'saved','ssid':'fixture-home','password':'must-not-export'}]
    return backend,network,setup


def test_options_do_not_scan_or_export_uuid_password_or_unknown_fields(wifi):
    backend,network,setup=wifi
    setup.save_state(networks=[{'ssid':'fixture-home','signal':80,'security':'WPA2','password':'must-not-export'}])
    result=backend.options()
    assert result['saved']==[{'ssid':'fixture-home','active':False}]
    assert result['networks']==[{'ssid':'fixture-home','signal':80,'security':'WPA2'}]
    assert not network.calls


@pytest.mark.parametrize('previous',[AP_UUID,SETUP_UUID,'saved',None])
def test_scan_restores_role_autoconnect_and_cell_without_changing_automation(wifi,previous):
    backend,network,setup=wifi;network.links['wlan0']=previous
    before=(setup.directory/'setup-ap.json').read_bytes()
    backend.call('wifi_scan',{})
    assert network.links=={'wlan0':previous,'modem':CELL_UUID} and network.auto=='yes'
    assert ('stop_automation',) not in network.calls
    assert before==(setup.directory/'setup-ap.json').read_bytes()
    assert setup.state()['networks'][0]['ssid']=='fixture-home'
    if previous not in (AP_UUID,SETUP_UUID):assert not any(c[0] in ('down','up') for c in network.calls)


def test_auto_switches_ap_to_saved_station_and_preserves_active_cell(wifi):
    backend,network,setup=wifi
    backend.call('wifi_auto',{})
    assert network.links=={'wlan0':'saved','modem':CELL_UUID} and network.auto=='yes'
    assert setup.read('setup-ap.json')['previous_wifi']=='saved'
    assert ('ap_forwarding',True) in network.calls and ('tether_update',) in network.calls
    assert ('down',CELL_UUID) not in network.calls


def test_no_saved_wifi_restores_ap_and_retains_fresh_scan(wifi):
    backend,network,setup=wifi;network.fail={'saved'}
    with pytest.raises(RuntimeError,match='WIFI_SAVED_NOT_FOUND'):backend.call('wifi_auto',{})
    assert network.links=={'wlan0':AP_UUID,'modem':CELL_UUID}
    assert setup.state()['networks'] and network.auto=='yes'


def test_ap_scan_waits_for_driver_cache_before_selecting_saved_station(wifi):
    backend,network,setup=wifi;original=network.scan;attempts=[];waits=[]
    def scan(refresh):
        attempts.append(refresh)
        return [] if len(attempts)==1 else original(refresh)
    network.scan=scan;backend.sleep=waits.append
    backend.call('wifi_auto',{})
    assert waits==[2] and network.links['wlan0']=='saved'
    assert network.links['modem']==CELL_UUID


def test_empty_ap_scan_is_bounded_and_restores_the_ap(wifi):
    backend,network,setup=wifi;attempts=[];waits=[]
    network.scan=lambda refresh:attempts.append(refresh) or []
    backend.sleep=waits.append
    backend.call('wifi_scan',{})
    assert len(attempts)==3 and waits==[2,2]
    assert network.links['wlan0']==AP_UUID and network.links['modem']==CELL_UUID


def test_scan_failure_restores_setup_dhcp_without_cell_operation(wifi):
    backend,network,_=wifi;network.links['wlan0']=SETUP_UUID;network.scan_fail=True
    with pytest.raises(RuntimeError,match='WIFI_SCAN_FAILED'):backend.call('wifi_scan',{})
    assert network.links['wlan0']==SETUP_UUID and network.links['modem']==CELL_UUID
    assert ('ap_services',False) in network.calls and ('ap_services',True) in network.calls


def test_missing_saved_profile_is_rejected_before_transport_changes(wifi):
    backend,network,_=wifi
    with pytest.raises(RuntimeError,match='WIFI_PROFILE_NOT_FOUND'):backend.call('wifi_saved',{'ssid':'absent'})
    assert not network.calls


def test_failed_password_replacement_restores_previous_keyfile_and_ap(wifi):
    backend,network,setup=wifi
    name='openstick-'+hashlib.sha256(b'fixture-home').hexdigest()[:16]+'.nmconnection'
    path=setup.profiles/name
    identity=str(uuid.uuid4());previous='[connection]\nuuid='+identity+'\n[wifi-security]\npsk=original-fixture\n'
    path.write_text(previous)
    def failed(ssid,password):
        path.write_text(previous.replace('original-fixture','wrong-fixture'))
        raise RuntimeError('private-password-in-error')
    backend.connect=failed
    with pytest.raises(RuntimeError,match='^WIFI_CONNECT_FAILED$'):
        backend.call('wifi_connect',{'ssid':'fixture-home','password':'wrong-fixture'})
    assert path.read_text()==previous and ('load',name) in network.calls
    assert network.links=={'wlan0':AP_UUID,'modem':CELL_UUID}


def test_local_writer_uses_derived_key_and_never_reacquires_transport_lock(wifi):
    import configparser
    backend,network,setup=wifi;backend.connect=backend._connect
    backend.call('wifi_connect',{'ssid':'IEEE','password':'password'})
    path=next(setup.profiles.glob('*.nmconnection'))
    profile=configparser.ConfigParser();profile.read(path)
    assert profile['wifi-security']['psk']=='f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e'
    assert 'password' not in path.read_text()
    assert network.links['wlan0']==profile['connection']['uuid'] and network.links['modem']==CELL_UUID
    assert ('load',path.name) in network.calls


def test_restore_failure_is_explicit_and_no_cellular_recovery_is_attempted(wifi):
    backend,network,_=wifi;network.fail={'saved',AP_UUID}
    with pytest.raises(RuntimeError,match='WIFI_RESTORE_FAILED'):backend.call('wifi_auto',{})
    assert network.links['modem']==CELL_UUID and ('down',CELL_UUID) not in network.calls


def test_disconnect_station_never_starts_ap_or_another_saved_network(wifi):
    backend,network,setup=wifi;network.links['wlan0']='saved'
    backend.call('wifi_off',{})
    assert network.links=={'wlan0':None,'modem':CELL_UUID} and network.auto=='no'
    assert not setup.read('setup-ap.json')['enabled']
    assert not any(c[0]=='up' for c in network.calls)


@pytest.mark.parametrize('extra',[{'ssid':'x','password':'short'},{'ssid':'x\n','password':'password'},
    {'ssid':'x','password':'password','command':'shell'},{'ssid':'🛜'*9,'password':'password'}])
def test_wifi_schema_rejects_invalid_credentials_before_operation(extra):
    with pytest.raises(ValueError):validate_quick({'action':'wifi_connect','confirm':True,'operation':str(uuid.uuid4()),**extra})

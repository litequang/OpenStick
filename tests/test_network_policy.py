from contextlib import nullcontext
import json
import subprocess

import pytest

from uz801_manager.network_policy import NetworkPolicy, PolicyNetwork, validate_policy
from uz801_manager.hotspot import AP_UUID, CELL_UUID, Hotspot
from uz801_manager.hosting import create_hosting_app

WIFI='07ca019c-485b-4f06-b99d-171c167e18bb'
OTHER='dd61b376-cce8-4a96-a243-4a1c6db9a836'


class Network:
    def __init__(self):
        self.current={'wlan0':WIFI,'qmi0':None};self.calls=[]
        self.health={'wlan0':True,'wwan4':True};self.saved=[{'uuid':WIFI,'ssid':'fixture'},{'uuid':OTHER,'ssid':'other'}]
    def active(self,interface):return self.current.get(interface)
    def devices(self):return ['qmi0']
    def cellular_interface(self,control):return 'wwan4' if self.current[control] else None
    def internet(self,interface,control):return self.health.get(interface,False)
    def profiles(self):return self.saved
    def available(self):return {'other':90}
    def checkpoint(self,interfaces):
        assert 'usb0' not in interfaces;self.original=self.current.copy();self.calls.append(('checkpoint',));return '/checkpoint'
    def checkpoint_action(self,path,rollback):
        self.calls.append(('rollback',rollback))
        if rollback:self.current=self.original.copy()
    def route(self,interface,preferred):self.calls.append(('route',interface,preferred))
    def up(self,identity):
        self.calls.append(('up',identity));self.current['qmi0' if identity==CELL_UUID else 'wlan0']=identity
    def down(self,identity):
        self.calls.append(('down',identity));self.current['qmi0' if identity==CELL_UUID else 'wlan0']=None
    def autoconnect(self,identity,enabled):self.calls.append(('autoconnect',identity,enabled))
    def nm(self,*args):
        self.calls.append(('nm',*args))
        if args[:2]==('device','disconnect'):self.current[args[2]]=None


@pytest.fixture
def policy(tmp_path):
    network=Network();clock=[1000]
    backend=NetworkPolicy(tmp_path,network=network,lock_factory=nullcontext,modem_lock_factory=nullcontext,
        readiness=lambda:{'registered':True,'sim_present':True,'ussd_state':1},clock=lambda:clock[0],boot=lambda:'fixture')
    backend.write('hotspot.json',{'ssid':'configured','enabled':False})
    return backend,network,clock


def configure(backend,mode='wifi_preferred',**changes):
    return backend.call('configure',mode=mode,enabled=True,auto_wifi=False,cellular_consent=True,confirm=True,**changes)


def test_default_status_and_disabled_daemon_do_not_touch_transport(policy):
    backend,network,_=policy
    assert not backend.call('status')['config']['enabled'];backend.tick()
    assert network.calls==[]


@pytest.mark.parametrize('value',[
    {'action':'configure','mode':'sim_only','enabled':True,'auto_wifi':False,'cellular_consent':False,'confirm':True},
    {'action':'configure','mode':[],'enabled':True,'auto_wifi':False,'cellular_consent':True,'confirm':True},
    {'action':'configure','mode':'wifi_only','enabled':1,'auto_wifi':False,'cellular_consent':False,'confirm':True},
    {'action':'wifi_activate','uuid':'../../secret','confirm':True},
    {'action':['status']},{'action':'status','command':'reboot'},
])
def test_invalid_policy_or_missing_consent_is_rejected(value):
    with pytest.raises((ValueError,TypeError)):validate_policy(value)


def test_wifi_preferred_does_not_activate_sim_while_wifi_is_healthy(policy):
    backend,network,_=policy
    result=configure(backend)
    assert result['runtime']['source']=='wifi'
    assert not any(c==('up',CELL_UUID) for c in network.calls)


def test_three_failures_and_cooldown_before_cellular_fallback(policy):
    backend,network,clock=policy;configure(backend);network.calls.clear()
    network.health['wlan0']=False;clock[0]+=121
    backend.tick();backend.tick()
    assert ('up',CELL_UUID) not in network.calls
    backend.tick()
    assert backend.state()['source']=='sim' and ('up',CELL_UUID) in network.calls
    network.health['wlan0']=True
    backend.tick();backend.tick();backend.tick()
    assert backend.state()['source']=='sim'  # recovered, still in cooldown
    clock[0]+=121;backend.tick()
    assert backend.state()['source']=='wifi'


def test_wifi_only_disconnects_owned_sim_even_if_previous_source_was_wifi(policy):
    backend,network,_=policy;configure(backend);network.current['qmi0']=CELL_UUID
    configure(backend,'wifi_only')
    assert ('down',CELL_UUID) in network.calls


def test_data_off_stops_owned_data_without_wifi_or_disabling_sms_radio(policy):
    backend,network,_=policy
    network.current={'wlan0':None,'qmi0':CELL_UUID};network.health['wlan0']=False
    result=backend.call('data_off',confirm=True)
    assert result['data_off'] and not result['config']['enabled'] and not result['config']['cellular_consent']
    assert network.current=={'wlan0':None,'qmi0':None}
    assert network.calls==[('autoconnect',CELL_UUID,False),('down',CELL_UUID)]
    backend.tick();assert network.current['qmi0'] is None


def test_data_off_does_not_claim_foreign_connection_was_stopped(policy):
    backend,network,_=policy;network.current['qmi0']=OTHER
    with pytest.raises(RuntimeError,match='CELLULAR_ALREADY_ACTIVE'):backend.call('data_off',confirm=True)
    assert network.calls==[] and network.current['qmi0']==OTHER


def test_sim_only_uses_runtime_interface_and_disconnects_station(policy):
    backend,network,_=policy;configure(backend,'sim_only')
    assert network.current['wlan0'] is None and backend.state()['source']=='sim'
    assert ('route','qmi0',True) in network.calls


def test_failed_switch_rolls_back_links_and_restores_prior_configuration(policy):
    backend,network,_=policy;configure(backend);before=backend.config()
    network.health['wwan4']=False
    with pytest.raises(RuntimeError,match='SWITCH_FAILED'):configure(backend,'sim_only')
    assert backend.config()==before and network.current=={'wlan0':WIFI,'qmi0':None}
    assert ('rollback',True) in network.calls


def test_hotspot_role_blocks_policy_before_any_activation(policy):
    backend,network,_=policy;network.current['wlan0']=AP_UUID
    with pytest.raises(RuntimeError,match='HOTSPOT_ACTIVE'):configure(backend)
    assert network.calls==[]


def test_policy_blocks_hotspot_start_before_transport(policy):
    backend,network,_=policy;configure(backend)
    hotspot=Hotspot(backend.directory,network=network,lock_factory=nullcontext,modem_lock_factory=nullcontext)
    with pytest.raises(RuntimeError,match='POLICY_ACTIVE'):
        hotspot.call('start',confirm=True,cellular_consent=True,switch_wifi=True)


def test_saved_wifi_switch_rolls_back_when_no_internet_and_cannot_forget_active(policy):
    backend,network,_=policy;network.health['wlan0']=False
    with pytest.raises(RuntimeError,match='WIFI_SWITCH_FAILED'):
        backend.call('wifi_activate',uuid=OTHER,confirm=True)
    assert network.current['wlan0']==WIFI
    with pytest.raises(RuntimeError,match='PROFILE_ACTIVE'):backend.call('wifi_forget',uuid=WIFI,confirm=True)
    assert not any('delete' in call for call in network.calls)


def test_automatic_wifi_uses_only_a_saved_available_profile(policy):
    backend,network,clock=policy
    backend.write('network-policy.json',{'mode':'wifi_only','enabled':True,'auto_wifi':True,'cellular_consent':False})
    network.current['wlan0']=None;backend.tick()
    assert ('up',OTHER) in network.calls and ('up',CELL_UUID) not in network.calls


def test_profile_queries_never_request_secrets_and_handle_escaped_names():
    def run(args,**kwargs):
        assert '--show-secrets' not in args and 'psk' not in ' '.join(args)
        text=WIFI+':802-11-wireless\n'+AP_UUID+':802-11-wireless' if args[-1]=='show' else 'fixture:colon\ninfrastructure\nwlan0\n'
        return subprocess.CompletedProcess(args,0,text,'')
    assert PolicyNetwork(run).profiles()==[{'uuid':WIFI,'ssid':'fixture:colon'}]


def test_private_policy_routes_require_token_and_filter_errors(policy):
    backend,network,_=policy
    app=create_hosting_app(backend=object(),network_backend=backend,usb_portal=True,token='fixture')
    client=app.test_client();base='http://172.16.42.1';headers={'X-OpenStick-Token':'fixture'}
    assert client.get('/internet',base_url=base).status_code==200
    assert client.get('/api/internet/state',base_url=base).status_code==403
    assert client.post('/api/internet',base_url=base,headers={**headers,'Origin':'https://evil.invalid'},json={'action':'status'}).status_code==403
    assert client.post('/api/internet',base_url=base,headers=headers,json={'action':'wifi_activate','uuid':'bad','confirm':True}).status_code==400
    network.current['wlan0']=AP_UUID
    assert client.post('/api/internet',base_url=base,headers=headers,json={'action':'profiles'}).status_code==202
    app.extensions['network_policy']['thread'].join(2)
    assert client.get('/api/internet/state',base_url=base,headers=headers).json['error']=='HOTSPOT_ACTIVE'


def test_failed_saved_wifi_does_not_block_sim_fallback(policy):
    backend,network,_=policy
    network.health['wlan0']=False
    backend.call('configure',mode='wifi_preferred',enabled=True,auto_wifi=True,cellular_consent=True,confirm=True)
    assert backend.state()['source']=='sim' and network.current['qmi0']==CELL_UUID
    assert backend.state()['wifi_retry_after'][OTHER]>1000


def test_recovered_saved_wifi_does_not_unnecessarily_start_sim(policy):
    backend,network,_=policy;network.current['wlan0']=None
    backend.call('configure',mode='wifi_preferred',enabled=True,auto_wifi=True,cellular_consent=True,confirm=True)
    assert backend.state()['source']=='wifi' and ('up',CELL_UUID) not in network.calls


def test_sim_only_continues_enforcing_station_disconnection(policy):
    backend,network,clock=policy;configure(backend,'sim_only')
    network.current['wlan0']=WIFI;clock[0]+=121
    backend.tick()
    assert network.current['wlan0'] is None and not backend.state()['health']['wifi']


def test_runtime_state_uses_separate_volatile_directory(tmp_path):
    backend=NetworkPolicy(tmp_path/'config',runtime=tmp_path/'run',boot=lambda:'fixture')
    backend.write('network-policy-state.json',{'boot':'fixture','source':'wifi'})
    assert not (tmp_path/'config').exists()
    assert backend.state()['source']=='wifi'

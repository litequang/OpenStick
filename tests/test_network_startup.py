"""Power-loss and service-race regression tests; no hardware operations."""
import json

import pytest

from test_quick_settings import quick,invoke,provision
from uz801_manager.hotspot import AP_UUID,CELL_UUID
from uz801_manager.network_startup import NAME,STATE,NetworkStartup,load,save,owns_wifi
from uz801_manager.quick_intent import save_intent


def worker(backend,**kwargs):
    return NetworkStartup(backend,boot=lambda:'next-boot',readiness=lambda:{},**kwargs)


def select_sim_ap(quick):
    backend,network,_,_=quick
    provision(backend)
    invoke(backend,'data_on',cellular_consent=True)
    invoke(backend,'local_ap_on')
    assert load(backend.directory)['wifi_role']=='ap'
    assert load(backend.directory)['data_on'] is True
    network.active_profiles={'wlan0':'saved-station','cell':None}
    network.calls.clear()
    return backend,network


def test_saved_sim_and_ap_restore_after_new_boot_not_old_station(quick):
    backend,network=select_sim_ap(quick)
    boot=worker(backend);boot.tick();boot.tick()
    assert network.active('wlan0')==AP_UUID and network.active('cell')==CELL_UUID
    assert network.calls.count(('up',CELL_UUID))==1
    assert network.calls.count(('up',AP_UUID))==1
    assert ('up','saved-station') not in network.calls
    state=backend._read(STATE)
    assert state['done'] and state['data_connected'] and state['phase']=='RESTORED'
    assert owns_wifi(backend.directory)
    from uz801_manager.cellular_recovery import read
    assert read(backend.directory)['seen'] and read(backend.directory)['boot']=='next-boot'


def test_current_boot_already_applied_selection_is_not_replayed(quick):
    backend,network=select_sim_ap(quick)
    NetworkStartup(backend,boot=lambda:'fixture-boot',readiness=lambda:{}).tick()
    assert not network.calls and not backend._read(STATE)


def test_sim_not_ready_keeps_ap_then_connects_once_when_registered(quick):
    backend,network=select_sim_ap(quick)
    radio=quick[2];radio.ready=False
    boot=worker(backend);boot.tick();boot.tick()
    assert network.active('wlan0')==AP_UUID and network.active('cell') is None
    assert backend._read(STATE)['phase']=='WAITING_SIM'
    assert ('up',CELL_UUID) not in network.calls
    radio.ready=True;boot.tick()
    assert network.calls.count(('up',CELL_UUID))==1 and backend._read(STATE)['done']


@pytest.mark.parametrize('airplane',[False,True])
def test_newer_data_off_or_airplane_veto_wins_over_saved_data_on(quick,airplane):
    backend,network=select_sim_ap(quick)
    save_intent(backend.directory,airplane=airplane,data_allowed=False)
    worker(backend).tick()
    assert network.active('wlan0')==AP_UUID and ('up',CELL_UUID) not in network.calls
    assert not backend._read(STATE)['data_connected']
    assert ('forward_ap',False) in network.calls


def test_missing_corrupt_or_unconsented_intent_never_grants_data(quick):
    backend,network=select_sim_ap(quick)
    (backend.directory/'quick-settings.json').unlink()
    worker(backend).tick()
    assert ('up',CELL_UUID) not in network.calls
    for value in ['', '{broken','[]']:
        (backend.directory/NAME).write_text(value)
        network.calls.clear();worker(backend).tick()
        assert load(backend.directory)=={} and owns_wifi(backend.directory)
        assert not network.calls
    (backend.directory/NAME).unlink()
    assert load(backend.directory) is None and not owns_wifi(backend.directory)


def test_pending_explicit_handoff_wins_and_automatic_policy_is_not_overridden(quick):
    backend,network=select_sim_ap(quick)
    for name in ['setup-pending.json','hotspot-pending.json']:
        backend.hotspot.write(name,{'pending':True})
        worker(backend).tick();assert not network.calls
        (backend.directory/name).unlink()
    backend.hotspot.write('network-policy.json',{'enabled':True})
    worker(backend).tick();assert not network.calls and not owns_wifi(backend.directory)


def test_activation_timeout_does_not_retry_bearer_or_reconnect_station(quick):
    backend,network=select_sim_ap(quick)
    up=network.up
    def fail_cell(identity):
        if identity==CELL_UUID:
            network.calls.append(('up',identity));raise RuntimeError('private modem error')
        up(identity)
    network.up=fail_cell
    boot=worker(backend);boot.tick();boot.tick()
    assert network.active('wlan0')==AP_UUID
    assert network.calls.count(('up',CELL_UUID))==1
    assert backend._read(STATE)['error']=='DATA_CONNECT_FAILED'
    assert 'private' not in json.dumps(backend._read(STATE))


def test_wait_for_saved_radio_mode_and_do_not_touch_ussd(quick):
    backend,network=select_sim_ap(quick)
    mode={'saved_mode':[4,0],'current_mode':[6,4]}
    boot=NetworkStartup(backend,boot=lambda:'next-boot',readiness=lambda:mode)
    boot.tick();assert ('up',CELL_UUID) not in network.calls
    assert backend._read(STATE)['phase']=='WAITING_RADIO_MODE'
    mode['current_mode']=[4,0];quick[2].ussd=3
    boot.tick();assert ('up',CELL_UUID) not in network.calls
    quick[2].ussd=1;boot.tick()
    assert network.calls.count(('up',CELL_UUID))==1 and not quick[2].calls


def test_wifi_off_and_local_ap_without_sim_are_saved_separately(quick):
    backend,network,_,_=quick
    save(backend.directory,wifi_role='off',boot='previous-boot')
    worker(backend).tick()
    assert network.active('wlan0') is None and ('up',CELL_UUID) not in network.calls
    assert owns_wifi(backend.directory)
    provision(backend);backend.hotspot.write('hotspot.json',{'ssid':'fixture','enabled':False});network.calls.clear()
    save(backend.directory,wifi_role='ap',data_on=False,boot='previous-boot')
    network.devices=lambda:[]
    worker(backend).tick()
    assert network.active('wlan0')==AP_UUID and ('up',CELL_UUID) not in network.calls


def test_station_restores_saved_profile_without_starting_sim(quick):
    backend,network,_,setup=quick
    save(backend.directory,wifi_role='station',station='saved-fixture',data_on=False,boot='previous-boot')
    setup.network.try_station=lambda identity:network.up(identity)
    setup.network.ready=lambda:True
    worker(backend).tick()
    assert network.active('wlan0')=='saved-fixture' and ('up',CELL_UUID) not in network.calls
    assert not owns_wifi(backend.directory)


def test_wifi_attempts_are_bounded_and_delayed_while_ap_service_starts(quick):
    backend,network=select_sim_ap(quick);quick[3].lan_ready=lambda:False
    now=[0];boot=worker(backend,clock=lambda:now[0])
    boot.tick();boot.tick();assert backend._read(STATE)['wifi_attempts']==1
    now[0]=15;boot.tick();now[0]=30;boot.tick();now[0]=45;boot.tick()
    assert backend._read(STATE)['done'] and backend._read(STATE)['wifi_attempts']==3
    assert ('up',CELL_UUID) not in network.calls


def test_failed_user_action_does_not_replace_saved_selection_and_reads_do_not_save(quick):
    backend,network=select_sim_ap(quick)
    before=(backend.directory/NAME).read_bytes()
    backend.status();assert (backend.directory/NAME).read_bytes()==before
    quick[2].ussd=3
    with pytest.raises(RuntimeError,match='MODEM_BUSY'):invoke(backend,'data_off')
    assert (backend.directory/NAME).read_bytes()==before


def test_save_failure_is_reported_and_new_data_off_veto_still_blocks_old_saved_on(quick,monkeypatch):
    from uz801_manager import network_startup
    backend,network=select_sim_ap(quick)
    def fail_save(*args,**kwargs):raise OSError('private disk error')
    monkeypatch.setattr(network_startup,'save',fail_save)
    with pytest.raises(RuntimeError,match='NETWORK_SAVE_FAILED'):invoke(backend,'data_off')
    assert load(backend.directory)['data_on'] is True
    network.calls.clear();worker(backend).tick()
    assert ('up',CELL_UUID) not in network.calls

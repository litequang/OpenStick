"""Simulated NM/MM disconnects; never access physical hardware."""
import json
import pytest

from test_quick_settings import quick, provision, invoke
from uz801_manager.hotspot import CELL_UUID, AP_UUID
from uz801_manager.cellular_recovery import CellularRecovery, NAME, public, read, MAX_ATTEMPTS
from uz801_manager.network_startup import load, save
from uz801_manager.quick_intent import save_intent


def configured(quick, *, connect=True):
    q,n,radio,_=quick
    provision(q)
    if connect:invoke(q,'data_on',cellular_consent=True)
    else:
        save_intent(q.directory,airplane=False,data_allowed=True)
        q.hotspot.write('hotspot.json',{'ssid':'fixture','enabled':False})
        save(q.directory,wifi_role='station',station='saved-station',data_on=True,boot=q.boot())
    # Use a real NM state response for the positive disconnect barrier.
    original=n.nm
    n.nm=lambda *a,**kw:'30 (disconnected)' if a[:2]==('-g','GENERAL.STATE') else original(*a,**kw)
    now=[0]
    w=CellularRecovery(q,clock=lambda:now[0],readiness=lambda:{},power_pending=lambda:False)
    n.calls.clear()
    return q,n,radio,now,w


def tick(w,now):
    w.tick();now[0]+=20


def drop(n):n.active_profiles['cell']=None


def test_connected_saved_ap_reconciles_lost_sharing_without_bearer_or_ap_restart(quick):
    q,n,radio,now,w=configured(quick)
    n.active_profiles['wlan0']=AP_UUID
    save(q.directory,wifi_role='ap',data_on=True,boot=q.boot())
    tick(w,now);tick(w,now)
    assert n.calls.count(('forward_ap',True))==2
    assert not any(c[0] in ('up','down','auto') for c in n.calls) and not radio.calls


def test_data_off_veto_never_repairs_sharing_or_activates_bearer(quick):
    q,n,radio,now,w=configured(quick)
    n.active_profiles['wlan0']=AP_UUID
    save(q.directory,wifi_role='ap',data_on=True,boot=q.boot())
    save_intent(q.directory,airplane=False,data_allowed=False)
    tick(w,now)
    assert not n.calls and not radio.calls


def test_observed_disconnect_reconnects_once_without_touching_ap_radio_or_intent(quick):
    q,n,radio,now,w=configured(quick)
    n.active_profiles['wlan0']=AP_UUID
    save(q.directory,wifi_role='ap',data_on=True,boot=q.boot())
    saved=(q.directory/'network-startup.json').read_bytes()
    intent=(q.directory/'quick-settings.json').read_bytes()
    tick(w,now);drop(n);tick(w,now)
    assert ('up',CELL_UUID) not in n.calls
    tick(w,now);tick(w,now)
    assert n.calls.count(('up',CELL_UUID))==1
    assert n.active('wlan0')==AP_UUID and not radio.calls
    assert all(c[:2]!=('auto',CELL_UUID) or c[2] is False for c in n.calls)
    assert saved==(q.directory/'network-startup.json').read_bytes()
    assert intent==(q.directory/'quick-settings.json').read_bytes()
    assert public(q.directory)['attempts']==1


def test_never_opens_first_connection_or_replays_failed_boot(quick):
    q,n,radio,now,w=configured(quick,connect=False);drop(n)
    for _ in range(8):tick(w,now)
    assert ('up',CELL_UUID) not in n.calls
    assert read(q.directory)['seen'] is False


def test_successful_data_on_arms_before_first_poll_and_ap_save_keeps_proof(quick):
    q,n,radio,now,w=configured(quick)
    first=read(q.directory)
    assert first['seen'] and first['phase']=='CONNECTED'  # No worker tick yet.
    activate=q._start_shared_ap
    def ap_then_drop(control):
        activate(control);drop(n)  # Connection drops during the AP transaction.
    q._start_shared_ap=ap_then_drop
    invoke(q,'local_ap_on')
    value=read(q.directory)
    assert value['revision']!=first['revision'] and value['seen']
    assert value['revision']==load(q.directory)['revision']
    n.calls.clear();tick(w,now);tick(w,now)
    assert n.calls.count(('up',CELL_UUID))==1 and n.active('wlan0')==AP_UUID


@pytest.mark.parametrize('phase,error,attempts',[('UNKNOWN','ACTIVATION_UNCERTAIN',1),('LIMIT_REACHED','RECOVERY_LIMIT',3)])
def test_ap_save_cannot_reset_stopped_recovery_budget(quick,phase,error,attempts):
    q,n,radio,now,w=configured(quick)
    value=read(q.directory);value.update(phase=phase,error=error,attempts=attempts)
    q.hotspot.write(NAME,value);drop(n)
    invoke(q,'local_ap_on')
    assert read(q.directory)['phase']==phase and read(q.directory)['attempts']==attempts
    n.calls.clear()
    for _ in range(4):tick(w,now)
    assert ('up',CELL_UUID) not in n.calls
    from uz801_manager.cellular_recovery import record_selection
    before=(q.directory/NAME).read_bytes()
    record_selection(q.directory,load(q.directory),'new-boot',connected=True)
    assert (q.directory/NAME).read_bytes()==before


@pytest.mark.parametrize('gate',['off','airplane','policy','legacy','setup_pending','hotspot_pending','power','usb_reboot','foreign','wifi_changed','mode','ussd','unregistered'])
def test_saved_consent_and_all_transition_vetoes_win(quick,gate):
    q,n,radio,now,w=configured(quick);tick(w,now);drop(n)
    if gate=='off':save_intent(q.directory,airplane=False,data_allowed=False)
    if gate=='airplane':save_intent(q.directory,airplane=True,data_allowed=False)
    if gate=='policy':q.hotspot.write('network-policy.json',{'enabled':True})
    if gate=='legacy':q.hotspot.write('hotspot.json',{'enabled':True})
    if gate=='setup_pending':q.hotspot.write('setup-pending.json',{'pending':True})
    if gate=='hotspot_pending':q.hotspot.write('hotspot-pending.json',{'pending':True})
    if gate=='power':w.power_pending=lambda:True
    if gate=='usb_reboot':q.tethering.status=lambda:{'reboot_pending':True}
    if gate=='foreign':n.active_profiles['cell']='foreign'
    if gate=='wifi_changed':n.active_profiles['wlan0']='different-station'
    if gate=='mode':w.readiness=lambda:{'saved_mode':[8,0],'current_mode':[4,0]}
    if gate=='ussd':radio.ussd=3
    if gate=='unregistered':radio.ready=False
    n.calls.clear()
    for _ in range(4):tick(w,now)
    assert ('up',CELL_UUID) not in n.calls and not radio.calls


@pytest.mark.parametrize('nm_state,core_state',[('40 (connecting)',8),('30 (disconnected)',11)])
def test_ambiguous_managers_do_not_allow_activation(quick,nm_state,core_state):
    q,n,radio,now,w=configured(quick);tick(w,now);drop(n)
    original=n.nm;n.nm=lambda *a,**kw:nm_state if a[:2]==('-g','GENERAL.STATE') else original(*a,**kw)
    original_radio=radio.status;radio.status=lambda:{**original_radio(),'state':core_state}
    for _ in range(5):tick(w,now)
    assert ('up',CELL_UUID) not in n.calls


def test_timeout_is_durable_and_never_replayed_even_after_worker_restart(quick):
    q,n,radio,now,w=configured(quick);tick(w,now);drop(n);n.fail_cell=True
    tick(w,now);tick(w,now)
    assert read(q.directory)['phase']=='UNKNOWN'
    for _ in range(5):tick(w,now)
    replacement=CellularRecovery(q,clock=lambda:now[0],readiness=lambda:{},power_pending=lambda:False)
    tick(replacement,now)
    assert n.calls.count(('up',CELL_UUID))==1
    assert 'raw-private' not in json.dumps(read(q.directory))
    receipts=list((q.directory/'quick-operations').glob('*.json'))
    assert any(json.loads(p.read_text()).get('failure')=='ACTIVATION_UNCERTAIN' for p in receipts)


def test_attempt_limit_survives_restart_and_new_owner_revision_can_rearm(quick):
    q,n,radio,now,w=configured(quick);tick(w,now)
    for _ in range(MAX_ATTEMPTS):
        drop(n);tick(w,now);tick(w,now);tick(w,now)
    drop(n)
    for _ in range(5):tick(w,now)
    assert public(q.directory)['phase']=='LIMIT_REACHED'
    assert n.calls.count(('up',CELL_UUID))==MAX_ATTEMPTS
    invoke(q,'data_on',cellular_consent=True)
    tick(w,now);assert read(q.directory)['attempts']==0


@pytest.mark.parametrize('content',['{broken','[]'])
def test_corrupt_state_blocks_and_status_is_read_only(quick,content):
    q,n,radio,now,w=configured(quick)
    (q.directory/NAME).write_text(content)
    before=list(q.directory.rglob('*'));status=public(q.directory)
    assert status['error']=='STATE_INVALID' and before==list(q.directory.rglob('*'))
    drop(n)
    for _ in range(4):tick(w,now)
    assert ('up',CELL_UUID) not in n.calls


def test_interrupted_attempt_and_boot_change_cannot_retransmit(quick):
    q,n,radio,now,w=configured(quick);tick(w,now)
    value=read(q.directory);value['phase']='ATTEMPTING'
    q.hotspot.write(NAME,value);drop(n);q.boot=lambda:'another-boot'
    tick(w,now);tick(w,now)
    assert read(q.directory)['error']=='RECOVERY_INTERRUPTED'
    assert ('up',CELL_UUID) not in n.calls


def test_poll_is_bounded_and_public_status_exposes_no_runtime_identifiers(quick):
    q,n,radio,now,w=configured(quick);tick(w,now)
    counter=[0];devices=n.devices
    def count():counter[0]+=1;return devices()
    n.devices=count
    for _ in range(10):w.tick()
    assert counter[0]==1
    status=public(q.directory)
    assert not any(k in status for k in ['boot','revision','ssid','mac','apn'])


def test_explicit_data_off_veto_at_submission_barrier(quick):
    q,n,radio,now,w=configured(quick);tick(w,now);drop(n);tick(w,now)
    preflight=q._preflight
    def veto():
        value=preflight();save_intent(q.directory,airplane=False,data_allowed=False);return value
    q._preflight=veto;tick(w,now)
    assert ('up',CELL_UUID) not in n.calls


def test_stable_connection_resets_burst_budget_but_worker_restart_does_not(quick):
    q,n,radio,now,w=configured(quick);tick(w,now);drop(n);tick(w,now);tick(w,now)
    assert read(q.directory)['attempts']==1
    w=CellularRecovery(q,clock=lambda:now[0],readiness=lambda:{},power_pending=lambda:False)
    tick(w,now);assert read(q.directory)['attempts']==1
    for _ in range(30):tick(w,now)
    assert read(q.directory)['attempts']==0


def test_stale_core_connected_but_searching_is_not_data_connected(quick):
    q,n,radio,now,w=configured(quick)
    original=radio.status
    radio.status=lambda:{**original(),'state':11,'registered':False,'registration_state':2}
    assert not q.status()['mobile_data_connected']


def test_recovery_ui_keeps_off_available_during_network_loss():
    import shutil,subprocess
    from pathlib import Path
    node=shutil.which('node')
    if not node:pytest.skip('Node required for UI regression')
    result=subprocess.run([node,str(Path(__file__).with_name('cellular_recovery_ui_fixture.cjs'))],capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stdout+result.stderr

"""Synthetic sysfs/NM regressions; no physical device or radio operations."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from uz801_manager.cellular_transport import TransportPower
from uz801_manager.hotspot import Network, CELL_UUID, AP_UUID
from test_quick_settings import quick, provision, invoke


@pytest.fixture
def transport(tmp_path, monkeypatch):
    root=tmp_path/'fixture';net=root/'sys/class/net/wwan0';device=root/'sys/devices/platform/bam-controller'
    (net/'device/driver').mkdir(parents=True);(device/'power').mkdir(parents=True)
    (device/'power/control').write_text('auto\n');(device/'power/runtime_status').write_text('active\n')
    resolve=Path.resolve
    def mapped(path,*args,**kwargs):
        if path==net/'device':return device
        if path==net/'device/driver':return root/'sys/bus/platform/drivers/bam-dmux'
        return resolve(path,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',mapped)
    now=[0.0]
    def sleep(seconds):now[0]+=seconds
    return TransportPower(root,clock=lambda:now[0],sleep=sleep),device


def test_status_is_read_only_and_never_exports_device_paths(transport):
    guard,device=transport
    before={p:p.read_bytes() for p in (device/'power').iterdir()}
    assert guard.status()=={'state':'active','held_awake':False,'error':None}
    assert not guard.marker.exists() and all(p.read_bytes()==v for p,v in before.items())
    assert 'device' not in guard.status() and str(device) not in json.dumps(guard.status())


def test_prepare_pins_only_bam_transport_and_keeps_own_hold_across_data_cycles(transport):
    guard,device=transport
    guard.prepare();marker=guard.marker.read_bytes()
    assert (device/'power/control').read_text().strip()=='on'
    assert json.loads(marker)=={'version':1,'device':str(device),'previous':'auto'}
    guard.prepare();assert guard.marker.read_bytes()==marker
    guard.release();assert not guard.marker.exists()
    assert (device/'power/control').read_text().strip()=='auto'


def test_preexisting_external_hold_is_never_claimed_or_released(transport):
    guard,device=transport;(device/'power/control').write_text('on\n')
    guard.prepare();guard.release()
    assert not guard.marker.exists() and (device/'power/control').read_text().strip()=='on'


def test_sticky_runtime_error_blocks_activation_without_any_write(transport):
    guard,device=transport;(device/'power/runtime_status').write_text('error\n')
    assert guard.status()=={'state':'error','error':'CELLULAR_TRANSPORT_POWER_ERROR'}
    with pytest.raises(RuntimeError,match='^CELLULAR_TRANSPORT_POWER_ERROR$'):guard.prepare()
    assert not guard.marker.exists() and (device/'power/control').read_text().strip()=='auto'


def test_resume_failure_is_not_reported_as_ready_and_never_retried(transport,monkeypatch):
    guard,device=transport;original=Path.write_text;writes=[]
    def fail_resume(path,value,*args,**kwargs):
        result=original(path,value,*args,**kwargs)
        if path==device/'power/control':
            writes.append(value);original(device/'power/runtime_status','error\n')
        return result
    monkeypatch.setattr(Path,'write_text',fail_resume)
    with pytest.raises(RuntimeError,match='^CELLULAR_TRANSPORT_POWER_ERROR$'):guard.prepare()
    assert writes==['on\n'] and guard.marker.exists()


def test_resume_wait_is_bounded_and_unknown_status_fails_closed(transport):
    guard,device=transport;(device/'power/runtime_status').write_text('resuming\n')
    with pytest.raises(RuntimeError,match='^CELLULAR_TRANSPORT_UNAVAILABLE$'):guard.prepare()
    assert 3<=guard.clock()<3.2
    (device/'power/runtime_status').write_text('private-unexpected-data\n')
    assert guard.status()=={'state':'unknown','error':'CELLULAR_TRANSPORT_UNAVAILABLE'}


def test_missing_or_other_driver_is_untouched(tmp_path):
    guard=TransportPower(tmp_path)
    guard.prepare();guard.release()
    assert guard.status()=={'state':'not_applicable','error':None} and not guard.marker.exists()


def test_corrupt_ownership_cannot_be_overwritten_or_release_an_external_hold(transport):
    guard,device=transport;guard.marker.parent.mkdir(parents=True)
    guard.marker.write_text('{broken-private-state')
    with pytest.raises(RuntimeError,match='^CELLULAR_TRANSPORT_UNAVAILABLE$'):guard.prepare()
    with pytest.raises(RuntimeError,match='^CELLULAR_TRANSPORT_UNAVAILABLE$'):guard.release()
    assert (device/'power/control').read_text().strip()=='auto'


@pytest.mark.parametrize('outside',[False,True])
def test_ambiguous_controller_or_outside_sysfs_never_grants_a_write(transport,monkeypatch,outside):
    guard,device=transport
    second=guard.root/'sys/class/net/wwan1';(second/'device/driver').mkdir(parents=True)
    other=guard.root/('outside-controller' if outside else 'sys/devices/platform/second-controller')
    original=Path.resolve
    def mapped(path,*args,**kwargs):
        if path==second/'device':return other
        if path==second/'device/driver':return guard.root/'sys/bus/platform/drivers/bam-dmux'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'resolve',mapped)
    assert guard.status()['error']=='CELLULAR_TRANSPORT_UNAVAILABLE'
    with pytest.raises(RuntimeError,match='^CELLULAR_TRANSPORT_UNAVAILABLE$'):guard.prepare()
    assert not guard.marker.exists() and (device/'power/control').read_text().strip()=='auto'


def test_network_cellular_up_prepares_transport_before_nm_and_does_not_touch_ap(monkeypatch):
    import uz801_manager.hotspot as module
    events=[]
    monkeypatch.setattr(module,'TransportPower',lambda:SimpleNamespace(prepare=lambda:events.append('prepare')))
    network=Network();network.nm=lambda *a,**k:events.append(('nm',a))
    network.up(CELL_UUID);assert events[0]=='prepare' and events[1][1][-1]==CELL_UUID
    events.clear();network.up(AP_UUID);assert len(events)==1 and events[0][0]=='nm'
    def error():raise RuntimeError('CELLULAR_TRANSPORT_POWER_ERROR')
    monkeypatch.setattr(module,'TransportPower',lambda:SimpleNamespace(prepare=error))
    events.clear()
    with pytest.raises(RuntimeError,match='^CELLULAR_TRANSPORT_POWER_ERROR$'):network.up(CELL_UUID)
    assert not events


def test_nm_connected_with_broken_transport_is_not_a_usable_interface(monkeypatch):
    import uz801_manager.hotspot as module
    network=Network();network.nm=lambda *a:'100 (connected)' if a[1]=='GENERAL.STATE' else 'wwan0'
    monkeypatch.setattr(module,'TransportPower',lambda:SimpleNamespace(status=lambda:{'error':'CELLULAR_TRANSPORT_POWER_ERROR'}))
    assert network.cellular_interface('fixture-control') is None


def test_quick_tile_reports_transport_error_without_claiming_connected(quick,monkeypatch):
    import uz801_manager.quick_settings as module
    q,network,_,_=quick;provision(q);invoke(q,'data_on',cellular_consent=True)
    monkeypatch.setattr(module,'TransportPower',lambda:SimpleNamespace(status=lambda:{'state':'error','error':'CELLULAR_TRANSPORT_POWER_ERROR'}))
    state=q.status()
    assert not state['mobile_data_connected'] and state['intent']['data_allowed']
    assert state['cellular_transport']['error']=='CELLULAR_TRANSPORT_POWER_ERROR'

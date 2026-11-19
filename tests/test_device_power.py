"""Mocked power commands only. No host/USB reboot or shutdown is executed."""
from contextlib import nullcontext,contextmanager
import json
import subprocess
from types import SimpleNamespace
import uuid

import pytest

from uz801_manager.device_power import DevicePower,validate
from uz801_manager.hosting import create_hosting_app


@pytest.fixture
def power(tmp_path):
    time=SimpleNamespace(value=100,boot='fixture-private-boot');calls=[]
    def run(args,**kwargs):
        assert kwargs=={'capture_output':True,'timeout':10,'shell':False}
        calls.append(args);return subprocess.CompletedProcess(args,0)
    backend=DevicePower(tmp_path/'private',tmp_path/'run',boot=lambda:time.boot,
                        clock=lambda:time.value,available=lambda:True,run=run,
                        gate_factory=lambda shared=False:nullcontext(),locks=(),sync=lambda:calls.append('sync'))
    backend.heartbeat('a'*32)
    return backend,time,calls


def request(backend,action='reboot',operation=None):
    return backend.call(action,operation=operation or str(uuid.uuid4()),confirm=True)


@pytest.mark.parametrize('action',['reboot','poweroff'])
def test_explicit_confirmed_request_waits_flushes_and_dispatches_normal_command_once(power,action):
    b,time,calls=power
    assert b.status()['phase']=='IDLE' and not b.path.exists()
    state=request(b,action);operation=state['operation']
    assert state['pending'] and not calls
    b.tick('a'*32);assert not calls
    time.value+=5
    def checkpoint():calls.append('checkpoint');return True
    b.tick('a'*32,checkpoint)
    assert calls==['checkpoint','sync',['/sbin/'+action]]
    assert b.status()['phase']=='DISPATCHED'
    b.tick('a'*32,checkpoint);assert len(calls)==3
    time.value+=110;b.tick('a'*32)
    assert b.status()['phase']=='UNKNOWN' and not b.status()['pending']
    with pytest.raises(RuntimeError,match='ALREADY_ATTEMPTED'):request(b,action,operation)
    assert 'fixture-private-boot' not in json.dumps(b.status()) and 'worker' not in b.status()


def test_cancel_and_expiry_do_not_dispatch(power):
    b,time,calls=power
    state=request(b);request(b,'cancel',state['operation']);time.value+=6;b.tick('a'*32)
    assert b.status()['phase']=='CANCELLED' and calls==[]
    request(b);time.value+=61;b.tick('a'*32)
    assert b.status()['phase']=='EXPIRED' and calls==[]


def test_worker_restart_and_new_boot_never_replay_power_requests(power):
    b,time,calls=power
    request(b,'poweroff');time.value+=6;b.tick('b'*32)
    assert b.status()['phase']=='CANCELLED' and not calls
    request(b);time.boot='another-private-boot';b.tick('b'*32)
    assert b.status()['phase']=='BOOT_CHANGED' and not b.status()['pending'] and not calls


def test_pending_and_stale_worker_reject_new_requests(power):
    b,time,calls=power
    request(b)
    with pytest.raises(RuntimeError,match='POWER_PENDING'):request(b,'poweroff')
    with pytest.raises(RuntimeError,match='POWER_PENDING'):
        with b.activity():pytest.fail('mutation must be blocked')
    time.value+=200
    with pytest.raises(RuntimeError,match='POWER_UNAVAILABLE'):request(b)
    assert calls==[]


def test_waits_for_inflight_locks_then_expires_instead_of_delayed_reboot(power):
    b,time,calls=power
    @contextmanager
    def busy():raise RuntimeError('MODEM_BUSY');yield
    b.locks=(busy,);request(b);time.value+=5;b.tick('a'*32)
    assert b.status()['phase']=='WAITING_BUSY' and not calls
    time.value+=61;b.tick('a'*32);b.locks=();b.tick('a'*32)
    assert b.status()['phase']=='EXPIRED' and not calls


def test_pending_network_trial_and_failed_usage_checkpoint_prevent_dispatch(power):
    b,time,calls=power
    b.directory.mkdir(parents=True);pending=b.directory/'setup-pending.json';pending.write_text('{}')
    with pytest.raises(RuntimeError,match='NETWORK_TRIAL_PENDING'):request(b)
    pending.unlink();request(b);time.value+=5;b.tick('a'*32,lambda:False)
    assert b.status()['error']=='USAGE_CHECKPOINT_FAILED' and calls==[]


def test_uncertain_command_never_retries_on_timeout_or_worker_restart(power):
    b,time,calls=power
    def timeout(args,**kwargs):calls.append(args);raise subprocess.TimeoutExpired('fixed',10)
    b.run=timeout;request(b);time.value+=5;b.tick('a'*32)
    assert b.status()['phase']=='UNKNOWN'
    b.tick('a'*32);b.tick('b'*32);assert calls==['sync',['/sbin/reboot']]


@pytest.mark.parametrize('value',[None,[],{}, {'action':'reboot','confirm':False,'operation':str(uuid.uuid4())},
    {'action':'poweroff -f','confirm':True,'operation':str(uuid.uuid4())},
    {'action':'reboot','confirm':True,'operation':'../reboot'},
    {'action':'reboot','confirm':True,'operation':str(uuid.uuid4()),'command':'erase'}])
def test_strict_payload_allowlist(value):
    with pytest.raises(ValueError):validate(value)


@pytest.mark.parametrize('raw',['partial','[]','{}','x'*4097])
def test_corrupt_queue_is_not_overwritten_or_executed(power,raw):
    b,time,calls=power;b.directory.mkdir(parents=True);b.path.write_text(raw)
    with pytest.raises(RuntimeError,match='POWER_STATE_INVALID'):request(b)
    with pytest.raises(RuntimeError,match='POWER_STATE_INVALID'):b.tick('a'*32)
    assert b.path.read_text()==raw and not calls


def test_save_failure_never_calls_power_command_and_receipt_cannot_be_reused(power,monkeypatch):
    b,time,calls=power;operation=str(uuid.uuid4());old=b.write
    def fail(value):raise RuntimeError('POWER_SAVE_FAILED')
    monkeypatch.setattr(b,'write',fail)
    with pytest.raises(RuntimeError,match='POWER_RESULT_UNKNOWN'):request(b,operation=operation)
    b.tick('a'*32);assert not calls
    monkeypatch.setattr(b,'write',old)
    with pytest.raises(RuntimeError,match='ALREADY_ATTEMPTED'):request(b,operation=operation)


def test_endpoints_inherit_host_origin_token_and_post_confirmation_and_get_is_passive(power):
    b,time,calls=power
    app=create_hosting_app(backend=object(),usb_portal=True,modem_backend=object(),power_backend=b,token='fixture')
    client=app.test_client();headers={'Host':'172.16.42.1','X-OpenStick-Token':'fixture','Origin':'http://172.16.42.1'}
    assert client.get('/settings/system',headers=headers).status_code==200
    assert 'Hệ thống' in client.get('/manage',headers=headers).text
    for _ in range(3):assert client.get('/api/device/power',headers=headers).json['phase']=='IDLE'
    assert not b.path.exists() and not calls
    payload={'action':'reboot','operation':str(uuid.uuid4()),'confirm':True}
    assert client.post('/api/device/power',json=payload,headers={'Host':'172.16.42.1'}).status_code==403
    assert client.post('/api/device/power',json=payload,headers={**headers,'Origin':'http://foreign.invalid'}).status_code==403
    assert client.post('/api/device/power',json={**payload,'confirm':False},headers=headers).status_code==400
    assert client.post('/api/device/power',json=payload,headers=headers).status_code==202
    assert client.post('/api/wifi',json={'action':'overview'},headers=headers).json['error']=='POWER_PENDING'
    assert client.get('/api/device/power',headers=headers).json['phase']=='QUEUED'
    assert not calls


def test_feature_absent_in_windows_and_unconfigured_preview(power):
    app=create_hosting_app(backend=object(),token='fixture')
    assert app.test_client().get('/settings/system',headers={'Host':'127.0.0.1:8770'}).status_code==404


def test_failure_recording_dispatched_command_is_unknown_not_safe_to_repeat(power,monkeypatch):
    b,time,calls=power;original=b.write
    def write(value):
        if value['phase']=='DISPATCHED':raise RuntimeError('POWER_SAVE_FAILED')
        original(value)
    monkeypatch.setattr(b,'write',write)
    request(b);time.value+=5;b.tick('a'*32)
    assert b.status()['phase']=='UNKNOWN' and calls==['sync',['/sbin/reboot']]
    b.tick('a'*32);assert len(calls)==2


def test_dispatch_intent_save_failure_never_runs_command(power,monkeypatch):
    b,time,calls=power;original=b.write
    def write(value):
        if value['phase']=='DISPATCHING':raise RuntimeError('POWER_SAVE_FAILED')
        original(value)
    monkeypatch.setattr(b,'write',write)
    request(b);time.value+=5;b.tick('a'*32)
    assert not calls and b.status()['phase']=='FAILED'


def test_lan_login_is_required_even_with_a_valid_power_token(power,tmp_path):
    from uz801_manager.lan_access import LanSettings
    from test_lan_access import login,BASE,PASSWORD
    b,_,calls=power;settings=LanSettings(tmp_path/'lan',address=lambda:'192.0.2.2')
    settings.configure(PASSWORD)
    app=create_hosting_app(backend=object(),modem_backend=object(),usb_portal=True,
                           power_backend=b,token='fixture-token',authority='192.0.2.2:8765',lan_auth=settings)
    client=app.test_client();headers={'X-OpenStick-Token':'fixture-token','Origin':BASE}
    payload={'action':'poweroff','confirm':True,'operation':str(uuid.uuid4())}
    assert client.get('/settings/system',base_url=BASE).location=='/login'
    assert client.post('/api/device/power',base_url=BASE,headers=headers,json=payload).status_code==401
    assert not b.path.exists() and not calls
    assert login(client).status_code==302
    assert client.get('/api/device/power',base_url=BASE,headers=headers).json['phase']=='IDLE'


@pytest.mark.parametrize('channel',['wifi','internet','hotspot'])
def test_async_job_keeps_power_gate_after_http_acknowledgement(power,channel):
    import threading
    b,_,calls=power;readers=[0];mutex=threading.Lock();started=threading.Event();release=threading.Event()
    @contextmanager
    def gate(shared=False):
        with mutex:
            if not shared and readers[0]:raise RuntimeError('POWER_BUSY')
            readers[0]+=int(shared)
        try:yield
        finally:
            with mutex:readers[0]-=int(shared)
    b.gate_factory=gate
    class Backend:
        def call(self,*args,**kwargs):
            started.set();assert release.wait(2);return {'connected':True}
    backend=Backend()
    app=create_hosting_app(backend=backend,usb_portal=True,modem_backend=object(),power_backend=b,token='fixture',
                           network_backend=backend if channel=='internet' else None,
                           hotspot_backend=backend if channel=='hotspot' else None)
    headers={'Host':'172.16.42.1','Origin':'http://172.16.42.1','X-OpenStick-Token':'fixture'}
    client=app.test_client()
    try:
        assert client.post('/api/'+channel,headers=headers,json={'action':'status'}).status_code==202
        assert started.wait(1)
        with pytest.raises(RuntimeError,match='POWER_BUSY'):request(b)
        assert not b.path.exists() and not calls
    finally:
        release.set();app.extensions[{'wifi':'hosting','internet':'network_policy','hotspot':'hotspot'}[channel]]['thread'].join(2)
    assert request(b)['phase']=='QUEUED'


@pytest.mark.parametrize('stage',['checkpoint','sync','service_stop'])
def test_preparation_timeout_or_service_stop_never_dispatches_late(power,stage):
    b,time,calls=power;stopped=[False]
    def checkpoint():
        if stage=='checkpoint':time.value+=61
        return True
    def sync():
        if stage=='sync':time.value+=61
        if stage=='service_stop':stopped[0]=True
    b.sync=sync;request(b);time.value+=5
    b.tick('a'*32,checkpoint,lambda:stopped[0])
    assert b.status()['phase']==('CANCELLED' if stage=='service_stop' else 'EXPIRED')
    assert not calls
    b.tick('a'*32);assert not calls

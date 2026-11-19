"""Slow/failing display producers must not occupy HTTP or authorize actions."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import json
import shutil
import subprocess
import threading
import time

import pytest

from uz801_manager.hosting import create_hosting_app
from uz801_manager.hosting_device import LocalWifi
from uz801_manager.telemetry import ReadOnlySnapshot, SnapshotPending, invalidate_display


def wait_for(predicate):
    end = time.monotonic()+2
    while not predicate() and time.monotonic()<end:time.sleep(.005)
    assert predicate()


def ready(snapshot):
    try:snapshot.get()
    except SnapshotPending:pass
    wait_for(lambda:not snapshot.running)
    return snapshot.get()


@pytest.mark.skipif(shutil.which('node') is None,reason='Node unavailable')
def test_shared_frontend_reads_coalesce_and_never_retry_mutations():
    subprocess.run(['node','tests/telemetry_ui_fixture.cjs'],check=True,timeout=10)


def test_single_flight_nonblocking_copy_and_bounded_stale_lifetime():
    release=threading.Event();started=threading.Event();calls=[];clock=[100]
    def collect():
        calls.append(True);started.set();assert release.wait(2);return {'nested':{'value':1}}
    source=ReadOnlySnapshot(collect,clock=lambda:clock[0])
    try:
        begin=time.monotonic()
        for _ in range(20):
            with pytest.raises(SnapshotPending):source.get()
        assert time.monotonic()-begin<1
        assert started.wait(1) and len(calls)==1
    finally:release.set()
    wait_for(lambda:not source.running)
    value=source.get();value['nested']['value']=999
    assert source.get()['nested']['value']==1
    release.clear();clock[0]=106
    try:
        stale=source.get()
        assert stale['_telemetry']=={'age_seconds':6,'stale':True,'refreshing':True}
        clock[0]=131
        with pytest.raises(SnapshotPending):source.get()
    finally:release.set()
    wait_for(lambda:not source.running)


def test_mutation_discards_inflight_generation_and_errors_do_not_reset_age():
    release=threading.Event();clock=[100];calls=[]
    def collect():
        calls.append(True);assert release.wait(2);return {'old':True}
    source=ReadOnlySnapshot(collect,clock=lambda:clock[0])
    with pytest.raises(SnapshotPending):source.get()
    source.invalidate();release.set();wait_for(lambda:not source.running)
    assert source.value is None
    assert ready(source)['old']
    source.producer=lambda:(_ for _ in ()).throw(TimeoutError('private secret'))
    clock[0]=106;source.get();wait_for(lambda:not source.running)
    assert source.get()['_telemetry']['age_seconds']==6
    clock[0]=131
    with pytest.raises(SnapshotPending):source.get()
    wait_for(lambda:not source.running)
    assert source.at==100  # Failed reads cannot turn an old sample into fresh data.


def test_blocked_producers_leave_html_assets_and_power_status_responsive():
    release=threading.Event();calls=[]
    def blocked(kind):
        calls.append(kind);assert release.wait(3);return {}
    class Backend:
        def call(self,action,**values):return blocked(action)
        def services(self):return blocked('services')
    class Quick:
        def status(self):return blocked('quick')
    class Power:
        def status(self):return {'phase':'IDLE','pending':False}
        def activity(self):return nullcontext()
        def call(self,*args,**kw):raise AssertionError('No power action allowed in this test')
    app=create_hosting_app(backend=Backend(),usb_portal=True,modem_backend=object(),
                           quick_backend=Quick(),power_backend=Power(),token='fixture')
    headers={'Host':'172.16.42.1','X-OpenStick-Token':'fixture'}
    def request(path):
        with app.test_client() as client:return client.get(path,headers=headers)
    try:
        for path in ['/api/header','/api/overview','/api/quick','/api/services']:
            value=request(path);assert value.status_code==503 and value.json['error']=='STATUS_PENDING'
            assert value.headers['Retry-After']=='1'
        wait_for(lambda:len(calls)==4)
        start=time.monotonic()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(request,['/overview','/static/portal.css','/api/device/power','/manage']))
        assert all(value.status_code==200 for value in results)
        assert time.monotonic()-start<1
        assert request('/api/overview').status_code==503 and len(calls)==4
        assert app.extensions['hosting']['state']=={'busy':False,'result':{},'error':False}
    finally:
        release.set()
        for source in app.extensions['telemetry'].values():wait_for(lambda:not source.running)


def test_cache_never_bypasses_lan_authentication_or_cross_origin_guards(tmp_path):
    from uz801_manager.lan_access import LanSettings
    settings=LanSettings(tmp_path,address=lambda:'192.0.2.2');settings.configure('fictional-password')
    calls=[]
    class Backend:
        def call(self,action,**kw):calls.append(action);return {'connected':True}
    app=create_hosting_app(backend=Backend(),usb_portal=True,modem_backend=object(),
        token='fixture',lan_auth=settings,authority='192.0.2.2:8765')
    source=app.extensions['telemetry']['header'];ready(source);count=len(calls)
    with app.test_client() as client:
        for path in ['/api/header','/api/overview','/api/services']:
            assert client.get(path,base_url='http://192.0.2.2:8765',headers={'X-OpenStick-Token':'fixture'}).status_code==401
            assert client.get(path,base_url='http://192.0.2.2:8765',headers={
                'X-OpenStick-Token':'fixture','Origin':'http://foreign.invalid'}).status_code==403
    assert len(calls)==count and app.extensions['telemetry']['overview'].value is None


def test_read_only_jobs_keep_cache_and_mutations_invalidate_on_enqueue_and_completion():
    release=threading.Event();entered=threading.Event();writes=[]
    class Backend:
        def call(self,action,**values):
            if action=='status':return {'connected':True}
            assert action=='connect';writes.append(values);entered.set();assert release.wait(2);return {'connected':False}
    app=create_hosting_app(backend=Backend(),usb_portal=True,modem_backend=object(),token='fixture')
    source=app.extensions['telemetry']['header'];ready(source)
    invalidate_display(app,'overview');assert source.value is not None
    headers={'Host':'172.16.42.1','X-OpenStick-Token':'fixture'}
    try:
        with app.test_client() as client:
            assert client.post('/api/wifi',headers=headers,json={
                'action':'connect','ssid':'fictional','password':'fictional-password'}).status_code==202
        assert entered.wait(1) and source.value is None
        ready(source);assert source.value is not None  # A display read during the operation.
    finally:
        release.set();app.extensions['hosting']['thread'].join(2)
    assert source.value is None and len(writes)==1


def test_local_status_coalesces_and_invalidates_without_waiting_for_a_slow_read(monkeypatch):
    release=threading.Event();entered=threading.Event();calls=[];clock=[100]
    def run(args,**kw):
        action=json.loads(kw['input'])['action'];calls.append(action)
        if action=='status':entered.set();assert release.wait(2)
        return subprocess.CompletedProcess(args,0,stdout=b'{"connected":true}')
    backend=LocalWifi(run=run,clock=lambda:clock[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(backend.call,'status');assert entered.wait(1)
        start=time.monotonic();backend.invalidate_status();assert time.monotonic()-start<.5
        release.set();assert first.result(1)['connected']
    assert backend.status_value is None  # In-flight pre-mutation sample was not cached.
    backend.call('status');backend.call('status');assert calls==['status','status']
    backend.call('connect',ssid='fictional',password='fictional-password')
    backend.call('status');assert calls==['status','status','connect','status']
    # Fast dashboard reads cannot spawn another modem/Wi-Fi process or wait on its lock.
    import uz801_manager.portal_metrics as metrics
    monkeypatch.setattr(metrics,'system_snapshot',lambda:{'ram':{'used':1}})
    monkeypatch.setattr(metrics,'service_snapshot',lambda:{'modemmanager':True})
    backend.status_lock.acquire()
    try:
        value=backend.dashboard();assert value['wifi']=={} and value['services']=={}
        assert backend.services()['services']['modemmanager']
        assert len(calls)==4
    finally:backend.status_lock.release()

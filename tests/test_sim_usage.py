"""Cellular accounting with synthetic counters; no real traffic or SIM IDs."""
import copy
from datetime import datetime, timezone
import json
import subprocess
from types import SimpleNamespace

import pytest

from uz801_manager import sim_usage as usage

BOOT = '00000000-0000-0000-0000-000000000001'


@pytest.fixture
def meter(tmp_path):
    clock = SimpleNamespace(wall=datetime(2026,11,18,12,tzinfo=timezone.utc).timestamp(), mono=0)
    source = SimpleNamespace(value={'boot':BOOT,'interface':'wwan0','index':7,'rx':100000,'tx':50000})
    def read():
        if isinstance(source.value,Exception):raise source.value
        return copy.deepcopy(source.value)
    source.read = read
    collector = usage.Collector(tmp_path/'var/lib/openstick',tmp_path/'run/openstick',
                                source=source,clock=lambda:clock.wall,monotonic=lambda:clock.mono)
    def tick(rx=0, tx=0, seconds=10):
        clock.wall += seconds;clock.mono += seconds
        if isinstance(source.value,dict):source.value['rx'] += rx;source.value['tx'] += tx
        collector.sample()
        return usage.snapshot(tmp_path,now=lambda:clock.wall)
    return collector,source,clock,tick,tmp_path


def test_initial_baseline_then_counts_only_deltas_and_private_identity_projection(meter):
    c,source,clock,tick,root=meter
    first=tick();assert first['today']['total_bytes']==0
    assert first['status']=='connected' and not first['stale']
    result=tick(4096,2048)
    assert result['today']=={'download_bytes':4096,'upload_bytes':2048,'total_bytes':6144}
    assert result['month']==result['session']==result['total']==result['today']
    exported=json.dumps(result)
    assert BOOT not in exported and 'wwan0' not in exported and 'index' not in exported
    assert usage.valid_state(c.state)
    unchanged=c.path.read_bytes();usage.snapshot(root,now=lambda:clock.wall)
    assert c.path.read_bytes()==unchanged


def test_checkpoint_is_bounded_and_process_restart_recovers_unflushed_delta_once(meter):
    c,source,clock,tick,root=meter
    tick();saved=c.path.read_bytes()
    tick(100,200);assert c.path.read_bytes()==saved
    fresh=usage.Collector(c.path.parent,c.runtime.parent,source=source,
                         clock=lambda:clock.wall,monotonic=lambda:clock.mono)
    fresh.sample();assert fresh.state['total']==[100,200]
    fresh.sample();assert fresh.state['total']==[100,200]
    c.flush(force=True)
    assert json.loads(c.path.read_text())['total']==[100,200]
    tick(10,20,60);assert json.loads(c.path.read_text())['total']==[110,220]
    assert usage.valid_state(json.loads(c.path.read_text()))


def test_boot_interface_and_counter_reset_preserve_total_without_adding_raw_bytes(meter):
    c,source,clock,tick,_=meter
    tick();tick(100,200)
    source.value['boot']='00000000-0000-0000-0000-000000000002'
    result=tick(9000,9000);assert result['total']['total_bytes']==300
    assert result['session']['total_bytes']==0 and result['continuity_gaps']==1
    tick(5,6);source.value['index']=8
    assert tick(9999,9999)['total']['total_bytes']==311
    source.value['rx']=1;source.value['tx']=1
    assert tick()['total']['total_bytes']==311
    assert tick(1,2)['total']['total_bytes']==314


def test_disconnect_retains_history_and_flushes_but_never_counts_reconnect_baseline(meter):
    c,source,_,tick,_=meter
    tick();tick(100,200);previous=copy.deepcopy(source.value);source.value=None
    result=tick();assert result['status']=='idle' and result['total']['total_bytes']==300
    assert result['session']['total_bytes']==0
    assert json.loads(c.path.read_text())['total']==[100,200]
    source.value=previous;assert tick(9000,9000)['total']['total_bytes']==300
    assert tick(1,2)['total']['total_bytes']==303


def test_source_failure_is_unknown_not_zero_and_recovery_does_not_double_count(meter):
    c,source,_,tick,_=meter
    tick();tick(100,200);previous=copy.deepcopy(source.value)
    source.value=RuntimeError('private identifiers must not escape')
    result=tick();assert result['stale'] and result['error']=='USAGE_SOURCE_UNAVAILABLE'
    assert result['total']['total_bytes']==300 and 'private' not in json.dumps(result)
    source.value=previous;assert tick(20,30)['total']['total_bytes']==350


def test_vietnam_day_month_rollover_and_clock_jump_do_not_reuse_old_period(meter):
    c,source,clock,tick,root=meter
    clock.wall=datetime(2026,11,30,16,59,50,tzinfo=timezone.utc).timestamp()
    tick(seconds=0);assert tick(10,20,5)['month']['total_bytes']==30
    result=tick(30,40,10)
    assert result['today']['total_bytes']==70 and result['month']['total_bytes']==70
    assert result['total']['total_bytes']==100
    # NTP moves backwards one day; only the lifetime total receives this interval.
    clock.wall-=86400
    result=tick(5,6)
    assert result['total']['total_bytes']==111 and result['undated']['total_bytes']==11
    assert result['continuity_gaps']==1
    clock.wall+=86400*3
    stale=usage.snapshot(root,now=lambda:clock.wall)
    assert stale['today'] is None and stale['stale']


def test_unsynced_boot_time_tracks_total_but_does_not_fabricate_calendar(meter):
    c,source,clock,tick,_=meter
    clock.wall=1000;tick();result=tick(1,2)
    assert result['today'] is None and result['month'] is None
    assert result['total']['total_bytes']==3 and result['undated']['total_bytes']==3


@pytest.mark.parametrize('value',['partial','[]','{}','{"version":1,"total":[true,0]}','x'*131073])
def test_corrupt_state_is_not_reset_or_overwritten(meter,value):
    c,_,_,tick,_=meter
    c.path.parent.mkdir(parents=True);c.path.write_text(value)
    result=tick();assert result['error']=='USAGE_STATE_INVALID' and not result['available']
    assert c.path.read_text()==value


def test_disk_full_reports_unsaved_live_totals_and_retry_preserves_counts(meter,monkeypatch):
    c,_,_,tick,_=meter
    tick();before=c.path.read_bytes();atomic=usage.atomic
    def full(path,*args,**kwargs):
        if path==c.path:raise OSError('private path/full disk')
        return atomic(path,*args,**kwargs)
    monkeypatch.setattr(usage,'atomic',full)
    result=tick(30,40,60)
    assert result['error']=='USAGE_SAVE_FAILED' and result['total']['total_bytes']==70
    assert c.path.read_bytes()==before and c.dirty
    monkeypatch.setattr(usage,'atomic',atomic)
    assert tick(1,2)['total']['total_bytes']==73
    assert json.loads(c.path.read_text())['total']==[31,42]


def test_missing_stale_and_malformed_runtime_never_claim_live_zero(meter):
    c,_,clock,tick,root=meter
    assert usage.snapshot(root)['error']=='USAGE_NOT_STARTED'
    tick();tick(1,2);c.flush(force=True);c.runtime.unlink()
    result=usage.snapshot(root,now=lambda:clock.wall)
    assert result['total']['total_bytes']==3 and result['stale']
    for text in ['[]','{}','NaN','null']:
        c.runtime.write_text(text);assert not usage.snapshot(root,now=lambda:clock.wall)['available']


def test_runtime_unknown_fields_are_not_exported_or_cached(meter):
    c,_,clock,tick,root=meter
    tick();value=json.loads(c.runtime.read_text());value['imsi']='private-fixture'
    value['today']['imsi']='private-fixture';c.runtime.write_text(json.dumps(value))
    result=usage.snapshot(root,now=lambda:clock.wall)
    assert 'private-fixture' not in json.dumps(result)


def test_calendar_history_is_bounded_but_lifetime_total_survives(meter):
    c,_,clock,tick,_=meter
    tick()
    for _ in range(402):tick(1,2,86400)
    assert len(c.state['days'])<=400 and c.state['total']==[402,804]
    assert usage.valid_state(c.state)


def test_counter_source_only_fixed_readonly_commands_and_cellular_family(tmp_path):
    calls=[];output=['wwan0:gsm\nwlan0:wifi\nusb0:ethernet','100 (connected)\nwwan0']
    def run(args,**kwargs):
        calls.append(args)
        assert kwargs=={'capture_output':True,'text':True,'shell':False,'timeout':3}
        assert args in [ ['nmcli','-t','-f','DEVICE,TYPE','device','status'],
                        ['nmcli','-g','GENERAL.STATE,GENERAL.IP-IFACE','device','show','wwan0'] ]
        return subprocess.CompletedProcess(args,0,output[0] if args[1]=='-t' else output[1])
    def write(name,value):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value)
    for name,value in [('ifindex','7'),('statistics/rx_bytes','100'),('statistics/tx_bytes','200')]:
        write('sys/class/net/wwan0/'+name,value)
    write('proc/sys/kernel/random/boot_id',BOOT)
    source=usage.CounterSource(tmp_path,run=run)
    assert source.read()['rx']==100 and len(calls)==3
    for raw in ['100 (connected)\nwlan0','100 (connected)\nusb0','100 (connected)\n../etc','partial']:
        output[1]=raw
        with pytest.raises(ValueError):source.read()
    output[1]='30 (disconnected)\n--';assert source.read() is None
    output[0]='wwan0:gsm\nwwan1:gsm'
    with pytest.raises(ValueError):source.read()
    output[0]=''
    with pytest.raises(ValueError):source.read()


def test_counter_source_timeout_is_not_a_valid_sample(tmp_path):
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('nmcli',3)
    with pytest.raises(subprocess.TimeoutExpired):usage.CounterSource(tmp_path,run=timeout).read()


@pytest.mark.parametrize('interface',['wwan0','rmnet_data0','wlan0','usb0','lo','../private','wwan0;id'])
def test_source_only_reads_confirmed_cellular_device_and_uses_readonly_commands(tmp_path,interface):
    base=tmp_path/'sys/class/net'/interface
    if interface in ('wwan0','rmnet_data0'):
        (base/'statistics').mkdir(parents=True)
        for name,value in [('ifindex','7'),('statistics/rx_bytes','1024'),('statistics/tx_bytes','2048')]:
            (base/name).write_text(value)
        boot=tmp_path/'proc/sys/kernel/random/boot_id';boot.parent.mkdir(parents=True);boot.write_text(BOOT)
    calls=[]
    def run(args,**kw):
        calls.append(args)
        assert args[0]=='nmcli' and kw['shell'] is False and kw['timeout']==3
        assert args in (['nmcli','-t','-f','DEVICE,TYPE','device','status'],
                        ['nmcli','-g','GENERAL.STATE,GENERAL.IP-IFACE','device','show','wwan0qmi0'])
        text='wwan0qmi0:gsm\nwlan0:wifi' if args[-1]=='status' else '100 (connected)\n'+interface
        return subprocess.CompletedProcess(args,0,text,'')
    source=usage.CounterSource(tmp_path,run)
    if interface in ('wwan0','rmnet_data0'):
        value=source.read();assert value['rx']==1024 and value['tx']==2048 and len(calls)==3
    else:
        with pytest.raises(ValueError):source.read()


def test_source_rejects_ambiguous_modems_and_invalid_state(tmp_path):
    for value in ['a:gsm\nb:gsm','x:gsm']:
        def run(args,**kw):return subprocess.CompletedProcess(args,0,value if args[-1]=='status' else 'invalid','')
        with pytest.raises(ValueError):usage.CounterSource(tmp_path,run).read()


def test_overview_telemetry_includes_usage_without_starting_or_writing_collector(meter):
    from uz801_manager.portal_metrics import system_snapshot
    c,_,clock,tick,root=meter
    tick();tick(1024,2048)
    before=c.runtime.read_bytes()
    result=system_snapshot(root,now=lambda:clock.wall)['sim_usage']
    assert result['today']['total_bytes']==3072 and c.runtime.read_bytes()==before


def test_first_probe_failure_never_creates_a_zero_usage_claim(meter):
    c,source,_,tick,_=meter
    source.value=RuntimeError('private failure')
    result=tick();assert result['available'] is False and result['error']=='USAGE_SOURCE_UNAVAILABLE'
    c.flush(force=True);assert not c.path.exists()


def test_partial_inventory_and_changed_link_are_unknown_not_idle(tmp_path):
    for value in ['partial','wwan0:gsm\ntruncated']:
        def run(args,**kwargs):return subprocess.CompletedProcess(args,0,value,'')
        with pytest.raises(ValueError):usage.CounterSource(tmp_path,run).read()
    base=tmp_path/'sys/class/net/wwan0';(base/'statistics').mkdir(parents=True)
    for name in ['ifindex','statistics/rx_bytes','statistics/tx_bytes']:(base/name).write_text('7')
    boot=tmp_path/'proc/sys/kernel/random/boot_id';boot.parent.mkdir(parents=True);boot.write_text(BOOT)
    calls=[]
    def run(args,**kwargs):
        calls.append(args)
        output='wwan0:gsm' if len(calls)==1 else '100 (connected)\n'+('wwan0' if len(calls)==2 else 'wlan0')
        return subprocess.CompletedProcess(args,0,output,'')
    with pytest.raises(ValueError):usage.CounterSource(tmp_path,run).read()


def test_background_is_started_only_by_worker_and_closed_on_worker_exit(monkeypatch):
    from contextlib import contextmanager
    import signal
    from uz801_manager import network_startup,ap_clients,device_power,cellular_recovery
    events=[]
    @contextmanager
    def background():
        events.append('collector_started')
        try:yield
        finally:events.append('collector_closed')
    monkeypatch.setattr(usage,'background',background)
    from contextlib import nullcontext
    monkeypatch.setattr(device_power,'background',lambda checkpoint:nullcontext(None))
    monkeypatch.setattr(signal,'signal',lambda *args:None)
    monkeypatch.setattr(network_startup,'NetworkStartup',lambda:SimpleNamespace(quick=object(),tick=lambda:events.append('startup_tick')))
    monkeypatch.setattr(cellular_recovery,'CellularRecovery',lambda quick:SimpleNamespace(tick=lambda:events.append('recovery_tick')))
    monkeypatch.setattr(ap_clients,'ApClients',lambda:SimpleNamespace(tick=lambda:events.append('clients_tick')))
    def stop(seconds):raise SystemExit(0)
    monkeypatch.setattr(network_startup.time,'sleep',stop)
    with pytest.raises(SystemExit):network_startup.main()
    assert events==['collector_started','clients_tick','startup_tick','recovery_tick','collector_closed']

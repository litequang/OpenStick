"""Passive cellular-interface accounting; no radio, bearer or route mutations.

One collector thread lives in the existing startup worker. Browser requests only
read sanitized snapshots; no SIM identity or packet content is ever collected.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time

ZONE = timezone(timedelta(hours=7))
NAME = 'sim-usage.json'
MAX = 2**64 - 1
PERIOD = 10
CHECKPOINT = 60
STALE = 60
ERRORS = {'USAGE_SOURCE_UNAVAILABLE', 'USAGE_STATE_INVALID', 'USAGE_SAVE_FAILED'}


def integer(value):
    return type(value) is int and 0 <= value <= MAX


def pair(value):
    return isinstance(value, list) and len(value) == 2 and all(integer(n) for n in value)


def stamp(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value < 4133980800


def day(value):
    # Boot clocks before 2020 are not useful for calendar accounting.
    return datetime.fromtimestamp(value, ZONE).date().isoformat() if value >= 1577836800 else None


def read_json(path, limit=131072):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, encoding='utf-8') as stream:
        if os.fstat(stream.fileno()).st_size > limit:raise ValueError()
        return json.loads(stream.read(limit + 1))


def atomic(path, value, durable=False):
    path = Path(path);path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():raise ValueError()
    fd, temporary = tempfile.mkstemp(prefix='.sim-usage-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, separators=(',', ':'), allow_nan=False)
            stream.flush()
            if durable:os.fsync(stream.fileno())
        os.replace(temporary, path)
        if durable and os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
    finally:
        try:os.unlink(temporary)
        except FileNotFoundError:pass


class CounterSource:
    """Discover exactly one connected GSM data interface, never a default route."""
    def __init__(self, root=Path('/'), run=subprocess.run, *, bearer_read=None):
        self.root, self.run = Path(root), run
        self.bearer_read = bearer_read

    def command(self, *args):
        result = self.run(['nmcli', *args], capture_output=True, text=True,
                          shell=False, timeout=3)
        if result.returncode or len(result.stdout) > 4096:raise ValueError()
        return result.stdout.strip()

    def read(self):
        rows = self.command('-t', '-f', 'DEVICE,TYPE', 'device', 'status').splitlines()
        if not rows or any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}:[A-Za-z0-9_-]{1,32}', row) for row in rows):
            raise ValueError()
        controls = [row[:-4] for row in rows if re.fullmatch(r'[A-Za-z0-9_.-]{1,32}:gsm', row)]
        if not controls:return None
        if len(controls) != 1:raise ValueError()
        args = ('-g', 'GENERAL.STATE,GENERAL.IP-IFACE', 'device', 'show', controls[0])
        state = self.command(*args).splitlines()
        code = re.match(r'^([0-9]{1,3})(?:\s|$)', state[0]) if state else None
        if not code or int(code[1]) not in (0,10,20,30,40,50,60,70,80,90,100,110,120):raise ValueError()
        if int(code[1]) != 100:return None
        if len(state) != 2 or not re.fullmatch(r'(?:wwan|rmnet)[A-Za-z0-9_.-]{0,26}', state[1]):
            raise ValueError()
        interface = state[1];base = self.root / 'sys/class/net' / interface
        def number(path):
            raw = path.read_text(encoding='ascii').strip()
            if not re.fullmatch(r'[0-9]{1,20}', raw) or int(raw) > MAX:raise ValueError()
            return int(raw)
        index = number(base / 'ifindex')
        rx = number(base / 'statistics/rx_bytes');tx = number(base / 'statistics/tx_bytes')
        source, epoch = 'netdev', ''
        # Physical UZ801 BAM-DMUX returns zero sysfs byte counters despite live
        # traffic. MM's connected bearer has verified, periodically updated
        # modem counters. Do not treat missing MM statistics as a valid zero.
        driver = base / 'device/driver'
        if driver.exists() and driver.resolve().name == 'bam-dmux':
            from .modem_counters import bearer_counters
            value = (self.bearer_read or bearer_counters)(interface)
            if not isinstance(value,dict) or set(value) != {'rx','tx','epoch'}:raise ValueError()
            rx, tx, epoch = value['rx'], value['tx'], value['epoch']
            source = 'modem_bearer'
        boot = (self.root / 'proc/sys/kernel/random/boot_id').read_text().strip()
        if (not re.fullmatch(r'[0-9a-f-]{36}', boot) or not index or index != number(base / 'ifindex')
                or self.command(*args).splitlines() != state):raise ValueError()
        return reading({'boot':boot,'interface':interface,'index':index,'rx':rx,'tx':tx,
                        'source':source,'epoch':epoch})


def reading(value):
    if value is None:return None
    basic = {'boot','interface','index','rx','tx'}
    if not isinstance(value,dict) or set(value) not in (basic,basic|{'source','epoch'}):raise ValueError()
    result = {'source':'netdev','epoch':'',**value}
    if (not isinstance(result['boot'],str) or not re.fullmatch(r'[0-9a-f-]{36}',result['boot'])
            or not isinstance(result['interface'],str) or not re.fullmatch(r'(?:wwan|rmnet)[A-Za-z0-9_.-]{0,26}',result['interface'])
            or any(not integer(result[k]) for k in ('index','rx','tx')) or not result['index']
            or result['source'] not in ('netdev','modem_bearer')
            or result['source']=='netdev' and result['epoch'] != ''
            or result['source']=='modem_bearer' and (not isinstance(result['epoch'],str)
                or not re.fullmatch(r'[0-9]{1,10}:[0-9]{1,20}:[0-9]{1,20}',result['epoch']))):
        raise ValueError()
    return result


def valid_state(value):
    try:
        if (set(value) != {'version','started_at','sampled_at','saved_at','total','undated',
                           'days','last','session','gaps'} or type(value['version']) is not int or value['version'] not in (1,2)
                or any(not stamp(value[k]) for k in ('started_at','sampled_at','saved_at'))
                or any(not pair(value[k]) for k in ('total','undated','session'))
                or not integer(value['gaps']) or not isinstance(value['days'], dict)
                or len(value['days']) > 400):return False
        for key, count in value['days'].items():
            if datetime.strptime(key, '%Y-%m-%d').date().isoformat() != key or not pair(count):return False
        for i in (0,1):
            if (sum(n[i] for n in value['days'].values()) + value['undated'][i] > value['total'][i]
                    or value['session'][i] > value['total'][i]):return False
        last = value['last']
        if last is not None:
            expected = {'boot','interface','index','rx','tx'} | ({'source','epoch'} if value['version']==2 else set())
            if set(last) != expected:return False
            reading(last)
        return True
    except (TypeError, ValueError, KeyError, AttributeError, OverflowError):return False


def counts(value):
    return {'download_bytes':value[0], 'upload_bytes':value[1], 'total_bytes':sum(value)}


def public(state, now, *, status='unknown', error=None):
    date = day(now);daily = state['days'].get(date, [0,0]);monthly = [0,0]
    for key, value in state['days'].items():
        if date and key[:7] == date[:7]:monthly = [a+b for a,b in zip(monthly,value)]
    return {'available':True, 'status':status, 'error':error, 'started_at':state['started_at'],
            'sampled_at':state['sampled_at'], 'saved_at':state['saved_at'],
            'today':counts(daily) if date else None, 'month':counts(monthly) if date else None,
            'session':counts(state['session']), 'total':counts(state['total']),
            'undated':counts(state['undated']), 'continuity_gaps':state['gaps'],
            'timezone':'Asia/Ho_Chi_Minh', 'scope':'all_sims_on_this_usb',
            'source':'modem_bearer_counters' if (state.get('last') or {}).get('source')=='modem_bearer' else 'cellular_interface_counters',
            'checkpoint_seconds':CHECKPOINT}


class Collector:
    def __init__(self, directory=Path('/var/lib/openstick'), runtime=Path('/run/openstick'),
                 *, source=None, clock=time.time, monotonic=time.monotonic):
        self.path = Path(directory) / NAME;self.runtime = Path(runtime) / NAME
        self.source = source or CounterSource();self.clock = clock;self.monotonic = monotonic
        self.state = None;self.last_flush = None;self.last_wall = None;self.last_mono = None
        self.dirty = False;self.status = 'unknown';self.error = None
        self.observed = False
        self.mutex = threading.RLock()

    def load(self, now):
        if self.state is not None:return
        if self.path.exists() or self.path.is_symlink():
            try:
                value = read_json(self.path)
                if not valid_state(value):raise ValueError()
                if value['version'] == 1:
                    value['version'] = 2
                    value['last'] = reading(value['last'])
                    self.dirty = True
                self.state = value
                self.observed = True
            except (OSError, ValueError, TypeError, UnicodeError):
                raise RuntimeError('USAGE_STATE_INVALID') from None
        else:
            self.state = {'version':2, 'started_at':now, 'sampled_at':now, 'saved_at':0,
                          'total':[0,0], 'undated':[0,0], 'days':{}, 'last':None,
                          'session':[0,0], 'gaps':0}
            self.dirty = True

    def flush(self, force=False):
        with self.mutex:return self._flush(force)

    def _flush(self, force=False):
        if not self.state or not self.dirty or not self.observed:return
        mono = self.monotonic()
        if not force and self.last_flush is not None and mono-self.last_flush < CHECKPOINT:return
        previous = self.state['saved_at'];self.state['saved_at'] = self.clock()
        try:atomic(self.path, self.state, durable=True)
        except (OSError, ValueError):
            self.state['saved_at'] = previous;self.error = 'USAGE_SAVE_FAILED';return
        self.last_flush = mono;self.dirty = False

    def sample(self):
        with self.mutex:return self._sample()

    def checkpoint(self):
        if not self.mutex.acquire(timeout=12):return False
        try:
            self._flush(force=True)
            return not self.observed or not self.dirty
        finally:self.mutex.release()

    def _sample(self):
        now = self.clock();mono = self.monotonic()
        if not stamp(now):raise ValueError('CLOCK_INVALID')
        try:self.load(now)
        except RuntimeError:
            atomic(self.runtime, {'available':False,'error':'USAGE_STATE_INVALID','sampled_at':now});return
        self.error = None
        try:sample = reading(self.source.read())
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            self.error = 'USAGE_SOURCE_UNAVAILABLE';self.status = 'unknown'
            if not self.observed:
                atomic(self.runtime, {'available':False,'error':self.error,'sampled_at':now});return
            self.flush();atomic(self.runtime, public(self.state, now, error=self.error));return
        self.observed = True
        previous = self.state['last'];delta = [0,0];changed = sample != previous
        if sample is None:
            self.status = 'idle';self.state['session'] = [0,0]
        else:
            self.status = 'connected'
            same = (previous and all(sample[k] == previous[k] for k in ('boot','interface','index','source','epoch')))
            if same and all(sample[k] >= previous[k] for k in ('rx','tx')):
                delta = [sample['rx']-previous['rx'], sample['tx']-previous['tx']]
            else:
                self.state['session'] = [0,0]
                if previous:self.state['gaps'] += 1
            self.state['session'] = [a+b for a,b in zip(self.state['session'],delta)]
        self.state['total'] = [a+b for a,b in zip(self.state['total'],delta)]
        stable = ((self.last_wall is None and day(now) == day(self.state['sampled_at']))
                  or self.last_wall is not None and abs((now-self.last_wall)-(mono-self.last_mono)) <= 120)
        date = day(now) if stable else None
        if sum(delta):
            target = self.state['days'].setdefault(date,[0,0]) if date else self.state['undated']
            target[:] = [a+b for a,b in zip(target,delta)]
            if not stable:self.state['gaps'] += 1
        for old in sorted(self.state['days'])[:-400]:del self.state['days'][old]
        self.state['last'] = sample;self.state['sampled_at'] = now
        self.last_wall = now;self.last_mono = mono
        self.dirty = self.dirty or changed or bool(sum(delta))
        self.flush(force=previous is not None and sample is None)
        atomic(self.runtime, public(self.state, now, status=self.status, error=self.error))


def snapshot(root=Path('/'), *, now=time.time):
    """Sanitized telemetry only. Never start a collector from a page request."""
    root = Path(root);current = now()
    if not stamp(current):return {'available':False,'error':'USAGE_STATE_INVALID','stale':True}
    try:
        value = read_json(root / 'run/openstick' / NAME)
        if value.get('available') is not True:
            error = value.get('error')
            return {'available':False, 'error':error if error in ERRORS else 'USAGE_STATE_INVALID', 'stale':True}
        # Rebuild the public projection; do not return unknown runtime fields.
        state = {'started_at':value['started_at'], 'sampled_at':value['sampled_at'],
                 'saved_at':value['saved_at'], 'total':[value['total']['download_bytes'],value['total']['upload_bytes']],
                 'session':[value['session']['download_bytes'],value['session']['upload_bytes']],
                 'undated':[value['undated']['download_bytes'],value['undated']['upload_bytes']],
                 'days':{}, 'gaps':value['continuity_gaps']}
        # RAM carries live period totals. Never use another day's cached total
        # as today's usage while waiting for a new collector sample.
        result = public(state, current, status=value['status'], error=value.get('error'))
        if value.get('source') == 'modem_bearer_counters':result['source'] = 'modem_bearer_counters'
        for key in ('today','month'):
            result[key] = value[key] if day(current) == day(value['sampled_at']) else None
    except FileNotFoundError:
        try:
            state = read_json(root / 'var/lib/openstick' / NAME)
            if not valid_state(state):raise ValueError()
            result = public(state, current)
        except FileNotFoundError:return {'available':False,'error':'USAGE_NOT_STARTED','stale':True}
        except (OSError, ValueError, TypeError, UnicodeError):
            return {'available':False,'error':'USAGE_STATE_INVALID','stale':True}
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, OverflowError, AttributeError):
        return {'available':False,'error':'USAGE_STATE_INVALID','stale':True}
    if (result['status'] not in ('connected','idle','unknown')
            or result['error'] is not None and result['error'] not in ERRORS
            or not all(stamp(result[k]) for k in ('started_at','sampled_at','saved_at'))
            or not integer(result['continuity_gaps'])
            or any(not isinstance(result[k],dict) or not pair([result[k].get('download_bytes'),result[k].get('upload_bytes')])
                   for k in ('total','session','undated'))):
        return {'available':False,'error':'USAGE_STATE_INVALID','stale':True}
    # Rebuild period counts too, keeping malformed or injected data out of API/cache.
    for key in ('today','month'):
        value = result[key]
        if value is not None:
            if not isinstance(value,dict) or not pair([value.get('download_bytes'),value.get('upload_bytes')]):
                return {'available':False,'error':'USAGE_STATE_INVALID','stale':True}
            result[key] = counts([value['download_bytes'],value['upload_bytes']])
    result['stale'] = not (0 <= current-result['sampled_at'] <= STALE) or result['status']=='unknown'
    return result


@contextmanager
def background():
    """No extra daemon. Exclusive lock prevents two workers counting twice."""
    import fcntl
    root = Path('/run/openstick');root.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(root / 'sim-usage.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    stop = threading.Event();collector = Collector();thread = None
    try:
        try:fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield;return
        def collect():
            try:
                while not stop.is_set():
                    try:collector.sample()
                    except Exception:pass  # Fixed categories only; never raw NM output.
                    stop.wait(PERIOD)
            finally:collector.flush(force=True)
        thread = threading.Thread(target=collect, name='sim-usage', daemon=True);thread.start()
        yield collector
    finally:
        stop.set()
        if thread:thread.join(timeout=12)
        os.close(fd)

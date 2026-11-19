"""Explicit, boot-bound normal power requests. Never force or replay shutdown."""
from contextlib import contextmanager, ExitStack, nullcontext
import os
from pathlib import Path
import secrets
import subprocess
import threading
import time
import uuid

from .sim_usage import atomic, read_json, stamp
from .hotspot import boot_id, network_lock
from .modem_device import modem_lock

COMMANDS = {'reboot':['/sbin/reboot'], 'poweroff':['/sbin/poweroff']}
PHASES = {'QUEUED','WAITING_BUSY','DISPATCHING','DISPATCHED','CANCELLED','EXPIRED','UNKNOWN','FAILED'}
ERRORS = {'POWER_UNAVAILABLE','POWER_BUSY','POWER_PENDING','POWER_STATE_INVALID',
          'POWER_SAVE_FAILED','POWER_RESULT_UNKNOWN','ALREADY_ATTEMPTED','POWER_NOT_CANCELLABLE',
          'NETWORK_TRIAL_PENDING','USAGE_CHECKPOINT_FAILED'}


def validate(value):
    try:
        if (not isinstance(value,dict) or set(value)!={'action','operation','confirm'}
                or value['action'] not in (*COMMANDS,'cancel') or value['confirm'] is not True
                or not isinstance(value['operation'],str)
                or str(uuid.UUID(value['operation']))!=value['operation']):raise ValueError()
    except (ValueError,TypeError,AttributeError):raise ValueError('INPUT_INVALID') from None
    return value['action']


@contextmanager
def file_gate(path, shared=False):
    import fcntl
    path=Path(path);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try:fcntl.flock(fd,(fcntl.LOCK_SH if shared else fcntl.LOCK_EX)|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('POWER_BUSY') from None
        yield
    finally:os.close(fd)


def supported():
    try:
        return (os.name=='posix' and os.geteuid()==0 and Path('/proc/1/exe').resolve().name=='busybox'
                and Path('/proc/1/comm').read_text().strip()=='init'
                and any(line.split('#',1)[0].strip().endswith(':/sbin/openrc shutdown')
                        and ':shutdown:' in line for line in Path('/etc/inittab').read_text().splitlines())
                and all(os.access(command[0],os.X_OK) for command in COMMANDS.values()))
    except (OSError,UnicodeError):return False


class DevicePower:
    def __init__(self,directory='/var/lib/openstick',runtime='/run/openstick',*,boot=boot_id,
                 clock=time.monotonic,wall=time.time,available=supported,run=subprocess.run,
                 gate_factory=None,locks=None,sync=os.sync if hasattr(os,'sync') else lambda:None):
        self.directory=Path(directory);self.runtime=Path(runtime);self.path=self.directory/'power-state.json'
        self.boot,self.clock,self.wall,self.available,self.run,self.sync=boot,clock,wall,available,run,sync
        self.gate_factory=gate_factory or (lambda shared=False:file_gate(self.runtime/'power-transition.lock',shared))
        self.locks=locks if locks is not None else (network_lock,modem_lock,lambda:file_gate(self.directory/'site.lock'))

    def read(self):
        if not self.path.exists() and not self.path.is_symlink():return None
        try:
            value=read_json(self.path,4096)
            if (set(value)!={'version','action','operation','boot','worker','phase','after','expires','error'}
                    or type(value['version']) is not int or value['version']!=1
                    or value['action'] not in COMMANDS or value['phase'] not in PHASES
                    or not isinstance(value['boot'],str) or not 0<len(value['boot'])<=128
                    or not isinstance(value['worker'],str) or len(value['worker'])!=32
                    or not stamp(value['after']) or not stamp(value['expires'])
                    or not 0<value['expires']-value['after']<=60
                    or value['error'] is not None and value['error'] not in ERRORS):raise ValueError()
            validate({'action':value['action'],'operation':value['operation'],'confirm':True})
            return value
        except (OSError,ValueError,TypeError,KeyError,UnicodeError):raise RuntimeError('POWER_STATE_INVALID') from None

    def write(self,value):
        try:atomic(self.path,value,durable=True)
        except (OSError,ValueError):raise RuntimeError('POWER_SAVE_FAILED') from None

    def heartbeat(self,worker):
        atomic(self.runtime/'power-worker.json',{'boot':self.boot(),'worker':worker,
               'at':self.clock(),'available':bool(self.available())})

    def ready(self):
        try:
            value=read_json(self.runtime/'power-worker.json',2048)
            if (value['boot']==self.boot() and value['available'] is True
                    and isinstance(value['worker'],str) and len(value['worker'])==32
                    and stamp(value['at']) and 0<=self.clock()-value['at']<=30):return value
        except (OSError,ValueError,KeyError,TypeError,UnicodeError):pass
        return None

    def pending(self):
        value=self.read()
        return bool(value and value['boot']==self.boot() and value['phase'] in
                    ('QUEUED','WAITING_BUSY','DISPATCHING','DISPATCHED')
                    and self.clock()<=value['expires']+45)

    def status(self):
        value=self.read();phase=value['phase'] if value else 'IDLE'
        if value and value['boot']!=self.boot():phase='BOOT_CHANGED'
        elif value and self.clock()>value['expires']+45 and phase in ('DISPATCHING','DISPATCHED'):phase='UNKNOWN'
        return {'available':self.ready() is not None,'pending':self.pending(), 'phase':phase,
                'action':value['action'] if value else None,'operation':value['operation'] if value else None,
                'error':value['error'] if value else None,
                'delay_seconds':max(0,round(value['after']-self.clock())) if value and phase=='QUEUED' else 0,
                'physical_power_cut':False,'hardware_power_cycle_tested':False}

    def conflicts(self):
        if any((self.directory/name).exists() for name in ('setup-pending.json','hotspot-pending.json')):
            raise RuntimeError('NETWORK_TRIAL_PENDING')
        path=self.directory/'usb-tethering-intent.json'
        if path.exists() or path.is_symlink():
            try:
                value=read_json(path,4096)
                if (value.get('request_boot')==self.boot() and value.get('phase') in
                        ('QUEUED','WAITING_MODEM','AWAIT_BOOT')):raise RuntimeError('NETWORK_TRIAL_PENDING')
            except (OSError,ValueError,TypeError,AttributeError):raise RuntimeError('POWER_STATE_INVALID') from None

    @contextmanager
    def activity(self):
        with self.gate_factory(True):
            if self.pending():raise RuntimeError('POWER_PENDING')
            yield

    def call(self,action,**values):
        validate({'action':action,**values})
        with self.gate_factory(False):
            old=self.read()
            if action=='cancel':
                if (not old or old['operation']!=values['operation'] or old['boot']!=self.boot()
                        or old['phase'] not in ('QUEUED','WAITING_BUSY')):raise RuntimeError('POWER_NOT_CANCELLABLE')
                self.write({**old,'phase':'CANCELLED','error':None});return self.status()
            if self.pending():raise RuntimeError('POWER_PENDING')
            worker=self.ready()
            if not worker:raise RuntimeError('POWER_UNAVAILABLE')
            self.conflicts()
            receipts=self.directory/'power-operations';receipts.mkdir(mode=0o700,parents=True,exist_ok=True)
            try:fd=os.open(receipts/(values['operation']+'.json'),os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0),0o600)
            except FileExistsError:raise RuntimeError('ALREADY_ATTEMPTED') from None
            try:
                with os.fdopen(fd,'w') as stream:
                    import json
                    json.dump({'action':action,'created_at':self.wall()},stream);stream.flush();os.fsync(stream.fileno())
                if os.name=='posix':
                    fd=os.open(receipts,os.O_RDONLY)
                    try:os.fsync(fd)
                    finally:os.close(fd)
                now=self.clock()
                self.write({'version':1,'action':action,'operation':values['operation'],'boot':self.boot(),
                            'worker':worker['worker'],'phase':'QUEUED','after':now+5,'expires':now+60,'error':None})
            except (OSError,ValueError):raise RuntimeError('POWER_SAVE_FAILED') from None
            except RuntimeError as error:
                if str(error)=='POWER_SAVE_FAILED':raise RuntimeError('POWER_RESULT_UNKNOWN') from None
                raise
            return self.status()

    def tick(self,worker,checkpoint=lambda:True,stopping=lambda:False):
        self.heartbeat(worker)
        first=self.read()
        if not first or first['boot']!=self.boot() or first['phase'] not in ('QUEUED','WAITING_BUSY','DISPATCHING','DISPATCHED'):return
        with self.gate_factory(False):
            value=self.read()
            if not value or value['boot']!=self.boot() or value['phase'] not in ('QUEUED','WAITING_BUSY','DISPATCHING','DISPATCHED'):return
            def finish(phase,error=None):self.write({**value,'phase':phase,'error':error})
            if value['phase'] in ('DISPATCHING','DISPATCHED'):
                if value['worker']!=worker or self.clock()>value['expires']+45:finish('UNKNOWN','POWER_RESULT_UNKNOWN')
                return
            if value['worker']!=worker:finish('CANCELLED');return
            if self.clock()>value['expires']:finish('EXPIRED','POWER_BUSY');return
            if self.clock()<value['after']:return
            if not self.available():finish('FAILED','POWER_UNAVAILABLE');return
            dispatched=False
            try:
                with ExitStack() as stack:
                    for lock in self.locks:stack.enter_context(lock())
                    self.conflicts()
                    if stopping():finish('CANCELLED');return
                    if not checkpoint():finish('FAILED','USAGE_CHECKPOINT_FAILED');return
                    if stopping():finish('CANCELLED');return
                    if self.clock()>value['expires']:finish('EXPIRED','POWER_BUSY');return
                    finish('DISPATCHING')  # Durable before dispatch; never retry an uncertain command.
                    self.sync()
                    if stopping():finish('CANCELLED');return
                    if self.clock()>value['expires']:finish('EXPIRED','POWER_BUSY');return
                    dispatched=True
                    try:
                        result=self.run(COMMANDS[value['action']],capture_output=True,timeout=10,shell=False)
                        finish('DISPATCHED' if result.returncode==0 else 'UNKNOWN',
                               None if result.returncode==0 else 'POWER_RESULT_UNKNOWN')
                    except (OSError,subprocess.SubprocessError):finish('UNKNOWN','POWER_RESULT_UNKNOWN')
            except (RuntimeError,OSError) as error:
                code=str(error) if isinstance(error,RuntimeError) else 'POWER_SAVE_FAILED'
                if dispatched:finish('UNKNOWN','POWER_RESULT_UNKNOWN')
                elif code in ('NETWORK_BUSY','MODEM_BUSY','POWER_BUSY'):finish('WAITING_BUSY','POWER_BUSY')
                elif code in ERRORS:finish('FAILED',code)
                else:finish('FAILED','POWER_BUSY')


def activity(app):
    backend=app.extensions.get('device_power')
    return backend.activity() if backend else nullcontext()


@contextmanager
def background(checkpoint=lambda:True):
    backend=DevicePower();stop=threading.Event();worker=secrets.token_hex(16)
    lock=file_gate(backend.runtime/'power-worker.lock')
    try:lock.__enter__()
    except RuntimeError:
        yield None;return
    def loop():
        while not stop.is_set():
            try:backend.tick(worker,checkpoint,stop.is_set)
            except Exception:pass  # Never emit command output or baseline identifiers.
            stop.wait(1)
    thread=threading.Thread(target=loop,name='device-power',daemon=True);thread.start()
    try:yield backend
    finally:
        stop.set();thread.join(timeout=15)
        try:
            value=read_json(backend.runtime/'power-worker.json',2048)
            if value.get('worker')==worker:(backend.runtime/'power-worker.json').unlink(missing_ok=True)
        except (OSError,ValueError,TypeError,AttributeError):pass
        lock.__exit__(None,None,None)

"""Bounded recovery of a previously connected, explicitly selected SIM link.

Never opens a first connection, enables NM boot autoconnect, changes radio/AP,
or repeats an activation with an uncertain result. State/receipts stay private.
"""
import json
from pathlib import Path
import time
import uuid

from .hotspot import AP_UUID, CELL_UUID, Hotspot
from .network_startup import load
from .quick_intent import load_intent

NAME = 'cellular-recovery.json'
POLL_SECONDS = 20
MAX_ATTEMPTS = 3
STABLE_SECONDS = 600
PHASES = {'WAITING_CONNECTION', 'CONNECTED', 'WAITING_NETWORK', 'WAITING_DISCONNECT',
          'WAITING_RECONNECT', 'ATTEMPTING', 'RECONNECTED', 'UNKNOWN', 'LIMIT_REACHED'}
ERRORS = {'ACTIVATION_UNCERTAIN', 'RECOVERY_INTERRUPTED', 'RECOVERY_LIMIT', 'STATE_INVALID'}


def selected(directory):
    config, intent = load(directory), load_intent(directory)
    if not config or not intent or not config['data_on'] or intent['airplane'] or not intent['data_allowed']:
        return None
    return config


def read(directory):
    path = Path(directory) / NAME
    if not path.exists() and not path.is_symlink():return None
    try:
        if path.is_symlink() or path.stat().st_size > 4096:raise ValueError()
        v = json.loads(path.read_text())
        if (set(v) != {'version','revision','boot','seen','misses','attempts','phase','error'}
                or type(v['version']) is not int or v['version'] != 1
                or not all(isinstance(v[k],str) and 0 < len(v[k]) <= 128 for k in ('revision','boot'))
                or type(v['seen']) is not bool or type(v['misses']) is not int or not 0 <= v['misses'] <= 2
                or type(v['attempts']) is not int or not 0 <= v['attempts'] <= MAX_ATTEMPTS
                or v['phase'] not in PHASES or v['error'] is not None and v['error'] not in ERRORS):
            raise ValueError()
        return v
    except (OSError,ValueError,TypeError,KeyError,UnicodeError):return {}


def public(directory):
    config = selected(directory)
    if not config:return {'enabled':False,'phase':'PAUSED'}
    value = read(directory)
    if value == {}:return {'enabled':True,'phase':'UNKNOWN','error':'STATE_INVALID'}
    if not value or value['revision'] != config['revision']:
        return {'enabled':True,'phase':'WAITING_CONNECTION','attempts':0,'max_attempts':MAX_ATTEMPTS}
    return {'enabled':True,**{k:value[k] for k in ('phase','attempts','error')},'max_attempts':MAX_ATTEMPTS}


def record_selection(directory, config, boot, *, connected, previous=None, rearm=False):
    """Persist connection proof inside the explicit transaction, under its locks.

    An AP/Wi-Fi save may transfer proof and the existing retry budget, including
    stopped/uncertain outcomes. Only an explicitly successful data-on rearms it.
    No connection/radio request is made here; reads never call this function.
    """
    latest = selected(directory)
    if not latest or latest['revision'] != config['revision']:return
    value = read(directory)
    if value == {}:return  # Preserve corrupt state for inspection, never reset it.
    transferable = bool(value and value['boot']==boot and (
        value['revision']==config['revision'] or previous and previous['data_on']
        and value['revision']==previous['revision']))
    if rearm:
        if not connected:return
        transferable = False
    elif value and value['phase'] in ('ATTEMPTING','UNKNOWN','LIMIT_REACHED') and not transferable:
        return  # A boot/other save cannot clear an uncertain outcome or retry cap.
    if not transferable:
        if not connected:return
        value = {'version':1,'revision':config['revision'],'boot':boot,'seen':True,
                 'misses':0,'attempts':0,'phase':'CONNECTED','error':None}
    else:
        value = dict(value,revision=config['revision'])
        if connected and value['phase'] not in ('ATTEMPTING','UNKNOWN','LIMIT_REACHED'):
            value.update(seen=True,misses=0,phase='CONNECTED',error=None)
    Hotspot.atomic(Path(directory)/NAME,json.dumps(value))


class CellularRecovery:
    def __init__(self, quick, *, clock=time.monotonic, readiness=None, power_pending=None):
        self.quick, self.directory, self.clock = quick, quick.directory, clock
        self.next_poll = 0
        self.healthy_since = self.last_good = None
        if readiness is None:
            from .modem_device import ModemManager
            from contextlib import nullcontext
            readiness = lambda:ModemManager(lock_factory=nullcontext).call('status')
        self.readiness = readiness
        if power_pending is None:
            from .device_power import DevicePower
            power_pending = DevicePower(self.directory).pending
        self.power_pending = power_pending

    def tick(self):
        if self.clock() < self.next_poll:return
        self.next_poll = self.clock() + POLL_SECONDS
        q = self.quick
        # All mutation checks and submission share the same locks as the UI.
        with q.lock_factory(), q.modem_lock_factory():
            config = selected(self.directory)
            if (not config or self.power_pending()
                    or q._read('network-policy.json').get('enabled')
                    or q._read('hotspot.json').get('enabled')
                    or q._read('setup-pending.json') or q._read('hotspot-pending.json')):return
            state = read(self.directory)
            if state == {}:return  # Corrupt state never grants another attempt.
            before = dict(state) if state else None
            if not state or state['revision'] != config['revision']:
                state = {'version':1,'revision':config['revision'],'boot':q.boot(),
                         'seen':False,'misses':0,'attempts':0,'phase':'WAITING_CONNECTION','error':None}

            def write(**changes):
                state.update(changes)
                if state != before:Hotspot.atomic(self.directory / NAME, json.dumps(state))

            if state['phase'] == 'ATTEMPTING':
                write(phase='UNKNOWN',error='RECOVERY_INTERRUPTED');return
            if state['phase'] in ('UNKNOWN','LIMIT_REACHED'):return
            if state['boot'] != q.boot():
                # A new boot must show a real connection before arming again.
                state.update(boot=q.boot(),seen=False,misses=0,phase='WAITING_CONNECTION')
                self.healthy_since = self.last_good = None
            if q.tethering.status().get('reboot_pending'):return
            wifi = q.network.active('wlan0')
            if ((config['wifi_role'] == 'ap' and wifi != AP_UUID)
                    or (config['wifi_role'] == 'off' and wifi is not None)
                    or (config['wifi_role'] == 'station' and wifi != config['station'])):return
            devices = q.network.devices()
            if len(devices) != 1:
                write(phase='WAITING_NETWORK',misses=0);return
            control = devices[0]
            active = q.network.active(control)
            if active not in (None,CELL_UUID):return
            radio = q.radio.status()
            if (not radio.get('sim_ready') or not radio.get('registered')
                    or radio.get('registration_state',1) not in (1,5) or radio.get('ussd_state') in (2,3)):
                self.healthy_since = self.last_good = None
                write(phase='WAITING_NETWORK',misses=0);return
            if active == CELL_UUID and q.network.cellular_interface(control):
                now = self.clock()
                if self.last_good is None or now-self.last_good > 2*POLL_SECONDS:
                    self.healthy_since = now
                self.last_good = now
                if self.healthy_since is not None and now-self.healthy_since >= STABLE_SECONDS:
                    state['attempts'] = 0  # Only continuously observed stability resets the burst budget.
                write(seen=True,misses=0,phase='CONNECTED',error=None);return
            self.healthy_since = self.last_good = None
            if not state['seen']:
                write(phase='WAITING_CONNECTION');return
            # Do not infer disconnect from a missing IP during activation. Both
            # managers must positively report idle/disconnected before retry.
            nm_state = q.network.nm('-g','GENERAL.STATE','device','show',control)
            if active is not None or not nm_state.startswith('30') or radio.get('state') != 8:
                write(phase='WAITING_DISCONNECT',misses=0);return
            modes = self.readiness()
            if modes.get('saved_mode') and modes.get('saved_mode') != modes.get('current_mode'):
                write(phase='WAITING_NETWORK',misses=0);return
            state['misses'] = min(2,state['misses']+1)
            if state['misses'] < 2:
                write(phase='WAITING_RECONNECT');return
            if state['attempts'] >= MAX_ATTEMPTS:
                write(phase='LIMIT_REACHED',error='RECOVERY_LIMIT');return
            fresh_radio, fresh_control = q._preflight()
            if (fresh_control != control or not fresh_radio.get('registered')
                    or fresh_radio.get('state') != 8 or q.network.active(control) is not None
                    or not q.network.nm('-g','GENERAL.STATE','device','show',control).startswith('30')):return
            latest = selected(self.directory)
            if not latest or latest['revision'] != config['revision'] or self.power_pending():return
            receipt = q.journal.begin(str(uuid.uuid4()),'cellular_recovery')
            # Durable submission barrier: worker restart/timeout cannot resend.
            write(phase='ATTEMPTING',attempts=state['attempts']+1)
            try:
                q.network.autoconnect(CELL_UUID,False)
                q.network.up(CELL_UUID)
                if (q.network.active(control) != CELL_UUID
                        or not q.network.cellular_interface(control)
                        or not q.radio.status().get('registered')):
                    raise RuntimeError('ACTIVATION_UNCERTAIN')
                if q.network.active('wlan0') == AP_UUID:q.ap_forwarding(True)
                q.tethering.update_uplinks()
                q.journal.finish(receipt,'COMPLETED')
                write(phase='RECONNECTED',misses=0,error=None)
            except Exception:
                # A failed NM call can have succeeded remotely. Never blindly
                # replay it, reset the modem, change APN or restart the AP.
                q.journal.finish(receipt,'UNKNOWN','ACTIVATION_UNCERTAIN')
                write(phase='UNKNOWN',error='ACTIVATION_UNCERTAIN')

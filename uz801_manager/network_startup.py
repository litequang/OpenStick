"""Durable, explicit network selection and bounded replay after power loss.

The saved data flag alone never grants consent: quick_intent remains the radio
and cellular veto. Status/scan do not save or replay anything. Boot IDs, profile
UUIDs and runtime details remain local; public status exports no identifiers.
"""
import json
from pathlib import Path
import secrets
import time

from .hotspot import AP_UUID, CELL_UUID, Hotspot, boot_id
from .quick_intent import load_intent
from .setup_ap import SETUP_UUID

NAME = 'network-startup.json'
STATE = 'network-startup-state.json'


def load(directory):
    path = Path(directory) / NAME
    if not path.exists():return None
    try:
        if path.is_symlink() or path.stat().st_size > 4096:raise ValueError()
        value = json.loads(path.read_text(encoding='utf-8'))
        if (set(value) != {'version','revision','saved_boot','wifi_role','station','data_on'}
                or value['version'] != 1 or value['wifi_role'] not in ('ap','station','off')
                or type(value['data_on']) is not bool
                or not all(isinstance(value[k],str) and 0 < len(value[k]) <= 128
                           for k in ('revision','saved_boot'))
                or (value['wifi_role'] == 'station' and
                    (not isinstance(value['station'],str) or not 0 < len(value['station']) <= 128
                     or any(ord(c)<32 for c in value['station'])))
                or (value['wifi_role'] != 'station' and value['station'] is not None)):
            raise ValueError()
        return value
    except (OSError,ValueError,TypeError,KeyError):
        return {}  # Present but corrupt never means permission to use data.


def save(directory, *, wifi_role, station=None, data_on=False, boot=None):
    root=Path(directory);root.mkdir(parents=True,exist_ok=True,mode=0o700)
    if (wifi_role not in ('ap','station','off') or type(data_on) is not bool
            or (wifi_role=='station' and (not isinstance(station,str) or not station
                                         or len(station)>128 or any(ord(c)<32 for c in station)))):
        raise ValueError('INPUT_INVALID')
    value={'version':1,'revision':secrets.token_hex(16),'saved_boot':boot or boot_id(),
           'wifi_role':wifi_role,'station':station if wifi_role=='station' else None,'data_on':data_on}
    Hotspot.atomic(root/NAME,json.dumps(value))
    return value


def save_current(quick):
    active=quick.network.active('wlan0')
    role='ap' if active in (AP_UUID,SETUP_UUID) else 'station' if active else 'off'
    intent=load_intent(quick.directory)
    return save(quick.directory,wifi_role=role,station=active,
                data_on=bool(intent and not intent['airplane'] and intent['data_allowed']),
                boot=quick.boot())


def owns_wifi(directory):
    value=load(directory)
    if value is None:return False
    # A separately selected automatic policy takes precedence over manual replay.
    try:policy=json.loads((Path(directory)/'network-policy.json').read_text())
    except (OSError,ValueError):policy={}
    if policy.get('enabled') is True:return False
    return not value or value['wifi_role'] in ('ap','off')


def public(directory):
    value=load(directory)
    if value is None:return {'saved':False}
    if not value:return {'saved':False,'error':'SAVED_NETWORK_INVALID'}
    return {'saved':True,'wifi_role':value['wifi_role'],'data_on':value['data_on']}


class NetworkStartup:
    def __init__(self,quick=None,*,boot=boot_id,clock=time.monotonic,readiness=None):
        if quick is None:
            from .quick_settings import QuickSettings
            quick=QuickSettings()
        self.quick=quick;self.directory=quick.directory
        self.boot,self.clock=boot,clock
        if readiness is None:
            from .modem_device import ModemManager
            from contextlib import nullcontext
            readiness=lambda:ModemManager(lock_factory=nullcontext).call('status')
        self.readiness=readiness

    def tick(self):
        q=self.quick
        with q.lock_factory(),q.modem_lock_factory():
            config=load(self.directory)
            if not config or config['saved_boot']==self.boot():return
            if q._read('setup-pending.json') or q._read('hotspot-pending.json'):return
            if q._read('network-policy.json').get('enabled') or q._read('hotspot.json').get('enabled'):return
            old=q._read(STATE)
            state=old if old.get('boot')==self.boot() and old.get('revision')==config['revision'] else {
                'boot':self.boot(),'revision':config['revision'],'wifi_attempts':0,'data_attempted':False}
            if state.get('done'):return
            def write(**values):
                state.update(values);q.hotspot.write(STATE,state)
            control_list=q.network.devices()
            control=control_list[0] if len(control_list)==1 else None
            active=q.network.active('wlan0')
            role=config['wifi_role']
            if not state.get('wifi_ready'):
                if self.clock()<state.get('next_wifi_attempt',0):return
                if state['wifi_attempts']>=3:
                    write(done=True,error='WIFI_RESTORE_FAILED');return
                write(wifi_attempts=state['wifi_attempts']+1,phase='RESTORING_WIFI')
                try:
                    if role=='ap':
                        q.network.nm('device','set','wlan0','autoconnect','no')
                        q._start_shared_ap(control)
                    elif role=='off':
                        q.network.nm('device','set','wlan0','autoconnect','no')
                        if active==SETUP_UUID:q.setup.network.local_services(False)
                        if active:q.network.down(active)
                        from .ap_clients import for_backend
                        for_backend(q.hotspot).suspend()
                        q.ap_forwarding(True)
                    else:
                        if active==SETUP_UUID:q.setup.network.local_services(False)
                        from .ap_clients import for_backend
                        for_backend(q.hotspot).suspend()
                        q.ap_forwarding(True)
                        if active!=config['station']:q.setup.network.try_station(config['station'])
                        if (q.network.active('wlan0')!=config['station']
                                or not q.setup.network.ready()):raise RuntimeError('WIFI_NOT_CONNECTED')
                        q.network.nm('device','set','wlan0','autoconnect','yes')
                    write(wifi_ready=True,error=None)
                except Exception:
                    write(error='WIFI_RESTORE_FAILED',next_wifi_attempt=self.clock()+15);return
            intent=load_intent(self.directory)
            allowed=bool(config['data_on'] and intent and not intent['airplane'] and intent['data_allowed'])
            if not allowed:
                if role=='ap':q.ap_forwarding(False)
                write(done=True,phase='RESTORED',data_connected=False,error=None);return
            if control is None:
                write(phase='WAITING_MODEM',error='MODEM_UNAVAILABLE');return
            try:
                radio=q.radio.status()
                if radio.get('ussd_state') in (2,3):
                    write(phase='WAITING_MODEM',error='MODEM_BUSY');return
                if not radio.get('sim_ready') or not radio.get('registered'):
                    write(phase='WAITING_SIM',error='SIM_NOT_READY');return
                modes=self.readiness()
                if modes.get('saved_mode') and modes.get('saved_mode')!=modes.get('current_mode'):
                    write(phase='WAITING_RADIO_MODE',error=None);return
                active_cell=q.network.active(control)
                if active_cell not in (None,CELL_UUID):
                    write(done=True,error='CELLULAR_ALREADY_ACTIVE');return
                connected=active_cell==CELL_UUID and bool(q.network.cellular_interface(control))
                if not connected and not state['data_attempted']:
                    # Receipt is durable before activation. After timeout/power
                    # loss never blindly issue another bearer activation this boot.
                    write(data_attempted=True,phase='CONNECTING_SIM')
                    q.network.autoconnect(CELL_UUID,False)
                    q.network.up(CELL_UUID)
                    connected=(q.network.active(control)==CELL_UUID and
                               bool(q.network.cellular_interface(control)))
                if not connected:
                    write(done=True,phase='RESTORE_FAILED',error='DATA_CONNECT_FAILED');return
                if role=='ap':q.ap_forwarding(True)
                q.tethering.update_uplinks()
                write(done=True,phase='RESTORED',data_connected=True,error=None)
            except Exception:
                write(phase='RESTORE_FAILED',error='DATA_CONNECT_FAILED',done=state['data_attempted'])


def main():
    import signal
    from .sim_usage import background
    def terminate(signum, frame):raise SystemExit(0)
    signal.signal(signal.SIGTERM, terminate)
    backend=NetworkStartup()
    from .ap_clients import ApClients
    clients=ApClients()
    with background():
        while True:
            try:clients.tick()
            except Exception:pass
            try:backend.tick()
            except Exception:pass  # Never log identifiers, credentials or subprocess output.
            time.sleep(5)


if __name__=='__main__':main()

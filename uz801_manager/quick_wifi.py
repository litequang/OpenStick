"""Explicit station/AP transitions for Quick Settings, without cellular changes."""
import hashlib
import re
import time
import uuid
from .hotspot import AP_UUID, CELL_UUID
from .network_policy import PolicyNetwork
from .setup_ap import SETUP_UUID


class QuickWifi:
    def __init__(self, quick, *, connect=None, sleep=time.sleep):
        self.quick = quick
        self.network = quick.network
        self.setup = quick.setup
        self.connect = connect or self._connect
        self.sleep = sleep

    def _scan_after_ap(self):
        # This board returns a successful but empty first list after AP down.
        # Give its station scan cache a bounded warm-up; never reset the radio.
        for attempt in range(3):
            if attempt:self.sleep(2)
            self.setup.capture_networks(True)
            if self.setup.state().get('networks'):break

    def _connect(self, ssid, password):
        # Caller already holds the network lock. Do not start the legacy worker,
        # which would try to acquire that lock again in a different process.
        from .hosting import station_profile
        path = self.setup.profiles / ('openstick-'+hashlib.sha256(ssid.encode()).hexdigest()[:16]+'.nmconnection')
        previous = path.read_text() if path.is_file() else ''
        match = re.search(r'^uuid=([0-9a-f-]{36})$', previous, re.M)
        identity = str(uuid.UUID(match[1])) if match else str(uuid.uuid4())
        self.setup.atomic(path, station_profile(ssid, password, identity))
        self.network.load(path)
        self.network.up(identity)

    def profiles(self):return PolicyNetwork(run=self.network.run).profiles()

    def options(self):
        active = self.network.active('wlan0')
        profiles = self.profiles()
        state = self.setup.state()
        return {'connected': active not in (None, AP_UUID, SETUP_UUID),
                'ssid': next((p['ssid'] for p in profiles if p['uuid'] == active), None),
                'saved': [{'ssid': p['ssid'], 'active': p['uuid'] == active} for p in profiles],
                'networks': [{key: n[key] for key in ('ssid', 'signal', 'security') if key in n}
                             for n in state.get('networks', [])[:100] if isinstance(n, dict)],
                'scan_at': state.get('scan_at'),
                'ap_active': active in (AP_UUID, SETUP_UUID)}

    def _pause(self, previous):
        self.network.nm('device', 'set', 'wlan0', 'autoconnect', 'no')
        if previous == SETUP_UUID:self.setup.network.local_services(False)
        if previous:self.network.down(previous)
        self.quick.ap_forwarding(True)  # Do not leave an AP guard on the station path.

    def _restore(self, previous, autoconnect, blocked):
        if previous:
            if previous == SETUP_UUID:self.setup.network.local_services(True)
            if previous in (SETUP_UUID, AP_UUID):self.quick.ap_forwarding(not blocked)
            self.network.up(previous)
        self.network.nm('device', 'set', 'wlan0', 'autoconnect',
                        'yes' if autoconnect == 'yes' else 'no')

    def call(self, action, values):
        previous = self.network.active('wlan0')
        old_auto = self.network.nm('-g', 'GENERAL.AUTOCONNECT', 'device', 'show', 'wlan0')
        from .quick_intent import data_allowed, radio_allowed
        connected = any(self.network.active(d) == CELL_UUID and self.network.cellular_interface(d)
                        for d in self.network.devices())
        blocked = not (data_allowed(self.quick.directory) and radio_allowed(self.quick.directory) and connected)
        if action == 'wifi_scan' and previous not in (SETUP_UUID, AP_UUID):
            try:self.setup.capture_networks(True)
            except Exception:raise RuntimeError('WIFI_SCAN_FAILED') from None
            return
        if action == 'wifi_off':
            if previous in (None, SETUP_UUID, AP_UUID):raise RuntimeError('WIFI_NOT_CONNECTED')
            self.quick._stop_automation()
            config = self.quick._read('setup-ap.json');config['enabled'] = False
            self.setup.write('setup-ap.json', config)
            self._pause(previous)
            return
        if action == 'wifi_auto' and previous not in (None, SETUP_UUID, AP_UUID):return
        target = None
        snapshot = None
        if action == 'wifi_saved':
            target = next((p['uuid'] for p in self.profiles() if p['ssid'] == values['ssid']), None)
            if not target:raise RuntimeError('WIFI_PROFILE_NOT_FOUND')
            if target == previous and self.setup.network.ready():return
        if action == 'wifi_connect':
            name = 'openstick-'+hashlib.sha256(values['ssid'].encode()).hexdigest()[:16]+'.nmconnection'
            path = self.setup.profiles / name
            if path.is_symlink():raise RuntimeError('WIFI_CONNECT_FAILED')
            snapshot = {'name': name, 'previous': path.read_text() if path.is_file() else None}
        if action != 'wifi_scan':self.quick._stop_automation()
        succeeded = False
        try:
            self._pause(previous)
            if previous in (SETUP_UUID, AP_UUID):self._scan_after_ap()
            if action == 'wifi_scan':
                pass  # AP scan performed above; non-AP scan returned earlier.
            else:
                if action == 'wifi_auto':
                    target = self.setup.try_saved()  # Scan, priority/hidden profiles, bounded fallback.
                    if not target:raise RuntimeError('WIFI_SAVED_NOT_FOUND')
                elif action == 'wifi_saved':self.setup.network.try_station(target)
                elif action == 'wifi_connect':
                    self.connect(values['ssid'], values['password'])
                    target = self.network.active('wlan0')
                if not self.setup.network.ready() or self.network.active('wlan0') != target:
                    raise RuntimeError('WIFI_CONNECT_FAILED')
                self.network.nm('device', 'set', 'wlan0', 'autoconnect', 'yes')
                config = self.quick._read('setup-ap.json');config['previous_wifi'] = target
                self.setup.write('setup-ap.json', config)
                self.quick.tethering.update_uplinks()
                succeeded = True
        except Exception as error:
            known = {'WIFI_SAVED_NOT_FOUND', 'WIFI_CONNECT_FAILED', 'WIFI_AUTH_REQUIRED',
                     'WIFI_TIMEOUT', 'WIFI_NOT_FOUND', 'NETWORK_BUSY', 'WIFI_SCAN_FAILED'}
            raise RuntimeError(str(error) if str(error) in known else
                               'WIFI_SCAN_FAILED' if action == 'wifi_scan' else 'WIFI_CONNECT_FAILED') from None
        finally:
            if not succeeded:
                try:
                    current = self.network.active('wlan0')
                    if current and current != previous:self.network.down(current)
                    if snapshot:
                        path = self.setup.profiles / snapshot['name']
                        if path.is_symlink():raise RuntimeError('WIFI_RESTORE_FAILED')
                        if path.is_file() and path.read_text() != snapshot['previous']:
                            identity = re.search(r'^uuid=([0-9a-f-]{36})$', path.read_text(), re.M)
                            if not identity:raise RuntimeError('WIFI_RESTORE_FAILED')
                            snapshot['identity'] = str(uuid.UUID(identity[1]))
                            self.setup.restore_profile(snapshot)
                    self._restore(previous, old_auto, blocked)
                except Exception:raise RuntimeError('WIFI_RESTORE_FAILED') from None

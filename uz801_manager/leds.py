"""Opt-in controls for the three case LEDs, using fixed Linux LED class paths."""
from contextlib import contextmanager
import copy
import ipaddress
import json
import os
from pathlib import Path
import re
import tempfile
import time


LEDS = {'red': ('red:power', 'Đỏ'), 'green': ('green:wlan', 'Xanh lá'),
        'blue': ('blue:wan', 'Xanh dương')}
MODES = {'default': None, 'off': 'none', 'on': 'none', 'blink': 'timer',
         'heartbeat': 'heartbeat', 'wifi_on': 'phy0radio',
         'wifi_link': 'phy0assoc', 'wifi_rx': 'phy0rx', 'wifi_tx': 'phy0tx'}
NETWORK_STATES = ('setup_hotspot', 'sim_hotspot', 'wifi_station', 'cellular_data', 'offline', 'unknown')
FACTORY = {'mode': 'default', 'on_ms': 500, 'off_ms': 500}


def default_network_rules():
    rules = {state: {color: {**FACTORY, 'mode': 'off'} for color in LEDS} for state in NETWORK_STATES}
    rules['setup_hotspot']['red'].update(mode='blink', on_ms=150, off_ms=150)
    rules['sim_hotspot']['green']['mode'] = 'on'
    rules['sim_hotspot']['blue']['mode'] = 'blink'
    rules['wifi_station']['green']['mode'] = 'on'
    rules['cellular_data']['blue']['mode'] = 'on'
    rules['offline']['red'].update(mode='blink', on_ms=1000, off_ms=1000)
    return rules


def validate_network_request(value):
    if (not isinstance(value, dict) or set(value) != {'action', 'enabled', 'rules', 'confirm'}
            or value['action'] != 'configure_network' or value['confirm'] is not True
            or type(value['enabled']) is not bool or not isinstance(value['rules'], dict)
            or set(value['rules']) != set(NETWORK_STATES)):raise ValueError('INPUT_INVALID')
    for settings in value['rules'].values():
        validate_led_request({'action': 'configure', 'settings': settings, 'confirm': True})
        if set(settings) != set(LEDS) or any(item['mode'] not in ('off', 'on', 'blink') for item in settings.values()):
            raise ValueError('INPUT_INVALID')
    return copy.deepcopy(value['rules'])


def select_network_state(state):
    # A SIM AP also has cellular data, but its complete three-color recipe
    # takes priority. Never mix conflicting recipes from concurrent roles.
    for key in NETWORK_STATES[:3]:
        if state.get(key) is True:return key
    if state.get('cellular_data') is True and all(state.get(key) is False for key in NETWORK_STATES[:3]):return 'cellular_data'
    return 'offline' if all(state.get(key) is False for key in NETWORK_STATES[:4]) else 'unknown'


def network_state(network=None):
    """Read link roles only: no activation, modem lock, scan or paid probe."""
    from .hotspot import AP_UUID, Network
    from .setup_ap import SETUP_UUID
    network = network or Network()
    state = {key: None for key in NETWORK_STATES[:4]}
    try:
        rows = network.nm('-g', 'GENERAL.STATE,GENERAL.CON-UUID,IP4.ADDRESS',
                          'device', 'show', 'wlan0', timeout=3).splitlines()
        ready = bool(rows and rows[0].startswith('100') and len(rows) >= 3
                     and ipaddress.IPv4Interface(rows[2]))
        identity = rows[1] if len(rows) >= 2 else ''
        station = False
        if ready and identity not in (AP_UUID, SETUP_UUID) and re.fullmatch('[0-9a-f-]{36}', identity):
            station = network.nm('-g', '802-11-wireless.mode', 'connection', 'show', 'uuid', identity, timeout=3) == 'infrastructure'
            if not station:station = None
        state.update(wifi_station=station if ready else False, sim_hotspot=ready and identity == AP_UUID,
                     setup_hotspot=ready and identity == SETUP_UUID)
    except Exception:pass
    try:
        rows = network.nm('-t', '-f', 'DEVICE,TYPE', 'device', 'status', timeout=3).splitlines()
        devices = [row.split(':')[0] for row in rows if re.fullmatch('[A-Za-z0-9_.-]{1,32}:gsm', row)]
        if not devices:state['cellular_data'] = False
        elif len(devices) == 1:
            rows = network.nm('-g', 'GENERAL.STATE,GENERAL.IP-IFACE', 'device', 'show', devices[0], timeout=3).splitlines()
            state['cellular_data'] = bool(rows and rows[0].startswith('100') and len(rows) == 2
                                          and re.fullmatch('[A-Za-z0-9_.-]{1,32}', rows[1]))
    except Exception:pass
    return state


@contextmanager
def led_lock():
    import fcntl
    directory = Path('/run/openstick')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(directory / 'led.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('LED_BUSY') from None
        yield
    finally:os.close(fd)


def validate_led_request(value):
    if (not isinstance(value, dict) or set(value) != {'action', 'settings', 'confirm'}
            or value['action'] != 'configure' or value['confirm'] is not True):
        raise ValueError('INPUT_INVALID')
    settings = value['settings']
    if not isinstance(settings, dict) or not settings or not set(settings) <= LEDS.keys():
        raise ValueError('INPUT_INVALID')
    for item in settings.values():
        if (not isinstance(item, dict) or set(item) != {'mode', 'on_ms', 'off_ms'}
                or not isinstance(item['mode'], str) or item['mode'] not in MODES
                or any(type(item[key]) is not int or not 100 <= item[key] <= 5000
                       for key in ('on_ms', 'off_ms'))):
            raise ValueError('INPUT_INVALID')
    return {key: dict(item) for key, item in settings.items()}


class LedSettings:
    def __init__(self, directory='/var/lib/openstick', *, root='/sys/class/leds', lock_factory=led_lock,
                 state_provider=network_state):
        self.directory, self.root = Path(directory), Path(root)
        self.lock_factory = lock_factory
        self.state_provider = state_provider

    def _network(self):
        try:
            value = self.state_provider()
            return value if isinstance(value, dict) else {}
        except Exception:return {}

    @staticmethod
    def _network_config(saved):
        return saved.get('network', {'enabled': False, 'rules': default_network_rules()}) if saved else {'enabled': False, 'rules': default_network_rules()}

    def _settings_for_state(self, saved, state):
        network = self._network_config(saved)
        return network['rules'][select_network_state(state)] if network['enabled'] else saved['settings']

    def _path(self, color, field):
        # Neither the LED node nor an attribute path comes from the request.
        return self.root / LEDS[color][0] / field

    def _read(self, color, field):
        return self._path(color, field).read_text().strip()

    def _write(self, color, field, value):
        self._path(color, field).write_text(str(value) + '\n')

    def _hardware(self):
        result = {}
        for color, (_, label) in LEDS.items():
            if not self._path(color, 'brightness').is_file():continue
            tokens = self._read(color, 'trigger').split()
            active = next((item[1:-1] for item in tokens if item.startswith('[') and item.endswith(']')), None)
            if active is None:
                if len(tokens) != 1:raise RuntimeError('LED_READ_FAILED')
                active = tokens[0]
            triggers = [item.strip('[]') for item in tokens]
            maximum = int(self._read(color, 'max_brightness'))
            brightness = int(self._read(color, 'brightness'))
            if not 1 <= maximum <= 65535 or not 0 <= brightness <= maximum:raise RuntimeError('LED_READ_FAILED')
            snapshot = {'trigger': active, 'brightness': brightness}
            if active == 'timer':
                snapshot.update(on_ms=int(self._read(color, 'delay_on')), off_ms=int(self._read(color, 'delay_off')))
            result[color] = {'label': label, 'maximum': maximum, 'triggers': triggers,
                             'snapshot': snapshot, 'modes': [key for key, trigger in MODES.items()
                                                          if trigger is None or trigger in triggers]}
        return result

    def _saved(self):
        path = self.directory / 'led-settings.json'
        if not path.exists():return None
        try:
            value = json.loads(path.read_text())
            if not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] not in (1, 2):
                raise ValueError()
            expected = {'version', 'settings', 'baseline'} | ({'network'} if value['version'] == 2 else set())
            if set(value) != expected:raise ValueError()
            if value['settings'] or value['version'] == 1:
                validate_led_request({'action': 'configure', 'settings': value['settings'], 'confirm': True})
            elif not isinstance(value['settings'], dict):raise ValueError()
            if value['version'] == 2:
                if not isinstance(value['network'], dict) or set(value['network']) != {'enabled', 'rules'}:raise ValueError()
                validate_network_request({'action': 'configure_network', **value['network'], 'confirm': True})
            baseline = value['baseline']
            if not isinstance(baseline, dict) or not set(value['settings']) <= baseline.keys() or not set(baseline) <= LEDS.keys():raise ValueError()
            if value['version'] == 2 and set(baseline) != set(LEDS):raise ValueError()
            for item in baseline.values():
                if (not isinstance(item, dict) or not set(item) <= {'trigger', 'brightness', 'on_ms', 'off_ms'}
                        or not isinstance(item.get('trigger'), str) or type(item.get('brightness')) is not int
                        or not 0 <= item['brightness'] <= 65535):raise ValueError()
                if item['trigger'] == 'timer' and any(type(item.get(k)) is not int or not 0 <= item[k] <= 3600000
                                                    for k in ('on_ms', 'off_ms')):raise ValueError()
            return value
        except (ValueError, TypeError, KeyError):raise RuntimeError('LED_CONFIG_INVALID') from None

    def _status(self, hardware, saved, state=None):
        settings = saved['settings'] if saved else {}
        network = copy.deepcopy(self._network_config(saved))
        network['state'] = select_network_state(state or {})
        return {'supported': bool(hardware), 'saved': saved is not None,
                'network': network,
                'leds': [{'id': color, 'label': data['label'], 'modes': data['modes'],
                          'settings': settings.get(color, dict(FACTORY)),
                          'lit': data['snapshot']['brightness'] > 0,
                          'controlled': data['snapshot']['trigger'] != 'none'}
                         for color, data in hardware.items()]}

    def status(self):
        state = self._network()
        with self.lock_factory():return self._status(self._hardware(), self._saved(), state)

    def _check(self, hardware, settings, baseline):
        for color, item in settings.items():
            if color not in hardware:raise RuntimeError('LED_UNAVAILABLE')
            if item['mode'] not in hardware[color]['modes']:raise RuntimeError('LED_MODE_UNSUPPORTED')
            if item['mode'] == 'default':
                snapshot = baseline[color]
                if (snapshot['trigger'] not in hardware[color]['triggers']
                        or snapshot['brightness'] > hardware[color]['maximum']):raise RuntimeError('LED_MODE_UNSUPPORTED')

    def _restore(self, color, snapshot, maximum):
        trigger = snapshot['trigger']
        self._write(color, 'trigger', 'none')
        self._write(color, 'brightness', snapshot['brightness'] if trigger == 'none' else maximum)
        if trigger != 'none':self._write(color, 'trigger', trigger)
        if trigger == 'timer':
            self._write(color, 'delay_on', snapshot['on_ms'])
            self._write(color, 'delay_off', snapshot['off_ms'])

    def _apply(self, hardware, settings, baseline, only_changed=False):
        for color, item in settings.items():
            if item['mode'] == 'default':
                self._restore(color, baseline[color], hardware[color]['maximum'])
                continue
            mode = item['mode']
            snapshot = hardware[color]['snapshot']
            if only_changed:
                if mode in ('on', 'off') and snapshot == {'trigger': 'none', 'brightness': hardware[color]['maximum'] if mode == 'on' else 0}:continue
                if mode == 'blink' and snapshot['trigger'] == 'timer' and all(snapshot.get(k) == item[k] for k in ('on_ms', 'off_ms')):continue
            self._write(color, 'trigger', 'none')
            self._write(color, 'brightness', hardware[color]['maximum'] if mode in ('on', 'blink') else 0)
            trigger = MODES[mode]
            if trigger != 'none':self._write(color, 'trigger', trigger)
            if mode == 'blink':
                self._write(color, 'delay_on', item['on_ms'])
                self._write(color, 'delay_off', item['off_ms'])

    def _persist(self, value):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd, temporary = tempfile.mkstemp(prefix='.led-settings-', dir=self.directory)
        try:
            with os.fdopen(fd, 'w') as output:
                json.dump(value, output);output.flush();os.fsync(output.fileno())
            os.replace(temporary, self.directory / 'led-settings.json')
        finally:
            if os.path.exists(temporary):os.unlink(temporary)

    def _transaction(self, hardware, settings, baseline, persist=None, only_changed=False):
        self._check(hardware, settings, baseline)
        try:
            self._apply(hardware, settings, baseline, only_changed=only_changed)
            if persist is not None:self._persist(persist)
        except Exception:
            failed = False
            for color in settings:
                try:self._restore(color, hardware[color]['snapshot'], hardware[color]['maximum'])
                except Exception:failed = True
            raise RuntimeError('LED_ROLLBACK_FAILED' if failed else 'LED_APPLY_FAILED') from None

    def configure(self, value):
        if isinstance(value, dict) and value.get('action') == 'configure_network':return self.configure_network(value)
        changes = validate_led_request(value)
        with self.lock_factory():
            hardware, saved = self._hardware(), self._saved()
            settings = {**(saved['settings'] if saved else {}), **changes}
            baseline = dict(saved['baseline']) if saved else {}
            for color, data in hardware.items():baseline.setdefault(color, data['snapshot'])
            persist = {'version': 1, 'settings': settings, 'baseline': baseline}
            apply = settings
            if saved and saved['version'] == 2:
                persist.update(version=2, network={**saved['network'], 'enabled': False})
                apply = {color: settings.get(color, dict(FACTORY)) for color in hardware}
            self._transaction(hardware, apply, baseline, persist=persist)
            return self._status(self._hardware(), self._saved())

    def configure_network(self, value):
        rules = validate_network_request(value)
        state = self._network()
        with self.lock_factory():
            hardware, saved = self._hardware(), self._saved()
            baseline = dict(saved['baseline']) if saved else {}
            for color, data in hardware.items():baseline.setdefault(color, data['snapshot'])
            # Validate ALL recipes before any write, including inactive roles.
            for settings in rules.values():self._check(hardware, settings, baseline)
            persist = {'version': 2, 'settings': saved['settings'] if saved else {}, 'baseline': baseline,
                       'network': {'enabled': value['enabled'], 'rules': rules}}
            settings = self._settings_for_state(persist, state)
            if not value['enabled']:settings = {color: settings.get(color, dict(FACTORY)) for color in hardware}
            self._transaction(hardware, settings, baseline, persist=persist)
            return self._status(self._hardware(), self._saved(), state)

    def apply_saved(self):
        previous = self._saved()
        state = self._network() if self._network_config(previous)['enabled'] else {}
        with self.lock_factory():
            saved = self._saved()
            if saved is not None:
                settings = self._settings_for_state(saved, state)
                if saved['version'] == 2 and not saved['network']['enabled']:
                    settings = {color: settings.get(color, dict(FACTORY)) for color in saved['baseline']}
                self._transaction(self._hardware(), settings, saved['baseline'])

    def sync_network(self):
        # Read network metadata outside the LED lock; never take network/modem
        # locks or reapply static modes while the background worker polls.
        saved = self._saved()
        if saved is None or not self._network_config(saved)['enabled']:return
        state = self._network()
        with self.lock_factory():
            saved = self._saved()
            if saved is None or not self._network_config(saved)['enabled']:return
            self._transaction(self._hardware(), self._settings_for_state(saved, state), saved['baseline'], only_changed=True)


def main(once=False):
    backend = LedSettings()
    for attempt in range(10):
        try:backend.apply_saved();break
        except RuntimeError as error:
            if str(error) not in {'LED_BUSY', 'LED_UNAVAILABLE', 'LED_MODE_UNSUPPORTED'} or attempt == 9:raise
            time.sleep(1)
    if once:return
    while True:
        time.sleep(3)
        try:backend.sync_network()
        except Exception:pass  # No raw filesystem/network details in service logs.


if __name__ == '__main__':
    import sys
    main(once='--once' in sys.argv[1:])

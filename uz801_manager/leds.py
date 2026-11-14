"""Opt-in controls for the three case LEDs, using fixed Linux LED class paths."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import time


LEDS = {'red': ('red:power', 'Đỏ'), 'green': ('green:wlan', 'Xanh lá'),
        'blue': ('blue:wan', 'Xanh dương')}
MODES = {'default': None, 'off': 'none', 'on': 'none', 'blink': 'timer',
         'heartbeat': 'heartbeat', 'wifi_on': 'phy0radio',
         'wifi_link': 'phy0assoc', 'wifi_rx': 'phy0rx', 'wifi_tx': 'phy0tx'}
FACTORY = {'mode': 'default', 'on_ms': 500, 'off_ms': 500}


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
    def __init__(self, directory='/var/lib/openstick', *, root='/sys/class/leds', lock_factory=led_lock):
        self.directory, self.root = Path(directory), Path(root)
        self.lock_factory = lock_factory

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
            if not isinstance(value, dict) or set(value) != {'version', 'settings', 'baseline'} or value['version'] != 1:
                raise ValueError()
            validate_led_request({'action': 'configure', 'settings': value['settings'], 'confirm': True})
            baseline = value['baseline']
            if not isinstance(baseline, dict) or not set(value['settings']) <= baseline.keys() or not set(baseline) <= LEDS.keys():raise ValueError()
            for item in baseline.values():
                if (not isinstance(item, dict) or not set(item) <= {'trigger', 'brightness', 'on_ms', 'off_ms'}
                        or not isinstance(item.get('trigger'), str) or type(item.get('brightness')) is not int
                        or not 0 <= item['brightness'] <= 65535):raise ValueError()
                if item['trigger'] == 'timer' and any(type(item.get(k)) is not int or not 0 <= item[k] <= 3600000
                                                    for k in ('on_ms', 'off_ms')):raise ValueError()
            return value
        except (ValueError, TypeError, KeyError):raise RuntimeError('LED_CONFIG_INVALID') from None

    def _status(self, hardware, saved):
        settings = saved['settings'] if saved else {}
        return {'supported': bool(hardware), 'saved': saved is not None,
                'leds': [{'id': color, 'label': data['label'], 'modes': data['modes'],
                          'settings': settings.get(color, dict(FACTORY)),
                          'lit': data['snapshot']['brightness'] > 0,
                          'controlled': data['snapshot']['trigger'] != 'none'}
                         for color, data in hardware.items()]}

    def status(self):
        with self.lock_factory():return self._status(self._hardware(), self._saved())

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

    def _apply(self, hardware, settings, baseline):
        for color, item in settings.items():
            if item['mode'] == 'default':
                self._restore(color, baseline[color], hardware[color]['maximum'])
                continue
            mode = item['mode']
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

    def _transaction(self, hardware, settings, baseline, persist=None):
        self._check(hardware, settings, baseline)
        try:
            self._apply(hardware, settings, baseline)
            if persist is not None:self._persist(persist)
        except Exception:
            failed = False
            for color in settings:
                try:self._restore(color, hardware[color]['snapshot'], hardware[color]['maximum'])
                except Exception:failed = True
            raise RuntimeError('LED_ROLLBACK_FAILED' if failed else 'LED_APPLY_FAILED') from None

    def configure(self, value):
        changes = validate_led_request(value)
        with self.lock_factory():
            hardware, saved = self._hardware(), self._saved()
            settings = {**(saved['settings'] if saved else {}), **changes}
            baseline = dict(saved['baseline']) if saved else {}
            for color, data in hardware.items():baseline.setdefault(color, data['snapshot'])
            self._transaction(hardware, settings, baseline,
                              persist={'version': 1, 'settings': settings, 'baseline': baseline})
            return self._status(self._hardware(), self._saved())

    def apply_saved(self):
        with self.lock_factory():
            saved = self._saved()
            if saved is not None:self._transaction(self._hardware(), saved['settings'], saved['baseline'])


def main():
    for attempt in range(10):
        try:LedSettings().apply_saved();return
        except RuntimeError as error:
            if str(error) not in {'LED_BUSY', 'LED_UNAVAILABLE', 'LED_MODE_UNSUPPORTED'} or attempt == 9:raise
            time.sleep(1)


if __name__ == '__main__':main()

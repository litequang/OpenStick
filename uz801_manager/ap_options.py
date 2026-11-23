"""Shared AP settings; backend acceptance is not physical-client verification."""
import configparser
import re

from .modem_device import system_bus

FIELDS = {'hidden', 'max_clients', 'isolation'}
ERRORS = {'AP_OPTIONS_INVALID', 'AP_OPTIONS_UNAVAILABLE', 'AP_OPTIONS_APPLY_FAILED',
          'AP_OPTIONS_ROLLBACK_FAILED', 'AP_LEGACY_ACTIVE'}
DEFAULTS = {'hidden': False, 'max_clients': 10, 'isolation': False}
SERVICE = 'fi.w1.wpa_supplicant1'
ROOT = '/fi/w1/wpa_supplicant1'
INTERFACE = SERVICE + '.Interface'
PROPS = 'org.freedesktop.DBus.Properties'


def validate(value):
    if (not isinstance(value, dict) or set(value) != FIELDS
            or type(value['hidden']) is not bool or type(value['isolation']) is not bool
            or type(value['max_clients']) is not int or not 1 <= value['max_clients'] <= 32):
        raise ValueError('INPUT_INVALID')
    return dict(value)


def options(config):
    if 'ap_options' not in config:return None  # Preserve legacy behavior until explicitly saved.
    try:return validate(config['ap_options'])
    except ValueError:raise RuntimeError('AP_OPTIONS_INVALID') from None


def wifi_lines(config):
    value = options(config)
    if value is None:return ''
    return f'hidden={str(value["hidden"]).lower()}\nap-isolation={int(value["isolation"])}\n'


def summary(config):
    try:value = options(config)
    except RuntimeError:
        return {'configured': False, **DEFAULTS, 'invalid': True,
                'hardware_verification': 'NOT_TESTED', 'max_clients_range': [1, 32]}
    return {'configured': value is not None, **(value or DEFAULTS),
            'hardware_verification': 'NOT_TESTED', 'max_clients_range': [1, 32]}


class SupplicantAP:
    """Fixed wlan0/property surface, bounded calls; never reads network secrets."""
    def __init__(self, bus_factory=system_bus):self.bus_factory = bus_factory

    def open(self):
        try:bus = self.bus_factory()
        except Exception:raise RuntimeError('AP_OPTIONS_UNAVAILABLE') from None
        try:
            path = str(bus.call_blocking(SERVICE, ROOT, SERVICE, 'GetInterface', 's', ['wlan0'], timeout=8))
            if not re.fullmatch(re.escape(ROOT) + r'/Interfaces/[0-9]+', path):raise ValueError()
            return bus, path
        except Exception:
            bus.close()
            raise RuntimeError('AP_OPTIONS_UNAVAILABLE') from None

    @staticmethod
    def get(bus, path, name):
        value = str(bus.call_blocking(SERVICE, path, PROPS, 'Get', 'ss', [INTERFACE, name], timeout=8))
        if not re.fullmatch(r'[0-9]{1,4}', value):raise ValueError()
        return int(value)

    @staticmethod
    def set_limit(bus, path, limit):
        # wpa_supplicant 2.11 dynamically exposes max_num_sta as STRING, not int.
        bus.call_blocking(SERVICE, path, PROPS, 'Set', 'ssv',
                          [INTERFACE, 'MaxNumSta', str(limit)], timeout=8)

    def activate(self, network, identity, value):
        bus, path = self.open()
        old, changed, attempted = None, False, False
        try:
            old = self.get(bus, path, 'MaxNumSta')
            if not 1 <= old <= 2007:raise ValueError()
            changed = True  # Even a timed-out Set may have reached the daemon.
            self.set_limit(bus, path, value['max_clients'])
            if self.get(bus, path, 'MaxNumSta') != value['max_clients']:raise ValueError()
            # max_num_sta is copied into the AP BSS at creation, not a live cap.
            attempted = True
            network.up(identity)
            if (network.active('wlan0') != identity
                    or self.get(bus, path, 'MaxNumSta') != value['max_clients']
                    or self.get(bus, path, 'ApIsolate') != int(value['isolation'])):
                raise ValueError()
        except Exception:
            failed = False
            try:
                if attempted and network.active('wlan0') == identity:network.down(identity)
            except Exception:failed = True
            try:
                if changed:
                    self.set_limit(bus, path, old)
                    if self.get(bus, path, 'MaxNumSta') != old:raise ValueError()
            except Exception:failed = True
            if failed:raise RuntimeError('AP_OPTIONS_ROLLBACK_FAILED') from None
            raise RuntimeError('AP_OPTIONS_APPLY_FAILED') from None
        finally:bus.close()


def activate(backend, identity):
    """All owned AP activation paths use this; saving/status never calls it."""
    from .hotspot import AP_UUID
    from .setup_ap import SETUP_UUID
    if identity not in (AP_UUID, SETUP_UUID):raise RuntimeError('AP_OPTIONS_INVALID')
    config = backend.read('setup-ap.json')
    if not config.get('ssid'):config = backend.read('hotspot.json')
    value = options(config)
    from .ap_clients import for_backend
    clients = for_backend(backend)
    if value is None:
        clients.prepare_ap()
        try:backend.network.up(identity)
        except Exception:
            if not clients.active():clients.suspend()
            raise
        return
    name = 'openstick-setup' if identity == SETUP_UUID else 'openstick-hotspot'
    path = backend.profiles / (name + '.nmconnection')
    try:
        if path.is_symlink():raise ValueError()
        profile = configparser.ConfigParser(interpolation=None)
        profile.read_string(path.read_text())
        if (profile.get('connection', 'uuid') != identity or profile.get('wifi', 'mode') != 'ap'
                # NM omits default-valued hidden=false when rewriting keyfiles.
                # Absence means false; a saved hidden=true must still fail closed.
                or profile.getboolean('wifi', 'hidden', fallback=False) != value['hidden']
                or profile.getint('wifi', 'ap-isolation') != int(value['isolation'])):raise ValueError()
    except (OSError, ValueError, configparser.Error):
        raise RuntimeError('AP_OPTIONS_INVALID') from None
    clients.prepare_ap()
    try:(backend.ap_backend or SupplicantAP()).activate(backend.network, identity, value)
    except Exception:
        if not clients.active():clients.suspend()
        raise

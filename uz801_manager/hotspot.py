"""Opt-in SIM Internet to a single Wi-Fi AP; no concurrent STA/AP promise."""
from contextlib import contextmanager, nullcontext
import configparser
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import uuid

from .modem_device import ModemManager, modem_lock

AP_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'https://openstick.invalid/hotspot'))
CELL_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'https://openstick.invalid/cellular'))
AP_ADDRESS = '192.168.8.1'
NM = 'org.freedesktop.NetworkManager'
NM_ROOT = '/org/freedesktop/NetworkManager'
DEVICE = NM + '.Device'
PROPS = 'org.freedesktop.DBus.Properties'
HOTSPOT_ERRORS = {'NETWORK_BUSY', 'MODEM_BUSY', 'HOTSPOT_ACTIVE', 'AP_UNSUPPORTED', 'CELLULAR_UNAVAILABLE',
                  'CELLULAR_ALREADY_ACTIVE', 'HOTSPOT_NOT_CONFIGURED', 'SIM_NOT_READY', 'CHECKPOINT_UNAVAILABLE',
                  'CELLULAR_NO_INTERNET', 'CELLULAR_CONNECT_FAILED', 'AP_START_FAILED', 'ROLLBACK_FAILED',
                  'HOTSPOT_START_FAILED', 'HOTSPOT_CONFIRM_EXPIRED', 'POLICY_ACTIVE', 'SETUP_ACTIVE',
                  'HOTSPOT_OPERATION_FAILED'}


def validate_hotspot(value):
    if not isinstance(value, dict) or not isinstance(value.get('action'), str):raise ValueError('INPUT_INVALID')
    action = value['action']
    fields = {'status': set(), 'configure': {'ssid', 'password', 'channel', 'apn', 'confirm'},
              'configure_apn': {'apn', 'confirm'},
              'start': {'confirm', 'cellular_consent', 'switch_wifi'},
              'keep': {'attempt', 'confirm'}, 'stop': {'confirm'}}
    if action not in fields or set(value) != fields[action] | {'action'}:raise ValueError('INPUT_INVALID')
    if action != 'status' and value.get('confirm') is not True:raise ValueError('CONFIRM_REQUIRED')
    if action in ('configure', 'configure_apn'):
        if (not isinstance(value['apn'], str) or len(value['apn']) > 100
                or (value['apn'] and not re.fullmatch('[a-z0-9][a-z0-9.-]*', value['apn']))):
            raise ValueError('INPUT_INVALID')
    if action == 'configure':
        if (not isinstance(value['ssid'], str) or not 1 <= len(value['ssid'].encode()) <= 32
                or any(ord(c) < 32 for c in value['ssid'])
                or not isinstance(value['password'], str) or not 8 <= len(value['password']) <= 63
                or any(ord(c) < 32 or ord(c) > 126 for c in value['password'])
                or type(value['channel']) is not int or value['channel'] not in (1, 6, 11)):
            raise ValueError('INPUT_INVALID')
    if action == 'start' and (value['cellular_consent'] is not True or value['switch_wifi'] is not True):
        raise ValueError('CONSENT_REQUIRED')
    if action == 'keep' and (not isinstance(value['attempt'], str) or not re.fullmatch('[0-9a-f]{32}', value['attempt'])):
        raise ValueError('INPUT_INVALID')
    return action


@contextmanager
def network_lock():
    import fcntl
    directory = Path('/run/openstick')
    directory.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(directory / 'network.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('NETWORK_BUSY') from None
        yield
    finally:os.close(fd)


class Network:
    """Bounded fixed-argument NetworkManager operations; no secret arguments."""
    def __init__(self, run=subprocess.run):self.run = run

    def command(self, args, timeout=12):
        result = self.run(args, capture_output=True, text=True, timeout=timeout, shell=False)
        if result.returncode or len(result.stdout) > 32768:raise RuntimeError('NETWORK_OPERATION_FAILED')
        return result.stdout.strip()

    def nm(self, *args, timeout=12):return self.command(['nmcli', *args], timeout)

    def devices(self):
        rows = self.nm('-t', '-f', 'DEVICE,TYPE', 'device', 'status').splitlines()
        return [row.split(':')[0] for row in rows if row.endswith(':gsm') and re.fullmatch('[A-Za-z0-9_.-]{1,32}:gsm', row)]

    def ap_capable(self):
        return self.nm('-g', 'WIFI-PROPERTIES.AP', 'device', 'show', 'wlan0') == 'yes'

    def active(self, interface):
        raw = self.nm('-g', 'GENERAL.CON-UUID', 'device', 'show', interface)
        return raw if re.fullmatch('[0-9a-f-]{36}', raw) else None

    def cellular_interface(self, control):
        state = self.nm('-g', 'GENERAL.STATE', 'device', 'show', control)
        if not state.startswith('100'):return None
        interface = self.nm('-g', 'GENERAL.IP-IFACE', 'device', 'show', control)
        if not re.fullmatch('[A-Za-z0-9_.-]{1,32}', interface):return None
        return interface

    def internet(self, interface, control):
        if not interface or not re.fullmatch('[A-Za-z0-9_.-]{1,32}', interface):return False
        try:
            # NM may render this array as either separate lines or "A | B".
            values = re.split(r'\s*\|\s*|\r?\n', self.nm('-g', 'IP4.DNS', 'device', 'show', control))
            dns = [str(ipaddress.IPv4Address(v.strip())) for v in values[:4] if v.strip()]
            if not dns:return False
            for url in ('https://cp.cloudflare.com/generate_204', 'https://www.gstatic.com/generate_204'):
                result = self.run(['curl', '--silent', '--show-error', '--fail', '--proxy', '', '--noproxy', '*',
                    '--proto', '=https', '--interface', interface, '--dns-interface', interface,
                    '--dns-servers', ','.join(dns), '--connect-timeout', '5', '--max-time', '8',
                    '--max-filesize', '1024', '--output', '/dev/null', '--write-out', '%{http_code}', url],
                    capture_output=True, text=True, timeout=10, shell=False)
                if result.returncode == 0 and result.stdout == '204':return True
        except (ValueError, OSError, subprocess.SubprocessError, RuntimeError):pass
        return False

    def up(self, identity):self.nm('-w', '55', 'connection', 'up', 'uuid', identity, timeout=60)
    def down(self, identity):self.nm('-w', '20', 'connection', 'down', 'uuid', identity, timeout=25)
    def autoconnect(self, identity, enabled):
        self.nm('connection', 'modify', 'uuid', identity, 'connection.autoconnect', 'yes' if enabled else 'no')

    def load(self, path):self.nm('connection', 'load', str(path))

    def checkpoint(self, interfaces):
        import dbus
        bus = dbus.SystemBus(private=True)
        try:
            manager = dbus.Interface(bus.get_object(NM, NM_ROOT), NM)
            paths = []
            for path in manager.GetDevices():
                props = dbus.Interface(bus.get_object(NM, path), PROPS)
                if str(props.Get(DEVICE, 'Interface')) in interfaces:paths.append(path)
            if len(paths) != len(interfaces):raise RuntimeError('CHECKPOINT_UNAVAILABLE')
            return str(manager.CheckpointCreate(dbus.Array(paths, signature='o'), dbus.UInt32(300), dbus.UInt32(0)))
        finally:bus.close()

    def checkpoint_action(self, path, rollback):
        if not isinstance(path, str) or not re.fullmatch(re.escape(NM_ROOT) + '/Checkpoint/[0-9]+', path):
            raise RuntimeError('CHECKPOINT_UNAVAILABLE')
        import dbus
        bus = dbus.SystemBus(private=True)
        try:
            manager = dbus.Interface(bus.get_object(NM, NM_ROOT), NM)
            if rollback:
                result = manager.CheckpointRollback(dbus.ObjectPath(path))
                if any(int(v) != 0 for v in result.values()):raise RuntimeError('ROLLBACK_FAILED')
            else:manager.CheckpointDestroy(dbus.ObjectPath(path))
        finally:bus.close()

    def extend_checkpoint(self, path):
        if not isinstance(path, str) or not re.fullmatch(re.escape(NM_ROOT) + '/Checkpoint/[0-9]+', path):
            raise RuntimeError('CHECKPOINT_UNAVAILABLE')
        import dbus
        bus = dbus.SystemBus(private=True)
        try:
            manager = dbus.Interface(bus.get_object(NM, NM_ROOT), NM)
            manager.CheckpointAdjustRollbackTimeout(dbus.ObjectPath(path), dbus.UInt32(120))
        finally:bus.close()


def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


class Hotspot:
    def __init__(self, directory='/var/lib/openstick', profiles='/etc/NetworkManager/system-connections',
                 network=None, lock_factory=network_lock, modem_lock_factory=modem_lock,
                 readiness=None, clock=time.monotonic, boot=boot_id, available=shutil.which):
        self.directory, self.profiles = Path(directory), Path(profiles)
        self.network = network or Network()
        self.lock_factory, self.modem_lock_factory = lock_factory, modem_lock_factory
        self.readiness = readiness or (lambda: ModemManager(lock_factory=nullcontext).call('status'))
        self.clock, self.boot, self.available = clock, boot, available

    def read(self, name):
        try:return json.loads((self.directory / name).read_text())
        except (OSError, ValueError):return {}

    def write(self, name, value):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.atomic(self.directory / name, json.dumps(value))

    @staticmethod
    def atomic(path, text):
        temporary = path.with_name(path.name + '.tmp')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w') as output:
            os.chmod(temporary, 0o600)
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
        if os.name != 'nt':
            fd = os.open(path.parent, os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)

    def status(self):
        config, pending = self.read('hotspot.json'), self.read('hotspot-pending.json')
        devices = self.network.devices()
        control = devices[0] if len(devices) == 1 else None
        ap = self.network.active('wlan0') == AP_UUID
        return {'configured': bool(config.get('ssid')), 'ssid': config.get('ssid'), 'channel': config.get('channel'),
                'apn': config.get('apn', ''), 'enabled': config.get('enabled', False),
                'ap_supported': self.network.ap_capable(), 'hotspot_active': ap,
                'cellular_connected': bool(control and self.network.cellular_interface(control)),
                'admin_url': 'http://' + AP_ADDRESS + ':8765', 'pending': bool(pending),
                'attempt': pending.get('attempt'),
                'seconds_remaining': max(0, int(pending.get('expires', 0) - self.clock())) if pending else 0,
                'verification': 'UNVERIFIED' if not config.get('tested') else 'DEVICE_LINKS_VERIFIED_CLIENT_UNVERIFIED'}

    def last_operation(self):
        value = self.read('hotspot-last-operation.json')
        if (isinstance(value, dict) and set(value) == {'action', 'error', 'at'}
                and value['action'] in ('configure', 'configure_apn', 'start', 'keep', 'stop')
                and (value['error'] is None or isinstance(value['error'], str) and value['error'] in HOTSPOT_ERRORS)
                and type(value['at']) in (int, float)):
            return value
        return None

    def record_operation(self, action, error):
        if action not in ('configure', 'configure_apn', 'start', 'keep', 'stop') or (error is not None and error not in HOTSPOT_ERRORS):
            raise ValueError('INPUT_INVALID')
        value = {'action': action, 'error': error, 'at': time.time()}
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.hotspot-result-', dir=self.directory)
        try:
            with os.fdopen(fd, 'w') as output:
                json.dump(value, output);output.flush();os.fsync(output.fileno())
            os.replace(temporary, self.directory / 'hotspot-last-operation.json')
        finally:
            if os.path.exists(temporary):os.unlink(temporary)
        return value

    def call(self, action, **values):
        validate_hotspot({'action': action, **values})
        with self.lock_factory():
            if action == 'status':return self.status()
            from .setup_ap import SETUP_UUID
            if self.network.active('wlan0') == SETUP_UUID or self.read('setup-pending.json'):
                raise RuntimeError('SETUP_ACTIVE')
            if action == 'configure':return self.configure(values)
            if action == 'configure_apn':return self.configure_apn(values['apn'])
            with self.modem_lock_factory():
                if action == 'start':return self.start()
                if action == 'keep':return self.keep(values['attempt'])
                if action == 'stop':return self.stop()
        raise RuntimeError('INPUT_INVALID')

    def configure_apn(self, apn):
        config = self.read('hotspot.json')
        if not config.get('ssid'):raise RuntimeError('HOTSPOT_NOT_CONFIGURED')
        if self.read('hotspot-pending.json') or self.network.active('wlan0') == AP_UUID:
            raise RuntimeError('HOTSPOT_ACTIVE')
        devices = self.network.devices()
        if len(devices) != 1:raise RuntimeError('CELLULAR_UNAVAILABLE')
        if self.network.active(devices[0]):raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
        if config.get('enabled') or self.read('network-policy.json').get('enabled'):
            raise RuntimeError('POLICY_ACTIVE')
        path = self.profiles / 'openstick-cellular.nmconnection'
        if path.is_symlink() or not path.is_file():raise RuntimeError('HOTSPOT_NOT_CONFIGURED')
        original, stored = path.read_text(), (self.directory / 'hotspot.json').read_text()
        profile = configparser.ConfigParser(interpolation=None)
        profile.read_string(original)
        if (profile.get('connection', 'uuid', fallback=None) != CELL_UUID
                or profile.get('connection', 'type', fallback=None) != 'gsm' or not profile.has_section('gsm')):
            raise RuntimeError('HOTSPOT_NOT_CONFIGURED')
        profile.set('gsm', 'auto-config', 'false' if apn else 'true')
        if apn:profile.set('gsm', 'apn', apn)
        else:profile.remove_option('gsm', 'apn')
        output = io.StringIO();profile.write(output, space_around_delimiters=False)
        try:
            self.atomic(path, output.getvalue())
            self.network.load(path)
            config.update(apn=apn, tested=False)
            self.write('hotspot.json', config)
        except Exception:
            try:
                self.atomic(path, original);self.network.load(path)
                self.atomic(self.directory / 'hotspot.json', stored)
            except Exception:raise RuntimeError('ROLLBACK_FAILED') from None
            raise RuntimeError('HOTSPOT_OPERATION_FAILED') from None
        return self.status()

    def configure(self, values):
        if self.read('hotspot-pending.json') or self.network.active('wlan0') == AP_UUID:
            raise RuntimeError('HOTSPOT_ACTIVE')
        if not self.network.ap_capable() or not self.available('dnsmasq'):raise RuntimeError('AP_UNSUPPORTED')
        devices = self.network.devices()
        if len(devices) != 1:raise RuntimeError('CELLULAR_UNAVAILABLE')
        if self.network.active(devices[0]):raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
        self.profiles.mkdir(parents=True, exist_ok=True)
        ssid = values['ssid'].replace('\\', '\\\\').replace(';', '\\;')
        psk = hashlib.pbkdf2_hmac('sha1', values['password'].encode(), values['ssid'].encode(), 4096, 32).hex()
        ap = (f'[connection]\nid=openstick-hotspot\nuuid={AP_UUID}\ntype=wifi\ninterface-name=wlan0\n'
              'autoconnect=false\nautoconnect-priority=100\n\n'
              f'[wifi]\nmode=ap\nband=bg\nchannel={values["channel"]}\nssid={ssid}\n'
              f'\n[wifi-security]\nkey-mgmt=wpa-psk\npsk={psk}\nproto=rsn;\npairwise=ccmp;\ngroup=ccmp;\npmf=1\n'
              f'\n[ipv4]\nmethod=shared\naddress1={AP_ADDRESS}/24\nnever-default=true\n\n[ipv6]\nmethod=disabled\n')
        gsm = 'auto-config=true' if not values['apn'] else 'auto-config=false\napn=' + values['apn']
        cell = (f'[connection]\nid=openstick-cellular\nuuid={CELL_UUID}\ntype=gsm\ninterface-name={devices[0]}\n'
                f'autoconnect=false\n\n[gsm]\n{gsm}\nhome-only=true\n'
                '\n[ipv4]\nmethod=auto\nroute-metric=600\ndns-priority=600\n'
                '\n[ipv6]\nmethod=auto\nroute-metric=600\ndns-priority=600\n')
        # Save/load only. Never activate a profile or change radio settings here.
        for name, data in [('openstick-hotspot', ap), ('openstick-cellular', cell)]:
            path = self.profiles / (name + '.nmconnection')
            self.atomic(path, data)
            self.network.load(path)
        self.write('hotspot.json', {'ssid': values['ssid'], 'channel': values['channel'], 'apn': values['apn'], 'enabled': False})
        return self.status()

    def start(self):
        if self.read('network-policy.json').get('enabled'):raise RuntimeError('POLICY_ACTIVE')
        config = self.read('hotspot.json')
        if not config.get('ssid'):raise RuntimeError('HOTSPOT_NOT_CONFIGURED')
        if self.read('hotspot-pending.json') or self.network.active('wlan0') == AP_UUID:raise RuntimeError('HOTSPOT_ACTIVE')
        ready = self.readiness()
        if not ready.get('registered') or ready.get('sim_locked') or not ready.get('sim_present'):
            raise RuntimeError('SIM_NOT_READY')
        if ready.get('ussd_state') in (2, 3):raise RuntimeError('MODEM_BUSY')
        if not self.network.ap_capable() or not self.available('dnsmasq'):raise RuntimeError('AP_UNSUPPORTED')
        devices = self.network.devices()
        if len(devices) != 1:raise RuntimeError('CELLULAR_UNAVAILABLE')
        control = devices[0]
        if self.network.active(control):raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
        previous = self.network.active('wlan0')
        checkpoint = self.network.checkpoint(['wlan0', control])
        pending = {'checkpoint': checkpoint, 'attempt': secrets.token_hex(16), 'boot': self.boot(),
                   'expires': self.clock() + 285, 'previous_wifi': previous}
        self.write('hotspot-pending.json', pending)
        phase = 'cellular'
        try:
            self.network.nm('radio', 'wwan', 'on')
            self.network.up(CELL_UUID)
            interface = self.network.cellular_interface(control)
            if not self.network.internet(interface, control):raise RuntimeError('CELLULAR_NO_INTERNET')
            # Replace STA only after the SIM has an actual bound Internet probe.
            phase = 'ap'
            self.network.up(AP_UUID)
            if self.network.active('wlan0') != AP_UUID:raise RuntimeError('AP_START_FAILED')
            return self.status()
        except Exception as error:
            try:self.network.checkpoint_action(checkpoint, True)
            except Exception:raise RuntimeError('ROLLBACK_FAILED') from None
            else:(self.directory / 'hotspot-pending.json').unlink(missing_ok=True)
            if str(error) in ('CELLULAR_NO_INTERNET', 'AP_START_FAILED'):raise
            raise RuntimeError('CELLULAR_CONNECT_FAILED' if phase == 'cellular' else 'AP_START_FAILED') from None

    def keep(self, attempt):
        pending = self.read('hotspot-pending.json')
        if (not pending or pending.get('attempt') != attempt or pending.get('boot') != self.boot()
                or self.clock() >= pending.get('expires', 0) or self.network.active('wlan0') != AP_UUID):
            raise RuntimeError('HOTSPOT_CONFIRM_EXPIRED')
        devices = self.network.devices()
        if len(devices) != 1 or not self.network.cellular_interface(devices[0]):
            raise RuntimeError('CELLULAR_NO_INTERNET')
        # A still-live native checkpoint is required before any persistent
        # autoconnect change. Give the short commit enough time to complete.
        try:self.network.extend_checkpoint(pending['checkpoint'])
        except Exception:raise RuntimeError('HOTSPOT_CONFIRM_EXPIRED') from None
        pending['expires'] = self.clock() + 110
        self.write('hotspot-pending.json', pending)
        # Cancel the native rollback only after writing persistent intent and
        # autoconnect. On an exception, leave pending recovery available.
        config = self.read('hotspot.json')
        self.network.autoconnect(CELL_UUID, True)
        self.network.autoconnect(AP_UUID, True)
        config.update(enabled=True, previous_wifi=pending.get('previous_wifi'), tested=True)
        self.write('hotspot.json', config)
        self.network.checkpoint_action(pending['checkpoint'], False)
        (self.directory / 'hotspot-pending.json').unlink(missing_ok=True)
        return self.status()

    def stop(self):
        config = self.read('hotspot.json')
        pending = self.read('hotspot-pending.json')
        if not config.get('ssid'):raise RuntimeError('HOTSPOT_NOT_CONFIGURED')
        self.network.autoconnect(AP_UUID, False)
        self.network.autoconnect(CELL_UUID, False)
        devices = self.network.devices()
        for identity, interface in [(AP_UUID, 'wlan0'), *[(CELL_UUID, d) for d in devices]]:
            if self.network.active(interface) == identity:self.network.down(identity)
        # Preserve saved STA credentials/profiles and restore the prior profile.
        previous = pending.get('previous_wifi') or config.get('previous_wifi')
        config.update(enabled=False)
        self.write('hotspot.json', config)
        if pending:
            try:self.network.checkpoint_action(pending['checkpoint'], False)
            except Exception:pass  # It might already have auto-expired.
            (self.directory / 'hotspot-pending.json').unlink(missing_ok=True)
        restored = False
        if isinstance(previous, str) and re.fullmatch('[0-9a-f-]{36}', previous):
            try:self.network.up(previous);restored = self.network.active('wlan0') == previous
            except Exception:pass
        return {**self.status(), 'wifi_restored': restored}

    def recover_pending(self):
        """Independent service recovery; no action at all when there is no trial."""
        with self.lock_factory():
            pending = self.read('hotspot-pending.json')
            if not pending:return
            if pending.get('boot') == self.boot() and self.clock() < pending.get('expires', 0):return
            # Native rollback normally fired already. Disable trial autoconnect
            # even if a keep operation failed partway through its persistence.
            self.network.autoconnect(AP_UUID, False)
            self.network.autoconnect(CELL_UUID, False)
            try:self.network.checkpoint_action(pending.get('checkpoint'), True)
            except Exception:
                for identity, interface in [(AP_UUID, 'wlan0'), *[(CELL_UUID, d) for d in self.network.devices()]]:
                    if self.network.active(interface) == identity:self.network.down(identity)
                previous = pending.get('previous_wifi')
                if previous and self.network.active('wlan0') != previous:self.network.up(previous)
            config = self.read('hotspot.json')
            config.update(enabled=False)
            self.write('hotspot.json', config)
            (self.directory / 'hotspot-pending.json').unlink(missing_ok=True)


def watch_hotspot():
    backend = Hotspot()
    while True:
        try:backend.recover_pending()
        except Exception:pass  # No SSIDs, credentials or raw modem errors in logs.
        time.sleep(5)


if __name__ == '__main__':watch_hotspot()

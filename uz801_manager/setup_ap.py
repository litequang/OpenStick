"""Local-only, password-protected provisioning AP and durable Wi-Fi handoff."""
import hashlib
import json
from pathlib import Path
import re
import secrets
import time
import uuid

from .hotspot import AP_UUID, AP_ADDRESS, Hotspot, Network
from .lan_access import LanSettings

SETUP_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, 'https://openstick.invalid/setup-ap'))


def validate_setup(value):
    if not isinstance(value, dict):raise ValueError('INPUT_INVALID')
    action = value.get('action')
    fields = {'enable': {'confirm'}, 'disable': {'confirm'}, 'start': {'confirm'},
              'stop': {'confirm'}, 'scan': {'confirm'}, 'connect': {'ssid', 'password', 'confirm'}}
    if action not in fields or set(value) != fields[action] | {'action'}:raise ValueError('INPUT_INVALID')
    if value.get('confirm') is not True:raise ValueError('CONFIRM_REQUIRED')
    if action == 'connect':
        ssid, password = value['ssid'], value['password']
        if (not isinstance(ssid, str) or not 1 <= len(ssid.encode()) <= 32
                or not isinstance(password, str) or not 8 <= len(password) <= 63
                or any(ord(c) < 32 for c in ssid + password)):
            raise ValueError('INPUT_INVALID')
    return action


class SetupNetwork(Network):
    def ready(self):return self.nm('-g', 'GENERAL.STATE', 'device', 'show', 'wlan0').startswith('100')

    def scan(self, refresh):
        from .network_policy import split_fields
        raw = self.nm('-t', '-e', 'yes', '-f', 'SSID,SIGNAL,SECURITY', 'device', 'wifi', 'list',
                      'ifname', 'wlan0', '--rescan', 'yes' if refresh else 'no', timeout=25)
        networks = {}
        for line in raw.splitlines():
            row = split_fields(line)
            if (len(row) != 3 or not row[0] or len(row[0].encode()) > 32
                    or not row[1].isdigit() or not 0 <= int(row[1]) <= 100):continue
            value = {'ssid': row[0], 'signal': int(row[1]), 'security': row[2][:80]}
            if value['signal'] >= networks.get(row[0], {}).get('signal', -1):networks[row[0]] = value
        return sorted(networks.values(), key=lambda n: -n['signal'])[:100]

    def local_services(self, enabled):
        # Separate table never edits the system firewall, USB or SIM hotspot.
        exists = self.run(['nft', 'list', 'table', 'inet', 'openstick_setup'],
                          capture_output=True, timeout=8).returncode == 0
        if enabled:
            if not exists:
                rules = ('table inet openstick_setup {\n chain forward {\n type filter hook forward priority -5; '
                         'policy accept;\n iifname "wlan0" drop;\n oifname "wlan0" drop;\n }\n}\n')
                result = self.run(['nft', '-f', '-'], input=rules, text=True, capture_output=True, timeout=8)
                if result.returncode:raise RuntimeError('SETUP_FIREWALL_FAILED')
            self.command(['rc-service', 'openstick-setup-dhcp', 'start'], timeout=20)
        else:
            self.command(['rc-service', 'openstick-setup-dhcp', 'stop'], timeout=20)
            if exists:self.command(['nft', 'delete', 'table', 'inet', 'openstick_setup'])

class SetupAP(Hotspot):
    def __init__(self, *args, runtime='/run/openstick', lan_ready=None, **kwargs):
        kwargs.setdefault('network', SetupNetwork())
        super().__init__(*args, **kwargs)
        self.runtime = Path(runtime)
        self.lan_ready = lan_ready or (lambda: LanSettings(self.directory).private() is not None)

    def state(self):
        try:value = json.loads((self.runtime / 'setup-state.json').read_text())
        except (OSError, ValueError):value = {}
        return value if value.get('boot') == self.boot() else {}

    def save_state(self, **values):
        self.runtime.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.atomic(self.runtime / 'setup-state.json', json.dumps({
            **self.state(), 'boot': self.boot(), **values}))

    def status(self, credentials=False):
        config, state = self.read('setup-ap.json'), self.state()
        active = self.network.active('wlan0') == SETUP_UUID and self.network.ready()
        result = {'enabled': config.get('enabled') is True, 'configured': bool(config.get('ssid')),
                  'ssid': config.get('ssid'), 'setup_active': active, 'lan_ready': self.lan_ready(),
                  'url': 'http://' + AP_ADDRESS + ':8765/setup',
                  'busy': bool(self.read('setup-pending.json')), 'result': state.get('result'),
                  'error': state.get('error'), 'attempt': state.get('attempt'),
                  'fallback_seconds': 60, 'ipv4': AP_ADDRESS if active else None,
                  'networks': state.get('networks', []), 'scan_at': state.get('scan_at')}
        if credentials:result['password'] = config.get('password')
        return result

    def assert_available(self):
        if not self.lan_ready():raise RuntimeError('LAN_NOT_CONFIGURED')
        if (self.read('hotspot-pending.json')
                or self.network.active('wlan0') == AP_UUID):raise RuntimeError('HOTSPOT_ACTIVE')
        if any(self.network.active(d) for d in self.network.devices()):raise RuntimeError('CELLULAR_ALREADY_ACTIVE')

    def provision(self):
        if not self.lan_ready():raise RuntimeError('LAN_NOT_CONFIGURED')
        if not self.network.ap_capable():raise RuntimeError('AP_UNSUPPORTED')
        config = self.read('setup-ap.json')
        if not config.get('ssid'):
            config = {'ssid': 'OpenStick-Setup-' + secrets.token_hex(2).upper(),
                      'password': secrets.token_urlsafe(15)}
        config['enabled'] = True
        self.write('setup-ap.json', config)
        ssid, password = config['ssid'], config['password']
        psk = hashlib.pbkdf2_hmac('sha1', password.encode(), ssid.encode(), 4096, 32).hex()
        text = (f'[connection]\nid=openstick-setup\nuuid={SETUP_UUID}\ntype=wifi\n'
                'interface-name=wlan0\nautoconnect=false\n\n'
                f'[wifi]\nmode=ap\nband=bg\nchannel=6\nssid={ssid}\n'
                'cloned-mac-address=permanent\npowersave=2\n\n'
                f'[wifi-security]\nkey-mgmt=wpa-psk\npsk={psk}\nproto=rsn;\npairwise=ccmp;\ngroup=ccmp;\npmf=1\n\n'
                f'[ipv4]\nmethod=manual\naddress1={AP_ADDRESS}/24\nnever-default=true\n\n'
                '[ipv6]\nmethod=disabled\n')
        self.profiles.mkdir(parents=True, exist_ok=True)
        path = self.profiles / 'openstick-setup.nmconnection'
        self.atomic(path, text)
        self.network.load(path)

    def call(self, action, **values):
        validate_setup({'action': action, **values})
        with self.lock_factory():
            if self.read('setup-pending.json'):raise RuntimeError('NETWORK_BUSY')
            if action == 'enable':
                self.provision()
                return self.status()
            if action == 'disable':
                config = self.read('setup-ap.json');config['enabled'] = False
                self.write('setup-ap.json', config)
                if self.network.active('wlan0') != SETUP_UUID:return self.status()
                action = 'stop'
            if action in ('start', 'connect', 'scan'):self.assert_available()
            if not self.read('setup-ap.json').get('ssid'):raise RuntimeError('SETUP_NOT_CONFIGURED')
            if action == 'connect' and self.network.active('wlan0') != SETUP_UUID:
                raise RuntimeError('SETUP_NOT_ACTIVE')
            intent = {'action': action, 'attempt': secrets.token_hex(16), 'boot': self.boot(),
                      'after': self.clock() + 3}
            if action == 'connect':
                ssid, password = values['ssid'], values['password']
                name = 'openstick-' + hashlib.sha256(ssid.encode()).hexdigest()[:16] + '.nmconnection'
                path = self.profiles / name
                previous = path.read_text() if path.exists() else None
                match = re.search(r'^uuid=([0-9a-f-]{36})$', previous or '', re.M)
                identity = str(uuid.UUID(match[1])) if match else str(uuid.uuid4())
                escaped = ssid.replace('\\', '\\\\').replace(';', '\\;')
                psk = hashlib.pbkdf2_hmac('sha1', password.encode(), ssid.encode(), 4096, 32).hex()
                text = (f'[connection]\nid={name[:-13]}\nuuid={identity}\ntype=wifi\ninterface-name=wlan0\n'
                        'autoconnect=true\nautoconnect-priority=20\n\n'
                        f'[wifi]\nmode=infrastructure\nssid={escaped}\ncloned-mac-address=permanent\npowersave=2\n\n'
                        f'[wifi-security]\nkey-mgmt=wpa-psk\npsk={psk}\n\n'
                        '[ipv4]\nmethod=auto\nroute-metric=100\n\n[ipv6]\nmethod=auto\nroute-metric=100\n')
                intent.update(name=name, identity=identity, profile=text, previous=previous)
            self.write('setup-pending.json', intent)
            self.save_state(result='QUEUED', error=None, attempt=intent['attempt'])
            return self.status()

    def start(self):
        self.assert_available()
        current = self.network.active('wlan0')
        if current != SETUP_UUID:
            try:self.capture_networks(False)
            except Exception:pass
        if current and current != SETUP_UUID:
            config = self.read('setup-ap.json');config['previous_wifi'] = current
            self.write('setup-ap.json', config)
        # Drop forwarding before AP becomes reachable. No cellular operation.
        self.network.local_services(True)
        try:self.network.up(SETUP_UUID)
        except Exception:
            self.network.local_services(False)
            raise
        self.save_state(result='AP_READY', error=None, missing_since=None)

    def capture_networks(self, refresh):
        own = {self.read('setup-ap.json').get('ssid'), self.read('hotspot.json').get('ssid')}
        rows = [n for n in self.network.scan(refresh) if n['ssid'] not in own]
        self.save_state(networks=rows, scan_at=time.time())

    def scan(self):
        self.assert_available()
        restore = self.network.active('wlan0') == SETUP_UUID
        previous_auto = self.network.nm('-g', 'GENERAL.AUTOCONNECT', 'device', 'show', 'wlan0')
        try:
            if restore:
                self.network.nm('device', 'set', 'wlan0', 'autoconnect', 'no')
                self.network.local_services(False)
                self.network.down(SETUP_UUID)
            self.capture_networks(True)
        finally:
            if restore:
                try:
                    # Preserve scan results; start() only captures cached rows
                    # when transitioning from an existing station connection.
                    self.network.local_services(True)
                    self.network.up(SETUP_UUID)
                finally:
                    self.network.nm('device', 'set', 'wlan0', 'autoconnect',
                                    'yes' if previous_auto == 'yes' else 'no')
        self.save_state(result='SCAN_READY', error=None)

    def stop(self):
        self.network.local_services(False)
        if self.network.active('wlan0') == SETUP_UUID:self.network.down(SETUP_UUID)
        previous = self.read('setup-ap.json').get('previous_wifi')
        if previous:
            try:self.network.up(previous)
            except Exception:pass
        self.save_state(result='STOPPED', error=None, missing_since=self.clock())

    def handoff(self, intent):
        path = self.profiles / intent['name']
        self.atomic(path, intent['profile'])
        self.network.load(path)
        self.network.local_services(False)
        if self.network.active('wlan0') == SETUP_UUID:self.network.down(SETUP_UUID)
        try:
            self.network.up(intent['identity'])
            if self.network.active('wlan0') != intent['identity']:raise RuntimeError('WIFI_CONNECT_FAILED')
        except Exception:
            # Preserve a previously working password even for the same SSID.
            if intent.get('previous') is not None:
                self.atomic(path, intent['previous']);self.network.load(path)
            else:
                try:self.network.nm('connection', 'delete', 'uuid', intent['identity'])
                except Exception:pass
                path.unlink(missing_ok=True)
            self.start()
            self.save_state(result='AP_READY', error='WIFI_CONNECT_FAILED')
            return
        config = self.read('setup-ap.json');config['previous_wifi'] = intent['identity']
        self.write('setup-ap.json', config)
        self.save_state(result='WIFI_CONNECTED', error=None, missing_since=None)

    def tick(self):
        with self.lock_factory():
            intent = self.read('setup-pending.json')
            if intent:
                if intent.get('boot') == self.boot() and self.clock() < intent.get('after', 0):return
                try:
                    if intent.get('boot') != self.boot():
                        # Recover a same-SSID profile overwritten before power loss.
                        if intent.get('action') == 'connect' and intent.get('previous') is not None:
                            path = self.profiles / intent['name']
                            self.atomic(path, intent['previous']);self.network.load(path)
                        self.start()
                        self.save_state(error='SETUP_INTERRUPTED', result='AP_READY')
                    elif intent['action'] == 'start':self.start()
                    elif intent['action'] == 'stop':self.stop()
                    elif intent['action'] == 'scan':self.scan()
                    elif intent['action'] == 'connect':self.handoff(intent)
                except Exception:
                    self.save_state(error='SETUP_OPERATION_FAILED')
                    raise
                finally:(self.directory / 'setup-pending.json').unlink(missing_ok=True)
                return
            active = self.network.active('wlan0')
            if active == SETUP_UUID:
                if not self.lan_ready():self.stop()
                else:self.network.local_services(True)
                return
            config, state = self.read('setup-ap.json'), self.state()
            if not config.get('enabled') or not self.lan_ready():return
            if active:
                self.save_state(missing_since=None)
                return
            try:self.assert_available()
            except RuntimeError:
                self.save_state(missing_since=None)
                return
            since = state.get('missing_since')
            if since is None:self.save_state(missing_since=self.clock())
            elif self.clock() - since >= 60:self.start()


def main():
    backend = SetupAP()
    while True:
        try:backend.tick()
        except Exception:
            # No secrets/raw subprocess errors in logs or API results.
            try:backend.save_state(error='SETUP_OPERATION_FAILED')
            except Exception:pass
        time.sleep(5)


if __name__ == '__main__':main()

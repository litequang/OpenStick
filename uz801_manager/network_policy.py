"""Opt-in Internet selection, separate from the mutually exclusive AP role."""
from contextlib import nullcontext
import json
from pathlib import Path
import re
import time
import uuid

from .hotspot import AP_UUID, CELL_UUID, Hotspot, Network, boot_id, network_lock
from .modem_device import ModemManager, modem_lock

MODES = ('wifi_only', 'sim_only', 'wifi_preferred', 'sim_preferred')


def validate_policy(value):
    if not isinstance(value, dict) or not isinstance(value.get('action'), str):raise ValueError('INPUT_INVALID')
    action = value['action']
    fields = {'status': set(), 'profiles': set(), 'data_off': {'confirm'},
              'configure': {'mode', 'enabled', 'auto_wifi', 'cellular_consent', 'confirm'},
              'wifi_activate': {'uuid', 'confirm'}, 'wifi_forget': {'uuid', 'confirm'}}
    if action not in fields or set(value) != fields[action] | {'action'}:raise ValueError('INPUT_INVALID')
    if action not in ('status', 'profiles') and value['confirm'] is not True:raise ValueError('CONFIRM_REQUIRED')
    if action == 'configure':
        if (value['mode'] not in MODES or any(type(value[k]) is not bool for k in
                ('enabled', 'auto_wifi', 'cellular_consent'))):raise ValueError('INPUT_INVALID')
        if value['enabled'] and value['mode'] != 'wifi_only' and not value['cellular_consent']:
            raise ValueError('CELLULAR_CONSENT_REQUIRED')
    if action.startswith('wifi_'):
        if not isinstance(value['uuid'], str) or str(uuid.UUID(value['uuid'])) != value['uuid']:
            raise ValueError('INPUT_INVALID')
    return action


def split_fields(line):
    parts, word, escaped = [], '', False
    for char in line:
        if escaped:word += char; escaped = False
        elif char == '\\':escaped = True
        elif char == ':':parts.append(word); word = ''
        else:word += char
    return parts + [word]


class PolicyNetwork(Network):
    def profiles(self):
        rows = self.nm('-t', '-e', 'yes', '-f', 'UUID,TYPE', 'connection', 'show').splitlines()
        result = []
        for line in rows[:200]:
            fields = split_fields(line)
            if len(fields) != 2 or fields[1] not in ('wifi', '802-11-wireless'):continue
            identity = fields[0]
            if not re.fullmatch('[0-9a-f-]{36}', identity) or identity == AP_UUID:continue
            # Explicit property allowlist: never query --show-secrets or PSKs.
            raw = self.nm('-g', '802-11-wireless.ssid,802-11-wireless.mode,connection.interface-name',
                          '-e', 'no', 'connection', 'show', 'uuid', identity).splitlines()
            if len(raw) < 2 or raw[1] not in ('infrastructure', ''):continue
            if len(raw) > 2 and raw[2] not in ('', 'wlan0', '--'):continue
            if not raw[0] or len(raw[0].encode()) > 32:continue
            result.append({'uuid': identity, 'ssid': raw[0]})
        return result

    def available(self):
        raw = self.nm('-t', '-e', 'yes', '-f', 'SSID,SIGNAL', 'device', 'wifi',
                      'list', 'ifname', 'wlan0', '--rescan', 'yes')
        result = {}
        for line in raw.splitlines():
            fields = split_fields(line)
            if len(fields) == 2 and fields[1].isdigit() and 0 <= int(fields[1]) <= 100:
                result[fields[0]] = max(int(fields[1]), result.get(fields[0], 0))
        return result

    def route(self, interface, preferred):
        # Runtime-only changes: preserve saved NetworkManager profiles. Negative
        # DNS priority excludes DNS from the standby link (IPv4 and IPv6).
        self.nm('device', 'modify', interface,
                'ipv4.route-metric', '50' if preferred else '900',
                'ipv6.route-metric', '50' if preferred else '900',
                'ipv4.dns-priority', '-50' if preferred else '900',
                'ipv6.dns-priority', '-50' if preferred else '900')


class NetworkPolicy:
    def __init__(self, directory='/var/lib/openstick', *, network=None, lock_factory=network_lock,
                 modem_lock_factory=modem_lock, readiness=None, clock=time.monotonic, boot=boot_id, runtime=None):
        self.directory = Path(directory)
        self.runtime = Path(runtime) if runtime is not None else (Path('/run/openstick') if str(directory) == '/var/lib/openstick' else self.directory)
        self.network = network or PolicyNetwork()
        self.lock_factory, self.modem_lock_factory = lock_factory, modem_lock_factory
        self.readiness = readiness or (lambda: ModemManager(lock_factory=nullcontext).call('status'))
        self.clock, self.boot = clock, boot

    def read(self, name):
        try:
            directory = self.runtime if name == 'network-policy-state.json' else self.directory
            data = json.loads((directory / name).read_text())
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):return {}

    def write(self, name, value):
        directory = self.runtime if name == 'network-policy-state.json' else self.directory
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        Hotspot.atomic(directory / name, json.dumps(value))

    def config(self):
        saved = self.read('network-policy.json')
        config = {'mode': 'wifi_only', 'enabled': False, 'auto_wifi': False, 'cellular_consent': False, **saved}
        # Corrupt/unknown persisted intent must never authorize data usage.
        try:validate_policy({'action': 'configure', 'confirm': True, **config})
        except (ValueError, TypeError):return {'mode': 'wifi_only', 'enabled': False, 'auto_wifi': False, 'cellular_consent': False}
        return config

    def state(self):
        state = self.read('network-policy-state.json')
        return state if state.get('boot') == self.boot() else {'boot': self.boot(), 'source': None, 'streaks': {}, 'last_switch': 0}

    def assert_station_role(self):
        from .setup_ap import SETUP_UUID
        if (self.read('hotspot-pending.json') or self.read('hotspot.json').get('enabled')
                or self.read('setup-pending.json')
                or self.network.active('wlan0') in (AP_UUID, SETUP_UUID)):raise RuntimeError('HOTSPOT_ACTIVE')

    def status(self):
        state = self.state()
        return {'config': self.config(), 'runtime': state, 'verification': 'DEVICE_TEST_REQUIRED',
                'cooldown_seconds': 120, 'health_samples': 3,
                'age_seconds': max(0, int(self.clock() - state['checked_at'])) if 'checked_at' in state else None}

    def saved_wifi(self):
        """Read saved station names on USB/LAN, even while setup AP is active.

        This never requests secrets, changes profiles or probes the Internet.
        """
        with self.lock_factory():
            active = self.network.active('wlan0')
            return {'profiles': [{'ssid': profile['ssid'], 'active': profile['uuid'] == active}
                                 for profile in self.network.profiles()]}

    def call(self, action, **values):
        validate_policy({'action': action, **values})
        with self.lock_factory():
            if action == 'status':return self.status()
            if action == 'profiles':
                active = self.network.active('wlan0')
                return {'profiles': [{**p, 'active': p['uuid'] == active} for p in self.network.profiles()]}
            self.assert_station_role()
            if action == 'data_off':
                with self.modem_lock_factory():
                    active = [self.network.active(d) for d in self.network.devices()]
                    if any(p and p != CELL_UUID for p in active):raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
                    # Stop automation before disconnecting; no Wi-Fi Internet
                    # prerequisite, and never disable the modem/SMS radio.
                    self.write('network-policy.json', {'mode': 'wifi_only', 'enabled': False,
                                                      'auto_wifi': False, 'cellular_consent': False})
                    if self.read('hotspot.json').get('ssid') or CELL_UUID in active:
                        self.network.autoconnect(CELL_UUID, False)
                    if CELL_UUID in active:self.network.down(CELL_UUID)
                    if any(self.network.active(d) for d in self.network.devices()):raise RuntimeError('DATA_DISCONNECT_FAILED')
                    self.write('network-policy-state.json', {'boot': self.boot(), 'source': None,
                        'streaks': {}, 'last_switch': 0, 'health': {'wifi': False, 'sim': False}})
                return {**self.status(), 'data_off': True}
            if action == 'configure':
                previous = self.config()
                config = {k: values[k] for k in ('mode', 'enabled', 'auto_wifi', 'cellular_consent')}
                if config['enabled'] and config['mode'] != 'wifi_only' and not self.read('hotspot.json').get('ssid'):
                    raise RuntimeError('CELLULAR_NOT_CONFIGURED')
                self.write('network-policy.json', config)
                if config['enabled']:
                    try:self._tick(force=True)
                    except Exception:
                        self.write('network-policy.json', previous)
                        raise
                return self.status()
            identity = values['uuid']
            profiles = self.network.profiles()
            if identity not in {p['uuid'] for p in profiles}:raise RuntimeError('PROFILE_NOT_FOUND')
            if action == 'wifi_forget':
                if self.network.active('wlan0') == identity:raise RuntimeError('PROFILE_ACTIVE')
                self.network.nm('connection', 'delete', 'uuid', identity)
                return {'deleted': True}
            if self.config()['enabled'] and self.config()['mode'] == 'sim_only':raise RuntimeError('POLICY_CONFLICT')
            checkpoint = self.network.checkpoint(['wlan0'])
            try:
                self.network.up(identity)
                if not self.network.internet('wlan0', 'wlan0'):raise RuntimeError('WIFI_NO_INTERNET')
                self.network.checkpoint_action(checkpoint, False)
            except Exception:
                self.network.checkpoint_action(checkpoint, True)
                raise RuntimeError('WIFI_SWITCH_FAILED') from None
            state = self.state()
            state.update(last_switch=self.clock(), checked_at=self.clock())
            self.write('network-policy-state.json', state)
            return {'connected': True}

    def tick(self):
        with self.lock_factory():
            if not self.config()['enabled']:return self.status()
            self.assert_station_role()
            return self._tick()

    def _tick(self, force=False):
        config, state, now = self.config(), self.state(), self.clock()
        controls = self.network.devices()
        control = controls[0] if len(controls) == 1 else None
        wifi = self.network.active('wlan0')
        cellular = self.network.active(control) if control else None
        if cellular and cellular != CELL_UUID:raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
        cell_interface = self.network.cellular_interface(control) if cellular else None
        health = {'wifi': bool(wifi and self.network.internet('wlan0', 'wlan0')),
                  'sim': bool(cell_interface and self.network.internet(cell_interface, control))}
        streaks = state.setdefault('streaks', {})
        for name, healthy in health.items():
            previous = streaks.get(name, 0)
            streaks[name] = min(3, max(0, previous) + 1) if healthy else max(-3, min(0, previous) - 1)
        state.update(health=health, checked_at=now)
        current = state.get('source')
        # Three failed samples before leaving an active source. A single failed
        # probe or service restart must not turn cellular data on.
        if not force and current and not health.get(current) and streaks.get(current, 0) > -3:
            self.write('network-policy-state.json', state);return self.status()
        if not force and now - state.get('last_switch', 0) < 120:
            self.write('network-policy-state.json', state);return self.status()
        preferred = 'sim' if config['mode'] in ('sim_only', 'sim_preferred') else 'wifi'
        permitted = ['wifi'] if config['mode'] == 'wifi_only' else ['sim'] if config['mode'] == 'sim_only' else [preferred, 'sim' if preferred == 'wifi' else 'wifi']
        # Stable successful samples before failback to a recovered link.
        if not force and current in permitted and health.get(current) and preferred != current and health.get(preferred) and streaks.get(preferred, 0) < 3:
            self.write('network-policy-state.json', state);return self.status()
        chosen = next((p for p in permitted if health[p]), None)
        need_wifi = config['auto_wifi'] and 'wifi' in permitted and (not health['wifi'])
        need_sim = 'sim' in permitted and not health['sim'] and (preferred == 'sim' or chosen is None)
        if not force and chosen == current and not need_wifi and not need_sim:
            # Keep enforcing exclusive modes if NM reconnected a forbidden link.
            if not ((config['mode'] == 'wifi_only' and cellular) or (config['mode'] == 'sim_only' and wifi)):
                self.write('network-policy-state.json', state);return self.status()
        interfaces = ['wlan0'] + ([control] if control else [])
        checkpoint = self.network.checkpoint(interfaces)
        try:
            if need_wifi:
                available = self.network.available()
                rejected = state.setdefault('wifi_retry_after', {})
                candidates = sorted([p for p in self.network.profiles() if p['ssid'] in available and p['uuid'] != wifi
                                     and rejected.get(p['uuid'], 0) <= now],
                                    key=lambda p: available[p['ssid']], reverse=True)
                # One bounded candidate per cooldown; preserve credentials.
                if candidates:
                    identity = candidates[0]['uuid']
                    try:
                        self.network.up(identity)
                        # A newly selected profile must pass three bound probes.
                        health['wifi'] = all(self.network.internet('wlan0', 'wlan0') for _ in range(3))
                    except Exception:health['wifi'] = False
                    if health['wifi']:wifi = identity
                    else:
                        rejected[identity] = now + 300
                        if wifi:
                            try:self.network.up(wifi)
                            except Exception:wifi = None
                        else:self.network.nm('device', 'disconnect', 'wlan0')
            if need_sim and (preferred == 'sim' or not health['wifi']):
                if not control or not config['cellular_consent']:raise RuntimeError('CELLULAR_UNAVAILABLE')
                with self.modem_lock_factory():
                    ready = self.readiness()
                    if not ready.get('registered') or ready.get('sim_locked') or not ready.get('sim_present'):
                        raise RuntimeError('SIM_NOT_READY')
                    if ready.get('ussd_state') in (2, 3):raise RuntimeError('MODEM_BUSY')
                    self.network.up(CELL_UUID)
                cell_interface = self.network.cellular_interface(control)
                health['sim'] = bool(cell_interface and self.network.internet(cell_interface, control))
                if not health['sim']:raise RuntimeError('CELLULAR_NO_INTERNET')
                cellular = CELL_UUID
            chosen = next((p for p in permitted if health[p]), None)
            if not chosen:raise RuntimeError('NO_INTERNET')
            if config['mode'] == 'wifi_only' and cellular:
                with self.modem_lock_factory():self.network.down(CELL_UUID)
                cellular = None;health['sim'] = False
            if config['mode'] == 'sim_only' and wifi:
                self.network.nm('device', 'disconnect', 'wlan0');wifi = None
                health['wifi'] = False
            if wifi:self.network.route('wlan0', chosen == 'wifi')
            if cellular:self.network.route(control, chosen == 'sim')
            interface, device = ('wlan0', 'wlan0') if chosen == 'wifi' else (cell_interface, control)
            if not self.network.internet(interface, device):raise RuntimeError('NO_INTERNET')
            self.network.checkpoint_action(checkpoint, False)
            state.update(source=chosen, health=health, last_switch=self.clock(), checked_at=self.clock(), error=None)
        except Exception:
            try:self.network.checkpoint_action(checkpoint, True)
            except Exception:raise RuntimeError('ROLLBACK_FAILED') from None
            # A failed trial's probe is not evidence about the restored links.
            state.update(error='SWITCH_FAILED', health={'wifi': False, 'sim': False}, last_switch=self.clock())
            self.write('network-policy-state.json', state)
            raise RuntimeError('SWITCH_FAILED') from None
        self.write('network-policy-state.json', state)
        return self.status()


def watch_policy():
    policy = NetworkPolicy()
    while True:
        try:policy.tick()
        except Exception:pass  # Never log SSIDs, profiles, SIM data or raw errors.
        time.sleep(15)


if __name__ == '__main__':watch_policy()

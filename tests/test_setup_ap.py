from contextlib import nullcontext
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from uz801_manager.hosting import create_hosting_app
from uz801_manager.setup_ap import SETUP_UUID, SetupAP, validate_setup
from uz801_manager.hotspot import AP_UUID


class Network:
    def __init__(self):
        self.wifi = None
        self.cell = None
        self.fail = None
        self.events = []
        self.connected = True
        self.saved = []
    def active(self, interface):return self.wifi if interface == 'wlan0' else self.cell
    def devices(self):return ['modem0']
    def ap_capable(self):return True
    def ready(self):return bool(self.wifi) and self.connected
    def station_url(self):return 'http://192.0.2.2:8765/setup'
    def saved_wifi(self):return self.saved
    def try_station(self, identity):self.up(identity)
    def reboot(self):self.events.append(('reboot', None))
    def scan(self, refresh):
        self.events.append(('scan', refresh))
        if self.fail == 'scan':raise RuntimeError('private error')
        return [{'ssid': 'fixture-network', 'signal': 70, 'security': 'WPA2'}]
    def load(self, path):self.events.append(('load', str(path)))
    def local_services(self, enabled):self.events.append(('services', enabled))
    def up(self, identity):
        self.events.append(('up', identity))
        if self.fail == identity:raise RuntimeError('private modem error')
        self.wifi = identity
        self.connected = True
    def down(self, identity):
        self.events.append(('down', identity))
        if self.wifi == identity:self.wifi = None
    def nm(self, *args):
        self.events.append(('nm', args))
        return 'yes'


@pytest.fixture
def setup(tmp_path):
    clock = [100]
    network = Network()
    backend = SetupAP(directory=tmp_path / 'private', profiles=tmp_path / 'profiles',
                      runtime=tmp_path / 'run', network=network, lock_factory=nullcontext,
                      modem_lock_factory=nullcontext, readiness=lambda: {'ussd_state': 1},
                      clock=lambda: clock[0], boot=lambda: 'boot-a', lan_ready=lambda: True)
    backend.call('enable', confirm=True)
    return backend, network, clock


def test_provision_is_stable_private_and_never_activates_network(setup):
    backend, network, _ = setup
    first = backend.status(credentials=True)
    backend.call('enable', confirm=True)
    assert backend.status(credentials=True)['password'] == first['password']
    assert len(first['password']) >= 16
    assert 'password' not in backend.status()
    assert not any(e[0] == 'up' for e in network.events)
    profile = (backend.profiles / 'openstick-setup.nmconnection').read_text()
    assert 'method=manual' in profile and 'shared' not in profile
    assert first['password'] not in profile
    assert 'autoconnect=false' in profile and 'mode=ap' in profile and 'pmf=1' in profile


def test_fallback_waits_then_starts_without_sim_and_never_activates_cellular(setup):
    backend, network, clock = setup
    backend.tick();clock[0] += 59;backend.tick()
    assert network.wifi is None
    clock[0] += 1;backend.tick()
    assert network.wifi == SETUP_UUID
    assert [e for e in network.events if e[0] == 'up'] == [('up', SETUP_UUID)]
    assert network.events.index(('services', True)) < network.events.index(('up', SETUP_UUID))


def test_connected_wifi_resets_fallback_timer(setup):
    backend, network, clock = setup
    backend.tick();clock[0] += 50;network.wifi = 'station';backend.tick()
    network.wifi = None;clock[0] += 50;backend.tick()
    assert network.wifi is None
    clock[0] += 60;backend.tick()
    assert network.wifi == SETUP_UUID


@pytest.mark.parametrize('role', ['cellular', 'ap', 'trial'])
def test_never_preempts_an_active_sim_hotspot_or_data_session(setup, role):
    backend, network, clock = setup
    if role == 'cellular':network.cell = 'existing-data'
    elif role == 'ap':network.wifi = AP_UUID
    else:backend.write('hotspot-pending.json', {'attempt': 'trial'})
    backend.tick();clock[0] += 100;backend.tick()
    assert network.wifi != SETUP_UUID


def submit(backend, network, clock):
    network.wifi = SETUP_UUID
    result = backend.call('connect', confirm=True, ssid='fixture-network', password='private-password')
    assert result['busy'] is True
    intent = backend.read('setup-pending.json')
    assert 'private-password' not in json.dumps(intent)
    backend.tick()
    assert network.wifi == SETUP_UUID
    clock[0] += 3
    return intent


def test_phone_handoff_survives_http_process_exit_and_succeeds(setup):
    backend, network, clock = setup
    intent = submit(backend, network, clock)
    replacement = SetupAP(directory=backend.directory, profiles=backend.profiles, runtime=backend.runtime,
                          network=network, lock_factory=nullcontext, clock=lambda: clock[0],
                          modem_lock_factory=nullcontext, readiness=lambda: {'ussd_state': 1},
                          boot=lambda: 'boot-a', lan_ready=lambda: True)
    replacement.tick()
    assert backend.read('setup-pending.json')['phase'] == 'await_boot'
    assert network.wifi == SETUP_UUID  # AP stays up until normal shutdown.
    assert network.events.count(('reboot', None)) == 1
    replacement.tick()
    assert network.events.count(('reboot', None)) == 1
    network.wifi = None;replacement.boot = lambda: 'boot-b'
    replacement.tick()
    assert network.wifi == intent['identity']
    assert replacement.status()['result'] == 'WIFI_CONNECTED'
    assert not backend.status()['busy']
    assert replacement.status()['station_url'] == 'http://192.0.2.2:8765/setup'


def test_wrong_password_returns_to_same_ap_and_removes_failed_profile(setup):
    backend, network, clock = setup
    credentials = backend.status(credentials=True)
    intent = submit(backend, network, clock)
    backend.tick();backend.boot = lambda: 'boot-b';network.wifi = None
    network.fail = intent['identity'];backend.tick()
    assert network.wifi == SETUP_UUID
    assert backend.status()['error'] == 'WIFI_CONNECT_FAILED'
    assert backend.status(credentials=True)['password'] == credentials['password']
    assert not (backend.profiles / intent['name']).exists()
    assert not backend.status()['busy']


@pytest.mark.parametrize('power_loss', [False, True])
def test_preserves_working_profile_after_same_ssid_failure_or_power_loss(setup, power_loss):
    backend, network, clock = setup
    first = submit(backend, network, clock)
    backend.tick();backend.boot = lambda: 'boot-b';network.wifi = None;backend.tick()
    path = backend.profiles / first['name']
    good = path.read_text()
    network.wifi = SETUP_UUID
    backend.call('connect', confirm=True, ssid='fixture-network', password='wrong-password')
    clock[0] += 3
    intent = backend.read('setup-pending.json')
    if power_loss:
        backend.atomic(path, intent['profile']);backend.boot = lambda: 'boot-c'
    else:
        backend.tick();backend.boot = lambda: 'boot-c';network.wifi = None
        network.fail = first['identity']
    backend.tick()
    assert path.read_text() == good
    assert network.wifi == SETUP_UUID
    assert not backend.status()['busy']


def test_connect_waits_for_active_ussd_then_reboots_once(setup):
    backend, network, clock = setup
    submit(backend, network, clock)
    backend.readiness = lambda: {'ussd_state': 3}
    backend.tick()
    assert backend.status()['result'] == 'WAITING_MODEM'
    assert backend.status()['busy'] and ('reboot', None) not in network.events
    backend.readiness = lambda: {'ussd_state': 1};backend.tick()
    assert network.events.count(('reboot', None)) == 1


def test_failed_reboot_restores_profile_without_loop(setup):
    backend, network, clock = setup
    intent = submit(backend, network, clock);backend.tick()
    clock[0] += 46;backend.tick()
    assert backend.status()['error'] == 'REBOOT_FAILED'
    assert not backend.status()['busy'] and network.wifi == SETUP_UUID
    assert network.events.count(('reboot', None)) == 1
    assert not (backend.profiles / intent['name']).exists()


def test_busy_connecting_uuid_does_not_prevent_automatic_ap(setup):
    backend, network, clock = setup
    network.wifi = 'retrying-station';network.connected = False
    backend.tick();clock[0] += 61;backend.tick()
    assert network.wifi == SETUP_UUID


def test_saved_network_is_tried_before_automatic_ap_without_internet_probe(setup):
    backend, network, clock = setup
    network.saved = [{'uuid': 'saved-id', 'ssid': 'fixture-network', 'hidden': False}]
    backend.tick();clock[0] += 61;backend.tick()
    assert network.wifi == 'saved-id' and ('up', SETUP_UUID) not in network.events
    assert backend.status()['result'] == 'SAVED_WIFI_CONNECTED'


def test_after_reboot_failure_can_use_another_saved_network(setup):
    backend, network, clock = setup
    intent = submit(backend, network, clock);backend.tick()
    network.saved = [{'uuid': 'other-good', 'ssid': 'fixture-network', 'hidden': False}]
    backend.boot = lambda: 'boot-b';network.wifi = None;network.fail = intent['identity']
    backend.tick()
    assert network.wifi == 'other-good'
    assert backend.status()['result'] == 'SAVED_WIFI_CONNECTED'
    assert network.events.count(('reboot', None)) == 1


def test_lan_password_required_before_provisioning_or_running_ap(setup):
    backend, network, _ = setup
    backend.lan_ready = lambda: False
    with pytest.raises(RuntimeError, match='LAN_NOT_CONFIGURED'):backend.call('enable', confirm=True)
    network.wifi = SETUP_UUID;backend.tick()
    assert network.wifi is None


def test_disable_does_not_reenable_after_wifi_loss(setup):
    backend, network, clock = setup
    backend.call('disable', confirm=True)
    backend.tick();clock[0] += 200;backend.tick()
    assert network.wifi is None


@pytest.mark.parametrize('scan_failure', [False, True])
def test_scan_restores_ap_even_on_failure_without_connecting_to_selected_network(setup, scan_failure):
    backend, network, clock = setup
    network.wifi = SETUP_UUID
    if scan_failure:network.fail = 'scan'
    backend.call('scan', confirm=True);clock[0] += 3
    if scan_failure:
        with pytest.raises(RuntimeError):backend.tick()
    else:backend.tick()
    assert network.wifi == SETUP_UUID
    assert ('scan', True) in network.events
    assert not backend.status()['busy']
    assert ('nm', ('device', 'set', 'wlan0', 'autoconnect', 'yes')) in network.events
    assert all(identity == SETUP_UUID for action, identity in network.events if action == 'up')
    if not scan_failure:assert backend.status()['networks'][0]['ssid'] == 'fixture-network'


def test_no_admin_token_no_credentials_or_actions(setup):
    backend, _, _ = setup
    app = create_hosting_app(usb_portal=True, token='fixture-token', setup_backend=backend, backend=object())
    with app.test_client() as client:
        base = 'http://172.16.42.1'
        assert client.get('/setup', base_url=base).status_code == 200
        for path in ('/api/setup', '/api/setup/credentials', '/api/setup/card'):
            assert client.get(path, base_url=base).status_code == 403
        headers = {'X-OpenStick-Token': 'fixture-token'}
        public = client.get('/api/setup', base_url=base, headers=headers).json
        assert 'password' not in public
        private = client.get('/api/setup/credentials', base_url=base, headers=headers).json
        assert len(private['password']) >= 16
        assert client.get('/api/setup/card', base_url=base, headers=headers).headers['Content-Disposition'].startswith('attachment')
        assert client.get('/api/setup/credentials', base_url=base, headers={**headers, 'Origin': 'http://evil.invalid'}).status_code == 403


@pytest.mark.parametrize('value', [{}, {'action': 'start', 'confirm': False},
    {'action': 'connect', 'confirm': True, 'ssid': 'fixture', 'password': 'short'},
    {'action': 'start', 'confirm': True, 'cellular_consent': True}])
def test_validation_rejects_invalid_or_extra_fields(value):
    with pytest.raises(ValueError):validate_setup(value)


@pytest.mark.skipif(shutil.which('node') is None, reason='Node unavailable')
def test_phone_setup_selection_does_not_submit_until_save():
    subprocess.run(['node', 'tests/setup_ui_fixture.cjs'], check=True, timeout=15)

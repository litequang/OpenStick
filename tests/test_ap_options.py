"""Offline AP policy regression; no USB, system bus, network or real clients."""
import configparser
import pytest

from test_setup_ap import setup
from test_quick_settings import quick
from uz801_manager import ap_options as ap
from uz801_manager.hotspot import AP_UUID, CELL_UUID, Hotspot
from uz801_manager.hosting import create_hosting_app
from uz801_manager.setup_ap import SETUP_UUID, validate_setup

VALUES = {'hidden': True, 'max_clients': 3, 'isolation': True}


def save(backend, **options):
    return backend.call('configure_ap', ssid='Fictional AP', password='', channel=6,
                        confirm=True, **(options or VALUES))


@pytest.mark.parametrize('field,value', [('hidden', 1), ('hidden', 'false'), ('isolation', 0),
    ('isolation', None), ('max_clients', True), ('max_clients', 0), ('max_clients', 33),
    ('max_clients', 1.5), ('max_clients', '10'), ('max_clients', '3\nkey=value')])
def test_reject_invalid_options_before_any_write_or_transport(setup, field, value):
    backend, network, _ = setup
    before = {p: p.read_bytes() for p in backend.profiles.glob('*')}
    config = (backend.directory / 'setup-ap.json').read_bytes()
    network.events.clear()
    with pytest.raises(ValueError, match='INPUT_INVALID'):save(backend, **{**VALUES, field: value})
    assert not network.events
    assert (backend.directory / 'setup-ap.json').read_bytes() == config
    assert all(p.read_bytes() == content for p, content in before.items())


def test_partial_unknown_fields_and_missing_confirmation_are_rejected():
    base = {'action': 'configure_ap', 'ssid': 'Fixture', 'password': '', 'channel': 6, 'confirm': True}
    for extra in [{'hidden': True}, {**VALUES, 'shell': 'ignored'}, {**VALUES, 'confirm': False}]:
        with pytest.raises(ValueError):validate_setup({**base, **extra})


@pytest.mark.parametrize('cap', [1, 10, 32])
def test_stage_and_preserve_advanced_options_without_live_changes(setup, cap):
    backend, network, _ = setup
    original = backend.status(credentials=True)['password']
    network.wifi = AP_UUID; network.cell = CELL_UUID; network.events.clear()
    backend.ap_backend = object()  # Saving must not touch the supplicant.
    state = save(backend, **{**VALUES, 'max_clients': cap})
    assert state['ap_options']['max_clients'] == cap
    assert state['ap_options']['hardware_verification'] == 'NOT_TESTED'
    assert state['ap_options']['hidden'] and state['ap_options']['isolation']
    assert 'password' not in state
    assert network.wifi == AP_UUID and network.cell == CELL_UUID
    assert [e[0] for e in network.events] == ['load']
    path = backend.profiles / 'openstick-setup.nmconnection'
    profile = configparser.ConfigParser(); profile.read(path)
    assert profile.getboolean('wifi', 'hidden')
    assert profile.getint('wifi', 'ap-isolation') == 1
    assert original not in path.read_text() and 'max-clients=' not in path.read_text()
    # An older client updating identity must not reset newly saved options.
    backend.call('configure_ap', ssid='Fictional rename', password='', channel=11, confirm=True)
    assert backend.status()['ap_options']['max_clients'] == cap
    assert backend.status(credentials=True)['password'] == original
    backend.provision()
    assert backend.status()['ap_options']['isolation']


def test_load_failure_rolls_back_advanced_config_and_profile(setup):
    backend, network, _ = setup
    paths = [backend.directory / 'setup-ap.json', backend.profiles / 'openstick-setup.nmconnection']
    before = {p: p.read_bytes() for p in paths}
    calls = []
    def fail_once(path):
        calls.append(path)
        if len(calls) == 1:raise RuntimeError('private-backend-error')
    network.load = fail_once
    with pytest.raises(RuntimeError, match='^SETUP_OPERATION_FAILED$'):save(backend)
    assert len(calls) == 2 and all(p.read_bytes() == content for p, content in before.items())


def test_legacy_autoconnect_cannot_bypass_limit_and_corrupt_options_fail_closed(setup):
    backend, network, _ = setup
    backend.write('hotspot.json', {'enabled': True})
    network.events.clear()
    with pytest.raises(RuntimeError, match='AP_LEGACY_ACTIVE'):save(backend)
    assert not network.events
    config = backend.read('setup-ap.json'); config['ap_options'] = {'max_clients': 0}
    backend.write('setup-ap.json', config)
    assert backend.status()['ap_options']['invalid']
    with pytest.raises(RuntimeError, match='AP_OPTIONS_INVALID'):backend.activate_ap(SETUP_UUID)
    assert not network.events


class Bus:
    def __init__(self):
        self.limit = 128; self.isolation = 1; self.calls = []; self.closed = False
        self.path = ap.ROOT + '/Interfaces/7'; self.fail_set = False
        self.ignore_set = False; self.bad_get = None
    def call_blocking(self, service, path, interface, method, signature, args, **kwargs):
        assert service == ap.SERVICE and kwargs == {'timeout': 8}
        self.calls.append((method, signature, list(args)))
        if method == 'GetInterface':
            assert path == ap.ROOT and interface == ap.SERVICE and args == ['wlan0']
            return self.path
        assert path == self.path and interface == ap.PROPS
        assert args[0] == ap.INTERFACE
        if method == 'Get':
            assert signature == 'ss' and args[1] in ('MaxNumSta', 'ApIsolate')
            return self.bad_get or str(self.limit if args[1] == 'MaxNumSta' else self.isolation)
        assert method == 'Set' and signature == 'ssv' and args[1] == 'MaxNumSta'
        assert type(args[2]) is str, 'The real property is a D-Bus string'
        if not self.ignore_set:self.limit = int(args[2])
        if self.fail_set:
            self.fail_set = False
            raise RuntimeError('private timed-out Set may have succeeded')
    def close(self):self.closed = True


def test_limit_set_and_readback_precede_ap_creation_and_station_is_untouched_on_failure(setup):
    backend, network, _ = setup; bus = Bus()
    backend.ap_backend = ap.SupplicantAP(lambda: bus)
    save(backend); network.events.clear()
    old_up = network.up
    def up(identity):
        assert bus.limit == 3 and bus.calls[-1] == ('Get', 'ss', [ap.INTERFACE, 'MaxNumSta'])
        old_up(identity)
    network.up = up
    backend.activate_ap(SETUP_UUID)
    assert bus.closed and network.wifi == SETUP_UUID and bus.limit == 3
    assert [e[0] for e in network.events] == ['up']


@pytest.mark.parametrize('failure', ['set_timeout', 'ignored_set', 'isolation', 'reset_at_up', 'up_timeout'])
def test_backend_failure_is_private_and_rolls_back_limit_and_new_ap(setup, failure):
    backend, network, _ = setup; bus = Bus()
    backend.ap_backend = ap.SupplicantAP(lambda: bus)
    save(backend); network.events.clear(); network.wifi = 'old-station'
    bus.fail_set = failure == 'set_timeout'; bus.ignore_set = failure == 'ignored_set'
    if failure == 'isolation':bus.isolation = 0
    normal_up = network.up
    def up(identity):
        normal_up(identity)
        if failure == 'reset_at_up':bus.limit = 128
        if failure == 'up_timeout':raise RuntimeError('private error with credentials')
    network.up = up
    with pytest.raises(RuntimeError, match='^AP_OPTIONS_APPLY_FAILED$'):backend.activate_ap(SETUP_UUID)
    assert bus.closed and bus.limit == 128 and network.wifi != SETUP_UUID
    assert not any(e == ('up', CELL_UUID) for e in network.events)
    if failure in ('set_timeout', 'ignored_set'):
        assert not network.events and network.wifi == 'old-station'


def test_missing_backend_wrong_path_bad_property_and_failed_rollback_are_explicit(setup):
    backend, network, _ = setup; save(backend); network.events.clear()
    bus = Bus(); bus.path = '/foreign/path'
    backend.ap_backend = ap.SupplicantAP(lambda: bus)
    with pytest.raises(RuntimeError, match='^AP_OPTIONS_UNAVAILABLE$'):backend.activate_ap(SETUP_UUID)
    assert bus.closed and not network.events
    bus = Bus(); bus.bad_get = 'private identifier'
    backend.ap_backend = ap.SupplicantAP(lambda: bus)
    with pytest.raises(RuntimeError, match='^AP_OPTIONS_APPLY_FAILED$'):backend.activate_ap(SETUP_UUID)
    assert bus.closed and not network.events
    bus = Bus(); bus.isolation = 0
    backend.ap_backend = ap.SupplicantAP(lambda: bus)
    network.down = lambda _: (_ for _ in ()).throw(RuntimeError('private rollback'))
    with pytest.raises(RuntimeError, match='^AP_OPTIONS_ROLLBACK_FAILED$'):backend.activate_ap(SETUP_UUID)
    assert bus.closed and bus.limit == 128, 'restore the limit even if stopping AP fails'


def test_shared_ap_adoption_preserves_credentials_cell_profile_and_advanced_policy(setup):
    backend, network, _ = setup; save(backend)
    original = backend.status(credentials=True)
    # Use a single fictional modem, as production does. Never activate it.
    hotspot = Hotspot(backend.directory, backend.profiles, network=network)
    hotspot._adopt_setup_ap()
    cell = backend.profiles / 'openstick-cellular.nmconnection'
    before = cell.read_bytes()
    shared = backend.profiles / 'openstick-hotspot.nmconnection'
    profile = configparser.ConfigParser(); profile.read(shared)
    assert profile.getboolean('wifi', 'hidden') and profile.getint('wifi', 'ap-isolation') == 1
    source = configparser.ConfigParser(); source.read(backend.profiles / 'openstick-setup.nmconnection')
    assert dict(profile['wifi-security']) == dict(source['wifi-security'])
    assert profile['wifi']['ssid'] == original['ssid'] and profile['ipv4']['method'] == 'shared'
    hotspot.ap_backend = ap.SupplicantAP(Bus)
    hotspot.activate_ap(AP_UUID)
    assert network.wifi == AP_UUID and cell.read_bytes() == before
    assert hotspot.read('hotspot.json')['ap_options'] == VALUES
    # A stale/mismatching profile cannot quietly start without the saved policy.
    shared.write_text(shared.read_text().replace('hidden=true', 'hidden=false'))
    network.events.clear()
    with pytest.raises(RuntimeError, match='^AP_OPTIONS_INVALID$'):hotspot.activate_ap(AP_UUID)
    assert not network.events


def test_api_stages_only_with_auth_confirmation_and_card_explains_hidden_join(setup):
    backend, network, _ = setup
    app = create_hosting_app(usb_portal=True, token='fixture-token', setup_backend=backend, backend=object())
    client = app.test_client(); base = 'http://172.16.42.1'
    headers = {'X-OpenStick-Token': 'fixture-token', 'Origin': base}
    payload = {'action': 'configure_ap', 'ssid': 'Fictional AP', 'password': '', 'channel': 6,
               'confirm': True, **VALUES}
    network.events.clear()
    assert client.post('/api/setup', base_url=base, json=payload).status_code == 403
    assert client.post('/api/setup', base_url=base, headers={**headers, 'Origin': 'https://evil.invalid'}, json=payload).status_code == 403
    assert client.post('/api/setup', base_url=base, headers=headers, json={**payload, 'confirm': False}).status_code == 400
    assert not network.events
    response = client.post('/api/setup', base_url=base, headers=headers, json=payload)
    assert response.status_code == 202 and response.json['ap_options']['configured']
    assert 'password' not in response.json
    assert [e[0] for e in network.events] == ['load']
    network.events.clear()
    assert client.get('/api/setup', base_url=base, headers=headers).status_code == 200
    card = client.get('/api/setup/card', base_url=base, headers=headers)
    assert card.status_code == 200 and 'thêm mạng thủ công' in card.text
    assert not network.events


@pytest.mark.parametrize('enabled', [False, True])
def test_enabling_and_disabling_hidden_and_isolation_reach_both_ap_profiles(setup, enabled):
    backend, network, _ = setup
    save(backend, hidden=enabled, max_clients=1, isolation=enabled)
    bus = Bus(); bus.isolation = int(enabled)
    backend.ap_backend = ap.SupplicantAP(lambda: bus)
    backend.activate_ap(SETUP_UUID)
    assert bus.limit == 1 and bus.closed
    backend._adopt_setup_ap()
    profile = configparser.ConfigParser();profile.read(backend.profiles / 'openstick-hotspot.nmconnection')
    assert profile.getboolean('wifi', 'hidden') is enabled
    assert profile.getint('wifi', 'ap-isolation') == int(enabled)


@pytest.mark.parametrize('identity', [SETUP_UUID, AP_UUID])
@pytest.mark.parametrize('hidden', [False, True])
def test_nm_omitted_default_hidden_is_accepted_only_for_saved_visible_ap(setup, identity, hidden):
    backend, network, _ = setup
    save(backend, hidden=hidden, max_clients=10, isolation=False)
    if identity == AP_UUID:backend._adopt_setup_ap()
    path = backend.profiles / ('openstick-setup.nmconnection' if identity == SETUP_UUID else 'openstick-hotspot.nmconnection')
    profile = configparser.ConfigParser();profile.read(path)
    profile.remove_option('wifi', 'hidden')  # Real NM normalization of false.
    with path.open('w') as stream:profile.write(stream)
    before = path.read_bytes();bus = Bus();bus.isolation = 0
    backend.ap_backend = ap.SupplicantAP(lambda: bus);network.events.clear()
    if hidden:
        with pytest.raises(RuntimeError, match='^AP_OPTIONS_INVALID$'):backend.activate_ap(identity)
        assert not network.events and not bus.calls
    else:
        backend.activate_ap(identity)
        assert network.wifi == identity and bus.limit == 10 and bus.closed
        assert [e[0] for e in network.events] == ['up']
    assert path.read_bytes() == before, 'activation must not rewrite saved security settings'


def test_shared_ap_adopts_normalized_visible_setup_profile_without_changing_cellular(setup):
    backend, network, _ = setup
    save(backend, hidden=False, max_clients=10, isolation=False)
    backend._adopt_setup_ap()  # Establish an existing cellular profile to preserve.
    source = backend.profiles / 'openstick-setup.nmconnection'
    profile = configparser.ConfigParser();profile.read(source);profile.remove_option('wifi', 'hidden')
    with source.open('w') as stream:profile.write(stream)
    cell = backend.profiles / 'openstick-cellular.nmconnection';before = cell.read_bytes()
    backend._adopt_setup_ap();bus = Bus();bus.isolation = 0
    backend.ap_backend = ap.SupplicantAP(lambda: bus);network.events.clear()
    backend.activate_ap(AP_UUID)
    assert network.wifi == AP_UUID and bus.limit == 10
    assert [e[0] for e in network.events] == ['up'] and cell.read_bytes() == before


def test_boot_replay_uses_same_advanced_ap_hook_without_granting_sim_data(quick, tmp_path):
    from contextlib import nullcontext
    from uz801_manager.network_startup import NetworkStartup, save as save_startup, STATE
    from uz801_manager.setup_ap import SetupAP
    backend, network, radio, _ = quick
    profiles = tmp_path / 'profiles'
    network.load = lambda path: network.calls.append(('load', path.name))
    network.ap_capable = lambda: True
    network.ready = lambda: network.active('wlan0') is not None
    backend.hotspot.profiles = profiles
    backend.setup = SetupAP(tmp_path, profiles, network=network, lock_factory=nullcontext,
                            modem_lock_factory=nullcontext, lan_ready=lambda: True,
                            boot=lambda: 'old-boot', runtime=tmp_path / 'run')
    backend.setup.provision(); save(backend.setup)
    backend.hotspot._adopt_setup_ap = lambda: Hotspot._adopt_setup_ap(backend.hotspot)
    bus = Bus(); backend.hotspot.ap_backend = ap.SupplicantAP(lambda: bus)
    save_startup(tmp_path, wifi_role='ap', data_on=False, boot='old-boot')
    radio.ready = False; network.calls.clear()
    worker = NetworkStartup(backend, boot=lambda: 'new-boot')
    worker.tick();worker.tick()
    assert bus.limit == 3 and bus.closed and network.active('wlan0') == AP_UUID
    assert ('up', CELL_UUID) not in network.calls and not radio.calls
    assert backend._read(STATE)['done'] and not backend._read(STATE)['data_connected']

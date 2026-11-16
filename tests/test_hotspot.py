from contextlib import nullcontext
import json
import subprocess
from pathlib import Path
import shutil

import pytest

from uz801_manager.hosting import create_hosting_app
from uz801_manager.hotspot import AP_UUID, CELL_UUID, Hotspot, Network, validate_hotspot
from uz801_manager.setup_ap import SETUP_UUID, SetupAP

WIFI = '07ca019c-485b-4f06-b99d-171c167e18bb'


class FakeNetwork:
    def __init__(self):
        self.current = {'wlan0': WIFI, 'wwan0qmi0': None}
        self.calls, self.auto = [], {}
        self.healthy, self.supported, self.fail_ap = True, True, False

    def devices(self):return ['wwan0qmi0']
    def ap_capable(self):return self.supported
    def active(self, interface):return self.current.get(interface)
    def cellular_interface(self, control):return 'wwan4' if self.current.get(control) == CELL_UUID else None
    def internet(self, interface, control):
        self.calls.append(('probe', interface, control))
        return self.healthy and interface == 'wwan4'
    def load(self, path):self.calls.append(('load', str(path)))
    def nm(self, *args):self.calls.append(('nm', *args))
    def checkpoint(self, interfaces):
        assert interfaces == ['wlan0', 'wwan0qmi0']  # Never checkpoint/change USB.
        self.original = self.current.copy()
        self.calls.append(('checkpoint',))
        return '/org/freedesktop/NetworkManager/Checkpoint/1'
    def checkpoint_action(self, path, rollback):
        self.calls.append(('checkpoint_action', rollback))
        if rollback:self.current = self.original.copy()
    def extend_checkpoint(self, path):self.calls.append(('extend_checkpoint',))
    def up(self, identity):
        self.calls.append(('up', identity))
        if identity == AP_UUID and self.fail_ap:raise RuntimeError('private raw error')
        self.current['wwan0qmi0' if identity == CELL_UUID else 'wlan0'] = identity
    def down(self, identity):
        self.calls.append(('down', identity))
        self.current['wwan0qmi0' if identity == CELL_UUID else 'wlan0'] = None
    def autoconnect(self, identity, enabled):self.auto[identity] = enabled


@pytest.fixture
def setup_hotspot(tmp_path):
    network, clock = FakeNetwork(), [100]
    backend = Hotspot(tmp_path / 'private', tmp_path / 'profiles', network=network,
                       lock_factory=nullcontext, modem_lock_factory=nullcontext,
                       readiness=lambda: {'registered': True, 'sim_present': True, 'ussd_state': 1},
                       clock=lambda: clock[0], boot=lambda: 'fixture-boot', available=lambda _: True)
    return backend, network, clock


def configure(backend):
    return backend.call('configure', ssid='Fixture USB', password='private-fixture-password', channel=6, apn='', confirm=True)


def start(backend):return backend.call('start', confirm=True, cellular_consent=True, switch_wifi=True)


def test_quick_settings_owned_data_can_be_shared_without_reconnecting_bearer(setup_hotspot):
    from uz801_manager.quick_intent import save_intent
    backend, network, _ = setup_hotspot
    configure(backend)
    save_intent(backend.directory, airplane=False, data_allowed=True)
    network.current['wwan0qmi0'] = CELL_UUID
    network.calls.clear()
    state = start(backend)
    assert state['hotspot_active'] and state['pending']
    assert ('up', CELL_UUID) not in network.calls
    assert ('up', AP_UUID) in network.calls


def setup_mode(backend, network):
    setup = SetupAP(directory=backend.directory, profiles=backend.profiles,
                    network=network, lock_factory=nullcontext, modem_lock_factory=nullcontext,
                    lan_ready=lambda: True)
    setup.provision()
    network.current['wlan0'] = SETUP_UUID
    return backend.read('setup-ap.json')


def test_setup_wifi_auto_switches_to_same_ssid_psk_and_restores_setup_on_stop(setup_hotspot):
    backend, network, _ = setup_hotspot
    saved = setup_mode(backend, network)
    backend.setup_services = lambda enabled: network.calls.append(('setup_services', enabled))
    assert backend.call('status')['configured']
    assert backend.call('status')['setup_active']
    assert backend.call('status')['setup_ssid'] == saved['ssid']
    trial = start(backend)
    assert trial['hotspot_active'] and trial['pending'] and trial['ssid'] == saved['ssid']
    assert network.current['wwan0qmi0'] == CELL_UUID
    profile = (backend.profiles / 'openstick-hotspot.nmconnection').read_text()
    setup_profile = (backend.profiles / 'openstick-setup.nmconnection').read_text()
    import configparser
    ap = configparser.ConfigParser();ap.read_string(profile)
    original = configparser.ConfigParser();original.read_string(setup_profile)
    assert ap.get('wifi', 'ssid') == original.get('wifi', 'ssid')
    assert ap.get('wifi-security', 'psk') == original.get('wifi-security', 'psk')
    assert ap.get('wifi', 'cloned-mac-address') == 'permanent'
    assert ap.get('ipv4', 'method') == 'shared'
    assert ap.get('ipv4', 'address1') == '192.168.8.1/24'
    assert network.calls.index(('probe', 'wwan4', 'wwan0qmi0')) < network.calls.index(('setup_services', False))
    assert network.calls.index(('setup_services', False)) < network.calls.index(('up', AP_UUID))
    assert not backend.call('status')['setup_active']
    kept = backend.call('keep', attempt=trial['attempt'], confirm=True)
    assert kept['enabled'] and not kept['pending']
    stopped = backend.call('stop', confirm=True)
    assert stopped['wifi_restored'] and stopped['setup_active']
    assert ('setup_services', True) in network.calls
    assert network.current['wwan0qmi0'] is None
    assert not (backend.directory / 'hotspot-setup-origin.json').exists()
    assert backend.call('status')['configured']
    # A later request can reuse the setup Wi-Fi, with no extra setup action.
    assert start(backend)['hotspot_active']


def test_setup_switch_keep_stop_restores_existing_custom_ap_and_apn(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup_mode(backend, network)
    backend.call('configure', ssid='Private old hotspot', password='fixture-old-password',
                 channel=1, apn='fixture.operator', confirm=True)
    paths = [backend.directory / 'hotspot.json', backend.profiles / 'openstick-hotspot.nmconnection',
             backend.profiles / 'openstick-cellular.nmconnection']
    originals = {path: path.read_bytes() for path in paths}
    backend.setup_services = lambda enabled: network.calls.append(('setup_services', enabled))
    trial = start(backend)
    assert backend.call('keep', attempt=trial['attempt'], confirm=True)['enabled']
    assert (backend.directory / 'hotspot-setup-origin.json').exists()
    assert backend.call('stop', confirm=True)['setup_active']
    assert all(path.read_bytes() == original for path, original in originals.items())
    assert not (backend.directory / 'hotspot-setup-origin.json').exists()
    assert network.auto[AP_UUID] is False and network.auto[CELL_UUID] is False


def test_setup_switch_preserves_existing_manual_cellular_apn_without_hotspot_config(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup_mode(backend, network)
    backend.setup_services = lambda enabled: network.calls.append(('setup_services', enabled))
    cellular = backend.profiles / 'openstick-cellular.nmconnection'
    cellular.write_text(f'[connection]\nuuid={CELL_UUID}\ntype=gsm\n[gsm]\nauto-config=false\napn=fixture.provider\n')
    original = cellular.read_bytes()
    trial = start(backend)
    assert trial['apn'] == 'fixture.provider'
    assert cellular.read_bytes() == original
    backend.call('keep', attempt=trial['attempt'], confirm=True)
    backend.call('stop', confirm=True)
    assert cellular.read_bytes() == original


def test_corrupt_setup_profile_cannot_switch_sim_or_erase_prior_config(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup_mode(backend, network)
    profile = backend.profiles / 'openstick-setup.nmconnection'
    profile.write_text(profile.read_text().replace('mode=ap', 'mode=infrastructure'))
    backend.setup_services = lambda enabled: network.calls.append(('setup_services', enabled))
    with pytest.raises(RuntimeError, match='CELLULAR_CONNECT_FAILED'):
        start(backend)
    assert ('up', CELL_UUID) not in network.calls
    assert network.current['wlan0'] == SETUP_UUID
    assert not backend.read('hotspot-pending.json')
    assert not backend.read('hotspot.json')


def test_setup_partial_profile_load_failure_restores_missing_nm_entries(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup_mode(backend, network)
    backend.setup_services = lambda enabled: network.calls.append(('setup_services', enabled))
    original_load, original_nm = network.load, network.nm

    def reject_first_ap_load(path):
        if path.name == 'openstick-hotspot.nmconnection':
            raise RuntimeError('profile failed before NetworkManager loaded it')
        return original_load(path)

    def reject_delete_missing(*args):
        if args[:2] == ('connection', 'delete'):
            raise RuntimeError('NM profile not found')
        if args == ('-t', '-f', 'UUID', 'connection', 'show'):
            return ''
        return original_nm(*args)

    network.load = reject_first_ap_load
    network.nm = reject_delete_missing
    with pytest.raises(RuntimeError, match='^CELLULAR_CONNECT_FAILED$'):
        start(backend)
    assert network.current['wlan0'] == SETUP_UUID
    assert ('up', CELL_UUID) not in network.calls
    assert not backend.read('hotspot-pending.json')
    assert not (backend.profiles / 'openstick-hotspot.nmconnection').exists()
    assert not (backend.profiles / 'openstick-cellular.nmconnection').exists()
    assert not backend.read('hotspot.json')


@pytest.mark.parametrize('failure', ['internet', 'ap', 'expiry', 'restart'])
def test_setup_switch_failure_recovers_old_config_and_setup_dhcp(setup_hotspot, failure):
    backend, network, clock = setup_hotspot
    setup_mode(backend, network)
    configure(backend)  # Existing separate SIM Wi-Fi settings must survive a failed trial.
    paths = [backend.directory / 'hotspot.json', backend.profiles / 'openstick-hotspot.nmconnection',
             backend.profiles / 'openstick-cellular.nmconnection']
    originals = {p: p.read_bytes() for p in paths}
    backend.setup_services = lambda enabled: network.calls.append(('setup_services', enabled))
    if failure == 'internet':network.healthy = False
    if failure == 'ap':network.fail_ap = True
    if failure in ('internet', 'ap'):
        with pytest.raises(RuntimeError):start(backend)
    else:
        trial = start(backend)
        assert trial['hotspot_active']
        if failure == 'expiry':clock[0] += 286
        else:backend.boot = lambda: 'rebooted-boot'
        backend.recover_pending()
    assert all(p.read_bytes() == original for p, original in originals.items())
    assert not backend.read('hotspot-pending.json')
    assert network.current == {'wlan0': SETUP_UUID, 'wwan0qmi0': None}
    assert network.calls[-1] == ('setup_services', True)


def test_setup_pending_change_blocks_sim_start_without_data(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup_mode(backend, network)
    backend.write('setup-pending.json', {'action': 'connect'})
    before = network.calls[:]
    with pytest.raises(RuntimeError, match='SETUP_ACTIVE'):start(backend)
    assert network.calls == before


def test_no_configuration_or_status_probe_activates_data_or_creates_files(setup_hotspot):
    backend, network, _ = setup_hotspot
    assert not backend.call('status')['configured']
    assert not backend.directory.exists() and network.calls == []
    status = configure(backend)
    assert status['configured'] and not status['enabled'] and not status['hotspot_active']
    assert all(call[0] == 'load' for call in network.calls)
    stored = (backend.directory / 'hotspot.json').read_text()
    assert 'password' not in stored
    for path in backend.profiles.glob('*'):
        text = path.read_text()
        assert 'private-fixture-password' not in text and 'autoconnect=false' in text
    ap = (backend.profiles / 'openstick-hotspot.nmconnection').read_text()
    assert 'mode=ap' in ap and 'method=shared' in ap and 'address1=192.168.8.1/24' in ap


@pytest.mark.parametrize('value', [
    {'action': 'start', 'confirm': True, 'cellular_consent': False, 'switch_wifi': True},
    {'action': 'start', 'confirm': True, 'cellular_consent': True, 'switch_wifi': False},
    {'action': 'start', 'confirm': False, 'cellular_consent': True, 'switch_wifi': True},
    {'action': 'start'}, {'action': 'raw', 'command': 'AT'}, {'action': ['status']},
    {'action': 'keep', 'attempt': '../../private', 'confirm': True},
])
def test_transitions_require_exact_schema_and_both_consents_before_transport(setup_hotspot, value):
    backend, network, _ = setup_hotspot
    with pytest.raises(ValueError):backend.call(**value)
    assert network.calls == []


@pytest.mark.parametrize('change', [{'password': 'short'}, {'password': 'mật-khẩu-dài-hơn'}, {'ssid': 'bad\nssid'},
                                    {'ssid': 'x' * 33}, {'channel': 7}, {'channel': True}, {'apn': 'x\npassword=secret'}])
def test_credentials_cannot_inject_keyfile_settings(setup_hotspot, change):
    backend, network, _ = setup_hotspot
    values = {'ssid': 'fixture', 'password': 'fixture-passphrase', 'channel': 6, 'apn': '', 'confirm': True}
    with pytest.raises(ValueError):backend.call('configure', **{**values, **change})
    assert not backend.directory.exists() and network.calls == []


def test_probe_cellular_before_replacing_wifi_and_keep_enables_boot_autoconnect(setup_hotspot):
    backend, network, _ = setup_hotspot
    configure(backend)
    result = start(backend)
    assert result['pending'] and result['hotspot_active'] and not result['enabled']
    assert network.calls.index(('probe', 'wwan4', 'wwan0qmi0')) < network.calls.index(('up', AP_UUID))
    assert network.auto == {}
    kept = backend.call('keep', attempt=result['attempt'], confirm=True)
    assert kept['enabled'] and not kept['pending']
    assert network.auto == {AP_UUID: True, CELL_UUID: True}
    assert ('checkpoint_action', False) in network.calls


def test_apn_only_save_preserves_wifi_and_never_activates_data(setup_hotspot):
    backend, network, _ = setup_hotspot;configure(backend)
    ap = backend.profiles / 'openstick-hotspot.nmconnection'
    original = ap.read_bytes();network.calls.clear()
    cell = backend.profiles / 'openstick-cellular.nmconnection'
    with cell.open('a') as out:out.write('\n[proxy]\nmethod=0\n')
    for apn in ('fixture.apn', ''):
        state=backend.call('configure_apn',apn=apn,confirm=True)
        assert state['apn']==apn and not state['enabled'] and not state['cellular_connected']
        assert ap.read_bytes()==original
        assert 'home-only=true' in cell.read_text() and '[proxy]' in cell.read_text()
        assert ('apn='+apn+'\n' in cell.read_text()) if apn else ('apn=' not in cell.read_text())
        assert ('auto-config=false' if apn else 'auto-config=true') in cell.read_text()
    assert all(call==('load',str(cell)) for call in network.calls)


@pytest.mark.parametrize('apn', ['bad\npassword=secret', 'x;bad', 'X', None, 'a'*101])
def test_apn_only_rejects_invalid_values_before_transport(setup_hotspot,apn):
    backend,network,_=setup_hotspot
    with pytest.raises(ValueError):backend.call('configure_apn',apn=apn,confirm=True)
    assert not network.calls and not backend.directory.exists()


@pytest.mark.parametrize('blocked', ['trial','active','cellular','policy'])
def test_apn_only_blocks_live_networks_without_writes(setup_hotspot,blocked):
    backend,network,_=setup_hotspot;configure(backend)
    if blocked=='trial':backend.write('hotspot-pending.json',{'attempt':'fixture'})
    if blocked=='active':network.current['wlan0']=AP_UUID
    if blocked=='cellular':network.current['wwan0qmi0']=CELL_UUID
    if blocked=='policy':backend.write('network-policy.json',{'enabled':True})
    original={p:p.read_bytes() for p in backend.profiles.glob('*')};network.calls.clear()
    with pytest.raises(RuntimeError):backend.call('configure_apn',apn='fixture.apn',confirm=True)
    assert not network.calls and all(p.read_bytes()==data for p,data in original.items())


def test_apn_only_rolls_back_file_and_nm_on_load_failure(setup_hotspot):
    backend,network,_=setup_hotspot;configure(backend)
    originals={p:p.read_bytes() for p in [*backend.profiles.glob('*'),backend.directory/'hotspot.json']}
    loads=[]
    def fail_once(path):
        loads.append(path.read_text())
        if len(loads)==1:raise RuntimeError('private provider error')
    network.load=fail_once
    with pytest.raises(RuntimeError,match='^HOTSPOT_OPERATION_FAILED$'):
        backend.call('configure_apn',apn='fixture.apn',confirm=True)
    assert len(loads)==2 and all(p.read_bytes()==data for p,data in originals.items())


def test_apn_save_bootstraps_from_shared_setup_wifi_without_starting_data(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup = setup_mode(backend, network)
    network.calls.clear()
    result = backend.call('configure_apn', apn='fixture.apn', confirm=True)
    assert result['configured'] and result['ssid'] == setup['ssid']
    assert result['apn'] == 'fixture.apn' and result['setup_active']
    assert backend.read('setup-ap.json') == setup
    assert 'apn=fixture.apn' in (backend.profiles / 'openstick-cellular.nmconnection').read_text()
    assert not any(call[0] in ('checkpoint', 'up', 'down') for call in network.calls)
    assert network.current['wwan0qmi0'] is None


def test_first_apn_save_restores_original_setup_on_profile_load_failure(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup_mode(backend, network)
    paths = [backend.directory / 'setup-ap.json', backend.profiles / 'openstick-setup.nmconnection']
    originals = {path: path.read_bytes() for path in paths}
    original_load = network.load
    failed = [False]
    def fail_cellular_once(path):
        if path.name == 'openstick-cellular.nmconnection' and not failed[0]:
            failed[0] = True
            raise RuntimeError('hidden test failure')
        return original_load(path)
    network.load = fail_cellular_once
    network.calls.clear()
    with pytest.raises(RuntimeError, match='^HOTSPOT_OPERATION_FAILED$'):
        backend.call('configure_apn', apn='fixture.apn', confirm=True)
    assert failed[0]
    assert all(path.read_bytes() == data for path, data in originals.items())
    assert not (backend.directory / 'hotspot.json').exists()
    assert not (backend.profiles / 'openstick-hotspot.nmconnection').exists()
    assert not (backend.profiles / 'openstick-cellular.nmconnection').exists()
    assert network.current['wlan0'] == SETUP_UUID
    assert not any(call[0] in ('checkpoint', 'up', 'down') for call in network.calls)


def test_sim_without_internet_keeps_home_wifi_and_stops_trial_data(setup_hotspot):
    backend, network, _ = setup_hotspot
    configure(backend)
    network.healthy = False
    with pytest.raises(RuntimeError, match='CELLULAR_NO_INTERNET'):start(backend)
    assert ('up', AP_UUID) not in network.calls
    assert network.current == {'wlan0': WIFI, 'wwan0qmi0': None}
    assert not backend.read('hotspot-pending.json')


def test_ap_failure_rolls_back_and_does_not_publish_raw_error(setup_hotspot):
    backend, network, _ = setup_hotspot
    configure(backend)
    network.fail_ap = True
    with pytest.raises(RuntimeError, match='^AP_START_FAILED$'):start(backend)
    assert network.current == {'wlan0': WIFI, 'wwan0qmi0': None}


def test_cellular_activation_error_is_distinct_and_private(setup_hotspot):
    backend, network, _ = setup_hotspot;configure(backend)
    def fail(_):raise RuntimeError('private APN/identifier/provider error')
    network.up = fail
    with pytest.raises(RuntimeError, match='^CELLULAR_CONNECT_FAILED$'):start(backend)
    assert network.current == {'wlan0': WIFI, 'wwan0qmi0': None}
    assert not backend.read('hotspot-pending.json')


@pytest.mark.parametrize('ready', [{'registered': False, 'sim_present': True},
                                   {'registered': True, 'sim_present': True, 'sim_locked': True},
                                   {'registered': True, 'sim_present': True, 'ussd_state': 3}])
def test_sim_lock_and_ussd_gates_precede_any_data_connection(setup_hotspot, ready):
    backend, network, _ = setup_hotspot
    configure(backend)
    backend.readiness = lambda: ready
    with pytest.raises(RuntimeError):start(backend)
    assert not any(call[0] in ('checkpoint', 'up', 'nm') for call in network.calls)


def test_start_cancels_idle_waiting_ussd_only_after_modem_ack(setup_hotspot):
    backend, network, _ = setup_hotspot
    configure(backend)
    state = {'registered': True, 'sim_present': True, 'ussd_state': 3}
    backend.readiness = lambda: state.copy()
    def cancel():
        assert not any(call[0] in ('checkpoint', 'up', 'nm') for call in network.calls)
        state['ussd_state'] = 1
        return {'cancelled': True, 'modem_acknowledged': True}
    backend.ussd_cancel = cancel
    assert start(backend)['hotspot_active']


@pytest.mark.parametrize('ussd_state,response,after', [
    (2, None, 2),
    (3, {'cancelled': True, 'modem_acknowledged': False}, 1),
    (3, {'cancelled': True, 'modem_acknowledged': True}, 3),
])
def test_start_does_not_change_network_when_ussd_cannot_safely_end(
        setup_hotspot, ussd_state, response, after):
    backend, network, _ = setup_hotspot
    configure(backend)
    state = {'registered': True, 'sim_present': True, 'ussd_state': ussd_state}
    backend.readiness = lambda: state.copy()
    callbacks = []
    def cancel():
        callbacks.append(True)
        state['ussd_state'] = after
        return response
    backend.ussd_cancel = cancel
    network.calls.clear()
    with pytest.raises(RuntimeError, match='^MODEM_BUSY$'):
        start(backend)
    assert len(callbacks) == (0 if ussd_state == 2 else 1)
    assert network.calls == []


def test_expired_trial_recovers_in_independent_worker_and_cannot_be_kept(setup_hotspot):
    backend, network, clock = setup_hotspot
    configure(backend)
    trial = start(backend)
    clock[0] += 286
    with pytest.raises(RuntimeError, match='HOTSPOT_CONFIRM_EXPIRED'):
        backend.call('keep', attempt=trial['attempt'], confirm=True)
    backend.recover_pending()
    assert network.current == {'wlan0': WIFI, 'wwan0qmi0': None}
    assert network.auto == {AP_UUID: False, CELL_UUID: False}
    assert not backend.read('hotspot-pending.json') and not backend.read('hotspot.json')['enabled']


def test_stale_confirmation_cannot_keep_another_trial_and_stop_preserves_sms_radio(setup_hotspot):
    backend, network, _ = setup_hotspot
    configure(backend)
    start(backend)
    with pytest.raises(RuntimeError, match='HOTSPOT_CONFIRM_EXPIRED'):
        backend.call('keep', attempt='a' * 32, confirm=True)
    result = backend.call('stop', confirm=True)
    assert result['wifi_restored'] and not result['hotspot_active'] and not result['cellular_connected']
    assert not any(call == ('nm', 'radio', 'wwan', 'off') for call in network.calls)


def test_recovery_without_pending_trial_never_changes_network(setup_hotspot):
    backend, network, _ = setup_hotspot
    backend.recover_pending()
    assert network.calls == []


def test_partial_confirmation_failure_is_reverted_by_worker(setup_hotspot):
    backend, network, clock = setup_hotspot
    configure(backend)
    trial = start(backend)
    original = network.checkpoint_action
    def fail_destroy(path, rollback):
        if not rollback:raise RuntimeError('synthetic disconnect')
        return original(path, rollback)
    network.checkpoint_action = fail_destroy
    with pytest.raises(RuntimeError):backend.call('keep', attempt=trial['attempt'], confirm=True)
    assert backend.read('hotspot-pending.json') and network.auto[AP_UUID]
    clock[0] += 111
    backend.recover_pending()
    assert not backend.read('hotspot.json')['enabled']
    assert not network.auto[AP_UUID] and not network.auto[CELL_UUID]
    assert network.current['wlan0'] == WIFI


def test_power_loss_during_unconfirmed_trial_restores_saved_wifi(setup_hotspot):
    backend, network, _ = setup_hotspot
    configure(backend)
    start(backend)
    backend.boot = lambda: 'new-boot'
    network.checkpoint_action = lambda *a: (_ for _ in ()).throw(RuntimeError('old daemon checkpoint gone'))
    backend.recover_pending()
    assert network.current == {'wlan0': WIFI, 'wwan0qmi0': None}
    assert not backend.read('hotspot-pending.json')


def test_missing_live_checkpoint_cannot_enable_autoconnect(setup_hotspot):
    backend, network, _ = setup_hotspot
    configure(backend)
    trial = start(backend)
    network.extend_checkpoint = lambda *a: (_ for _ in ()).throw(RuntimeError('checkpoint gone'))
    with pytest.raises(RuntimeError, match='HOTSPOT_CONFIRM_EXPIRED'):
        backend.call('keep', attempt=trial['attempt'], confirm=True)
    assert network.auto == {}


@pytest.mark.parametrize('raw,expected', [('192.0.2.53\n','192.0.2.53'),
    ('192.0.2.53\n192.0.2.54\n','192.0.2.53,192.0.2.54'),
    ('192.0.2.53 | 192.0.2.54','192.0.2.53,192.0.2.54')])
def test_internet_probe_binds_both_https_and_dns_to_actual_modem_interface(raw,expected):
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        assert kwargs['shell'] is False
        if args[0] == 'nmcli':return subprocess.CompletedProcess(args, 0, raw)
        assert args[args.index('--interface') + 1] == 'wwan4'
        assert args[args.index('--dns-interface') + 1] == 'wwan4'
        assert args[args.index('--dns-servers') + 1] == expected
        assert '--max-filesize' in args and '--max-time' in args and '--proxy' in args
        assert args[-1] == 'https://cp.cloudflare.com/generate_204'
        return subprocess.CompletedProcess(args, 0, '204')
    assert Network(run=run).internet('wwan4', 'wwan0qmi0')
    assert len(calls) == 2


def test_hotspot_routes_keep_auth_token_host_and_error_privacy(setup_hotspot):
    backend, _, _ = setup_hotspot
    app = create_hosting_app(backend=object(), usb_portal=True, hotspot_backend=backend, token='fixture')
    client, base = app.test_client(), 'http://172.16.42.1'
    headers = {'X-OpenStick-Token': 'fixture', 'Origin': base}
    assert client.get('/hotspot', base_url=base).status_code == 200
    assert client.post('/api/hotspot', base_url=base, json={'action': 'status'}).status_code == 403
    assert client.post('/api/hotspot', base_url=base, headers={**headers, 'Origin': 'https://evil.invalid'},
                       json={'action': 'status'}).status_code == 403
    assert client.post('/api/hotspot', base_url=base, headers=headers, json={'action': 'start'}).status_code == 400
    backend.call = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError('private APN/IMEI/password error'))
    assert client.post('/api/hotspot', base_url=base, headers=headers, json={'action': 'status'}).status_code == 202
    app.extensions['hotspot']['thread'].join(2)
    response = client.get('/api/hotspot/state', base_url=base, headers=headers)
    assert response.json['error'] == 'HOTSPOT_OPERATION_FAILED' and 'private' not in response.text


def test_hotspot_ui_never_activates_without_explicit_consent_and_confirmation(setup_hotspot, tmp_path):
    node = shutil.which('node')
    if not node:pytest.skip('Node.js required for synthetic hotspot fixture')
    backend, _, _ = setup_hotspot
    app = create_hosting_app(backend=object(), usb_portal=True, hotspot_backend=backend, token='fixture')
    page = tmp_path / 'hotspot.html'
    page.write_text(app.test_client().get('/hotspot', base_url='http://172.16.42.1').text, encoding='utf-8')
    result = subprocess.run([node, str(Path(__file__).with_name('hotspot_ui_fixture.cjs')), str(page)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


def test_status_refresh_does_not_erase_last_hotspot_action_failure(setup_hotspot):
    backend, network, _ = setup_hotspot;configure(backend);network.fail_ap = True
    app=create_hosting_app(backend=object(),usb_portal=True,hotspot_backend=backend,token='fixture')
    client=app.test_client();base='http://172.16.42.1';headers={'X-OpenStick-Token':'fixture'}
    payload={'action':'start','confirm':True,'cellular_consent':True,'switch_wifi':True}
    assert client.post('/api/hotspot',base_url=base,headers=headers,json=payload).status_code==202
    app.extensions['hotspot']['thread'].join(2)
    first=client.get('/api/hotspot/state',base_url=base,headers=headers).json
    assert first['error']=='AP_START_FAILED'
    for _ in range(2):
        assert client.post('/api/hotspot',base_url=base,headers=headers,json={'action':'status'}).status_code==202
        app.extensions['hotspot']['thread'].join(2)
        current=client.get('/api/hotspot/state',base_url=base,headers=headers).json
        assert current['error'] is None and current['last_operation']==first['last_operation']
        assert set(current['last_operation'])=={'action','error','at'}
    # USB and authenticated LAN use separate app/backend instances.
    replacement=Hotspot(backend.directory,backend.profiles,network=network,lock_factory=nullcontext)
    other=create_hosting_app(backend=object(),usb_portal=True,hotspot_backend=replacement,token='fixture').test_client()
    assert other.get('/api/hotspot/state',base_url=base,headers=headers).json['last_operation']==first['last_operation']
    stored=(backend.directory/'hotspot-last-operation.json').read_text()
    assert 'private' not in stored and 'ssid' not in stored and 'checkpoint' not in stored


def test_reconnected_portal_reads_real_pending_trial_without_repeating_start(setup_hotspot):
    backend, network, _ = setup_hotspot
    setup_mode(backend, network)
    backend.setup_services = lambda enabled: network.calls.append(('setup_services', enabled))
    trial = start(backend)
    backend.record_operation('start', None)
    # Model an entirely new listener process on USB after the phone reconnects.
    replacement = Hotspot(backend.directory, backend.profiles, network=network,
                          lock_factory=nullcontext, clock=backend.clock, boot=backend.boot)
    app = create_hosting_app(backend=object(), usb_portal=True, hotspot_backend=replacement, token='fixture')
    client = app.test_client()
    response = client.get('/api/hotspot/state', base_url='http://172.16.42.1',
                          headers={'X-OpenStick-Token': 'fixture'})
    assert response.status_code == 200
    state = response.json
    assert not state['busy'] and state['error'] is None
    assert state['result']['hotspot_active'] and state['result']['pending']
    assert state['result']['attempt'] == trial['attempt']
    assert state['last_operation']['action'] == 'start'
    assert state['last_operation']['error'] is None
    assert network.current['wwan0qmi0'] == CELL_UUID


def test_other_portal_reports_busy_if_hotspot_transition_holds_network_lock(setup_hotspot):
    backend, _, _ = setup_hotspot
    backend.call = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('NETWORK_BUSY'))
    app = create_hosting_app(backend=object(), usb_portal=True, hotspot_backend=backend, token='fixture')
    result = app.test_client().get('/api/hotspot/state', base_url='http://172.16.42.1',
                                   headers={'X-OpenStick-Token': 'fixture'}).json
    assert result['busy'] is True and result['error'] is None
    assert result['result'] == {}

"""Quick Settings simulated transactions. No USB, SIM or system DBus operations."""
from contextlib import nullcontext
import json
import uuid

import pytest

from uz801_manager.hotspot import AP_UUID, CELL_UUID, Hotspot
from uz801_manager.hosting import create_hosting_app
from uz801_manager.modem_device import OperationJournal
from uz801_manager.quick_intent import data_allowed, load_intent, radio_allowed, save_intent
from uz801_manager.quick_settings import QuickSettings, validate_quick
from uz801_manager.setup_ap import SETUP_UUID


class Network:
    def __init__(self):
        self.active_profiles = {'wlan0': 'saved-station', 'cell': None}
        self.calls = []
        self.fail_cell = False
        self.foreign_auto = False

    def devices(self): return ['cell']
    def active(self, interface): return self.active_profiles.get(interface)
    def nm(self, *args, **kwargs):
        if args[:3] == ('-t', '-f', 'UUID,TYPE'):
            return CELL_UUID + ':gsm' + ('\n' + str(uuid.UUID(int=1)) + ':gsm' if self.foreign_auto else '')
        if args[:2] == ('-g', 'connection.autoconnect'): return 'yes'
        self.calls.append(('nm', args))
        return ''
    def autoconnect(self, identity, enabled): self.calls.append(('auto', identity, enabled))
    def up(self, identity):
        self.calls.append(('up', identity))
        if self.fail_cell: raise RuntimeError('raw-private-error')
        self.active_profiles['cell' if identity == CELL_UUID else 'wlan0'] = identity
    def down(self, identity):
        self.calls.append(('down', identity))
        for interface in self.active_profiles:
            if self.active_profiles[interface] == identity: self.active_profiles[interface] = None
    def cellular_interface(self, control): return 'cell-data' if self.active(control) == CELL_UUID else None


class Radio:
    def __init__(self): self.calls = []; self.ready = True; self.ussd = 1
    def status(self):
        return {'state': 8 if self.ready else -1, 'power_state': 3 if self.ready else 1,
                'sim_ready': self.ready, 'registered': self.ready, 'ussd_state': self.ussd}
    def enable(self, enabled): self.calls.append(enabled)


class Setup:
    def __init__(self, hotspot, network): self.hotspot = hotspot; self.network = network; self.fail = False
    def lan_ready(self): return True
    def start(self):
        if self.fail: raise RuntimeError('raw-private-setup-error')
        self.network.calls.append(('local_ap',))
        self.network.active_profiles['wlan0'] = SETUP_UUID
    def stop(self): self.network.active_profiles['wlan0'] = None
    def write(self, name, value): self.hotspot.write(name, value)


@pytest.fixture
def quick(tmp_path, monkeypatch):
    network = Network(); radio = Radio()
    hotspot = Hotspot(tmp_path, network=network, lock_factory=nullcontext, modem_lock_factory=nullcontext)
    setup = Setup(hotspot, network)
    journal = OperationJournal(tmp_path / 'quick-operations')
    if __import__('os').name == 'nt': monkeypatch.setattr(journal, '_sync_directory', lambda: None)
    backend = QuickSettings(tmp_path, network=network, radio=radio, lock_factory=nullcontext,
                            modem_lock_factory=nullcontext, hotspot=hotspot, setup=setup, journal=journal,
                            identity_matches=lambda:True)
    return backend, network, radio, setup


def invoke(backend, action, identity=None, **values):
    return backend.call(action, operation=identity or str(uuid.uuid4()), confirm=True, **values)


def provision(backend):
    backend.hotspot.write('hotspot.json', {'ssid': 'fictional-ap', 'enabled': True})
    backend.hotspot.write('setup-ap.json', {'ssid': 'fictional-ap', 'enabled': True})


def test_read_status_creates_no_intent_receipt_or_transport_changes(quick, tmp_path):
    backend, network, radio, _ = quick
    before = list(tmp_path.rglob('*'))
    result = backend.status()
    assert result['intent'] is None and result['wifi_role'] == 'station'
    assert not result['internet_verified'] and not result['usb_tethering']['available']
    assert list(tmp_path.rglob('*')) == before and not network.calls and not radio.calls


def test_connection_uuid_while_configuring_is_not_connected_data(quick):
    backend, network, _, _ = quick
    network.active_profiles['cell'] = CELL_UUID
    network.cellular_interface=lambda _:None
    assert not backend.status()['mobile_data_connected']


def test_airplane_off_disables_data_and_automation_without_recreating_bearer(quick):
    backend, network, radio, _ = quick
    provision(backend); network.active_profiles['cell'] = CELL_UUID
    save_intent(backend.directory, airplane=True, data_allowed=False)
    result = invoke(backend, 'airplane_off')
    assert radio.calls == [True]
    assert result['intent'] == {'version': 1, 'airplane': False, 'data_allowed': False}
    assert not result['mobile_data_connected'] and ('up', CELL_UUID) not in network.calls
    assert backend._read('network-policy.json')['cellular_consent'] is False
    assert backend._read('hotspot.json')['enabled'] is False
    assert network.active('wlan0') == 'saved-station'


def test_airplane_on_veto_persists_and_wifi_station_is_untouched(quick):
    backend, network, radio, _ = quick
    provision(backend)
    invoke(backend, 'airplane_on')
    assert not radio_allowed(backend.directory) and not data_allowed(backend.directory)
    assert radio.calls == [False] and network.active('wlan0') == 'saved-station'
    assert ('nm', ('radio', 'wwan', 'off')) in network.calls
    assert not any(call[:2] == ('nm', ('radio', 'wifi', 'off')) for call in network.calls)


def test_data_off_from_sim_ap_restores_local_ap_without_old_wifi_or_radio_toggle(quick):
    backend, network, radio, _ = quick
    provision(backend); network.active_profiles.update(wlan0=AP_UUID, cell=CELL_UUID)
    result = invoke(backend, 'data_off')
    assert result['wifi_role'] == 'local_ap' and not result['mobile_data_connected']
    assert radio.calls == [] and ('up', 'saved-station') not in network.calls
    assert network.calls.index(('down', CELL_UUID)) < network.calls.index(('down', AP_UUID)) < network.calls.index(('local_ap',))
    assert not data_allowed(backend.directory)


def test_failed_ap_recovery_never_restores_data_and_airplane_still_disables_radio(quick):
    backend, network, radio, setup = quick
    provision(backend); setup.fail = True
    network.active_profiles.update(wlan0=AP_UUID, cell=CELL_UUID)
    identity = str(uuid.uuid4())
    with pytest.raises(RuntimeError, match='DATA_OFF_AP_FAILED'):
        invoke(backend, 'airplane_on', identity)
    assert not network.active('cell') and not data_allowed(backend.directory)
    assert radio.calls == [False]
    assert backend.receipt(identity)['state'] == 'UNKNOWN'
    assert backend.receipt(identity)['failure'] == 'DATA_OFF_AP_FAILED'


def test_automation_save_error_still_attempts_disconnect_and_never_reenables(quick):
    backend, network, radio, _ = quick
    provision(backend);network.active_profiles['cell']=CELL_UUID
    def fail():raise RuntimeError('private filesystem failure')
    backend._stop_automation=fail
    with pytest.raises(RuntimeError,match='QUICK_OPERATION_FAILED'):invoke(backend,'data_off')
    assert not network.active('cell') and not data_allowed(backend.directory) and not radio.calls


@pytest.mark.parametrize('busy', ['trial', 'ussd', 'foreign_active', 'foreign_auto'])
def test_conflicts_are_blocked_before_intent_receipt_or_mutation(quick, tmp_path, busy):
    backend, network, radio, _ = quick
    if busy == 'trial': backend.hotspot.write('hotspot-pending.json', {'attempt': 'fixture'})
    if busy == 'ussd': radio.ussd = 2
    if busy == 'foreign_active': network.active_profiles['cell'] = 'foreign'
    if busy == 'foreign_auto': network.foreign_auto = True
    with pytest.raises(RuntimeError): invoke(backend, 'data_off')
    assert not network.calls and not radio.calls
    assert load_intent(tmp_path) is None and not (tmp_path / 'quick-operations').exists()


def test_missing_sim_and_airplane_block_data_on_before_activation(quick):
    backend, network, radio, _ = quick
    provision(backend); radio.ready = False
    with pytest.raises(RuntimeError, match='SIM_NOT_READY'): invoke(backend, 'data_on', cellular_consent=True)
    radio.ready = True; save_intent(backend.directory, airplane=True, data_allowed=False)
    with pytest.raises(RuntimeError, match='AIRPLANE_ACTIVE'): invoke(backend, 'data_on', cellular_consent=True)
    assert ('up', CELL_UUID) not in network.calls


def test_failed_data_activation_is_fail_closed_and_receipt_is_replay_safe(quick):
    backend, network, _, _ = quick
    provision(backend); network.fail_cell = True; identity = str(uuid.uuid4())
    with pytest.raises(RuntimeError, match='QUICK_OPERATION_FAILED'): invoke(backend, 'data_on', identity, cellular_consent=True)
    calls = list(network.calls)
    assert not data_allowed(backend.directory)
    with pytest.raises(RuntimeError, match='ALREADY_ATTEMPTED'): invoke(backend, 'data_on', identity, cellular_consent=True)
    assert calls == network.calls and 'raw-private' not in json.dumps(backend.receipt(identity))


def test_data_on_keeps_wifi_role_and_never_enables_boot_autoconnect(quick):
    backend, network, radio, _ = quick
    provision(backend)
    result = invoke(backend, 'data_on', cellular_consent=True)
    assert result['mobile_data_connected'] and result['wifi_role'] == 'station'
    assert not radio.calls and ('auto', CELL_UUID, True) not in network.calls
    assert not result['internet_verified']


def test_corrupt_intent_fails_closed_and_new_instances_read_same_intent(tmp_path):
    assert radio_allowed(tmp_path) and data_allowed(tmp_path)
    (tmp_path / 'quick-settings.json').write_text('{broken')
    assert not radio_allowed(tmp_path) and not data_allowed(tmp_path)
    save_intent(tmp_path, airplane=False, data_allowed=False)
    assert radio_allowed(tmp_path) and not data_allowed(tmp_path)


def test_watchdog_never_enables_or_replays_mode_under_airplane(monkeypatch):
    from uz801_manager import modem_device
    from uz801_manager import quick_settings
    calls = []
    class StopLoop(BaseException): pass
    class Modem:
        def call(self, *args, **kwargs): calls.append(args); raise AssertionError('Must not reach modem')
    monkeypatch.setattr(modem_device, 'ModemManager', Modem)
    monkeypatch.setattr(modem_device, 'radio_allowed', lambda: False)
    class Recovery:
        def reconcile_airplane(self): calls.append('recover_off')
    monkeypatch.setattr(quick_settings, 'QuickSettings', Recovery)
    monkeypatch.setattr(modem_device.time, 'sleep', lambda _: (_ for _ in ()).throw(StopLoop()))
    with pytest.raises(StopLoop): modem_device.watch_radio()
    assert calls == ['recover_off']


def test_boot_recovery_only_applies_saved_airplane_off_never_data_on(quick):
    backend, network, radio, _ = quick
    provision(backend)
    backend.reconcile_airplane()
    assert not network.calls and not radio.calls
    save_intent(backend.directory, airplane=True, data_allowed=False)
    backend.reconcile_airplane()
    assert radio.calls == [False] and ('up', CELL_UUID) not in network.calls


def test_mismatched_staged_ap_identity_cannot_be_reported_as_same_wifi(quick):
    backend, network, _, _ = quick
    provision(backend);backend.identity_matches=lambda:False
    network.active_profiles.update(wlan0=AP_UUID,cell=CELL_UUID)
    with pytest.raises(RuntimeError,match='DATA_OFF_AP_FAILED'): invoke(backend,'data_off')
    assert not network.active('cell') and ('local_ap',) not in network.calls


def test_legacy_modem_enable_is_vetoed_before_opening_bus(monkeypatch):
    from uz801_manager import modem_device
    monkeypatch.setattr(modem_device, 'radio_allowed', lambda: False)
    modem = modem_device.ModemManager(bus_factory=lambda: pytest.fail('Must not open bus'))
    with pytest.raises(RuntimeError, match='AIRPLANE_ACTIVE'): modem.call('enable', confirm=True)


def test_legacy_hotspot_and_policy_worker_cannot_bypass_persisted_veto(quick):
    from uz801_manager.network_policy import NetworkPolicy
    backend, network, _, _ = quick
    provision(backend); save_intent(backend.directory, airplane=True, data_allowed=False)
    with pytest.raises(RuntimeError, match='AIRPLANE_ACTIVE'):
        backend.hotspot.call('start',confirm=True,cellular_consent=True,switch_wifi=True)
    backend.hotspot.write('hotspot.json', {'ssid':'fictional-ap','enabled':False})
    backend.hotspot.write('network-policy.json', {'enabled':True,'mode':'sim_only','auto_wifi':False,'cellular_consent':True})
    policy = NetworkPolicy(backend.directory, network=network, lock_factory=nullcontext, boot=lambda:'fixture-boot')
    with pytest.raises(RuntimeError, match='CELLULAR_DISABLED'): policy.tick()
    assert not network.calls


@pytest.mark.parametrize('value', [{}, {'action': 'data_on', 'operation': str(uuid.uuid4()), 'confirm': True},
    {'action': 'data_off', 'operation': '../bad', 'confirm': True},
    {'action': 'airplane_on', 'operation': str(uuid.uuid4()), 'confirm': False},
    {'action': 'usb_tether_on', 'operation': str(uuid.uuid4()), 'confirm': True}])
def test_schema_requires_exact_action_confirmation_and_consent(value):
    with pytest.raises(ValueError): validate_quick(value)


def test_typed_radio_reads_no_identifiers_and_honors_separate_qmi_session():
    from uz801_manager.quick_settings import RadioControl
    class Bus:
        def __init__(self): self.enabled=[];self.properties=[]
        def call_blocking(self, service, path, interface, method, signature, args, **kwargs):
            if method=='Introspect':return '<node><node name="0"/></node>'
            if method=='Enable':self.enabled.append(args[0]);return None
            assert method=='Get';self.properties.append(args[1])
            return {'State':8,'PowerState':3,'Sim':'/fixture/sim','UnlockRequired':1}[args[1]] if args[0].endswith('.Modem') else 1
        def close(self):pass
    bus=Bus();radio=RadioControl(bus_factory=lambda:bus,ussd_state=lambda:3)
    assert radio.status()['ussd_state']==3
    with pytest.raises(RuntimeError,match='MODEM_BUSY'):radio.enable(False)
    assert not bus.enabled
    radio=RadioControl(bus_factory=lambda:bus,ussd_state=lambda:1)
    radio.enable(False)
    assert bus.enabled==[False]
    assert set(bus.properties)<={'State','PowerState','Sim','UnlockRequired'}


def test_private_api_guards_and_read_only_open(quick):
    backend, network, radio, _ = quick
    app = create_hosting_app(backend=object(), usb_portal=True, modem_backend=object(),
                             quick_backend=backend, token='fixture')
    with app.test_client() as client:
        base = 'http://172.16.42.1'; headers = {'X-OpenStick-Token': 'fixture'}
        assert client.get('/quick', base_url=base).status_code == 200
        assert client.get('/api/quick', base_url=base).status_code == 403
        assert client.get('/api/quick', base_url=base, headers=headers).status_code == 200
        assert client.get('/api/quick', base_url='http://bad.invalid', headers=headers).status_code == 403
        assert client.post('/api/quick', base_url=base, headers=headers, json={'action': 'airplane_on'}).status_code == 400
        assert not network.calls and not radio.calls
        identity = str(uuid.uuid4())
        response = client.post('/api/quick', base_url=base, headers=headers,
                               json={'action':'airplane_on','operation':identity,'confirm':True})
        assert response.status_code == 202
        app.extensions['quick_settings']['thread'].join(3)
        assert client.get('/api/quick/operation/'+identity,base_url=base,headers=headers).json['state'] == 'COMPLETED'
        assert client.post('/api/quick',base_url=base,headers=headers,
                          json={'action':'airplane_on','operation':identity,'confirm':True}).status_code == 409

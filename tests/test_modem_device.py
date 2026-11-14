import json
import uuid
from contextlib import nullcontext

import pytest

from uz801_manager.modem import validate_action
from uz801_manager.modem_device import (
    INTRO, MESSAGING, MODEM, PROPS, ROOT, SMS, USSD, ModemManager, OperationJournal, RadioPreference,
)


class Bus:
    def __init__(self, *, sim=True, state=8, session=1, send_timeout=False):
        self.calls = []
        self.closed = False
        self.send_timeout = send_timeout
        self.nodes = ['0']
        self.props = {
            MODEM: {'State': state if sim else -1, 'StateFailedReason': 0 if sim else 2,
                    'Sim': ROOT + '/SIM/0' if sim else '/', 'UnlockRequired': 1 if sim else 0,
                    'SupportedModes': [(8, 0), (4, 0), (14, 8), (14, 0)], 'CurrentModes': (14, 8)},
            MESSAGING: {'Messages': [ROOT + '/SMS/4']},
            USSD: {'State': session, 'NetworkRequest': '', 'NetworkNotification': ''},
            SMS: {'State': 3, 'Number': '+84900111222', 'Text': '<script>fixture OTP</script>',
                  'Timestamp': '2026-11-14T10:00:00Z'},
        }

    def call_blocking(self, service, path, interface, method, signature, args, **kwargs):
        self.calls.append((path, interface, method, signature, args))
        if method == 'Introspect':
            if path == ROOT + '/Modem':
                return '<node>' + ''.join(f'<node name="{n}"/>' for n in self.nodes) + '</node>'
            return '<node>' + ''.join(f'<interface name="{n}"/>' for n in self.props) + '</node>'
        if method == 'Get':
            assert interface == PROPS
            return self.props[args[0]][args[1]]
        if method == 'Create':
            return ROOT + '/SMS/9'
        if method == 'Send':
            if self.send_timeout:
                raise TimeoutError('private SMS +84900111222 fixture OTP')
            return None
        if method in ('Initiate', 'Respond'):
            return 'Synthetic network reply'
        if method in ('Enable', 'Cancel', 'SetCurrentModes'):
            return None
        raise AssertionError('Unexpected DBus method: ' + method)

    def close(self):
        self.closed = True


@pytest.fixture
def make_modem(tmp_path, monkeypatch):
    def make(bus):
        journal = OperationJournal(tmp_path)
        # The product is Linux-only. Windows fixtures cannot fsync a directory
        # handle, while file fsync and exclusive attempt creation remain real.
        monkeypatch.setattr(journal, '_sync_directory', lambda: None)
        radio = RadioPreference(tmp_path / 'radio')
        monkeypatch.setattr(radio, '_sync_directory', lambda: None)
        return ModemManager(bus_factory=lambda: bus, journal=journal, radio=radio, lock_factory=nullcontext)
    return make


def request(action='send', **values):
    return {'action': action, 'operation': str(uuid.uuid4()), 'confirm': True, **values}


def test_missing_sim_is_read_only_and_exposes_no_identifiers(make_modem, tmp_path):
    bus = Bus(sim=False)
    modem = make_modem(bus)
    result = modem.call('status')
    assert result['sim_missing'] and not result['can_send'] and not result['can_ussd']
    assert result['mobile_data'] == 'UNVERIFIED_NOT_CONFIGURED'
    assert all(c[2] in ('Introspect', 'Get') for c in bus.calls)
    assert {c[4][1] for c in bus.calls if c[2] == 'Get'} == {
        'State', 'StateFailedReason', 'Sim', 'UnlockRequired', 'SupportedModes', 'CurrentModes'}
    with pytest.raises(RuntimeError, match='SIM_REQUIRED'):
        modem.call(**request(number='+84900111222', text='test'))
    assert not list(tmp_path.iterdir())
    assert bus.closed


def test_inbox_reads_cached_messages_without_delete_or_identity(make_modem):
    bus = Bus()
    result = make_modem(bus).call('messages')
    assert result['messages'][0]['text'] == '<script>fixture OTP</script>'
    assert not result['limited']
    assert all(c[2] in ('Introspect', 'Get') for c in bus.calls)
    assert not any(c[4] and c[4][-1] in ('Imsi', 'EquipmentIdentifier', 'GetAll') for c in bus.calls)


def test_sms_uses_typed_dbus_and_durable_replay_guard(make_modem, tmp_path):
    bus = Bus()
    values = request(number='+84900111222', text="quote ', comma, test")
    result = make_modem(bus).call(**values)
    assert result['submitted'] and not result['delivery_verified']
    create = next(c for c in bus.calls if c[2] == 'Create')
    assert create[3] == 'a{sv}' and create[4] == [{'number': values['number'], 'text': values['text']}]
    with pytest.raises(RuntimeError, match='ALREADY_ATTEMPTED'):
        make_modem(bus).call(**values)
    assert sum(c[2] == 'Send' for c in bus.calls) == 1
    journal = next(tmp_path.glob('*.json')).read_text()
    assert 'COMPLETED' in journal and values['number'] not in journal and values['text'] not in journal


def test_uncertain_send_is_not_retried_after_new_client(make_modem, tmp_path):
    bus = Bus(send_timeout=True)
    values = request(number='+84900111222', text='fixture OTP')
    with pytest.raises(RuntimeError, match='^RESULT_UNKNOWN$'):
        make_modem(bus).call(**values)
    assert json.loads(next(tmp_path.glob('*.json')).read_text())['state'] == 'UNKNOWN'
    with pytest.raises(RuntimeError, match='ALREADY_ATTEMPTED'):
        make_modem(bus).call(**values)
    assert sum(c[2] == 'Send' for c in bus.calls) == 1


@pytest.mark.parametrize('action,session,method,values', [
    ('ussd_start', 1, 'Initiate', {'code': '*101#'}),
    ('ussd_reply', 3, 'Respond', {'text': '1'}),
    ('ussd_cancel', 2, 'Cancel', {}),
])
def test_ussd_methods_have_separate_session_gates(make_modem, action, session, method, values):
    bus = Bus(session=session)
    result = make_modem(bus).call(**request(action, **values))
    assert any(c[2] == method for c in bus.calls)
    assert result.get('reply') or result.get('cancelled')


def test_active_ussd_cannot_be_replaced_by_new_code(make_modem, tmp_path):
    bus = Bus(session=3)
    with pytest.raises(RuntimeError, match='USSD_SESSION_STATE'):
        make_modem(bus).call(**request('ussd_start', code='*101#'))
    assert not list(tmp_path.iterdir())
    assert not any(c[2] == 'Initiate' for c in bus.calls)


def test_locked_and_unregistered_modems_cannot_send(make_modem):
    bus = Bus(state=7)
    with pytest.raises(RuntimeError, match='NOT_REGISTERED'):
        make_modem(bus).call(**request(number='+84900111222', text='test'))
    bus.props[MODEM]['UnlockRequired'] = 2
    with pytest.raises(RuntimeError, match='SIM_LOCKED'):
        make_modem(bus).call(**request('ussd_start', code='*101#'))
    assert all(c[2] in ('Get', 'Introspect') for c in bus.calls)


@pytest.mark.parametrize('lock,label', [(3, 'pin2'), (5, 'puk2')])
def test_secondary_sim_locks_do_not_hide_registered_capabilities(make_modem, lock, label):
    bus = Bus()
    bus.props[MODEM]['UnlockRequired'] = lock
    modem = make_modem(bus)
    status = modem.call('status')
    assert status['registered'] and not status['sim_locked']
    assert status['secondary_lock'] == label
    assert status['can_send'] and status['can_ussd'] and status['can_set_mode']
    assert modem.call('messages')['messages']
    assert all(c[2] in ('Get', 'Introspect') for c in bus.calls)


@pytest.mark.parametrize('lock', [0, 2, 4, 6, 7, 17, 99])
def test_unknown_and_primary_locks_still_block_all_actions(make_modem, lock):
    bus = Bus()
    bus.props[MODEM]['UnlockRequired'] = lock
    modem = make_modem(bus)
    assert modem.call('status')['sim_locked']
    for values in [request(number='+84900111222', text='fixture'),
                   request('ussd_start', code='*101#'), {'action': 'messages'},
                   {'action': 'mode', 'allowed': 8, 'preferred': 0, 'confirm': True}]:
        with pytest.raises(RuntimeError, match='SIM_LOCKED'):
            modem.call(**values)
    assert all(c[2] in ('Get', 'Introspect') for c in bus.calls)


def test_explicit_locked_modem_state_is_not_overridden_by_secondary_lock(make_modem):
    bus = Bus(state=2)
    bus.props[MODEM]['UnlockRequired'] = 3
    status = make_modem(bus).call('status')
    assert status['sim_locked'] and not status['can_send'] and not status['can_enable']


def test_enable_only_sets_radio_and_never_creates_data_bearer(make_modem):
    bus = Bus(state=3)
    assert make_modem(bus).call('enable', confirm=True)['enable_requested']
    writes = [c for c in bus.calls if c[2] not in ('Get', 'Introspect')]
    assert [(c[1], c[2], c[3], c[4]) for c in writes] == [(MODEM, 'Enable', 'b', [True])]
    bus.props[MODEM]['State'] = 1
    with pytest.raises(RuntimeError, match='MODEM_UNAVAILABLE'):
        make_modem(bus).call('enable', confirm=True)
    assert sum(c[2] == 'Enable' for c in bus.calls) == 1


def test_4g_only_uses_advertised_mode_and_persists_for_new_client(make_modem, tmp_path):
    bus = Bus()
    result = make_modem(bus).call('mode', allowed=8, preferred=0, confirm=True)
    assert result['saved']
    call = next(c for c in bus.calls if c[2] == 'SetCurrentModes')
    assert call[3:] == ('(uu)', [(8, 0)])
    assert make_modem(bus).call('status')['saved_mode'] == [8, 0]
    assert json.loads((tmp_path / 'radio/radio.json').read_text()) == {'allowed': 8, 'preferred': 0}


def test_unsupported_mode_and_active_ussd_cannot_change_radio(make_modem):
    bus = Bus()
    with pytest.raises(RuntimeError, match='UNSUPPORTED'):
        make_modem(bus).call('mode', allowed=16, preferred=0, confirm=True)
    bus.props[USSD]['State'] = 3
    with pytest.raises(RuntimeError, match='USSD_SESSION_STATE'):
        make_modem(bus).call('mode', allowed=8, preferred=0, confirm=True)
    assert not any(c[2] == 'SetCurrentModes' for c in bus.calls)


@pytest.mark.parametrize('values', [
    request(number='1,number=999', text='test'),
    request(number='+84900111222', text='\0'),
    request(number='+84900111222', text='😀' * 36),
    request(number='+84900111222', text='test', operation='../escape'),
    request('ussd_start', code='AT+CFUN=1'),
    request('ussd_start', code='*101#', confirm=False),
    {'action': 'data_connect', 'apn': 'internet'},
    {'action': 'raw', 'command': 'AT'},
    {'action': 'mode', 'allowed': True, 'preferred': 0, 'confirm': True},
    {'action': 'mode', 'allowed': 8, 'preferred': 4, 'confirm': True},
    {'action': 'mode', 'allowed': -1, 'preferred': 0, 'confirm': True},
])
def test_invalid_actions_never_open_the_bus(values):
    modem = ModemManager(bus_factory=lambda: pytest.fail('Bus must not be opened'))
    with pytest.raises((ValueError, UnicodeError)):
        modem.call(**values)


def test_multiple_modems_fail_closed(make_modem):
    bus = Bus()
    bus.nodes = ['0', '1']
    with pytest.raises(RuntimeError, match='MODEM_AMBIGUOUS'):
        make_modem(bus).call('status')
    assert all(c[2] == 'Introspect' for c in bus.calls)

"""Typed ModemManager DBus client. Secrets and message bodies never enter logs."""
import json
import os
import re
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path

from .modem import validate_action

SERVICE = 'org.freedesktop.ModemManager1'
ROOT = '/org/freedesktop/ModemManager1'
MODEM = SERVICE + '.Modem'
SMS = SERVICE + '.Sms'
MESSAGING = MODEM + '.Messaging'
USSD = MODEM + '.Modem3gpp.Ussd'
PROPS = 'org.freedesktop.DBus.Properties'
INTRO = 'org.freedesktop.DBus.Introspectable'
STATES = {-1: 'failed', 0: 'unknown', 1: 'initializing', 2: 'locked',
          3: 'disabled', 4: 'disabling', 5: 'enabling', 6: 'enabled',
          7: 'searching', 8: 'registered', 9: 'disconnecting',
          10: 'connecting', 11: 'connected'}


class OperationJournal:
    """Persist attempt IDs before transmission; never automatically resend."""
    def __init__(self, directory='/var/lib/openstick/modem-operations'):
        self.directory = Path(directory)

    def begin(self, identity, kind):
        # Callers validate UUIDs before any path construction.
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        target = self.directory / (identity + '.json')
        record = {'kind': kind, 'state': 'STARTED', 'created_at': time.time()}
        try:
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise RuntimeError('ALREADY_ATTEMPTED') from None
        with os.fdopen(fd, 'w', encoding='utf-8') as output:
            json.dump(record, output)
            output.flush()
            os.fsync(output.fileno())
        self._sync_directory()
        return target, record

    def _sync_directory(self):
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def finish(self, receipt, outcome):
        target, record = receipt
        record = {**record, 'state': outcome}
        temporary = target.with_suffix('.tmp')
        with temporary.open('w', encoding='utf-8') as output:
            os.chmod(temporary, 0o600)
            json.dump(record, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        self._sync_directory()


class RadioPreference:
    def __init__(self, directory='/var/lib/openstick'):
        self.directory = Path(directory)

    def load(self):
        try:
            value = json.loads((self.directory / 'radio.json').read_text())
            validate_action({'action': 'mode', 'confirm': True, **value})
            return [value['allowed'], value['preferred']]
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def save(self, allowed, preferred):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = self.directory / 'radio.tmp'
        with temporary.open('w') as output:
            os.chmod(temporary, 0o600)
            json.dump({'allowed': allowed, 'preferred': preferred}, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, self.directory / 'radio.json')
        self._sync_directory()

    def _sync_directory(self):
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


@contextmanager
def modem_lock():
    import fcntl
    directory = Path('/run/openstick')
    directory.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(directory / 'modem.lock', os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('MODEM_BUSY') from None
        yield
    finally:
        os.close(fd)


def system_bus():
    # This dependency exists only on the Linux device, not the Windows Manager.
    import dbus
    return dbus.SystemBus(private=True)


class ModemManager:
    def __init__(self, *, bus_factory=system_bus, journal=None, radio=None, lock_factory=modem_lock):
        self.bus_factory = bus_factory
        self.journal = journal or OperationJournal()
        self.radio = radio or RadioPreference()
        self.lock_factory = lock_factory

    def call(self, action, **values):
        validate_action({'action': action, **values})
        with self.lock_factory():
            return self._call(action, values)

    def _call(self, action, values):
        bus = self.bus_factory()
        try:
            def invoke(path, interface, method, signature='', args=(), timeout=15):
                return bus.call_blocking(SERVICE, path, interface, method,
                                         signature, list(args), timeout=timeout)

            # Introspection discovers paths/interfaces without fetching SIM or
            # device identity properties via GetAll/GetManagedObjects.
            tree = ET.fromstring(str(invoke(ROOT + '/Modem', INTRO, 'Introspect')))
            names = [n.get('name', '') for n in tree.findall('node')]
            paths = [ROOT + '/Modem/' + n for n in names if re.fullmatch(r'[0-9]+', n)]
            if not paths:
                raise RuntimeError('MODEM_UNAVAILABLE')
            if len(paths) != 1:
                raise RuntimeError('MODEM_AMBIGUOUS')
            path = paths[0]
            xml = ET.fromstring(str(invoke(path, INTRO, 'Introspect')))
            interfaces = {n.get('name') for n in xml.findall('interface')}

            def get(interface, name, object_path=path):
                return invoke(object_path, PROPS, 'Get', 'ss', (interface, name))

            state = int(get(MODEM, 'State'))
            failed_reason = int(get(MODEM, 'StateFailedReason'))
            sim = str(get(MODEM, 'Sim'))
            unlock = int(get(MODEM, 'UnlockRequired'))
            present = sim not in ('', '/') and failed_reason != 2
            # ModemManager treats NONE, SIM_PIN2 and SIM_PUK2 as operational.
            # Secondary locks must not be confused with the primary SIM PIN.
            unlocked = unlock in (1, 3, 5) and state != 2
            messaging = MESSAGING in interfaces and present and unlocked
            ussd = USSD in interfaces and present and unlocked
            registered = state >= 8
            session = int(get(USSD, 'State')) if ussd else 0
            modes = [[int(a), int(p)] for a, p in get(MODEM, 'SupportedModes')]
            modes = [m for m in modes if m[0] and not m[1] & ~m[0]][:64]
            current_mode = [int(n) for n in get(MODEM, 'CurrentModes')]
            status = {'state': STATES.get(state, 'unknown'), 'sim_present': present,
                      'sim_missing': failed_reason == 2, 'sim_locked': present and not unlocked,
                      'secondary_lock': {3: 'pin2', 5: 'puk2'}.get(unlock),
                      'registered': registered, 'sms_available': messaging,
                      'can_send': messaging and registered, 'ussd_available': ussd,
                      'can_ussd': ussd and registered, 'ussd_state': session,
                      'can_enable': present and unlocked and state == 3,
                      'supported_modes': modes, 'current_mode': current_mode,
                      'saved_mode': self.radio.load(),
                      'can_set_mode': present and unlocked and state >= 6 and bool(modes),
                      'mobile_data': 'UNVERIFIED_NOT_CONFIGURED', 'verification': 'UNVERIFIED'}
            if action == 'status':
                if ussd:
                    status['ussd_prompt'] = str(get(USSD, 'NetworkRequest'))[:8192]
                    status['ussd_notification'] = str(get(USSD, 'NetworkNotification'))[:8192]
                return status
            if not present:
                raise RuntimeError('SIM_REQUIRED')
            if not unlocked:
                raise RuntimeError('SIM_LOCKED')
            if action == 'enable':
                if state == 3:
                    invoke(path, MODEM, 'Enable', 'b', (True,), timeout=60)
                elif state < 6:
                    raise RuntimeError('MODEM_UNAVAILABLE')
                return {'enable_requested': True}
            if action == 'mode':
                pair = [values['allowed'], values['preferred']]
                if pair not in modes:
                    raise RuntimeError('UNSUPPORTED')
                if state < 6:
                    raise RuntimeError('NOT_REGISTERED')
                if session in (2, 3):
                    raise RuntimeError('USSD_SESSION_STATE')
                invoke(path, MODEM, 'SetCurrentModes', '(uu)', (tuple(pair),), timeout=60)
                self.radio.save(*pair)
                return {'mode_requested': pair, 'saved': True}
            if action == 'messages':
                if not messaging:
                    raise RuntimeError('UNSUPPORTED')
                messages = list(get(MESSAGING, 'Messages'))
                result = []
                for item in messages[-20:]:
                    item = str(item)
                    if not re.fullmatch(re.escape(ROOT) + r'/SMS/[0-9]+', item):
                        continue
                    row = {k.lower(): str(get(SMS, k, item))[:4096]
                           for k in ('Number', 'Text', 'Timestamp')}
                    row['state'] = int(get(SMS, 'State', item))
                    result.append(row)
                return {'messages': result, 'limited': len(messages) > 20}
            if not registered:
                raise RuntimeError('NOT_REGISTERED')
            if action == 'send' and not messaging:
                raise RuntimeError('UNSUPPORTED')
            if action.startswith('ussd_'):
                if not ussd:
                    raise RuntimeError('UNSUPPORTED')
                if ((action == 'ussd_start' and session != 1)
                        or (action == 'ussd_reply' and session != 3)
                        or (action == 'ussd_cancel' and session not in (2, 3))):
                    raise RuntimeError('USSD_SESSION_STATE')
            receipt = self.journal.begin(values['operation'], action)
            try:
                if action == 'send':
                    sms = str(invoke(path, MESSAGING, 'Create', 'a{sv}',
                                     ({'number': values['number'], 'text': values['text']},)))
                    if not re.fullmatch(re.escape(ROOT) + r'/SMS/[0-9]+', sms):
                        raise RuntimeError('INVALID_SMS_PATH')
                    invoke(sms, SMS, 'Send', timeout=60)
                    result = {'submitted': True, 'delivery_verified': False}
                elif action == 'ussd_start':
                    reply = invoke(path, USSD, 'Initiate', 's', (values['code'],), timeout=60)
                    result = {'reply': str(reply)[:8192]}
                elif action == 'ussd_reply':
                    reply = invoke(path, USSD, 'Respond', 's', (values['text'],), timeout=60)
                    result = {'reply': str(reply)[:8192]}
                elif action == 'ussd_cancel':
                    invoke(path, USSD, 'Cancel', timeout=30)
                    result = {'cancelled': True}
                else:
                    raise ValueError('INPUT_INVALID')
                self.journal.finish(receipt, 'COMPLETED')
                return {**result, 'operation': values['operation']}
            except Exception:
                self.journal.finish(receipt, 'UNKNOWN')
                raise RuntimeError('RESULT_UNKNOWN') from None
        finally:
            bus.close()


def watch_radio():
    """Enable a ready unlocked SIM for SMS; never create a data bearer."""
    modem = ModemManager()
    attempts = 0
    mode_attempts = 0
    applied = None
    while True:
        try:
            status = modem.call('status')
            if status['can_enable'] and attempts < 3:
                attempts += 1
                modem.call('enable', confirm=True)
            preference = status['saved_mode']
            if (preference and preference != applied and mode_attempts < 3
                    and status['can_set_mode'] and status['ussd_state'] not in (2, 3)
                    and preference in status['supported_modes']):
                if status['current_mode'] != preference:
                    mode_attempts += 1
                    modem.call('mode', allowed=preference[0], preferred=preference[1], confirm=True)
                applied = preference
        except Exception:
            pass  # No raw modem/SIM/message data in service logs.
        time.sleep(30)


if __name__ == '__main__':
    watch_radio()

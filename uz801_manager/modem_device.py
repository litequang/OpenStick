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
THREEGPP = MODEM + '.Modem3gpp'
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

    def finish(self, receipt, outcome, failure=None):
        target, record = receipt
        record = {**record, 'state': outcome}
        if failure:
            record['failure'] = failure  # Fixed category, never raw DBus error text.
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
    def __init__(self, *, bus_factory=system_bus, journal=None, radio=None, lock_factory=modem_lock,
                 ussd_grace=12, clock=time.monotonic, sleep=time.sleep, ussd_transport=None):
        self.bus_factory = bus_factory
        self.journal = journal or OperationJournal()
        self.radio = radio or RadioPreference()
        self.lock_factory = lock_factory
        self.ussd_grace, self.clock, self.sleep = ussd_grace, clock, sleep
        from .ussd_qmi import QmiUssd
        self.ussd_transport = ussd_transport or QmiUssd()

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
            qmi_available = ussd and self.ussd_transport.available()
            qmi_session = self.ussd_transport.status() if qmi_available else {}
            if qmi_session.get('state') in (2, 3):session = qmi_session['state']
            retry_after = max(0, int(qmi_session.get('cooldown_until', 0) - time.time()) + 1) if qmi_session.get('cooldown_until') else 0
            use_qmi = qmi_available and (action != 'ussd_cancel' or qmi_session.get('cid'))
            modes = [[int(a), int(p)] for a, p in get(MODEM, 'SupportedModes')]
            modes = [m for m in modes if m[0] and not m[1] & ~m[0]][:64]
            current_mode = [int(n) for n in get(MODEM, 'CurrentModes')]
            def optional(interface, name):
                try:
                    return get(interface, name)
                except Exception:
                    return None  # Unsupported telemetry is unknown, never zero bars.

            quality = optional(MODEM, 'SignalQuality')
            signal = None
            recent = False
            if quality is not None and len(quality) == 2:
                percent = int(quality[0])
                if 0 <= percent <= 100:
                    signal, recent = percent, bool(quality[1])
            technology = optional(MODEM, 'AccessTechnologies')
            operator = optional(THREEGPP, 'OperatorName') if THREEGPP in interfaces else None
            registration = optional(THREEGPP, 'RegistrationState') if THREEGPP in interfaces else None
            status = {'state': STATES.get(state, 'unknown'), 'sim_present': present,
                      'sim_missing': failed_reason == 2, 'sim_locked': present and not unlocked,
                      'secondary_lock': {3: 'pin2', 5: 'puk2'}.get(unlock),
                      'operator_name': str(operator)[:80] if operator is not None else None,
                      'registration_state': int(registration) if registration is not None else None,
                      'access_technologies': int(technology) if technology is not None else None,
                      'signal_percent': signal, 'signal_recent': recent,
                      'registered': registered, 'sms_available': messaging,
                      'can_send': messaging and registered, 'ussd_available': ussd,
                      'can_ussd': ussd and registered and not retry_after, 'ussd_state': session,
                      'ussd_retry_after_seconds': retry_after,
                      'ussd_backend': 'qmi-ascii' if qmi_available else 'modemmanager',
                      'can_enable': present and unlocked and state == 3,
                      'supported_modes': modes, 'current_mode': current_mode,
                      'saved_mode': self.radio.load(),
                      'can_set_mode': present and unlocked and state >= 6 and bool(modes),
                      'mobile_data': 'UNVERIFIED_NOT_CONFIGURED', 'verification': 'UNVERIFIED'}
            if action == 'status':
                if ussd:
                    status['ussd_prompt'] = str(get(USSD, 'NetworkRequest'))[:8192]
                    status['ussd_notification'] = str(get(USSD, 'NetworkNotification'))[:8192]
                    if qmi_session:
                        status['ussd_prompt'] = str(qmi_session.get('prompt', ''))[:8192]
                        status['ussd_notification'] = str(qmi_session.get('notification', ''))[:8192]
                        status['ussd_received_at'] = qmi_session.get('received_at')
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
            if action in ('messages', 'delete'):
                if not messaging:
                    raise RuntimeError('UNSUPPORTED')
                messages = list(get(MESSAGING, 'Messages'))
                result = []
                for item in (messages[-200:] if action == 'messages' else [values['path']]):
                    item = str(item)
                    if item not in [str(p) for p in messages]:raise RuntimeError('MESSAGE_NOT_ON_MODEM')
                    if not re.fullmatch(re.escape(ROOT) + r'/SMS/[0-9]+', item):
                        continue
                    row = {k.lower(): str(get(SMS, k, item))[:4096]
                           for k in ('Number', 'Text', 'Timestamp')}
                    row['state'] = int(get(SMS, 'State', item))
                    row['path'] = item
                    if action == 'delete':
                        from .sms_archive import message_fingerprint
                        if message_fingerprint(row) != values['fingerprint']:raise RuntimeError('MESSAGE_CHANGED')
                        try:invoke(path, MESSAGING, 'Delete', 'o', (item,))
                        except Exception:raise RuntimeError('RESULT_UNKNOWN') from None
                        return {'deleted': True}
                    result.append(row)
                return {'messages': result, 'limited': len(messages) > 200}
            if not registered:
                raise RuntimeError('NOT_REGISTERED')
            if action == 'send' and not messaging:
                raise RuntimeError('UNSUPPORTED')
            if action.startswith('ussd_'):
                if not ussd:
                    raise RuntimeError('UNSUPPORTED')
                if action == 'ussd_start' and retry_after:raise RuntimeError('MODEM_BUSY')
                if ((action == 'ussd_start' and session != 1)
                        or (action == 'ussd_reply' and session != 3)
                        or (action == 'ussd_cancel' and session not in (2, 3))):
                    raise RuntimeError('USSD_SESSION_STATE')
            baseline = {}
            if action in ('ussd_start', 'ussd_reply') and not use_qmi:
                baseline = {name: str(get(USSD, name))[:8192]
                            for name in ('NetworkRequest', 'NetworkNotification')}
            receipt = self.journal.begin(values['operation'], action)
            try:
                if action.startswith('ussd_') and use_qmi:
                    result = self.ussd_transport.call(action, **values)
                elif action == 'send':
                    sms = str(invoke(path, MESSAGING, 'Create', 'a{sv}',
                                     ({'number': values['number'], 'text': values['text']},)))
                    if not re.fullmatch(re.escape(ROOT) + r'/SMS/[0-9]+', sms):
                        raise RuntimeError('INVALID_SMS_PATH')
                    invoke(sms, SMS, 'Send', timeout=60)
                    result = {'submitted': True, 'delivery_verified': False, 'path': sms}
                elif action == 'ussd_start':
                    # QMI USSD waits up to 100 seconds in ModemManager. The
                    # caller must not abandon the result at 60 seconds.
                    reply = invoke(path, USSD, 'Initiate', 's', (values['code'],), timeout=115)
                    result = {'reply': str(reply)[:8192]}
                elif action == 'ussd_reply':
                    reply = invoke(path, USSD, 'Respond', 's', (values['text'],), timeout=115)
                    result = {'reply': str(reply)[:8192]}
                elif action == 'ussd_cancel':
                    # QMI cancellation has the same 100-second modem timeout.
                    invoke(path, USSD, 'Cancel', timeout=115)
                    result = {'cancelled': True, 'modem_acknowledged': True}
                else:
                    raise ValueError('INPUT_INVALID')
                if action in ('ussd_start', 'ussd_reply') and not use_qmi:
                    if not result.get('reply'):raise RuntimeError('USSD_EMPTY_REPLY')
                    result.update(response_source='MODEMMANAGER_METHOD', modem_acknowledged=True)
                self.journal.finish(receipt, 'COMPLETED')
                return {**result, 'operation': values['operation']}
            except Exception as exc:
                name = ''
                if callable(getattr(exc, 'get_dbus_name', None)):
                    name = exc.get_dbus_name()
                categories = {
                    SERVICE + '.Error.Core.Unsupported': 'UNSUPPORTED',
                    SERVICE + '.Error.Core.Failed': 'MODEM_FAILED',
                    SERVICE + '.Error.MobileEquipment.NotSupported': 'UNSUPPORTED',
                    SERVICE + '.Error.MobileEquipment.NoNetwork': 'NO_NETWORK',
                    SERVICE + '.Error.MobileEquipment.NetworkTimeout': 'TIMEOUT',
                    'org.freedesktop.DBus.Error.NoReply': 'TIMEOUT',
                    'org.freedesktop.DBus.Error.Timeout': 'TIMEOUT',
                }
                failure = 'TIMEOUT' if isinstance(exc, TimeoutError) else categories.get(name, 'OPERATION_FAILED')
                if action == 'ussd_cancel' and not use_qmi:
                    # QMI resets the exported session even when Cancel returns
                    # an error (e.g. the network has already ended it). Confirm
                    # that state instead of falsely leaving a stuck-session UI.
                    try:ended = int(get(USSD, 'State')) == 1
                    except Exception:ended = False
                    if ended:
                        self.journal.finish(receipt, 'COMPLETED')
                        return {'cancelled': True, 'modem_acknowledged': False,
                                'operation': values['operation']}
                if baseline and failure not in ('UNSUPPORTED',):
                    # A QMI method error can precede a separate network URC.
                    # Observe only changed, nonempty properties; cached content
                    # from an earlier request must never become a new result.
                    deadline = self.clock() + self.ussd_grace
                    while True:
                        try:
                            current = int(get(USSD, 'State'))
                            for prop in ('NetworkRequest', 'NetworkNotification'):
                                reply = str(get(USSD, prop))[:8192]
                                if (reply and reply != baseline[prop]
                                        and (prop != 'NetworkRequest' or current == 3)):
                                    self.journal.finish(receipt, 'RESPONSE_OBSERVED')
                                    return {'reply': reply, 'response_source': prop,
                                            'modem_acknowledged': False,
                                            'operation': values['operation']}
                        except Exception:
                            break
                        remaining = deadline - self.clock()
                        if remaining <= 0:break
                        self.sleep(min(.5, remaining))
                self.journal.finish(receipt, 'UNKNOWN', failure)
                from .ussd_qmi import ERRORS as QMI_ERRORS
                error = (str(exc) if use_qmi and str(exc) in QMI_ERRORS else
                         {'UNSUPPORTED': 'USSD_UNSUPPORTED', 'NO_NETWORK': 'USSD_NO_NETWORK',
                          'TIMEOUT': 'USSD_TIMEOUT'}.get(failure, 'USSD_FAILED')
                         if action.startswith('ussd_') else 'RESULT_UNKNOWN')
                raise RuntimeError(error) from None
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

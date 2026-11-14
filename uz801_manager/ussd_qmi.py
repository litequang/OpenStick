"""Typed libqmi USSD transport, isolated from SMS and packet-data operations.

ASCII commands avoid the device firmware's unreliable UCS2 request path.
Every result comes from the current QMI response/indication, including when
its text matches an earlier result. No automatic USSD retransmission.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SESSION = Path('/run/openstick/ussd-qmi.json')
ERRORS = {'USSD_FAILED', 'USSD_TIMEOUT', 'USSD_NO_NETWORK', 'USSD_UNSUPPORTED',
          'USSD_SESSION_STATE', 'USSD_MONITOR_UNAVAILABLE'}


def read_session(path=SESSION):
    try:
        value = json.loads(path.read_text())
        if (type(value.get('state')) is not int or value['state'] not in (1, 2, 3)
                or (value.get('cid') is not None and (type(value['cid']) is not int or not 1 <= value['cid'] <= 255))):return {}
        return value
    except (OSError, ValueError, TypeError, AttributeError):return {}


def write_session(value, path=SESSION):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as output:
        os.fchmod(output.fileno(), 0o600)
        json.dump(value, output);output.flush();os.fsync(output.fileno())
    os.replace(temporary, path)


class QmiUssd:
    def __init__(self, *, run=subprocess.run, session=SESSION):
        self.run, self.session = run, session

    def available(self):
        return (sys.platform == 'linux' and len(list(Path('/dev').glob('wwan*qmi*'))) == 1
                and importlib.util.find_spec('gi') is not None)

    def status(self):return read_session(self.session)

    def call(self, action, **values):
        from .modem import validate_action
        payload = {'action': action, **values}
        validate_action(payload)
        if action not in ('ussd_start', 'ussd_reply', 'ussd_cancel'):raise ValueError('INPUT_INVALID')
        try:
            result = self.run([sys.executable, '-m', 'uz801_manager.ussd_qmi'],
                input=json.dumps(payload).encode(), capture_output=True, timeout=145,
                cwd=str(Path(__file__).resolve().parent.parent), shell=False)
        except subprocess.TimeoutExpired:raise RuntimeError('USSD_TIMEOUT') from None
        if len(result.stdout) > 65536:raise RuntimeError('USSD_FAILED')
        try:reply = json.loads(result.stdout)
        except (ValueError, UnicodeError):raise RuntimeError('USSD_FAILED') from None
        if not isinstance(reply, dict):raise RuntimeError('USSD_FAILED')
        if result.returncode or 'error' in reply:
            raise RuntimeError(reply.get('error') if reply.get('error') in ERRORS else 'USSD_FAILED')
        if action == 'ussd_cancel':
            if reply.get('cancelled') is not True:raise RuntimeError('USSD_FAILED')
        elif (not isinstance(reply.get('reply'), str) or not reply['reply'] or len(reply['reply']) > 8192
                or reply.get('ussd_state') not in (1, 3)
                or reply.get('response_source') not in ('QMI_METHOD_RESPONSE', 'QMI_USSD_INDICATION')):
            raise RuntimeError('USSD_FAILED')
        return reply


def execute(payload):
    import gi
    gi.require_version('Qmi', '1.0')
    from gi.repository import Gio, GLib, Qmi
    from .modem import validate_action
    action = validate_action(payload)
    if action not in ('ussd_start', 'ussd_reply', 'ussd_cancel'):raise ValueError('INPUT_INVALID')
    paths = list(Path('/dev').glob('wwan*qmi*'))
    if len(paths) != 1:raise RuntimeError('USSD_MONITOR_UNAVAILABLE')
    previous = read_session()
    if ((action == 'ussd_start' and previous.get('state', 1) != 1)
            or (action == 'ussd_reply' and previous.get('state') != 3)
            or (action == 'ussd_cancel' and previous.get('state') not in (2, 3))):
        raise RuntimeError('USSD_SESSION_STATE')
    loop = GLib.MainLoop();cancel = Gio.Cancellable()
    state = {'device': None, 'client': None, 'finished': False, 'sent': False,
             'session': {**previous}, 'result': None, 'error': None}

    def save():
        state['session'].update(operation=payload['operation'], updated_at=time.time())
        write_session(state['session'])

    def closed(device, result, *_):
        try:device.close_finish(result)
        except Exception:pass
        loop.quit()

    def close_device():
        if state['device']:state['device'].close_async(3, None, closed, None)
        else:loop.quit()

    def released(device, result, *_):
        try:
            device.release_client_finish(result)
            if state['session'].get('state') == 1:
                state['session']['cid'] = None;save()
        except Exception:
            if action == 'ussd_cancel' and state['result'] and not state['result'].get('modem_acknowledged'):
                state['error'] = 'USSD_FAILED';state['session']['state'] = 2;save()
        close_device()

    def finish(result=None, error=None):
        if state['finished']:return False
        state.update(finished=True, result=result, error=error)
        cancel.cancel()
        if state['sent']:
            try:save()
            except OSError:state['error'] = 'USSD_FAILED'
        if state['client']:
            # Keep the CID only for an interactive or uncertain active session.
            flags = Qmi.DeviceReleaseClientFlags.RELEASE_CID if state['session'].get('state') == 1 else Qmi.DeviceReleaseClientFlags.NONE
            state['device'].release_client(state['client'], flags, 3, None, released, None)
        else:close_device()
        return False

    def decode(output):
        try:return b''.join(int(n).to_bytes(2, 'little') for n in output.get_uss_data_utf16()).decode('utf-16-le')
        except GLib.Error:
            scheme, data = output.get_uss_data()
            if scheme == Qmi.VoiceUssDataCodingScheme.ASCII:return bytes(data).decode('ascii')
            if scheme == Qmi.VoiceUssDataCodingScheme.UCS2:return bytes(data).decode('utf-16-be')
            raise ValueError('USSD_ENCODING_UNSUPPORTED')

    def response(output, source):
        if state['finished']:return
        try:reply = decode(output)[:8192]
        except Exception:return
        if not reply:return
        try:interactive = output.get_user_action() == Qmi.VoiceUserAction.REQUIRED
        except (AttributeError, GLib.Error):interactive = False
        state['session'].update(state=3 if interactive else 1,
            prompt=reply if interactive else '', notification='' if interactive else reply,
            received_at=time.time())
        finish({'reply': reply, 'ussd_state': state['session']['state'],
                'response_source': source, 'modem_acknowledged': source == 'QMI_METHOD_RESPONSE'})

    def indication(client, output):response(output, 'QMI_USSD_INDICATION')

    def session_released(client, output):
        if state['finished']:return
        state['session']['state'] = 1
        if action == 'ussd_cancel':finish({'cancelled': True, 'modem_acknowledged': True})
        # Give a paired response indication a short opportunity to arrive.
        else:GLib.timeout_add_seconds(2, lambda: finish(error='USSD_FAILED'))

    def failure(error):
        if state['finished']:return
        category = 'USSD_FAILED'
        if isinstance(error, GLib.Error):
            try:
                name = Qmi.ProtocolError(error.code).value_name if error.domain == GLib.quark_to_string(Qmi.protocol_error_quark()) else ''
            except (ValueError, AttributeError):name = ''
            if name.endswith('_NO_NETWORK_FOUND'):category = 'USSD_NO_NETWORK'
            elif name.endswith('_NOT_SUPPORTED'):category = 'USSD_UNSUPPORTED'
        if action == 'ussd_cancel' and state['sent']:
            state['session'].update(state=1, prompt='', cooldown_until=time.time() + 30)
            finish({'cancelled': True, 'local_session_closed': True, 'modem_acknowledged': False})
        elif not state['sent']:finish(error='USSD_MONITOR_UNAVAILABLE')
        else:GLib.timeout_add_seconds(12, lambda: finish(error=category))

    def sent(client, result, *_):
        if state['finished']:return
        try:
            if action == 'ussd_start':output = client.originate_ussd_finish(result)
            elif action == 'ussd_reply':output = client.answer_ussd_finish(result)
            else:output = client.cancel_ussd_finish(result)
            output.get_result()
            if action == 'ussd_cancel':
                state['session'].update(state=1, prompt='')
                finish({'cancelled': True, 'modem_acknowledged': True})
            elif action == 'ussd_start':response(output, 'QMI_METHOD_RESPONSE')
            # Empty ACKs remain pending until this request's own indication.
        except Exception as error:failure(error)

    def registered(client, result, *_):
        try:
            client.indication_register_finish(result).get_result()
            state['session'].update(cid=int(client.get_cid()), state=2, prompt='')
            state['sent'] = True;save()  # Persist before the single transmission.
            if action == 'ussd_cancel':client.cancel_ussd(None, 100, cancel, sent, None)
            else:
                text = payload['code'] if action == 'ussd_start' else payload['text']
                scheme = Qmi.VoiceUssDataCodingScheme.ASCII if text.isascii() else Qmi.VoiceUssDataCodingScheme.UCS2
                data = list(text.encode('ascii' if text.isascii() else 'utf-16-be'))
                value = Qmi.MessageVoiceOriginateUssdInput.new() if action == 'ussd_start' else Qmi.MessageVoiceAnswerUssdInput.new()
                value.set_uss_data(scheme, data)
                if action == 'ussd_start':client.originate_ussd(value, 100, cancel, sent, None)
                else:client.answer_ussd(value, 100, cancel, sent, None)
        except Exception as error:failure(error)

    def allocated(device, result, *_):
        try:
            client = device.allocate_client_finish(result);state['client'] = client
            # New allocations are released if setup fails before transmission.
            state['session'].update(cid=int(client.get_cid()), state=previous.get('state', 1))
            client.connect('ussd', indication);client.connect('release-ussd', session_released)
            value = Qmi.MessageVoiceIndicationRegisterInput.new();value.set_ussd_notification_events(True)
            client.indication_register(value, 5, cancel, registered, None)
        except Exception as error:failure(error)

    def opened(device, result, *_):
        try:
            device.open_finish(result)
            device.allocate_client(Qmi.Service.VOICE, previous.get('cid') or Qmi.CID_NONE, 5, cancel, allocated, None)
        except Exception as error:failure(error)

    def created(source, result, *_):
        try:
            device = Qmi.Device.new_finish(result);state['device'] = device
            device.open(Qmi.DeviceOpenFlags.PROXY, 5, cancel, opened, None)
        except Exception as error:failure(error)

    GLib.timeout_add_seconds(125, lambda: finish(error='USSD_TIMEOUT'))
    Qmi.Device.new(Gio.File.new_for_path(str(paths[0])), cancel, created, None);loop.run()
    if state['error']:raise RuntimeError(state['error'])
    return state['result'] or {}


if __name__ == '__main__':
    try:
        payload = json.loads(sys.stdin.buffer.read(4097))
        print(json.dumps(execute(payload), ensure_ascii=True), flush=True)
    except Exception as error:
        code = str(error)
        print(json.dumps({'error': code if code in ERRORS else 'USSD_FAILED'}), flush=True)
        sys.exit(1)

"""USB portal modem jobs. No raw AT/QMI, firmware or mobile-data operations."""
import re
import threading
import time
import uuid

from flask import abort, jsonify, redirect, render_template, request


def validate_action(body):
    if not isinstance(body, dict):
        raise ValueError('INPUT_INVALID')
    action = body.get('action')
    fields = {
        'status': set(), 'messages': set(), 'archive': set(), 'enable': {'confirm'},
        'archive_delete': {'id', 'delete_modem', 'confirm'},
        'delete': {'path', 'fingerprint', 'confirm'},
        'mode': {'allowed', 'preferred', 'confirm'},
        'send': {'number', 'text', 'operation', 'confirm'},
        'ussd_start': {'code', 'operation', 'confirm'},
        'ussd_reply': {'text', 'operation', 'confirm'},
        'ussd_cancel': {'operation', 'confirm'},
    }
    if not isinstance(action, str) or action not in fields or set(body) != fields[action] | {'action'}:
        raise ValueError('INPUT_INVALID')
    if 'confirm' in body and body['confirm'] is not True:
        raise ValueError('CONFIRM_REQUIRED')
    if 'operation' in body:
        value = body['operation']
        if not isinstance(value, str) or str(uuid.UUID(value)) != value:
            raise ValueError('INPUT_INVALID')
    if action == 'archive_delete':
        if (not isinstance(body['id'], str) or str(uuid.UUID(body['id'])) != body['id']
                or type(body['delete_modem']) is not bool):raise ValueError('INPUT_INVALID')
    if action == 'delete':
        if (not isinstance(body['path'], str)
                or not re.fullmatch(r'/org/freedesktop/ModemManager1/SMS/[0-9]+', body['path'])
                or not isinstance(body['fingerprint'], str)
                or not re.fullmatch('[0-9a-f]{64}', body['fingerprint'])):raise ValueError('INPUT_INVALID')
    if action == 'mode':
        for key in ('allowed', 'preferred'):
            value = body[key]
            if type(value) is not int or not 0 <= value <= 0xffffffff:
                raise ValueError('INPUT_INVALID')
        if not body['allowed'] or body['preferred'] & ~body['allowed']:
            raise ValueError('INPUT_INVALID')
    if action == 'send':
        if not isinstance(body['number'], str) or not re.fullmatch(r'\+?[0-9]{3,20}', body['number']):
            raise ValueError('INPUT_INVALID')
    if action in ('send', 'ussd_reply'):
        value = body['text']
        if (not isinstance(value, str) or not value.strip()
                or len(value.encode('utf-16-le')) > 140
                or any(ord(c) < 32 and c not in '\n\t' for c in value)):
            raise ValueError('INPUT_INVALID')
    if action == 'ussd_start':
        value = body['code']
        if not isinstance(value, str) or not re.fullmatch(r'[*#][*#0-9]{0,29}#', value):
            raise ValueError('INPUT_INVALID')
    return action


def register_modem_routes(app, backend, token):
    lock = threading.Lock()
    state = {'busy': False, 'result': {}, 'error': None}
    last_ussd = {}
    receipts = {}  # Small private result cache; polling tabs cannot replace it.
    app.extensions['modem'] = {'state': state}

    @app.get('/modem')
    def modem_page():
        return redirect('/modem/sms')

    @app.get('/modem/<page>')
    def modem_section(page):
        titles = {'sms': 'Gửi / nhận SMS', 'ussd': 'USSD', 'network': 'Mạng SIM'}
        if page not in titles:
            abort(404)
        return render_template('sms.html' if page == 'sms' else 'modem.html',
                               token=token, page=page, title=titles[page])

    @app.get('/api/modem/state')
    def modem_state():
        with lock:
            operation = request.args.get('operation')
            if operation is not None:
                if not re.fullmatch('[0-9a-f-]{36}', operation):return jsonify(error='INPUT_INVALID'), 400
                if operation not in receipts:return jsonify(error='OPERATION_NOT_FOUND'), 404
                return jsonify(receipts[operation])
            return jsonify(state)

    @app.post('/api/modem')
    def modem_action():
        body = request.get_json(silent=True)
        try:
            action = validate_action(body)
            if action == 'delete':raise ValueError('INPUT_INVALID')  # Internal verified archive reference only.
        except (ValueError, TypeError, UnicodeError, AttributeError):
            return jsonify(error='INPUT_INVALID'), 400
        with lock:
            if state['busy']:
                return jsonify(error='BUSY'), 409
            operation = body.get('operation')
            if operation in receipts:return jsonify(error='ALREADY_ATTEMPTED'), 409
            if operation:
                while len(receipts) >= 16:receipts.pop(next(iter(receipts)))
                receipts[operation] = {'busy': True, 'result': {}, 'error': None}
            state.update(busy=True, result={}, error=None)
            if action.startswith('ussd_'):
                last_ussd.clear()
                last_ussd.update(action=action, busy=True, result={}, error=None,
                                 started_at=time.time())

        def work():
            try:
                result = backend.call(action, **{k: v for k, v in body.items() if k != 'action'})
                with lock:
                    if action == 'status' and last_ussd:
                        result = {**result, 'last_ussd': dict(last_ussd)}
                    if action.startswith('ussd_'):
                        last_ussd.update(busy=False, result=result, finished_at=time.time())
                    state['result'] = result
            except Exception as exc:
                # Never return DBus errors, SMS contents, destinations or codes.
                allowed = {'SIM_REQUIRED', 'SIM_LOCKED', 'NOT_REGISTERED', 'UNSUPPORTED',
                           'MODEM_UNAVAILABLE', 'MODEM_AMBIGUOUS', 'ALREADY_ATTEMPTED',
                           'RESULT_UNKNOWN', 'USSD_SESSION_STATE', 'MODEM_BUSY',
                           'USSD_TIMEOUT', 'USSD_UNSUPPORTED', 'USSD_NO_NETWORK', 'USSD_FAILED', 'USSD_MONITOR_UNAVAILABLE',
                           'MESSAGE_NOT_FOUND', 'MESSAGE_NOT_ON_MODEM', 'MESSAGE_CHANGED'}
                code = str(exc)
                with lock:
                    state.update(result={}, error=code if code in allowed else 'MODEM_OPERATION_FAILED')
                    if action.startswith('ussd_'):
                        last_ussd.update(busy=False, error=state['error'], finished_at=time.time())
            finally:
                body.clear()
                with lock:
                    state['busy'] = False
                    if operation:receipts[operation] = dict(state)
        thread = threading.Thread(target=work, daemon=True)
        app.extensions['modem']['thread'] = thread
        thread.start()
        return jsonify(accepted=True), 202

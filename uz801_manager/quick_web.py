"""Quick Settings endpoints inherit USB/LAN Host, Origin, token and login guards."""
import threading
import uuid

from flask import jsonify, render_template, request

from .quick_settings import ERRORS, validate_quick


def register_quick_routes(app, backend, token):
    lock = threading.Lock()
    state = {'busy': False, 'operation': None, 'error': None}
    app.extensions['quick_settings'] = {'state': state}

    @app.get('/quick')
    def quick_page():
        return render_template('quick.html', page='quick', token=token)

    @app.get('/api/quick')
    def quick_status():
        try:
            return jsonify(backend.status())
        except Exception:
            return jsonify(error='QUICK_STATUS_UNAVAILABLE'), 503

    @app.get('/api/quick/wifi')
    def quick_wifi_options():
        try:return jsonify(backend.wifi.options())
        except Exception:return jsonify(error='WIFI_STATUS_UNAVAILABLE'), 503

    @app.get('/api/quick/operation/<identity>')
    def quick_receipt(identity):
        try:
            if str(uuid.UUID(identity)) != identity:
                raise ValueError()
            receipt = backend.receipt(identity)
        except (ValueError, TypeError):
            return jsonify(error='INPUT_INVALID'), 400
        with lock:
            if state['operation'] == identity:
                return jsonify(**receipt, busy=state['busy'], error=state['error'])
        return jsonify(**receipt, busy=receipt.get('state') == 'STARTED', error=receipt.get('failure'))

    @app.post('/api/quick')
    def quick_action():
        value = request.get_json(silent=True)
        try:
            validate_quick(value)
        except (ValueError, TypeError, AttributeError):
            return jsonify(error='INPUT_INVALID'), 400
        with lock:
            if state['busy']:
                return jsonify(error='NETWORK_BUSY'), 409
            if backend.receipt(value['operation']).get('state') != 'NOT_FOUND':
                return jsonify(error='ALREADY_ATTEMPTED'), 409
            state.update(busy=True, operation=value['operation'], error=None)

        def work():
            try:
                backend.call(value['action'], **{k: v for k, v in value.items() if k != 'action'})
            except Exception as error:
                with lock:
                    state['error'] = str(error) if str(error) in ERRORS else 'QUICK_OPERATION_FAILED'
            finally:
                value.clear()
                with lock:
                    state['busy'] = False
        worker = threading.Thread(target=work, daemon=True)
        app.extensions['quick_settings']['thread'] = worker
        worker.start()
        return jsonify(accepted=True), 202

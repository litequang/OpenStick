"""Private asynchronous Internet policy endpoints, under the portal guards."""
import threading

from flask import jsonify, render_template, request

from .network_policy import validate_policy


def register_network_routes(app, backend, token):
    lock = threading.Lock()
    state = {'busy': False, 'result': {}, 'error': None}
    app.extensions['network_policy'] = {'state': state}

    @app.get('/internet')
    def internet_page():
        return render_template('internet.html', token=token, page='wifi')

    @app.get('/api/internet/state')
    def internet_state():
        with lock:return jsonify(state)

    @app.post('/api/internet')
    def internet_action():
        body = request.get_json(silent=True)
        try:action = validate_policy(body)
        except (ValueError, TypeError, AttributeError):return jsonify(error='INPUT_INVALID'), 400
        with lock:
            if state['busy']:return jsonify(error='BUSY'), 409
            state.update(busy=True, result={}, error=None)

        def work():
            try:
                result = backend.call(action, **{k: v for k, v in body.items() if k != 'action'})
                with lock:state['result'] = result
            except Exception as exc:
                allowed = {'HOTSPOT_ACTIVE', 'CELLULAR_NOT_CONFIGURED', 'CELLULAR_ALREADY_ACTIVE',
                           'PROFILE_NOT_FOUND', 'PROFILE_ACTIVE', 'POLICY_CONFLICT', 'WIFI_SWITCH_FAILED',
                           'SWITCH_FAILED', 'ROLLBACK_FAILED', 'NETWORK_BUSY', 'DATA_DISCONNECT_FAILED'}
                with lock:state['error'] = str(exc) if str(exc) in allowed else 'NETWORK_OPERATION_FAILED'
            finally:
                body.clear()
                with lock:state['busy'] = False
        thread = threading.Thread(target=work, daemon=True)
        app.extensions['network_policy']['thread'] = thread
        thread.start()
        return jsonify(accepted=True), 202

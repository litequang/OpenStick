"""Private hotspot workflows; profiles are saved separately from activation."""
import threading

from flask import jsonify, render_template, request

from .hotspot import validate_hotspot

ERRORS = {'NETWORK_BUSY', 'MODEM_BUSY', 'HOTSPOT_ACTIVE', 'AP_UNSUPPORTED', 'CELLULAR_UNAVAILABLE',
          'CELLULAR_ALREADY_ACTIVE', 'HOTSPOT_NOT_CONFIGURED', 'SIM_NOT_READY', 'CHECKPOINT_UNAVAILABLE',
          'CELLULAR_NO_INTERNET', 'AP_START_FAILED', 'ROLLBACK_FAILED', 'HOTSPOT_START_FAILED',
          'HOTSPOT_CONFIRM_EXPIRED', 'POLICY_ACTIVE', 'SETUP_ACTIVE'}


def register_hotspot_routes(app, backend, token):
    lock = threading.Lock()
    state = {'busy': False, 'result': {}, 'error': None}
    app.extensions['hotspot'] = {'state': state}

    @app.get('/hotspot')
    def hotspot_page():
        return render_template('hotspot.html', token=token, page='wifi')

    @app.get('/api/hotspot/state')
    def hotspot_current():
        with lock:return jsonify(state)

    @app.post('/api/hotspot')
    def hotspot_action():
        value = request.get_json(silent=True)
        try:validate_hotspot(value)
        except (ValueError, TypeError, UnicodeError):return jsonify(error='INPUT_INVALID'), 400
        with lock:
            if state['busy']:return jsonify(error='BUSY'), 409
            state.update(busy=True, result={}, error=None)
        def work():
            try:
                result = backend.call(value['action'], **{k: v for k, v in value.items() if k != 'action'})
                with lock:state.update(result=result)
            except Exception as error:
                code = str(error)
                with lock:state.update(error=code if code in ERRORS else 'HOTSPOT_OPERATION_FAILED', result={})
            finally:
                value.clear()
                with lock:state['busy'] = False
        thread = threading.Thread(target=work, daemon=True)
        app.extensions['hotspot']['thread'] = thread
        thread.start()
        return jsonify(accepted=True), 202

"""Private hotspot workflows; profiles are saved separately from activation."""
import threading
import time

from flask import jsonify, render_template, request

from .hotspot import HOTSPOT_ERRORS, validate_hotspot

ERRORS = HOTSPOT_ERRORS


def register_hotspot_routes(app, backend, token):
    lock = threading.Lock()
    state = {'busy': False, 'result': {}, 'error': None, 'last_operation': None}
    app.extensions['hotspot'] = {'state': state}

    @app.get('/hotspot')
    def hotspot_page():
        return render_template('hotspot.html', token=token, page='wifi')

    @app.get('/api/hotspot/state')
    def hotspot_current():
        latest = None
        if hasattr(backend, 'last_operation'):
            try:latest = backend.last_operation()
            except Exception:pass
        with lock:
            candidates = [v for v in (latest, state['last_operation']) if v]
            return jsonify({**state, 'last_operation': max(candidates, key=lambda v: v['at']) if candidates else None})

    @app.post('/api/hotspot')
    def hotspot_action():
        value = request.get_json(silent=True)
        try:validate_hotspot(value)
        except (ValueError, TypeError, UnicodeError):return jsonify(error='INPUT_INVALID'), 400
        action = value['action']
        with lock:
            if state['busy']:return jsonify(error='BUSY'), 409
            state.update(busy=True, result={}, error=None)
        def work():
            operation_error = None
            try:
                result = backend.call(action, **{k: v for k, v in value.items() if k != 'action'})
                with lock:
                    state.update(result=result)
            except Exception as error:
                code = str(error)
                with lock:
                    filtered = code if code in ERRORS else 'HOTSPOT_OPERATION_FAILED'
                    state.update(error=filtered, result={})
                    operation_error = filtered
            finally:
                if action != 'status':
                    operation = {'action': action, 'error': operation_error, 'at': time.time()}
                    if hasattr(backend, 'record_operation'):
                        try:operation = backend.record_operation(action, operation_error)
                        except Exception:pass
                    with lock:state['last_operation'] = operation
                value.clear()
                with lock:state['busy'] = False
        thread = threading.Thread(target=work, daemon=True)
        app.extensions['hotspot']['thread'] = thread
        thread.start()
        return jsonify(accepted=True), 202

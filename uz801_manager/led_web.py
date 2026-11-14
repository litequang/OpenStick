"""Local USB/LAN LED configuration under the existing portal guards."""
from flask import jsonify, render_template, request


def register_led_routes(app, backend, token):
    @app.get('/settings/leds')
    def led_page():
        return render_template('leds.html', token=token, page='leds')

    @app.route('/api/leds', methods=['GET', 'POST'])
    def led_settings():
        try:
            if request.method == 'GET':return jsonify(backend.status())
            return jsonify(backend.configure(request.get_json(silent=True)))
        except (ValueError, TypeError):return jsonify(error='INPUT_INVALID'), 400
        except Exception as error:
            allowed = {'LED_BUSY', 'LED_UNAVAILABLE', 'LED_MODE_UNSUPPORTED', 'LED_CONFIG_INVALID',
                       'LED_APPLY_FAILED', 'LED_ROLLBACK_FAILED'}
            code = str(error) if str(error) in allowed else 'LED_OPERATION_FAILED'
            return jsonify(error=code), 409 if code == 'LED_BUSY' else 503

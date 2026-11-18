"""Same-origin provisioning, protected by the existing USB/LAN portal guard."""
from flask import jsonify, render_template, request, Response

from .setup_ap import validate_setup
from .lan_access import LAN_URL
from .ap_options import ERRORS as AP_ERRORS
from .ap_clients import validate as validate_client_action, ERRORS as CLIENT_ERRORS


def register_setup_routes(app, backend, token):
    clients = getattr(backend, 'clients', None)

    @app.get('/api/ap/clients')
    def ap_client_status():
        try:
            if clients is None:raise RuntimeError('AP_CLIENTS_UNAVAILABLE')
            return jsonify(clients.status())
        except Exception as error:
            return jsonify(error=str(error) if str(error) in CLIENT_ERRORS else 'AP_CLIENTS_UNAVAILABLE'), 503

    @app.post('/api/ap/clients')
    def ap_client_action():
        value = request.get_json(silent=True)
        try:
            action = validate_client_action(value)
            if clients is None:raise RuntimeError('AP_CLIENTS_UNAVAILABLE')
            return jsonify(clients.call(action,**{k:v for k,v in value.items() if k!='action'}))
        except (ValueError,TypeError,UnicodeError):return jsonify(error='INPUT_INVALID'),400
        except Exception as error:
            return jsonify(error=str(error) if str(error) in CLIENT_ERRORS else 'AP_CLIENTS_UNAVAILABLE'),409
        finally:
            if isinstance(value,dict):value.clear()

    @app.get('/setup')
    def setup_page():
        return render_template('setup.html', token=token, page='wifi')

    @app.get('/api/setup')
    def setup_status():
        try:return jsonify(backend.status())
        except Exception:return jsonify(error='SETUP_STATUS_FAILED'), 503

    @app.get('/api/setup/credentials')
    def setup_credentials():
        try:return jsonify(backend.status(credentials=True))
        except Exception:return jsonify(error='SETUP_STATUS_FAILED'), 503

    @app.get('/api/setup/card')
    def setup_card():
        try:
            value = backend.status(credentials=True)
            text = ('OpenStick — Wi-Fi cài đặt\n\nTên Wi-Fi: ' + (value['ssid'] or 'Chưa cấu hình') +
                    '\nMật khẩu Wi-Fi: ' + (value.get('password') or '') + '\nTrang cài đặt: ' + value['url'] +
                    '\nĐịa chỉ chung PC / điện thoại: ' + LAN_URL + '/setup' +
                    ('\nWi-Fi ẩn: Có — thêm mạng thủ công bằng đúng tên SSID.' if value.get('ap_options', {}).get('hidden') else '\nWi-Fi ẩn: Không.') +
                    '\n\nĐăng nhập bằng mật khẩu quản trị LAN đã đặt.\n'
                    'Khi điện thoại báo Wi-Fi không có Internet, chọn tiếp tục kết nối.\n'
                    'Hotspot cài đặt không cần SIM và không tự bật dữ liệu SIM.\n')
            return Response(text, mimetype='text/plain', headers={
                'Content-Disposition': 'attachment; filename="openstick-wifi-setup.txt"'})
        except Exception:return jsonify(error='SETUP_STATUS_FAILED'), 503

    @app.post('/api/setup')
    def setup_action():
        value = request.get_json(silent=True)
        try:
            action = validate_setup(value)
            return jsonify(backend.call(action, **{k: v for k, v in value.items() if k != 'action'})), 202
        except (ValueError, TypeError, UnicodeError):return jsonify(error='INPUT_INVALID'), 400
        except Exception as error:
            allowed = {'NETWORK_BUSY', 'LAN_NOT_CONFIGURED', 'AP_UNSUPPORTED', 'HOTSPOT_ACTIVE',
                       'POLICY_ACTIVE', 'CELLULAR_ALREADY_ACTIVE', 'SETUP_NOT_CONFIGURED', 'SETUP_NOT_ACTIVE',
                       'SETUP_OPERATION_FAILED'} | AP_ERRORS
            return jsonify(error=str(error) if str(error) in allowed else 'SETUP_OPERATION_FAILED'), 409
        finally:
            if isinstance(value, dict):value.clear()

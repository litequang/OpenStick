import uuid
import shutil
import subprocess
from pathlib import Path

import pytest

from uz801_manager.hosting import create_hosting_app


class Backend:
    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def call(self, action, **values):
        self.calls.append((action, values))
        if self.error:
            raise RuntimeError(self.error)
        return {'sim_missing': True, 'can_send': False, 'can_ussd': False}


def setup(error=None, usb=True):
    backend = Backend(error)
    app = create_hosting_app(backend=object(), modem_backend=backend,
                             usb_portal=usb, token='test-token')
    return app, app.test_client(), backend


def headers(**extra):
    return {'Host': '172.16.42.1', 'Origin': 'http://172.16.42.1',
            'X-OpenStick-Token': 'test-token', **extra}


def test_modem_page_bootstraps_usb_token_and_preserves_guards():
    app, client, backend = setup()
    response = client.get('/modem', headers={'Host': '172.16.42.1'})
    page = response.get_data(as_text=True)
    assert response.status_code == 200 and 'SMS / USSD' in page
    assert 'test-token' in page
    assert response.headers['Cache-Control'] == 'no-store'
    assert response.headers['X-Frame-Options'] == 'DENY'
    assert client.get('/api/modem/state', headers={'Host': '172.16.42.1'}).status_code == 403
    assert client.post('/api/modem', json={'action': 'status'}, headers=headers(Origin='https://evil.invalid')).status_code == 403
    assert client.get('/modem', headers={'Host': 'evil.invalid'}).status_code == 403
    assert not backend.calls
    assert '/modem' in client.get('/', headers={'Host': '172.16.42.1'}).get_data(as_text=True)


def test_windows_launcher_does_not_expose_modem_routes():
    app, client, backend = setup(usb=False)
    assert client.get('/modem', headers={'Host': '127.0.0.1:8770'}).status_code == 404


def test_status_job_and_sensitive_errors_are_filtered():
    app, client, backend = setup(error='private OTP +84900111222')
    assert client.post('/api/modem', json={'action': 'status'}, headers=headers()).status_code == 202
    app.extensions['modem']['thread'].join(2)
    response = client.get('/api/modem/state', headers=headers())
    assert response.json == {'busy': False, 'result': {}, 'error': 'MODEM_OPERATION_FAILED'}
    assert 'OTP' not in response.get_data(as_text=True)


def test_no_sim_blocks_without_a_send_attempt():
    app, client, backend = setup(error='SIM_REQUIRED')
    payload = {'action': 'send', 'number': '+84900111222', 'text': 'fixture OTP',
               'confirm': True, 'operation': str(uuid.uuid4())}
    assert client.post('/api/modem', json=payload, headers=headers()).status_code == 202
    app.extensions['modem']['thread'].join(2)
    response = client.get('/api/modem/state', headers=headers())
    assert response.json['error'] == 'SIM_REQUIRED'
    assert 'fixture OTP' not in response.get_data(as_text=True)
    assert 'number' not in app.extensions['modem']['state']


def test_confirm_and_exact_schema_required_before_a_job():
    app, client, backend = setup()
    payload = {'action': 'send', 'number': '+84900111222', 'text': 'test',
               'confirm': False, 'operation': str(uuid.uuid4())}
    assert client.post('/api/modem', json=payload, headers=headers()).status_code == 400
    assert client.post('/api/modem', json={'action': 'status', 'raw': 'AT'}, headers=headers()).status_code == 400
    assert client.post('/api/modem', json={'action': ['status']}, headers=headers()).status_code == 400
    assert not backend.calls


def test_real_ui_script_handles_private_http_and_lost_send_reply(tmp_path):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is needed for the synthetic UI fixture')
    app, client, _ = setup()
    page = tmp_path / 'modem.html'
    page.write_text(client.get('/modem', headers={'Host': '172.16.42.1'}).get_data(as_text=True), encoding='utf-8')
    result = subprocess.run([node, str(Path(__file__).with_name('modem_ui_fixture.cjs')), str(page)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr

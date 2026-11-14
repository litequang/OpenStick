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
    assert client.get('/modem', headers={'Host': '172.16.42.1'}).location == '/modem/sms'
    response = client.get('/modem/sms', headers={'Host': '172.16.42.1'})
    page = response.get_data(as_text=True)
    assert response.status_code == 200 and 'Tin nhắn' in page
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


def test_last_ussd_reply_survives_status_refresh_without_retaining_code():
    class UssdBackend(Backend):
        def call(self, action, **values):
            return {'reply': '<script>private fixture</script>'} if action == 'ussd_start' else {'registered': True}
    app = create_hosting_app(backend=object(), modem_backend=UssdBackend(), usb_portal=True, token='test-token')
    client = app.test_client()
    payload = {'action': 'ussd_start', 'code': '*101#', 'confirm': True, 'operation': str(uuid.uuid4())}
    assert client.post('/api/modem', json=payload, headers=headers()).status_code == 202
    app.extensions['modem']['thread'].join(2)
    for _ in range(2):
        assert client.post('/api/modem', json={'action': 'status'}, headers=headers()).status_code == 202
        app.extensions['modem']['thread'].join(2)
        response = client.get('/api/modem/state', headers=headers())
        assert response.json['result']['last_ussd']['result']['reply'] == '<script>private fixture</script>'
        assert '*101#' not in response.text and '"code"' not in response.text
    receipt=client.get('/api/modem/state?operation='+payload['operation'],headers=headers())
    assert receipt.json['result']['reply']=='<script>private fixture</script>'
    assert client.post('/api/modem',json=payload,headers=headers()).status_code==409
    assert '*101#' not in receipt.text


def test_overview_is_private_and_all_navigation_destinations_work(tmp_path):
    app, client, _ = setup()
    for route in ['/overview', '/manage', '/', '/modem/sms', '/modem/ussd', '/modem/network']:
        response = client.get(route, headers={'Host': '172.16.42.1'})
        assert response.status_code == 200 and 'id="portal-nav"' in response.text
        assert 'id="chip-sim"' in response.text and 'id="chip-modem"' in response.text
        assert 'id="chip-wifi"' in response.text and 'id="chip-signal"' not in response.text
        assert 'id="signal-status"' in response.text
        assert response.headers['Cache-Control'] == 'no-store'
    management = client.get('/manage', headers={'Host': '172.16.42.1'}).text
    assert 'aria-current="page"' in management
    assert all(f'href="{path}"' in management for path in ['/', '/modem/network', '/modem/sms', '/modem/ussd'])
    assert 'href="/internet"' not in management  # backend is absent in this fixture
    assert client.get('/overview', headers={'Host': 'evil.invalid'}).status_code == 403
    assert client.get('/manage', headers={'Host': 'evil.invalid'}).status_code == 403
    node = shutil.which('node')
    if not node:pytest.skip('Node.js is needed for the synthetic UI fixture')
    page = tmp_path / 'overview.html'
    page.write_text(client.get('/overview', headers={'Host': '172.16.42.1'}).text, encoding='utf-8')
    result = subprocess.run([node, str(Path(__file__).with_name('overview_ui_fixture.cjs')), str(page)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr


def test_header_snapshot_is_private_and_does_not_overwrite_wifi_job():
    class Wifi:
        def call(self, action, **values):
            assert action == 'status' and not values
            return {'connected': True, 'ssid': '<script>fixture SSID</script>'}
    app = create_hosting_app(backend=Wifi(), modem_backend=Backend(), usb_portal=True, token='test-token')
    client = app.test_client()
    state = app.extensions['hosting']['state']
    state.update(busy=True, result={'operation': 'keep this result'}, error=False)
    before = dict(state)
    assert client.get('/api/header', headers={'Host': '172.16.42.1'}).status_code == 403
    assert client.get('/api/header', headers=headers(Origin='https://evil.invalid')).status_code == 403
    result = client.get('/api/header', headers=headers())
    assert result.status_code == 200 and result.json['connected']
    assert result.headers['Cache-Control'] == 'no-store' and state == before


@pytest.mark.parametrize('section,present,absent', [
    ('sms', 'sms-compose-form', ('ussd-fields', 'mode-fields')),
    ('ussd', 'ussd-fields', ('sms-compose-form', 'mode-fields')),
    ('network', 'mode-fields', ('sms-compose-form', 'ussd-fields')),
])
def test_separate_pages_contain_only_their_own_forms(section, present, absent):
    _, client, _ = setup()
    response = client.get('/modem/' + section, headers={'Host': '172.16.42.1'})
    assert response.status_code == 200
    assert f'id="{present}"' in response.text
    assert all(f'id="{field}"' not in response.text for field in absent)
    assert 'id="network-status"' in response.text
    if section == 'network':
        assert 'data-section-active="true"' in response.text
        assert 'href="/manage"' in response.text
    else:
        assert 'aria-current="page"' in response.text
    assert client.get('/modem/invalid', headers={'Host': '172.16.42.1'}).status_code == 404


@pytest.mark.parametrize('section', ['sms', 'ussd', 'network'])
def test_real_ui_script_handles_private_http_and_lost_send_reply(tmp_path, section):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is needed for the synthetic UI fixture')
    app, client, _ = setup()
    page = tmp_path / 'modem.html'
    page.write_text(client.get('/modem/' + section, headers={'Host': '172.16.42.1'}).get_data(as_text=True), encoding='utf-8')
    fixture = 'sms_ui_fixture.cjs' if section == 'sms' else 'modem_ui_fixture.cjs'
    result = subprocess.run([node, str(Path(__file__).with_name(fixture)), str(page), section],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr

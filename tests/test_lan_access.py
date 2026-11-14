import json
import re

import pytest

from uz801_manager.hosting import create_hosting_app
from uz801_manager.lan_access import LanSettings, LoginLimiter

BASE = 'http://192.0.2.2:8765'
PASSWORD = 'fixture-admin-passphrase'


@pytest.fixture
def lan(tmp_path):
    settings = LanSettings(tmp_path, address=lambda: '192.0.2.2')
    settings.configure(PASSWORD)
    app = create_hosting_app(backend=object(), modem_backend=object(), usb_portal=True,
                             token='fixture-token', authority=lambda: '192.0.2.2:8765', lan_auth=settings)
    return app, app.test_client(), settings


def login(client, password=PASSWORD):
    page = client.get('/login', base_url=BASE)
    token = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
    return client.post('/login', base_url=BASE, headers={'Origin': BASE}, data={'csrf': token, 'password': password})


def test_credentials_stay_local_and_no_default_password_is_enabled(tmp_path):
    settings = LanSettings(tmp_path, address=lambda: '192.0.2.2')
    assert settings.private() is None and not settings.status()['enabled']
    result = settings.configure(PASSWORD)
    stored = (tmp_path / 'lan-admin.json').read_text()
    assert PASSWORD not in stored and 'password_hash' not in json.dumps(result)
    assert result == {'enabled': True, 'url': BASE}
    for password in ('short', None, 'x' * 129, 'valid-password\n'):
        with pytest.raises(ValueError):settings.configure(password)


def test_lan_requires_login_even_if_api_token_is_known(lan):
    app, client, _ = lan
    assert client.get('/overview', base_url=BASE).location == '/login'
    response = client.get('/api/modem/state', base_url=BASE, headers={'X-OpenStick-Token': 'fixture-token'})
    assert response.status_code == 401 and response.json['error'] == 'LOGIN_REQUIRED'
    assert 'fixture-token' not in client.get('/login', base_url=BASE).text


def test_login_logout_cookie_and_host_origin_guards(lan):
    app, client, _ = lan
    assert client.post('/login', base_url=BASE, data={'password': PASSWORD}).status_code == 403
    assert client.post('/login', base_url=BASE, data={'csrf': 'không-hợp-lệ', 'password': PASSWORD}).status_code == 403
    assert login(client).status_code == 302
    page = client.get('/overview', base_url=BASE)
    assert page.status_code == 200 and 'Đăng xuất' in page.text
    assert client.get('/overview', base_url='http://evil.invalid').status_code == 403
    assert client.get('/overview', base_url=BASE, headers={'Origin': 'http://evil.invalid'}).status_code == 403
    assert client.post('/api/lan', base_url=BASE, headers={'X-OpenStick-Token': 'fixture-token'}, json={'action': 'status'}).status_code == 404
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
    assert client.post('/logout', base_url=BASE, data={'csrf': csrf}).status_code == 302
    assert client.get('/overview', base_url=BASE).status_code == 302
    assert app.config['SESSION_COOKIE_HTTPONLY'] and app.config['SESSION_COOKIE_SAMESITE'] == 'Strict'
    assert "form-action 'self'" in page.headers['Content-Security-Policy']
    assert page.headers['Referrer-Policy'] == 'same-origin'
    assert client.post('/login', base_url=BASE, headers={'Origin': 'null'},
                       data={'password': PASSWORD}).status_code == 403


def test_wrong_password_throttle_and_rotation_invalidate_sessions(lan):
    app, client, settings = lan
    assert login(client, 'wrong-fixture-password').status_code == 200
    assert client.get('/overview', base_url=BASE).status_code == 302
    assert login(client).status_code == 302
    settings.configure('different-fixture-passphrase')
    assert client.get('/overview', base_url=BASE).status_code == 403


def test_disabled_lan_refuses_every_private_request(lan):
    _, client, settings = lan
    login(client)
    settings.disable()
    assert client.get('/overview', base_url=BASE).status_code == 403


def test_global_and_per_client_rate_limits_expire():
    clock = [0]
    limit = LoginLimiter(clock=lambda: clock[0])
    assert all(limit.allow('one') for _ in range(5))
    assert not limit.allow('one')
    for i in range(15):assert limit.allow('other-' + str(i))
    assert not limit.allow('last')
    clock[0] = 301
    assert limit.allow('one')


def test_usb_configuration_needs_token_exact_fields_and_confirmation(tmp_path):
    settings = LanSettings(tmp_path, address=lambda: '192.0.2.2')
    app = create_hosting_app(backend=object(), usb_portal=True, lan_settings=settings, token='fixture')
    client = app.test_client()
    base = 'http://172.16.42.1'
    headers = {'X-OpenStick-Token': 'fixture', 'Origin': base}
    assert client.post('/api/lan', base_url=base, json={'action': 'status'}).status_code == 403
    assert client.post('/api/lan', base_url=base, headers=headers,
                       json={'action': 'configure', 'password': PASSWORD, 'confirm': False}).status_code == 400
    response = client.post('/api/lan', base_url=base, headers=headers,
                           json={'action': 'configure', 'password': PASSWORD, 'confirm': True})
    assert response.status_code == 200 and PASSWORD not in response.text and 'hash' not in response.text
    assert client.post('/api/lan', base_url=base, headers={**headers, 'Origin': 'http://evil.invalid'}, json={'action': 'disable', 'confirm': True}).status_code == 403

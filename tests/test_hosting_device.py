import json
import subprocess

import pytest

from uz801_manager import hosting_device
from uz801_manager.hosting import create_hosting_app


class Backend:
    def call(self, action, **values):
        return {'state': '100 (connected)'}


def test_usb_portal_bootstraps_token_but_rejects_cross_site_and_wrong_host():
    app = create_hosting_app(backend=Backend(), token='fixture-token', usb_portal=True)
    with app.test_client() as client:
        page = client.get('/', base_url='http://172.16.42.1')
        assert page.status_code == 200 and "fixture-token" in page.text
        assert page.headers['X-Frame-Options'] == 'DENY'
        assert client.get('/', base_url='http://example.com').status_code == 403
        assert client.get('/', base_url='http://172.16.42.1', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
        assert client.get('/api/state', base_url='http://172.16.42.1').status_code == 403
        headers = {'X-OpenStick-Token': 'fixture-token', 'Origin': 'http://172.16.42.1'}
        assert client.get('/api/state', base_url='http://172.16.42.1', headers=headers).status_code == 200
        assert client.post('/api/wifi', base_url='http://172.16.42.1', headers={**headers, 'Origin': 'https://attacker.invalid'}, json={'action': 'connect', 'ssid': 'x', 'password': 'fixture-password'}).status_code == 403


def test_windows_page_does_not_publish_its_api_token():
    with create_hosting_app(backend=Backend(), token='private-fixture').test_client() as client:
        assert 'private-fixture' not in client.get('/', base_url='http://127.0.0.1:8770').text


def test_device_socket_requires_usb_interface_before_binding_address(monkeypatch):
    calls = []
    class Socket:
        def setsockopt(self, level, option, value):
            calls.append(('option', option, value))
        def bind(self, address):
            calls.append(('bind', address))
        def close(self):
            calls.append(('close',))
    monkeypatch.setattr(hosting_device.socket, 'SO_BINDTODEVICE', 25, raising=False)
    monkeypatch.setattr(hosting_device.socket, 'socket', lambda *a: Socket())
    hosting_device.usb_socket()
    assert ('option', 25, b'usb0\0') in calls
    assert calls.index(('option', 25, b'usb0\0')) < calls.index(('bind', ('172.16.42.1', 80)))


def test_device_socket_fails_closed_when_interface_binding_fails(monkeypatch):
    calls = []
    class Socket:
        def setsockopt(self, level, option, value):
            raise OSError('USB unavailable')
        def bind(self, address):
            calls.append('bind')
        def close(self):
            calls.append('closed')
    monkeypatch.setattr(hosting_device.socket, 'socket', lambda *a: Socket())
    with pytest.raises(OSError):
        hosting_device.usb_socket()
    assert calls == ['closed']


def test_local_backend_does_not_put_password_in_command_or_error():
    secret = 'private-fixture-password'
    def run(args, **kwargs):
        assert secret not in ' '.join(args)
        assert json.loads(kwargs['input'])['password'] == secret
        assert kwargs['shell'] is False
        return subprocess.CompletedProcess(args, 1, secret.encode(), secret.encode())
    with pytest.raises(RuntimeError, match='^NETWORK_OPERATION_FAILED$'):
        hosting_device.LocalWifi(run=run).call('connect', ssid='fixture', password=secret)

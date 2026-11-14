import ast
import json
import subprocess
import threading

import pytest

from uz801_manager.hosting import LinuxWifi, HTML, REMOTE, create_hosting_app

BASE = 'http://127.0.0.1:8770'
HEADERS = {'X-OpenStick-Token': 'test', 'Origin': BASE}
SECRET = 'fixture-private-password'


class Backend:
    def __init__(self):
        self.calls = []

    def call(self, action, **values):
        self.calls.append((action, values))
        return {'connected': True} if action == 'connect' else {'state': '100 (connected)', 'connection': 'openstick-home'}


def test_ssh_credentials_and_user_input_are_not_shell_arguments(tmp_path):
    def run(args, **kwargs):
        assert SECRET not in ' '.join(args)
        assert kwargs['shell'] is False
        assert json.loads(kwargs['input'])['password'] == SECRET
        assert 'StrictHostKeyChecking=yes' in args
        assert 'IdentityAgent=none' in args
        assert args[-2] == 'user@172.16.42.1'
        assert args[-1].startswith('sudo -n python3 -c ')
        return subprocess.CompletedProcess(args, 0, b'{"connected":true}', b'')
    result = LinuxWifi(tmp_path, run=run).call('connect', ssid='a;$(touch unexpected)', password=SECRET)
    assert result == {'connected': True}


def test_ssh_error_never_exposes_remote_output(tmp_path):
    def run(args, **kwargs):
        return subprocess.CompletedProcess(args, 1, SECRET.encode(), SECRET.encode())
    with pytest.raises(RuntimeError, match='^USB_SSH_UNAVAILABLE$'):
        LinuxWifi(tmp_path, run=run).call('status')


@pytest.mark.parametrize('headers,base', [({}, BASE), ({**HEADERS, 'Origin':'https://evil.example'}, BASE),
    (HEADERS, 'http://evil.example:8770'), ({**HEADERS, 'Sec-Fetch-Site':'cross-site'}, BASE)])
def test_hosting_api_rejects_unauthenticated_or_cross_site(headers, base):
    app = create_hosting_app(backend=Backend(), token='test')
    with app.test_client() as client:
        response = client.post('/api/wifi', base_url=base, headers=headers, json={'action':'scan'})
        assert response.status_code == 403


@pytest.mark.parametrize('body', [{'action':'shell'}, {'action':'scan', 'command':'reboot'},
    {'action':'connect','ssid':'ok','password':'short'},
    {'action':'connect','ssid':'a\nb','password':SECRET},
    {'action':'connect','ssid':'界'*20,'password':SECRET},
    {'action':'connect','ssid':'valid','password':None}])
def test_hosting_rejects_extra_commands_and_invalid_wifi(body):
    backend = Backend()
    app = create_hosting_app(backend=backend, token='test')
    with app.test_client() as client:
        assert client.post('/api/wifi', base_url=BASE, headers=HEADERS, json=body).status_code == 400
    assert not backend.calls


def test_wifi_job_does_not_retain_password_or_raw_errors():
    class Broken(Backend):
        def call(self, action, **values):
            raise RuntimeError(SECRET)
    app = create_hosting_app(backend=Broken(), token='test')
    with app.test_client() as client:
        assert client.post('/api/wifi', base_url=BASE, headers=HEADERS,
            json={'action':'connect','ssid':'fixture-home','password':SECRET}).status_code == 202
        app.extensions['hosting']['thread'].join(3)
        response = client.get('/api/state', base_url=BASE, headers=HEADERS)
        assert response.get_json()['error'] is True
        assert SECRET not in response.text
        assert response.headers['Cache-Control'] == 'no-store'


def test_concurrent_wifi_changes_are_rejected():
    entered, finish = threading.Event(), threading.Event()
    class Blocking(Backend):
        def call(self, action, **values):
            entered.set()
            finish.wait(3)
            return {'connected': True}
    app = create_hosting_app(backend=Blocking(), token='test')
    with app.test_client() as client:
        first = client.post('/api/wifi', base_url=BASE, headers=HEADERS, json={'action':'scan'})
        assert first.status_code == 202 and entered.wait(2)
        assert client.post('/api/wifi', base_url=BASE, headers=HEADERS, json={'action':'scan'}).status_code == 409
        finish.set()
        app.extensions['hosting']['thread'].join(3)


def test_local_ui_and_remote_parser_handle_escaped_ssids():
    assert 'type="password"' in HTML and 'Kết nối Wi-Fi' in HTML
    assert 'replaceChildren' in HTML and 'textContent' in HTML
    module = ast.parse(REMOTE)
    function = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'fields')
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), '<remote-parser>', 'exec'), namespace)
    assert namespace['fields'](r'home\:wifi:80:WPA2') == ['home:wifi', '80', 'WPA2']

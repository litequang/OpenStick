import ast
import json
import subprocess
import threading
import re
import shutil
from pathlib import Path
from types import SimpleNamespace

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


def remote_functions(**overrides):
    module = ast.parse(REMOTE)
    functions = [n for n in module.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('fields', 'wifi_status', 'download_speed')]
    namespace = {'re': re, 'shutil': SimpleNamespace(which=lambda _: False),
                 'subprocess': subprocess, **overrides}
    exec(compile(ast.Module(body=functions, type_ignores=[]), '<remote>', 'exec'), namespace)
    return namespace


def test_wifi_status_reads_connected_ssid_signal_and_negotiated_rates_without_scan():
    calls = []
    def run(args, timeout=15):
        calls.append(args)
        if 'show' in args:
            return 'GENERAL.STATE:100 (connected)\nGENERAL.CONNECTION:fixture\nIP4.ADDRESS[1]:192.0.2.2/24\nIP4.GATEWAY:192.0.2.1\n'
        assert args[-2:] == ['--rescan', 'no']
        return r'*:fixture\:home:64'
    def iw(args, **kwargs):
        assert args == ['iw', 'dev', 'wlan0', 'link']
        return subprocess.CompletedProcess(args, 0, 'SSID: fixture:home\n signal: -65 dBm\n tx bitrate: 90.0 MBit/s\n rx bitrate: 121.5 MBit/s\n')
    functions = remote_functions(run=run, shutil=SimpleNamespace(which=lambda _: True),
                                 subprocess=SimpleNamespace(run=iw, SubprocessError=subprocess.SubprocessError))
    value = functions['wifi_status']()
    assert value['connected'] and value['ssid'] == 'fixture:home'
    assert value['signal_dbm'] == -65 and value['signal_percent'] == 64
    assert (value['tx_mbps'], value['rx_mbps']) == (90.0, 121.5)
    assert value['ipv4'] == ['192.0.2.2/24'] and value['gateway'] == '192.0.2.1'
    assert len(calls) == 2


def test_wifi_missing_metrics_are_unknown_and_disconnected_never_scans():
    calls = []
    def run(args, timeout=15):
        calls.append(args)
        return 'GENERAL.STATE:30 (disconnected)\nGENERAL.CONNECTION:--\n'
    value = remote_functions(run=run)['wifi_status']()
    assert not value['connected'] and value['ssid'] is None
    assert value['tx_mbps'] is None and value['signal_dbm'] is None and len(calls) == 1
    def incomplete(args, timeout=15):
        if 'show' in args:return 'GENERAL.STATE:100 (connected)\n'
        raise RuntimeError('cached scan unavailable')
    value = remote_functions(run=incomplete)['wifi_status']()
    assert value['connected'] and value['signal_percent'] is None


@pytest.mark.parametrize('response,success', [('200 2097152 1250000 1.68', True),
                                            ('200 500 1250000 1.68', False),
                                            ('403 2097152 1250000 1.68', False)])
def test_speed_measurement_is_bounded_fixed_https_and_bound_to_wifi(response, success):
    calls = []
    def run(args, timeout=15):
        calls.append(args)
        assert args[args.index('--interface') + 1] == 'wlan0'
        assert args[args.index('--max-filesize') + 1] == '2097152'
        assert args[-1] == 'https://speed.cloudflare.com/__down?bytes=2097152'
        assert timeout == 25 and '--max-time' in args
        return response
    functions = remote_functions(run=run)
    functions['wifi_status'] = lambda: {'connected': True}
    if success:
        assert functions['download_speed']()['download_mbps'] == 10.0
    else:
        with pytest.raises(RuntimeError, match='SPEED_TEST_FAILED'):functions['download_speed']()
    functions['wifi_status'] = lambda: {'connected': False}
    with pytest.raises(RuntimeError, match='WIFI_NOT_CONNECTED'):functions['download_speed']()
    assert len(calls) == 1


@pytest.mark.parametrize('state', ['connected', 'disconnected'])
def test_wifi_ui_prioritizes_current_connection_and_only_measures_on_click(tmp_path, state):
    node = shutil.which('node')
    if not node:pytest.skip('Node.js is needed for the synthetic UI fixture')
    app = create_hosting_app(backend=Backend(), modem_backend=object(), token='fixture', usb_portal=True)
    page = tmp_path / 'wifi.html'
    with app.test_client() as client:
        page.write_text(client.get('/', base_url='http://172.16.42.1').text, encoding='utf-8')
    value = subprocess.run([node, str(Path(__file__).with_name('wifi_ui_fixture.cjs')), str(page), state],
                           capture_output=True, text=True, timeout=10)
    assert value.returncode == 0, value.stdout + value.stderr

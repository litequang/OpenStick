import ast
import configparser
import hashlib
import json
import subprocess
from types import SimpleNamespace

import pytest

from uz801_manager.hosting import REMOTE, LinuxWifi, create_hosting_app
from uz801_manager.hosting_device import LocalWifi


def test_saved_station_profile_keeps_compatibility_and_known_wpa_vector():
    function=next(n for n in ast.parse(REMOTE).body if isinstance(n,ast.FunctionDef) and n.name=='station_profile')
    namespace={'hashlib':hashlib}
    exec(compile(ast.Module(body=[function],type_ignores=[]),'<profile>','exec'),namespace)
    text=namespace['station_profile']('IEEE','password','07ca019c-485b-4f06-b99d-171c167e18bb')
    config=configparser.ConfigParser();config.read_string(text)
    assert config['wifi']['cloned-mac-address']=='permanent'
    assert config['wifi']['powersave']=='2'
    assert config['connection']['autoconnect']=='true'
    assert config['wifi-security']['psk']=='f42c6fc52df0ebef9ebb4b90b38a5f902e83fe1b135a70e23aed762e9710a12e'
    assert 'password' not in text


@pytest.mark.parametrize('code',['WIFI_AUTH_REQUIRED','WIFI_TIMEOUT','POLICY_ACTIVE'])
@pytest.mark.parametrize('backend',['local','ssh'])
def test_fixed_wifi_failure_survives_transport_without_raw_output(tmp_path,code,backend):
    def run(args,**kwargs):
        assert kwargs['timeout']>60
        return subprocess.CompletedProcess(args,1,json.dumps({'error':code}).encode(),b'private fixture password')
    worker=LocalWifi(run=run) if backend=='local' else LinuxWifi(tmp_path,run=run)
    with pytest.raises(RuntimeError,match='^'+code+'$'):
        worker.call('connect',ssid='fixture',password='private fixture password')


def test_modem_auth_failure_category_is_exposed_but_private_error_is_not():
    class Backend:
        def call(self,*args,**kwargs):raise RuntimeError('WIFI_AUTH_REQUIRED')
    app=create_hosting_app(backend=Backend(),token='fixture')
    with app.test_client() as client:
        headers={'X-OpenStick-Token':'fixture'};base='http://127.0.0.1:8770'
        assert client.post('/api/wifi',base_url=base,headers=headers,json={
            'action':'connect','ssid':'fixture','password':'private fixture password'}).status_code==202
        app.extensions['hosting']['thread'].join(2)
        state=client.get('/api/state',base_url=base,headers=headers).json
        assert state['error'] is True and state['error_code']=='WIFI_AUTH_REQUIRED'
        assert 'private fixture password' not in json.dumps(state)

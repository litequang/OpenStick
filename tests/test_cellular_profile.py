import configparser
import json

import pytest

from uz801_manager.cellular_profile import apply, from_key_string, key_string, parse_profile, summary
from uz801_manager.hosting import create_hosting_app
from uz801_manager.hotspot import CELL_UUID


@pytest.mark.parametrize('auth',['auto','none','pap','chap','pap_chap'])
@pytest.mark.parametrize('family',['auto','ipv4','ipv6','ipv4v6'])
def test_auth_and_ip_family_roundtrip_with_literal_keyfile_secrets(auth,family):
    p=configparser.ConfigParser(interpolation=None)
    p.read_string(f'[connection]\nuuid={CELL_UUID}\ntype=gsm\nautoconnect=false\n[gsm]\n[ipv4]\nroute-metric=600\n[ipv6]\nroute-metric=600\n')
    value=dict(apn='fixture.apn',username=' fixture\\user ',password=' fixture\\secret %;=# ',
               password_action='replace',auth=auth,ip_family=family,roaming=False)
    apply(p,value);out=summary(p,'Fixture')
    assert out['auth']==auth and out['ip_family']==family
    assert out['username']==value['username'] and out['password_saved']
    assert from_key_string(p['gsm']['password'])==value['password']
    assert 'secret' not in json.dumps(out)
    assert p['connection']['autoconnect']=='false' and p['ipv4']['route-metric']=='600'


def test_keyfile_escape_does_not_treat_literal_backslash_s_as_space():
    text='\\s pass\\word '
    assert from_key_string(key_string(text))==text


def test_nm_normalized_trailing_password_spaces_survive_keep_and_resave():
    p=parse_profile('[gsm]\nusername=\\sfixture-user \npassword=\\sfixture\\\\secret %;=# \n')
    assert from_key_string(p['gsm']['password'])==' fixture\\secret %;=# '
    assert summary(p)['username']==' fixture-user '


def test_apn_page_and_settings_endpoint_require_existing_token_and_do_not_write():
    class Backend:
        def __init__(self):self.calls=[]
        def call(self,action,**values):
            self.calls.append(action)
            assert action=='status'
            return {'cellular_settings':{'available':True,'password_saved':True},'cellular_connected':False}
    backend=Backend()
    app=create_hosting_app(backend=object(),modem_backend=object(),hotspot_backend=backend,
                           token='fixture',usb_portal=True)
    client=app.test_client();base='http://172.16.42.1'
    assert client.get('/sim/apn',base_url=base).status_code==200 and backend.calls==[]
    assert client.get('/api/cellular',base_url=base).status_code==403
    result=client.get('/api/cellular',base_url=base,headers={'X-OpenStick-Token':'fixture'})
    assert result.status_code==200 and result.json['settings']['password_saved']
    assert backend.calls==['status']
    assert client.get('/api/cellular',base_url='http://evil.invalid',headers={'X-OpenStick-Token':'fixture'}).status_code==403

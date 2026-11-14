from contextlib import nullcontext
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

from uz801_manager.hosting import create_hosting_app
from uz801_manager.lan_access import LanSettings
from uz801_manager.leds import (FACTORY, LEDS, LedSettings, validate_led_request,
    default_network_rules, network_state, select_network_state)


BASE = 'http://172.16.42.1'
HEADERS = {'X-OpenStick-Token': 'fixture'}
TRIGGERS = ['none', 'timer', 'heartbeat', 'phy0radio', 'phy0assoc', 'phy0rx', 'phy0tx']


class Hardware(LedSettings):
    """Model kernel trigger files, without accessing real LEDs."""
    def __init__(self, directory, root):
        super().__init__(directory, root=root, lock_factory=nullcontext, state_provider=lambda: {})
        self.calls = []
        self.fail = None

    def _path(self, color, field):
        # Windows cannot create ':' names; only this fake changes the layout.
        return self.root / LEDS[color][0].replace(':', '_') / field

    def _write(self, color, field, value):
        self.calls.append((color, field, value))
        if self.fail == (color, field, value):
            self.fail = None
            raise OSError('Synthetic hardware failure')
        if field == 'trigger':
            self._path(color, field).write_text(' '.join('['+item+']' if item == value else item for item in TRIGGERS))
        else:super()._write(color, field, value)


@pytest.fixture
def leds(tmp_path):
    root = tmp_path / 'leds'
    for color, (name, _) in LEDS.items():
        node = root / name.replace(':', '_');node.mkdir(parents=True)
        for field, text in {'brightness': '1' if color == 'red' else '0', 'max_brightness': '1',
                            'trigger': '[none] ' + ' '.join(TRIGGERS[1:]), 'delay_on': '500', 'delay_off': '500'}.items():
            (node / field).write_text(text)
    unrelated = root / 'mmc0__';unrelated.mkdir();(unrelated / 'brightness').write_text('23')
    return Hardware(tmp_path / 'private', root)


def request(**changes):
    return {'action': 'configure', 'settings': {color: {**FACTORY, **item} for color, item in changes.items()}, 'confirm': True}


def test_discovery_and_opening_status_do_not_change_leds_or_mmc(leds):
    status = leds.status()
    assert status['supported'] and not status['saved']
    assert [item['id'] for item in status['leds']] == ['red', 'green', 'blue']
    assert status['leds'][0]['lit'] and not status['leds'][1]['lit']
    assert leds.calls == [] and not (leds.directory / 'led-settings.json').exists()
    leds.apply_saved();assert leds.calls == []
    assert (leds.root / 'mmc0__' / 'brightness').read_text() == '23'


@pytest.mark.parametrize('value', [None, {}, {'action': 'configure', 'settings': {}, 'confirm': True},
    {'action': 'configure', 'settings': {'../../mmc0::': FACTORY}, 'confirm': True},
    request(blue={'mode': 'panic'}), request(blue={'mode': ['on']}),
    request(blue={'on_ms': 99}), request(blue={'off_ms': 5001}),
    request(blue={'on_ms': True}), request(blue={'path': '/etc/passwd'}),
    {**request(blue={'mode': 'on'}), 'confirm': False},
    {**request(blue={'mode': 'on'}), 'command': 'reboot'}])
def test_only_allowlisted_colors_modes_and_bounded_integer_times_are_accepted(leds, value):
    with pytest.raises(ValueError):leds.configure(value)
    assert leds.calls == []


def test_save_blink_reapplies_after_restart_and_default_restores_original_state(leds):
    result = leds.configure(request(blue={'mode': 'blink', 'on_ms': 250, 'off_ms': 750}))
    assert result['saved']
    assert leds._hardware()['blue']['snapshot'] == {'trigger': 'timer', 'brightness': 1, 'on_ms': 250, 'off_ms': 750}
    path = leds.directory / 'led-settings.json';saved = path.read_bytes()
    leds._write('blue', 'trigger', 'none');leds._write('blue', 'brightness', 0)
    replacement = Hardware(leds.directory, leds.root);replacement.apply_saved()
    assert replacement._hardware()['blue']['snapshot']['trigger'] == 'timer'
    assert path.read_bytes() == saved
    replacement.configure(request(blue={'mode': 'default'}))
    assert replacement._hardware()['blue']['snapshot'] == {'trigger': 'none', 'brightness': 0}
    assert replacement._hardware()['red']['snapshot'] == {'trigger': 'none', 'brightness': 1}
    assert (leds.root / 'mmc0__' / 'brightness').read_text() == '23'


def test_unsupported_trigger_is_rejected_before_any_write(leds):
    leds._path('green', 'trigger').write_text('[none] timer')
    with pytest.raises(RuntimeError, match='LED_MODE_UNSUPPORTED'):
        leds.configure(request(red={'mode': 'off'}, green={'mode': 'wifi_link'}))
    assert leds.calls == []


def test_mid_apply_failure_rolls_back_all_changed_colors_and_preserves_saved_configuration(leds):
    leds.configure(request(red={'mode': 'on'}))
    before = (leds.directory / 'led-settings.json').read_bytes()
    leds.fail = ('green', 'brightness', 1)
    with pytest.raises(RuntimeError, match='^LED_APPLY_FAILED$'):
        leds.configure(request(red={'mode': 'off'}, green={'mode': 'on'}))
    assert (leds.directory / 'led-settings.json').read_bytes() == before
    assert leds._hardware()['red']['snapshot']['brightness'] == 1
    assert leds._hardware()['green']['snapshot']['brightness'] == 0


def test_persistence_failure_restores_hardware(leds, monkeypatch):
    def fail(_):raise OSError('Synthetic storage failure')
    monkeypatch.setattr(leds, '_persist', fail)
    with pytest.raises(RuntimeError, match='LED_APPLY_FAILED'):leds.configure(request(red={'mode': 'off'}))
    assert leds._hardware()['red']['snapshot']['brightness'] == 1
    assert not (leds.directory / 'led-settings.json').exists()


def test_corrupt_saved_config_is_not_applied(leds):
    leds.directory.mkdir();(leds.directory / 'led-settings.json').write_text('{"version":1}')
    with pytest.raises(RuntimeError, match='LED_CONFIG_INVALID'):leds.apply_saved()
    assert leds.calls == []


def test_api_is_private_and_windows_launcher_cannot_access_hardware(leds):
    app = create_hosting_app(backend=object(), modem_backend=object(), led_backend=leds,
                             usb_portal=True, token='fixture')
    client = app.test_client()
    assert '/settings/leds' in client.get('/manage', base_url=BASE).text
    assert client.get('/settings/leds', base_url=BASE).status_code == 200
    assert client.get('/api/leds', base_url=BASE).status_code == 403
    assert client.post('/api/leds', base_url=BASE, headers={**HEADERS, 'Origin': 'http://evil.invalid'}, json=request(red={'mode': 'off'})).status_code == 403
    assert client.get('/api/leds', base_url='http://evil.invalid', headers=HEADERS).status_code == 403
    assert client.get('/api/leds', base_url=BASE, headers=HEADERS).status_code == 200
    assert leds.calls == []
    assert client.post('/api/leds', base_url=BASE, headers=HEADERS, json=request(red={'mode': 'off'})).status_code == 200
    assert leds._hardware()['red']['snapshot']['brightness'] == 0
    windows = create_hosting_app(backend=object(), led_backend=leds, token='fixture').test_client()
    assert windows.get('/api/leds', base_url='http://127.0.0.1:8770', headers=HEADERS).status_code == 404


def test_led_changes_over_lan_require_existing_login(leds, tmp_path):
    settings = LanSettings(tmp_path / 'lan');settings.configure('fixture-admin-password')
    base = 'http://openstick.local:8765'
    app = create_hosting_app(backend=object(), modem_backend=object(), led_backend=leds, usb_portal=True,
                             token='fixture', lan_auth=settings, authority='openstick.local:8765')
    client = app.test_client()
    assert client.get('/settings/leds', base_url=base).status_code == 302
    assert client.post('/api/leds', base_url=base, headers=HEADERS, json=request(red={'mode': 'off'})).status_code == 401
    page = client.get('/login', base_url=base)
    csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
    client.post('/login', base_url=base, headers={'Origin': base}, data={'csrf': csrf, 'password': 'fixture-admin-password'})
    assert client.post('/api/leds', base_url=base, headers={**HEADERS, 'Origin': base}, json=request(red={'mode': 'off'})).status_code == 200


def test_error_responses_do_not_leak_driver_or_filesystem_details():
    class Broken:
        def status(self):raise RuntimeError('private details /etc/secret')
    client = create_hosting_app(backend=object(), led_backend=Broken(), usb_portal=True, token='fixture').test_client()
    response = client.get('/api/leds', base_url=BASE, headers=HEADERS)
    assert response.status_code == 503 and response.json == {'error': 'LED_OPERATION_FAILED'}


def test_led_page_only_submits_after_explicit_save(leds, tmp_path):
    node = shutil.which('node')
    if not node:pytest.skip('Node.js is needed for the synthetic UI fixture')
    app = create_hosting_app(backend=object(), led_backend=leds, usb_portal=True, token='fixture')
    page = tmp_path / 'leds.html';page.write_text(app.test_client().get('/settings/leds', base_url=BASE).text, encoding='utf-8')
    run = subprocess.run([node, str(Path(__file__).with_name('leds_ui_fixture.cjs')), str(page)], capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stdout + run.stderr


def rules_request(**changes):
    rules=default_network_rules()
    for state,settings in changes.items():rules[state].update(settings)
    return {'action':'configure_network','enabled':True,'rules':rules,'confirm':True}


def test_state_recipe_mixes_three_leds_and_polling_does_not_reset_blink(leds):
    state={'sim_hotspot':True,'cellular_data':True}
    leds.state_provider=lambda:state
    recipe={'red':{'mode':'on','on_ms':500,'off_ms':500},
            'green':{'mode':'blink','on_ms':200,'off_ms':800},
            'blue':{'mode':'blink','on_ms':700,'off_ms':300}}
    result=leds.configure(rules_request(sim_hotspot=recipe))
    assert result['network']['enabled'] and result['network']['state']=='sim_hotspot'
    hardware=leds._hardware()
    assert hardware['red']['snapshot']=={'trigger':'none','brightness':1}
    assert hardware['green']['snapshot']['on_ms']==200 and hardware['green']['snapshot']['off_ms']==800
    assert hardware['blue']['snapshot']['on_ms']==700
    saved=(leds.directory/'led-settings.json').read_bytes();leds.calls.clear()
    # Timer brightness naturally toggles; the worker must not restart its phase.
    leds._path('green','brightness').write_text('0')
    leds.sync_network();assert not leds.calls
    state.clear();state.update(wifi_station=True)
    leds.sync_network()
    assert leds._hardware()['red']['snapshot']['brightness']==0
    assert leds._hardware()['green']['snapshot']=={'trigger':'none','brightness':1}
    assert leds._hardware()['blue']['snapshot']=={'trigger':'none','brightness':0}
    assert (leds.directory/'led-settings.json').read_bytes()==saved
    assert (leds.root/'mmc0__'/'brightness').read_text()=='23'


def test_legacy_config_replay_disable_and_original_baseline_are_preserved(leds):
    leds.configure(request(red={'mode':'on'},blue={'mode':'blink','on_ms':250,'off_ms':750}))
    original=leds._saved();assert original['version']==1
    leds.state_provider=lambda:{'setup_hotspot':True}
    value=rules_request();leds.configure(value)
    assert leds._saved()['settings']==original['settings']
    replacement=Hardware(leds.directory,leds.root);replacement.state_provider=lambda:{'cellular_data':True,'sim_hotspot':False,'setup_hotspot':False,'wifi_station':False}
    replacement.apply_saved();assert replacement._hardware()['blue']['snapshot']=={'trigger':'none','brightness':1}
    replacement.configure({**value,'enabled':False})
    assert replacement._hardware()['blue']['snapshot']['on_ms']==250
    assert replacement._hardware()['red']['snapshot']['brightness']==1
    replacement.calls.clear();replacement.sync_network();assert not replacement.calls
    replacement.configure(value)
    replacement.configure(request(red={'mode':'default'},green={'mode':'default'},blue={'mode':'default'}))
    assert not replacement._saved()['network']['enabled']
    assert replacement._hardware()['red']['snapshot']=={'trigger':'none','brightness':1}
    assert replacement._hardware()['blue']['snapshot']=={'trigger':'none','brightness':0}


def test_all_recipes_validated_before_write_and_storage_failure_rolls_back(leds,monkeypatch):
    value=rules_request();value['rules']['offline']['green']['on_ms']=False
    with pytest.raises(ValueError):leds.configure(value)
    assert not leds.calls
    value=rules_request();value['rules']['unknown']['red']['mode']='heartbeat'
    with pytest.raises(ValueError):leds.configure(value)
    value=rules_request();del value['rules']['offline']['blue']
    with pytest.raises(ValueError):leds.configure(value)
    def fail(_):raise OSError('fixture')
    monkeypatch.setattr(leds,'_persist',fail)
    leds.state_provider=lambda:{'sim_hotspot':True}
    with pytest.raises(RuntimeError,match='LED_APPLY_FAILED'):leds.configure(rules_request())
    assert leds._hardware()['green']['snapshot']=={'trigger':'none','brightness':0}
    assert not (leds.directory/'led-settings.json').exists()


@pytest.mark.parametrize('state,expected',[
    ({'setup_hotspot':True,'sim_hotspot':True,'cellular_data':True},'setup_hotspot'),
    ({'sim_hotspot':True,'cellular_data':True},'sim_hotspot'),
    ({'wifi_station':True,'cellular_data':True},'wifi_station'),
    ({'cellular_data':True,'sim_hotspot':False,'setup_hotspot':False,'wifi_station':False},'cellular_data'),
    ({'cellular_data':True},'unknown'),
    ({key:False for key in ['setup_hotspot','sim_hotspot','wifi_station','cellular_data']},'offline'),
    ({},'unknown'),({'cellular_data':'registered'},'unknown')])
def test_state_priority_and_unknown_are_explicit(state,expected):
    assert select_network_state(state)==expected


def test_network_role_reader_is_read_only_and_registration_is_not_sim_data():
    from uz801_manager.hotspot import AP_UUID
    class Metadata:
        def __init__(self):self.calls=[];self.cell='30 (disconnected)\n--';self.wifi='100 (connected)\n'+AP_UUID+'\n192.168.8.1/24'
        def nm(self,*args,**kwargs):
            self.calls.append(args);assert kwargs['timeout']==3
            if args[:3]==('-t','-f','DEVICE,TYPE'):return 'wlan0:wifi\nwwan0qmi0:gsm'
            if args[1]=='GENERAL.STATE,GENERAL.CON-UUID,IP4.ADDRESS':return self.wifi
            if args[1]=='GENERAL.STATE,GENERAL.IP-IFACE':return self.cell
            if args[1]=='802-11-wireless.mode':return 'infrastructure'
            raise AssertionError('Unexpected metadata operation')
    source=Metadata();state=network_state(source)
    assert state['sim_hotspot'] and not state['cellular_data']
    source.cell='100 (connected)\nwwan0';assert network_state(source)['cellular_data']
    source.wifi='50 (configuring)\n'+AP_UUID+'\n192.168.8.1/24'
    assert not network_state(source)['sim_hotspot']
    source.wifi='100 (connected)\n07ca019c-485b-4f06-b99d-171c167e18bb\n192.0.2.4/24'
    assert network_state(source)['wifi_station']
    assert all('up' not in call and 'down' not in call and 'radio' not in call for call in source.calls)

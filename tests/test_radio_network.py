"""Synthetic policy, DBus and profile tests; no physical radio changes."""
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from uz801_manager.hotspot import CELL_UUID
from uz801_manager.modem import validate_action
from uz801_manager.radio_network import band_choices, set_roaming, roaming_status
from test_modem_device import Bus, make_modem
from uz801_manager.modem_device import MODEM, SERVICE, ROOT


@pytest.fixture
def owner(tmp_path):
    path = tmp_path / 'openstick-cellular.nmconnection'
    path.write_text(f'[connection]\nuuid={CELL_UUID}\ntype=gsm\n[gsm]\napn=fixture\npassword=private-fixture\nhome-only=false\n[ipv4]\nmethod=auto\n')
    calls=[]
    network=SimpleNamespace(devices=lambda:['cell'],active=lambda _:None,load=lambda p:calls.append('load'))
    return SimpleNamespace(profiles=tmp_path,network=network,read=lambda _: {},
                           atomic=lambda p,v:p.write_text(v),calls=calls)


def test_home_lock_uses_sim_home_and_preserves_other_settings(owner):
    result=set_roaming(owner,False,'00101',lambda value:owner.calls.append(value))
    assert result['roaming']=={'available':True,'allowed':False,'home_locked':True}
    text=(owner.profiles/'openstick-cellular.nmconnection').read_text()
    assert 'network-id=00101' in text and 'password=private-fixture' in text and 'apn=fixture' in text
    assert owner.calls==['load','00101']
    set_roaming(owner,True,'',lambda value:owner.calls.append(value))
    assert roaming_status(owner)['allowed'] and not roaming_status(owner)['home_locked']
    assert owner.calls[-1]==''


def test_active_data_and_unknown_home_cannot_change_anything(owner):
    original=(owner.profiles/'openstick-cellular.nmconnection').read_text()
    for home in ('','bad','00101\npassword=x'):
        with pytest.raises(RuntimeError,match='HOME_NETWORK_UNAVAILABLE'):set_roaming(owner,False,home,lambda _:pytest.fail())
    owner.network.active=lambda _:CELL_UUID
    with pytest.raises(RuntimeError,match='CELLULAR_ALREADY_ACTIVE'):set_roaming(owner,False,'00101',lambda _:pytest.fail())
    assert (owner.profiles/'openstick-cellular.nmconnection').read_text()==original and not owner.calls


def test_uncertain_registration_restores_profile_without_retry(owner):
    original=(owner.profiles/'openstick-cellular.nmconnection').read_text()
    attempts=[]
    def fail(value):attempts.append(value);raise TimeoutError('private')
    with pytest.raises(RuntimeError,match='RESULT_UNKNOWN'):set_roaming(owner,False,'00101',fail)
    assert attempts==['00101'] and owner.calls==['load','load']
    assert (owner.profiles/'openstick-cellular.nmconnection').read_text()==original


def test_candidates_never_add_unsupported_bands_or_remove_3g_fallback():
    choices=band_choices([1,4,31,33,38,256])
    assert choices[0]['bands']==[256]
    assert next(c for c in choices if c['id']=='vietnam')['bands']==[1,4,31,33,38]
    assert next(c for c in choices if c['id']=='b3')['bands']==[1,4,33]
    assert all(c['id']!='b41' for c in choices)
    assert band_choices([0,256])==[]


def test_band_apply_uses_typed_dbus_and_saves_only_separate_preference(make_modem,monkeypatch):
    import uz801_manager.hotspot as hotspot
    monkeypatch.setattr(hotspot,'network_lock',nullcontext)
    bus=Bus();bus.props[MODEM]['SupportedBands']=[1,33,38];bus.props[MODEM]['CurrentBands']=[256]
    original=bus.call_blocking
    def call(*args,**kwargs):
        if args[3]=='SetCurrentBands':bus.calls.append(args[1:6]);return None
        return original(*args,**kwargs)
    bus.call_blocking=call
    modem=make_modem(bus)
    modem.call('bands',selection='b3',confirm=True)
    assert modem.radio.load_bands()=='b3' and modem.radio.load() is None
    assert any(c[2]=='SetCurrentBands' and c[3]=='au' and c[4]==[[1,33]] for c in bus.calls)
    with pytest.raises(RuntimeError,match='UNSUPPORTED'):modem.call('bands',selection='b41',confirm=True)


def test_roaming_reads_home_from_sim_not_serving_operator(make_modem,monkeypatch,owner):
    import uz801_manager.hotspot as hotspot
    monkeypatch.setattr(hotspot,'network_lock',nullcontext)
    monkeypatch.setattr(hotspot,'Hotspot',lambda:owner)
    bus=Bus();bus.props[SERVICE+'.Sim']={'OperatorIdentifier':'00101'}
    original=bus.call_blocking
    def call(*args,**kwargs):
        if args[3]=='Register':owner.calls.append(args[5][0]);return None
        return original(*args,**kwargs)
    bus.call_blocking=call
    result=make_modem(bus).call('roaming',allowed=False,confirm=True)
    assert result['saved'] and owner.calls[-1]=='00101'
    assert '00101' not in str(result)


@pytest.mark.parametrize('body',[
    {'action':'roaming','allowed':1,'confirm':True},
    {'action':'bands','selection':'b99','confirm':True},
    {'action':'bands','selection':'auto','confirm':False},
])
def test_exact_radio_action_validation(body):
    with pytest.raises(ValueError):validate_action(body)


def test_background_display_does_not_take_the_action_lock(make_modem):
    modem=make_modem(Bus())
    def locked():raise RuntimeError('MODEM_BUSY')
    modem.lock_factory=locked
    assert modem.call('status')['registered']
    with pytest.raises(RuntimeError,match='MODEM_BUSY'):modem.call('mode',allowed=8,preferred=0,confirm=True)

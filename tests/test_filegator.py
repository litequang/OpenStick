import io
import json
import re
import zipfile

from flask import Flask
import pytest

from uz801_manager.filegator import CHUNK_REQUEST_LIMIT, register_filegator
from uz801_manager.hosting import create_hosting_app
from uz801_manager.lan_access import LanSettings
from uz801_manager.static_site import StaticSite
from uz801_manager.website_panel import WebsitePanel


@pytest.fixture
def bridge(tmp_path):
    root = tmp_path / 'public';root.mkdir()
    (root/'index.html').write_text('owner')
    panel = WebsitePanel(StaticSite(root, lock_path=None), 'fixture.example.com')
    calls = []
    class Connection:
        reply = b'{"data":[]}'
        def __init__(self, host, port, timeout):
            assert (host, port) == ('127.0.0.1',8788)
            self.closed = False
        def request(self, method, path, body, headers):
            calls.append((method,path,body,headers))
        def getresponse(self):
            result=io.BytesIO(self.reply);result.status=200
            result.getheaders=lambda:[('Content-Type','application/json'),('X-CSRF-Token','fixture'),
                                      ('Set-Cookie','filegator=fixture; Path=/files/main/'),
                                      ('Server','do-not-forward')]
            return result
        def close(self):self.closed=True
    app=Flask(__name__)
    register_filegator(app,panel,enabled=True,connection=Connection)
    return app.test_client(),panel,calls,Connection


def test_upstream_is_fixed_and_only_selected_site_and_scoped_cookie_are_forwarded(bridge):
    client,panel,calls,_=bridge
    client.set_cookie('openstick_lan_session','private-login')
    client.set_cookie('filegator','fixture',path='/files/main/')
    response=client.get('/files/main/?r=/getuser',headers={'X-OpenStick-Root':'/etc','Authorization':'private'})
    assert response.status_code==200 and response.json=={'data':[]}
    assert calls[0][3]['X-OpenStick-Root']==str(panel.default.directory)
    assert calls[0][3]['Cookie']=='filegator=fixture'
    assert 'Authorization' not in calls[0][3] and 'Server' not in response.headers
    assert response.headers['Set-Cookie'].startswith('filegator=')


@pytest.mark.parametrize('path',[
    '/files/unknown/','/files/main/private/users.json','/files/main/img/../../private/users.json',
    '/files/main/?r=http://evil.invalid','/files/main/?r=/login','/files/main/?r=/storeuser',
    '/files/main/?r=/getdir&r=/deleteitems',
])
def test_invalid_site_actions_and_private_assets_never_reach_upstream(bridge,path):
    client,_,calls,_=bridge
    assert client.get(path).status_code==400
    assert not calls


def test_chunk_limit_and_interrupted_zip_gate_block_before_upstream(bridge):
    client,panel,calls,_=bridge
    assert client.post('/files/main/?r=/upload',data=b'x'*(CHUNK_REQUEST_LIMIT+1)).status_code==413
    assert not calls
    files=panel.files(panel.read()[0]);work=files.private/'operation-fixture';work.mkdir(parents=True)
    (work/'journal.json').write_text('broken')
    assert client.get('/files/main/').json['error']=='ZIP_RECOVERY_REQUIRED'
    assert not calls


def test_direct_upstream_extraction_uses_existing_safe_zip_backend_after_csrf(bridge):
    client,panel,calls,connection=bridge
    root=panel.default.directory
    with zipfile.ZipFile(root/'website.zip','w') as archive:
        archive.writestr('assets/main.css','body{}')
    response=client.post('/files/main/?r=/unzipitem',json={'item':'/website.zip','destination':'/'},
                         headers={'X-CSRF-Token':'fixture'})
    assert response.status_code==200 and response.json=={'data':'Done'}
    assert (root/'assets/main.css').read_text()=='body{}'
    assert (root/'index.html').read_text()=='owner'
    assert calls[0][1]=='/?r=/getdir' and calls[0][3]['X-CSRF-Token']=='fixture'
    connection.reply=b''
    (root/'assets/main.css').unlink()
    assert client.post('/files/main/?r=/unzipitem',json={'item':'/website.zip','destination':'/'}).status_code==403
    assert not (root/'assets/main.css').exists()


def test_zip_traversal_remains_blocked(bridge):
    client,panel,_,_=bridge
    with zipfile.ZipFile(panel.default.directory/'bad.zip','w') as archive:
        archive.writestr('../escaped.html','blocked')
    response=client.post('/files/main/?r=/unzipitem',json={'item':'/bad.zip','destination':'/'})
    assert response.status_code==400
    assert not (panel.default.directory.parent/'escaped.html').exists()


def test_bridge_inherits_real_lan_auth_origin_and_credential_rotation(tmp_path,monkeypatch):
    from uz801_manager import filegator
    monkeypatch.setattr(filegator,'installed',lambda:True)
    root=tmp_path/'public';root.mkdir()
    settings=LanSettings(tmp_path/'private');settings.configure('fixture-password-123')
    app=create_hosting_app(backend=object(),site_backend=StaticSite(root,lock_path=None),
                           token='fixture-token',usb_portal=True,modem_backend=object(),
                           authority='192.0.2.2:8765',lan_auth=settings)
    client=app.test_client();base='http://192.0.2.2:8765'
    assert client.get('/files/main/',base_url=base).location=='/login'
    assert client.post('/files/main/?r=/deleteitems',base_url=base,headers={'Origin':'http://evil.invalid'}).status_code==403
    page=client.get('/login',base_url=base)
    csrf=re.search(r'name="csrf" value="([^"]+)"',page.text)[1]
    assert client.post('/login',base_url=base,headers={'Origin':base},
                       data={'csrf':csrf,'password':'fixture-password-123'}).status_code==302
    page=client.get('/website/files',base_url=base)
    assert b'id="web-filegator"' in page.data
    settings.configure('fixture-new-password-123')
    assert client.get('/files/main/',base_url=base).status_code==403


def test_embedding_is_same_origin_and_only_file_manager_page_can_host_frames(tmp_path,monkeypatch):
    from uz801_manager import filegator
    monkeypatch.setattr(filegator,'installed',lambda:True)
    root=tmp_path/'public';root.mkdir()
    app=create_hosting_app(backend=object(),site_backend=StaticSite(root,lock_path=None),
                          token='fixture',usb_portal=True,modem_backend=object(),authority='127.0.0.1:8765')
    client=app.test_client();base='http://127.0.0.1:8765'
    # Unknown site is rejected before any upstream connection; the same header
    # policy wraps every bridge response, including errors and streamed HTML.
    child=client.get('/files/unknown/',base_url=base)
    assert child.status_code==400
    assert child.headers['X-Frame-Options']=='SAMEORIGIN'
    assert "frame-ancestors 'self'" in child.headers['Content-Security-Policy']
    assert "script-src 'self';" in child.headers['Content-Security-Policy']
    for path in ['/website/files','/website/uploads']:
        parent=client.get(path,base_url=base)
        assert parent.status_code==200
        assert "frame-src 'self'" in parent.headers['Content-Security-Policy']
        assert "frame-ancestors 'none'" in parent.headers['Content-Security-Policy']
        assert parent.headers['X-Frame-Options']=='DENY'
    for path in ['/website','/overview','/login']:
        other=client.get(path,base_url=base)
        assert "frame-src 'self'" not in other.headers['Content-Security-Policy']
        assert other.headers['X-Frame-Options']=='DENY'

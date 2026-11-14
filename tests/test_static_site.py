import base64
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from uz801_manager.hosting import create_hosting_app
from uz801_manager.static_site import FILE_LIMIT, SiteError, StaticSite


@pytest.fixture
def site(tmp_path):
    root = tmp_path / 'website'
    root.mkdir()
    return StaticSite(root, lock_path=None)


def put(site, path='index.html', text='<h1>Fixture</h1>', expected=None):
    return site.call({'action': 'put', 'path': path, 'text': text, 'expected': expected, 'confirm': True})


def test_editor_persists_utf8_and_rejects_stale_overwrite_and_delete(site):
    saved = put(site, text='<h1>Xin chào</h1>')
    reopened = StaticSite(site.directory, lock_path=None).call({'action': 'get', 'path': 'index.html'})
    assert reopened['text'] == '<h1>Xin chào</h1>' and reopened['etag'] == saved['etag']
    with pytest.raises(SiteError, match='FILE_CHANGED'):put(site)
    second = put(site, text='new version', expected=saved['etag'])
    with pytest.raises(SiteError, match='FILE_CHANGED'):
        site.call({'action': 'delete', 'path': 'index.html', 'expected': saved['etag'], 'confirm': True})
    assert site.call({'action': 'delete', 'path': 'index.html', 'expected': second['etag'], 'confirm': True})['deleted']


@pytest.mark.parametrize('path', ['../secret.txt', '/etc/a.txt', 'assets/../../a.js', 'assets\\a.js',
                                  'a//x.js', '.env', 'keys.pem', 'a.php', 'a.py', 'a.exe', 'a\x00.html',
                                  'a/./x.css', 'a/../x.css', 'a:b.html'])
def test_path_validation_cannot_escape_public_site_or_upload_server_code(site, path):
    with pytest.raises(SiteError, match='PATH_INVALID'):put(site, path=path)
    assert site.call({'action': 'list'})['files'] == []


def test_upload_is_binary_exact_with_size_and_confirmation_limits(site):
    data = bytes(range(256)) * 6
    value = {'action': 'upload', 'path': 'assets/image.png', 'base64': base64.b64encode(data).decode(),
             'expected': None, 'confirm': False}
    with pytest.raises(SiteError, match='CONFIRM_REQUIRED'):site.call(value)
    value['confirm'] = True
    site.call(value)
    assert (site.directory / 'assets/image.png').read_bytes() == data
    assert site.call({'action': 'get', 'path': 'assets/image.png'})['text'] is None
    value.update(path='x.png', base64='not valid base64!!')
    with pytest.raises(SiteError, match='INPUT_INVALID'):site.call(value)
    with pytest.raises(SiteError, match='FILE_TOO_LARGE'):put(site, path='x.txt', text='x' * (FILE_LIMIT + 1))
    assert not list(site.directory.rglob('.openstick-*'))


def test_symlink_is_not_listed_or_read_or_overwritten(site, tmp_path):
    secret = tmp_path / 'secret.txt'
    secret.write_text('private-fixture')
    try:(site.directory / 'leak.txt').symlink_to(secret)
    except OSError:pytest.skip('OS account cannot create symlinks')
    assert site.call({'action': 'list'})['files'] == []
    with pytest.raises(SiteError, match='PATH_INVALID'):site.call({'action': 'get', 'path': 'leak.txt'})
    with pytest.raises(SiteError, match='PATH_INVALID'):put(site, path='leak.txt')
    assert secret.read_text() == 'private-fixture'


def test_directory_symlink_rejected_even_without_os_symlink_privilege(site, monkeypatch):
    original = Path.is_symlink
    monkeypatch.setattr(Path, 'is_symlink', lambda p: p.name == 'escape' or original(p))
    with pytest.raises(SiteError, match='PATH_INVALID'):put(site, path='escape/leak.txt')


def test_site_quota_and_file_limit_do_not_replace_original(site, monkeypatch):
    first = put(site)
    monkeypatch.setattr('uz801_manager.static_site.SITE_LIMIT', 10)
    with pytest.raises(SiteError, match='SITE_TOO_LARGE'):put(site, text='x' * 11, expected=first['etag'])
    assert site.call({'action': 'get', 'path': 'index.html'})['etag'] == first['etag']


def test_routes_need_local_host_and_api_token_and_keep_non_upload_limit(site):
    app = create_hosting_app(backend=object(), usb_portal=True, token='fixture', site_backend=site)
    client = app.test_client()
    base = 'http://172.16.42.1'
    h = {'X-OpenStick-Token': 'fixture', 'Origin': base}
    assert client.get('/website', base_url=base).status_code == 200
    assert client.post('/api/site', base_url=base, json={'action': 'list'}).status_code == 403
    assert client.post('/api/site', base_url=base, headers={**h, 'Origin': 'null'}, json={'action': 'list'}).status_code == 403
    assert client.post('/api/site', base_url=base, headers=h,
                       json={'action': 'put', 'path': 'index.html', 'text': 'x' * 8000,
                             'expected': None, 'confirm': True}).status_code == 200
    assert client.post('/api/wifi', base_url=base, headers=h, data='x' * 8000,
                       content_type='application/json').status_code == 413
    assert client.post('/api/site', base_url=base, headers=h, data='x' * 1500001,
                       content_type='application/json').status_code == 413
    app = create_hosting_app(backend=object(), token='fixture', site_backend=site)
    assert app.test_client().get('/website', base_url='http://127.0.0.1:8770').status_code == 404


def test_lan_site_routes_remain_authenticated(site, tmp_path):
    from uz801_manager.lan_access import LanSettings
    settings = LanSettings(tmp_path / 'settings')
    settings.configure('fixture-long-passphrase')
    app = create_hosting_app(backend=object(), usb_portal=True, token='fixture', site_backend=site,
                             authority='192.0.2.2:8765', lan_auth=settings)
    client = app.test_client()
    base = 'http://192.0.2.2:8765'
    assert client.get('/website', base_url=base).location == '/login'
    assert client.post('/api/site', base_url=base, headers={'X-OpenStick-Token': 'fixture'},
                       json={'action': 'list'}).status_code == 401


def test_editor_script_uses_literal_content_and_never_publishes_without_confirmation(site, tmp_path):
    node = shutil.which('node')
    if not node:pytest.skip('Node.js required for synthetic editor fixture')
    app = create_hosting_app(backend=object(), usb_portal=True, token='fixture', site_backend=site)
    page = tmp_path / 'page.html'
    page.write_text(app.test_client().get('/website', base_url='http://172.16.42.1').text, encoding='utf-8')
    result = subprocess.run([node, str(Path(__file__).with_name('website_ui_fixture.cjs')), str(page)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr

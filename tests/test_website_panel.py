import io
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import zipfile

import pytest

from uz801_manager.hosting import create_hosting_app
from uz801_manager.site_domains import DomainPublisher
from uz801_manager.site_files import SiteFiles, UPLOAD_LIMIT
from uz801_manager.static_site import SiteError, StaticSite
from uz801_manager.website_panel import WebsitePanel


@pytest.fixture
def panel(tmp_path):
    root = tmp_path / 'public';root.mkdir()
    (root / 'index.html').write_text('original', encoding='utf-8')
    return WebsitePanel(StaticSite(root, lock_path=None), 'original.example.com')


def create(panel, name='Second', domains=None, expected=None):
    return panel.call({'action':'create', 'name':name, 'domains':domains or [],
                       'expected':expected or panel.call({'action':'sites'})['revision'], 'confirm':True})


def listing(panel, identity='main'):
    return panel.call({'action':'list', 'site':identity})


def archive(items):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for name, data in items:package.writestr(name, data)
    stream.seek(0)
    return stream


def test_registry_creation_is_private_and_isolated_without_touching_legacy_site(panel):
    initial = panel.call({'action':'sites'})
    assert not panel.directory.exists(), 'Reading the panel must not initialize private state'
    created = create(panel, domains=['two.example.com'])
    identity = created['selected']
    assert identity != 'main' and created['sites'][1]['domains'] == ['two.example.com']
    assert (panel.default.directory / 'index.html').read_text() == 'original'
    rev = listing(panel, identity)['revision']
    panel.call({'action':'put', 'site':identity, 'path':'index.html', 'text':'second',
                'expected':None, 'revision':rev, 'confirm':True})
    assert (panel.roots / identity / 'index.html').read_text() == 'second'
    assert (panel.default.directory / 'index.html').read_text() == 'original'
    reopened = WebsitePanel(panel.default, panel.hostname)
    assert reopened.read()[1]['id'] == identity
    if __import__('os').name != 'nt':assert (panel.directory / 'sites.json').stat().st_mode & 0o077 == 0
    with pytest.raises(SiteError, match='FILE_CHANGED'):
        create(panel, expected=initial['revision'])


@pytest.mark.parametrize('domain', ['http://evil.example', 'x.example;root', '*.example.com',
                                  'openstick.local', '127.0.0.1', 'x.example/path', '-x.example.com'])
def test_domains_cannot_inject_nginx_or_route_local_management(panel, domain):
    with pytest.raises(SiteError, match='DOMAIN_INVALID'):create(panel, domains=[domain])
    assert not panel.roots.exists()


def test_domain_unique_primary_protected_and_corrupt_registry_fails_closed(panel):
    created = create(panel, domains=['two.example.com'])
    with pytest.raises(SiteError, match='DOMAIN_DUPLICATE'):create(panel, domains=['TWO.EXAMPLE.COM'])
    with pytest.raises(SiteError, match='PRIMARY_DOMAIN_PROTECTED'):
        panel.call({'action':'configure','site':'main','name':'Main','domains':[],
                    'expected':created['revision'],'confirm':True})
    private = panel.directory / 'sites.json'
    private.write_text('{broken', encoding='utf-8')
    with pytest.raises(SiteError, match='REGISTRY_INVALID'):panel.call({'action':'sites'})
    assert private.read_text() == '{broken'


def test_file_manager_mkdir_copy_move_delete_and_stale_conflict(panel):
    files = panel.files(panel.read()[0])
    old = files.listing()['revision']
    state = files.mutate('mkdir','assets/ảnh',old)
    assert (files.root / 'assets/ảnh').is_dir()
    with pytest.raises(SiteError, match='FILE_CHANGED'):files.mutate('delete','index.html',old)
    state = files.mutate('copy','index.html',state['revision'],'assets/ảnh/copy.html')
    state = files.mutate('move','assets/ảnh',state['revision'],'images')
    assert (files.root / 'images/copy.html').read_text() == 'original'
    with pytest.raises(SiteError, match='PATH_EXISTS'):
        files.mutate('copy','images/copy.html',state['revision'],'index.html')
    files.mutate('delete','images',state['revision'])
    assert not (files.root / 'images').exists()
    assert (files.root / 'index.html').read_text() == 'original'


@pytest.mark.parametrize('name', ['../secret.html','/etc/x.html','a\\x.html','.env','a/.git',
                                'a//x.html','a/../x.html','C:/x.html','NUL.html','x.php','id.pem'])
def test_advanced_file_paths_confined_and_server_code_blocked(panel, name):
    files = panel.files(panel.read()[0])
    with pytest.raises(SiteError):files.upload(name,io.BytesIO(b'bad'),files.listing()['revision'])
    assert (files.root / 'index.html').read_text() == 'original'


def test_large_upload_streams_beyond_old_one_mib_without_base64(panel):
    files = panel.files(panel.read()[0])
    class Source:
        remaining=2*1048576+73
        def read(self, amount):
            assert 0 < amount <= 65536
            count = min(self.remaining, amount);self.remaining -= count
            return b'\x80' * count
    files.upload('large.pdf',Source(),files.listing()['revision'])
    assert (files.root / 'large.pdf').stat().st_size == 2*1048576+73
    assert not list(files.private.glob('operation-*'))


def test_upload_quota_and_reserve_rejection_leave_old_file(panel, monkeypatch):
    files = panel.files(panel.read()[0])
    monkeypatch.setattr('uz801_manager.site_files.UPLOAD_LIMIT', 5)
    with pytest.raises(SiteError, match='FILE_TOO_LARGE'):
        files.upload('index.html',io.BytesIO(b'123456'),files.listing()['revision'])
    monkeypatch.setattr('uz801_manager.site_files.shutil.disk_usage', lambda _:SimpleNamespace(free=1))
    with pytest.raises(SiteError, match='DISK_SPACE_LOW'):
        files.upload('index.html',io.BytesIO(b'new'),files.listing()['revision'])
    assert (files.root / 'index.html').read_text() == 'original'


def test_zip_preview_does_not_publish_then_confirmed_extract_preserves_unrelated(panel):
    files = panel.files(panel.read()[0]);(files.root / 'keep.txt').write_text('keep')
    data = [('index.html',b'<h1>New</h1>'),('assets/a.css',b'body{}'),('empty/',b'')]
    preview = files.unzip(archive(data),'')
    assert preview['files'][0]['overwrite'] is True
    assert (files.root / 'index.html').read_text() == 'original' and not (files.root / 'assets').exists()
    state = files.unzip(archive(data),'',publish=True,expected=preview['revision'],digest=preview['digest'])
    assert state['published'] == 2
    assert (files.root / 'assets/a.css').read_bytes() == b'body{}'
    assert (files.root / 'keep.txt').read_text() == 'keep' and (files.root / 'empty').is_dir()
    assert not list(files.private.glob('operation-*'))


@pytest.mark.parametrize('items', [[('../x.html',b'x')],[('/x.html',b'x')],[('.env',b'x')],
                                  [('x.php',b'x')],[('a.html',b'x'),('A.html',b'y')],
                                  [('a.html/x.js',b'x'),('a.html',b'y')]])
def test_zip_slip_duplicates_code_and_file_parent_collisions_do_not_write(panel, items):
    files = panel.files(panel.read()[0])
    with pytest.raises(SiteError):files.unzip(archive(items),'')
    assert len(files.listing()['entries']) == 1
    assert not list(files.private.glob('operation-*'))


def test_zip_symlink_rejected_without_needing_windows_symlink_privilege(panel):
    files = panel.files(panel.read()[0]);info=zipfile.ZipInfo('link.html')
    info.create_system=3;info.external_attr=(stat.S_IFLNK|0o777)<<16
    with pytest.raises(SiteError,match='ZIP_INVALID'):files.unzip(archive([(info,b'../secret')]),'')


def test_zip_bounds_stale_site_and_different_archive_fail_before_public_mutation(panel, monkeypatch):
    files = panel.files(panel.read()[0]);data=[('new.html',b'new')]
    preview=files.unzip(archive(data),'')
    (files.root/'other.txt').write_text('changed')
    with pytest.raises(SiteError,match='FILE_CHANGED'):
        files.unzip(archive(data),'',publish=True,expected=preview['revision'],digest=preview['digest'])
    preview=files.unzip(archive(data),'')
    with pytest.raises(SiteError,match='FILE_CHANGED'):
        files.unzip(archive([('new.html',b'different')]),'',publish=True,expected=preview['revision'],digest=preview['digest'])
    monkeypatch.setattr('uz801_manager.site_files.UPLOAD_LIMIT', 2)
    with pytest.raises(SiteError,match='FILE_TOO_LARGE'):files.unzip(archive(data),'')
    assert not (files.root/'new.html').exists()


def test_zip_io_failure_rolls_back_overwrites_and_created_directories(panel, monkeypatch):
    files=panel.files(panel.read()[0]);data=[('index.html',b'new'),('new/a.css',b'css')]
    preview=files.unzip(archive(data),'');replace=files.replace
    def fail(name, source):
        if name=='new/a.css':raise OSError('fixture disk error')
        return replace(name,source)
    monkeypatch.setattr(files,'replace',fail)
    with pytest.raises(SiteError,match='ZIP_PUBLISH_FAILED'):
        files.unzip(archive(data),'',publish=True,expected=preview['revision'],digest=preview['digest'])
    assert (files.root/'index.html').read_text()=='original'
    assert not (files.root/'new').exists()


def interrupted_zip(panel, monkeypatch):
    files=panel.files(panel.read()[0]);data=[('index.html',b'partial'),('new/a.css',b'new')]
    preview=files.unzip(archive(data),'');replace=files.replace
    def interrupted(name,source):
        if name=='new/a.css':raise SystemExit('fixture process terminated')
        return replace(name,source)
    monkeypatch.setattr(files,'replace',interrupted)
    with pytest.raises(SystemExit):
        files.unzip(archive(data),'',publish=True,expected=preview['revision'],digest=preview['digest'])
    monkeypatch.setattr(files,'replace',replace)
    return files


def test_interrupted_publication_retains_originals_blocks_writes_and_recovers(panel,monkeypatch):
    files=interrupted_zip(panel,monkeypatch)
    assert files.listing()['recovery_required'] is True
    assert (files.root/'index.html').read_bytes()==b'partial'
    assert len(list(files.private.glob('operation-*/before-*')))==1
    with pytest.raises(SiteError,match='ZIP_RECOVERY_REQUIRED'):
        files.mutate('delete','index.html',files.listing()['revision'])
    state=files.recover()
    assert state['recovery_required'] is False and not (files.root/'new').exists()
    assert (files.root/'index.html').read_text()=='original'
    assert not list(files.private.glob('operation-*'))


def test_recovery_refuses_to_overwrite_later_external_edits(panel,monkeypatch):
    files=interrupted_zip(panel,monkeypatch)
    (files.root/'index.html').write_text('external edit')
    with pytest.raises(SiteError,match='ZIP_RECOVERY_CHANGED'):files.recover()
    assert (files.root/'index.html').read_text()=='external edit'
    assert files.listing()['recovery_required'] is True


def test_zip_member_count_bounded_before_constructing_zipfile(panel,monkeypatch):
    package=archive([(f'x{i}.txt',b'') for i in range(2001)])
    monkeypatch.setattr('uz801_manager.site_files.zipfile.ZipFile',lambda *a,**kw:pytest.fail('Unbounded metadata allocation'))
    files=panel.files(panel.read()[0])
    with pytest.raises(SiteError,match='ZIP_INVALID'):files.unzip(package,'')


def test_download_zip_roundtrip_contains_only_public_tree(panel):
    files=panel.files(panel.read()[0]);(files.root/'assets').mkdir()
    (files.root/'assets/x.png').write_bytes(bytes(range(256)))
    output=io.BytesIO();files.archive('',output);output.seek(0)
    with zipfile.ZipFile(output) as package:
        assert package.read('assets/x.png')==bytes(range(256))
        assert package.read('index.html')==b'original'


def test_new_routes_keep_tokens_origins_lan_and_non_upload_limits(panel,tmp_path):
    app=create_hosting_app(backend=object(),usb_portal=True,token='fixture',site_backend=panel.default,
                           hostname=panel.hostname)
    client=app.test_client();base='http://172.16.42.1';h={'X-OpenStick-Token':'fixture','Origin':base}
    assert client.post('/api/websites',base_url=base,json={'action':'sites'}).status_code==403
    assert client.post('/api/websites',base_url=base,headers={**h,'Origin':'null'},json={'action':'sites'}).status_code==403
    current=client.post('/api/websites',base_url=base,headers=h,json={'action':'list','site':'main'}).json
    uploaded=client.post('/api/websites/transfer',base_url=base,headers=h,data={
        'action':'upload','site':'main','path':'x.pdf','revision':current['revision'],'confirm':'true',
        'file':(io.BytesIO(b'x'*(2*1048576)),'x.pdf')})
    assert uploaded.status_code==200
    downloaded=client.post('/api/websites/download',base_url=base,headers=h,json={
        'site':'main','path':'x.pdf','revision':uploaded.json['revision']})
    assert downloaded.data==b'x'*(2*1048576)
    downloaded.close()
    assert client.post('/api/wifi',base_url=base,headers=h,data='x'*8000,content_type='application/json').status_code==413
    from uz801_manager.lan_access import LanSettings
    settings=LanSettings(tmp_path/'lan');settings.configure('fixture-long-password')
    lan=create_hosting_app(backend=object(),usb_portal=True,token='fixture',site_backend=panel.default,
                           hostname=panel.hostname,authority='192.0.2.1:8765',lan_auth=settings).test_client()
    assert lan.post('/api/websites',base_url='http://192.0.2.1:8765',headers={'X-OpenStick-Token':'fixture'},json={'action':'sites'}).status_code==401
    assert lan.post('/api/websites/transfer',base_url='http://192.0.2.1:8765',headers={'X-OpenStick-Token':'fixture'}).status_code==401


def publisher(tmp_path, run):
    nginx=tmp_path/'nginx.conf';tunnel=tmp_path/'config.yml'
    nginx.write_text('events {}\nhttp {\n server { listen 127.0.0.1:8080 default_server; root /var/www/original; }\n}\n')
    tunnel.write_text('tunnel: private-fixture\ncredentials-file: /private/credentials.json\ningress:\n'
                      '  - hostname: original.example.com\n    service: http://127.0.0.1:8080\n  - service: http_status:404\n')
    result=DomainPublisher(nginx=nginx,tunnel=tunnel,virtual_hosts=tmp_path/'panel.conf',run=run)
    result.available=lambda:True
    return result


def test_domain_apply_preserves_original_tunnel_credentials_and_default_server(tmp_path):
    calls=[]
    p=publisher(tmp_path,lambda args,**kw:(calls.append(args) or SimpleNamespace(returncode=0)))
    sites=[{'domains':['original.example.com'],'root':'/var/www/original'},
           {'domains':['two.example.com','www.two.example.com'],'root':'/var/www/openstick-sites/fixed-id'}]
    original=p.tunnel.read_text()
    result=p.apply(sites,'original.example.com',tmp_path/'private')
    assert result['dns']=='UNVERIFIED' and len(calls)==4
    assert 'default_server; root /var/www/original' in p.nginx.read_text()
    assert original.split('ingress:')[0] in p.tunnel.read_text()
    assert 'two.example.com' in p.virtual_hosts.read_text()
    assert p.tunnel.read_text().endswith('  - service: http_status:404\n')
    assert p.state(sites,'original.example.com')['local']=='CONFIG_SAVED'
    p.apply(sites,'original.example.com',tmp_path/'private')
    assert p.tunnel.read_text().count(p.BEGIN)==1 and p.nginx.read_text().count(p.INCLUDE)==1


def test_domain_validation_failure_restores_all_config_and_does_not_restart(tmp_path):
    calls=[]
    p=publisher(tmp_path,lambda args,**kw:(calls.append(args) or SimpleNamespace(returncode=1)))
    originals=[p.nginx.read_bytes(),p.tunnel.read_bytes()]
    with pytest.raises(SiteError,match='DOMAIN_PUBLISH_FAILED'):
        p.apply([{'domains':['two.example.com'],'root':'/var/www/sites/id'}],'original.example.com',tmp_path/'private')
    assert [p.nginx.read_bytes(),p.tunnel.read_bytes()]==originals
    assert not p.virtual_hosts.exists() and len(calls)==1
    assert 'rc-service' not in calls[0]


def test_unknown_tunnel_schema_refuses_to_overwrite(tmp_path):
    p=publisher(tmp_path,lambda *a,**kw:pytest.fail('Must not run services'))
    p.tunnel.write_text('ingress:\n - hostname: unknown.example.com\n   service: https://other.example.com\n')
    before=p.tunnel.read_bytes()
    with pytest.raises(SiteError,match='DOMAIN_CONFIG_UNSUPPORTED'):p.apply([], 'original.example.com',tmp_path/'private')
    assert p.tunnel.read_bytes()==before and not p.virtual_hosts.exists()

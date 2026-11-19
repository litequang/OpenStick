import hashlib
import re

from uz801_manager.hosting import create_hosting_app
from uz801_manager.portal_assets import fingerprinted_filegator_asset

BASE='http://172.16.42.1'


def test_versioned_assets_cache_but_html_api_errors_and_unversioned_assets_do_not():
    app=create_hosting_app(backend=object(),usb_portal=True,modem_backend=object(),token='fixture')
    c=app.test_client();html=c.get('/overview',base_url=BASE)
    assert html.headers['Cache-Control']=='no-store'
    urls=re.findall(r'(?:src|href)="(/static/[^" ]+)"',html.text)
    assert urls and all('?v=' in u for u in urls)
    for url in urls:
        r=c.get(url,base_url=BASE)
        assert r.status_code==200 and 'immutable' in r.headers['Cache-Control']
        assert hashlib.sha256(r.data).hexdigest()[:24]==url.split('?v=')[1]
        assert c.get(url,base_url=BASE,headers={'If-None-Match':r.headers['ETag']}).status_code==304
        assert c.get(url+'&v=duplicate',base_url=BASE).headers['Cache-Control']=='no-store'
        assert c.get(url,base_url='http://evil.invalid').headers['Cache-Control']=='no-store'
    for path in ['/static/portal.css','/static/portal.css?v=old','/static/missing.js?v=unknown','/api/header','/login']:
        assert c.get(path,base_url=BASE).headers['Cache-Control']=='no-store'


def test_versions_change_with_asset_bytes_and_are_not_private_configuration(tmp_path):
    from flask import Flask
    from uz801_manager.portal_assets import install_assets
    (tmp_path/'test.js').write_text('one')
    app=Flask(__name__,static_folder=str(tmp_path));install_assets(app)
    first=app.jinja_env.globals['portal_asset']('test.js')
    (tmp_path/'test.js').write_text('two')
    other=Flask(__name__,static_folder=str(tmp_path));install_assets(other)
    assert first!=other.jinja_env.globals['portal_asset']('test.js')
    assert first==app.jinja_env.globals['portal_asset']('test.js')  # Frozen per process.
    assert not any(key in first for key in ['token','ssid','hostname'])


def test_filegator_cache_allowlist_excludes_api_downloads_and_nonfingerprinted_assets():
    assert fingerprinted_filegator_asset('js/app.1234abcd.js')
    assert fingerprinted_filegator_asset('fonts/icon.1234abcd.woff2')
    for name in ['','index.html','js/app.js','js/../../app.1234abcd.js','configuration.php','js/config.1234abcd.php']:
        assert not fingerprinted_filegator_asset(name)

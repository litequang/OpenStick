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


def test_filegator_numeric_cachebusters_and_unquoted_attributes_are_replaced_only_for_known_bundles():
    from uz801_manager.portal_assets import version_filegator_html
    source='<link href=css/app.css?123 rel=stylesheet><script src="js/app.js?456"></script><script src="js/app.js?token=private"></script><script src="js/unknown.js?789"></script>'
    result=version_filegator_html(source,{'css/app.css':'csshash','js/app.js':'jshash'})
    assert 'href="css/app.css?v=csshash"' in result
    assert 'src="js/app.js?v=jshash"' in result
    assert 'js/app.js?token=private' in result and 'js/unknown.js?789' in result

"""Exercise only scripts/preview_portal.py's disposable website and registry."""
import io
import json
from pathlib import Path
import zipfile

from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8771'
OUT = Path('artifacts/website-browser')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        try:
            page=browser.new_page();errors=[];actions=[]
            page.add_init_script("""window.fixtureTransfers=[];
              const send=XMLHttpRequest.prototype.send;
              XMLHttpRequest.prototype.send=function(data){
                if(data instanceof FormData)window.fixtureTransfers.push(data.get('action'));
                return send.call(this,data);
              };""")
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda r:actions.append(r.post_data_json['action'])
                    if r.method=='POST' and r.url.endswith('/api/websites') else None)
            for width in [320,390,768,1280]:
                page.set_viewport_size({'width':width,'height':900})
                assert page.goto(BASE+'/website').status==200
                expect(page.locator('#web-status')).to_contain_text('Sẵn sàng')
                assert 'MÔ PHỎNG' in page.locator('body').inner_text()
                expect(page.locator('[data-nav=website]')).to_have_attribute('aria-current','page')
                for tab in ['files','uploads','domains']:
                    page.locator('[data-web-tab='+tab+']').click()
                    assert page.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth'),(width,tab)
                assert not errors,errors
                page.locator('[data-web-tab=files]').click()
                page.evaluate('window.scrollTo(0,0);document.activeElement.blur()')
                if width in [390,1280]:page.screenshot(path=str(OUT/f'panel-{width}.png'),full_page=True)
            assert set(actions)=={'sites','list'},'Opening the UI published something'
            page.set_viewport_size({'width':1280,'height':1000})
            page.locator('.web-file[data-path="index.html"]').click()
            expect(page.locator('#web-download')).to_be_enabled()
            original=page.locator('#site-text').input_value()
            page.locator('#site-text').fill('<h1>Edited fixture</h1>')
            page.once('dialog',lambda d:d.dismiss());page.locator('#site-save').click()
            assert 'put' not in actions
            page.once('dialog',lambda d:d.accept());page.locator('#site-save').click()
            expect(page.locator('#web-status')).to_contain_text('Đã xuất bản file')
            assert actions.count('put')==1
            page.locator('#web-mkdir').click();page.locator('#web-target').fill('assets')
            page.locator('#web-path-form button[type=submit]').click()
            expect(page.locator('#web-path-dialog')).not_to_be_visible()
            expect(page.locator('.web-file[data-path=assets]')).to_be_visible()
            page.locator('.web-file[data-path="index.html"]').click();page.locator('#web-copy').click()
            page.locator('#web-target').fill('assets/copy.html');page.locator('#web-path-form button[type=submit]').click()
            expect(page.locator('#web-path-dialog')).not_to_be_visible()
            page.locator('#web-search').fill('copy.html')
            page.locator('.web-file[data-path="assets/copy.html"]').click()
            expect(page.locator('#site-text')).to_have_value('<h1>Edited fixture</h1>')
            page.locator('#web-rename').click();page.locator('#web-target').fill('assets/renamed.html')
            page.locator('#web-path-form button[type=submit]').click()
            expect(page.locator('#web-path-dialog')).not_to_be_visible()
            page.locator('#web-search').fill('renamed.html')
            expect(page.locator('.web-file[data-path="assets/renamed.html"]')).to_be_visible()
            page.locator('#web-search').fill('')

            # A second document root; the original site's file stays byte-identical.
            page.locator('#web-create').click();page.locator('#web-site-name').fill('Demo second')
            page.locator('#web-site-domains').fill('second.example.com\nwww.second.example.com')
            page.locator('#web-site-form button[type=submit]').click()
            expect(page.locator('#web-site-dialog')).not_to_be_visible()
            expect(page.locator('#web-count')).to_contain_text('0 file')
            second=page.locator('#web-site').input_value()
            page.locator('[data-web-tab=uploads]').click()
            page.locator('#site-upload').set_input_files([
                {'name':'hello.html','mimeType':'text/html','buffer':b'<h1>Second root</h1>'},
                {'name':'large.pdf','mimeType':'application/pdf','buffer':b'x'*(2*1048576+17)}])
            expect(page.locator('#web-upload-list .web-transfer-row')).to_have_count(2)
            page.once('dialog',lambda d:d.accept());page.locator('#site-upload-send').click()
            expect(page.locator('#web-status')).to_contain_text('Đã xuất bản 2 file',timeout=30000)
            package=io.BytesIO()
            with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr('index.html','<h1>ZIP demo</h1>');z.writestr('styles/main.css','body{color:blue}')
            before=len(page.evaluate('window.fixtureTransfers'))
            # Regression: the ordinary file picker must accept ZIP and route to
            # inspection, not try to publish a blocked .zip as a static asset.
            page.locator('#site-upload').set_input_files({'name':'site.ZIP','mimeType':'application/zip','buffer':package.getvalue()})
            expect(page.locator('#web-zip-publish')).to_be_enabled()
            assert page.evaluate('window.fixtureTransfers')[before:]==['inspect_zip']
            expect(page.locator('#web-upload-status')).to_contain_text('kiểm tra thành công')
            expect(page.locator('#web-zip-selected')).to_contain_text('site.ZIP')
            expect(page.locator('#web-zip-summary')).to_contain_text('2 mục')
            page.once('dialog',lambda d:d.dismiss());page.locator('#web-zip-publish').click()
            expect(page.locator('#web-zip-publish')).to_be_enabled()
            assert page.evaluate('window.fixtureTransfers')[before:]==['inspect_zip'],'Cancel extracted the ZIP'
            page.once('dialog',lambda d:d.accept());page.locator('#web-zip-publish').click()
            expect(page.locator('#web-status')).to_contain_text('Đã giải nén và xuất bản 2 file')
            page.locator('[data-web-tab=files]').click()
            page.locator('.web-file[data-path="index.html"]').click()
            expect(page.locator('#site-text')).to_have_value('<h1>ZIP demo</h1>')
            with page.expect_download() as downloaded:page.locator('#web-download').click()
            assert Path(downloaded.value.path()).read_bytes()==b'<h1>ZIP demo</h1>'
            with page.expect_download() as downloaded:page.locator('#web-download-all').click()
            with zipfile.ZipFile(downloaded.value.path()) as z:assert z.read('styles/main.css')==b'body{color:blue}'
            page.locator('[data-web-tab=uploads]').click()
            blocked=io.BytesIO()
            with zipfile.ZipFile(blocked,'w') as z:z.writestr('blocked.php','fixture only')
            page.locator('#web-zip').set_input_files({'name':'blocked.zip','mimeType':'application/zip','buffer':blocked.getvalue()})
            expect(page.locator('#web-upload-status')).to_contain_text('blocked.php')
            expect(page.locator('#web-zip-publish')).to_be_disabled()
            # HTTP and connection failures stay visible by the picker and never
            # replay themselves or leave a stale extraction button enabled.
            failures=[]
            def too_large(route):failures.append(True);route.fulfill(status=413,body='too large')
            page.route('**/api/websites/transfer',too_large)
            page.locator('#web-zip').set_input_files({'name':'retry.zip','mimeType':'application/zip','buffer':package.getvalue()})
            expect(page.locator('#web-upload-status')).to_contain_text('HTTP 413')
            expect(page.locator('#web-upload-status')).not_to_contain_text('ZIP vượt 128 MiB')
            expect(page.locator('#web-zip-publish')).to_be_disabled()
            page.wait_for_timeout(300);assert len(failures)==1
            page.unroute('**/api/websites/transfer')
            def disconnected(route):failures.append(True);route.abort()
            page.route('**/api/websites/transfer',disconnected)
            page.locator('#web-zip-inspect').click()
            expect(page.locator('#web-upload-status')).to_contain_text('Mất kết nối')
            page.wait_for_timeout(300);assert len(failures)==2
            page.unroute('**/api/websites/transfer')
            page.locator('[data-web-tab=files]').click()
            page.locator('#web-site').select_option('main')
            expect(page.locator('.web-file[data-path="index.html"]')).to_be_visible()
            page.locator('.web-file[data-path="index.html"]').click()
            expect(page.locator('#site-text')).to_have_value('<h1>Edited fixture</h1>')
            page.locator('#site-text').fill(original)
            page.once('dialog',lambda d:d.accept());page.locator('#site-save').click()
            expect(page.locator('#web-status')).to_contain_text('Đã xuất bản file')
            page.locator('#web-site').select_option(second)
            expect(page.locator('.web-file[data-path="index.html"]')).to_be_visible()
            page.locator('[data-web-tab=domains]').click()
            expect(page.locator('#web-domains')).to_contain_text('second.example.com')
            expect(page.locator('#web-apply-domains')).to_be_disabled()
            assert not errors,errors
            print(json.dumps({'demo_only':True,'layouts':12,'javascript_errors':0,
                              'multisite_isolation':True,'file_operations':True,'upload_over_one_mib':True,
                              'zip_inspect_and_publish':True,'downloads':True,'cancel_does_not_publish':True,
                              'zip_from_normal_picker':True,'visible_failure_feedback':True,'no_automatic_retry':True}))
        finally:browser.close()


if __name__=='__main__':main()

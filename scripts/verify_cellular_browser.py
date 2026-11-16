"""APN form QA against loopback preview with fictional routed API responses."""
import json

from playwright.sync_api import sync_playwright, expect


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        try:
            page=browser.new_page();errors=[];writes=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            settings={'available':True,'name':'Fixture','apn':'fixture.apn','username':'fixture-user',
                      'password_saved':True,'auth':'pap','ip_family':'ipv4','roaming':False}
            page.route('**/api/cellular',lambda r:r.fulfill(json={'settings':settings,'blocked':False}))
            def save(route):
                writes.append(route.request.post_data_json)
                route.fulfill(status=202,json={'accepted':True})
            page.route('**/api/hotspot',save)
            page.route('**/api/hotspot/state',lambda r:r.fulfill(json={'busy':False,'result':{},'error':None,
                       'last_operation':{'action':'configure_cellular','error':None,'at':1}}))
            assert page.goto('http://127.0.0.1:8771/').url.endswith('/overview')
            for width in (320,390,768,1280):
                page.set_viewport_size({'width':width,'height':844})
                assert page.goto('http://127.0.0.1:8771/sim/apn').status==200
                expect(page.locator('#cellular-fields')).to_be_enabled()
                assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth')
                assert page.locator('.app-bottom-nav-item:visible').last.get_attribute('data-nav')=='overview'
                expect(page.locator('#cellular-password')).to_have_value('')
            assert not writes
            page.once('dialog',lambda d:d.dismiss());page.locator('#cellular-save').click()
            assert not writes
            page.locator('#cellular-password-action').select_option('replace')
            page.locator('#cellular-password').fill('fictional-apn-secret')
            page.once('dialog',lambda d:d.accept());page.locator('#cellular-save').click()
            expect(page.locator('#cellular-result')).to_contain_text('Đã lưu APN')
            expect(page.locator('#cellular-password')).to_have_value('')
            assert len(writes)==1 and writes[0]['password']=='fictional-apn-secret'
            assert 'fictional-apn-secret' not in page.evaluate('JSON.stringify(sessionStorage)')
            assert not errors
            print(json.dumps({'apn_viewports':4,'root_overview':True,'rightmost_overview':True,
                              'consent_and_secret_clear':'PASS','javascript_errors':0,'hardware_operations':0}))
        finally:browser.close()


if __name__=='__main__':main()

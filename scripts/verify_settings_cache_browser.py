"""Fictional preview: reopen settings while all live reads fail; no mutations."""
from playwright.sync_api import sync_playwright, expect
from verify_radio_refresh_browser import CAP

BASE='http://127.0.0.1:8771'


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        context=browser.new_context(viewport={'width':390,'height':844})
        page=context.new_page();blocked=[False];writes=[];errors=[]
        cellular={'available':True,'name':'Fictional APN','apn':'fixture','username':'fixture-private-user',
                  'password':'fixture-private-password','password_saved':True,'auth':'pap','ip_family':'ipv4','roaming':False}
        def route(request_route):
            request=request_route.request
            if request.method=='POST':writes.append(request.url)
            if blocked[0] and '/api/' in request.url:
                request_route.abort();return
            if request.url.endswith('/api/modem/status'):request_route.fulfill(json=CAP)
            elif request.url.endswith('/api/header'):
                request_route.fulfill(json={'connected':True,'hotspot_active':False,'ssid':'Fictional Wi-Fi','ipv4':[], 'modem_status':CAP})
            elif request.url.endswith('/api/cellular'):
                request_route.fulfill(json={'settings':cellular,'profiles':[],'blocked':False})
            else:request_route.continue_()
        context.route('**/*',route)
        page.on('pageerror',lambda error:errors.append(str(error)))
        cases=[('/quick','#quick-ap','quick'),('/modem/network','#radio-mode','modem'),
               ('/setup','#setup-ap-ssid','setup'),('/settings/leds','#led-mode-red','leds'),
               ('/internet','#internet-mode','policy'),('/sim/apn','#cellular-name','cellular')]
        for path,selector,kind in cases:
            blocked[0]=False
            page.goto(BASE+path)
            expect(page.locator(selector)).to_be_enabled(timeout=15000)
            page.wait_for_function('(kind)=>Object.keys(localStorage).some(k=>k.startsWith("openstick-settings-display-v1-"+kind))',arg=kind)
            blocked[0]=True
            page.reload(wait_until='domcontentloaded')
            expect(page.locator(selector)).to_be_enabled(timeout=1000)
            assert page.evaluate('document.body.scrollWidth<=innerWidth'),path
        assert not page.evaluate('JSON.stringify({...localStorage,...sessionStorage}).includes("fixture-private")')
        tab=context.new_page();tab.goto(BASE+'/quick',wait_until='domcontentloaded')
        expect(tab.locator('#quick-ap')).to_be_enabled(timeout=1000)
        tab.locator('#quick-ap').click();expect(tab.locator('#quick-dialog')).to_be_visible()
        assert not writes,writes
        assert not errors,errors
        # A cached APN excludes credentials. Saving an unrelated edit must
        # retrieve and preserve the current username, never silently clear it.
        blocked[0]=False
        pending=[];hold=[True];saved=[]
        def apn_read(route):
            if hold[0]:pending.append(route);return
            route.fulfill(json={'settings':{**cellular,'username':'fixture-private-updated'},'profiles':[],'blocked':False})
        page.route('**/api/cellular',apn_read)
        page.route('**/api/hotspot',lambda r:(saved.append(r.request.post_data_json),r.fulfill(status=202,json={'accepted':True})))
        page.route('**/api/hotspot/state',lambda r:r.fulfill(json={'busy':False,'last_operation':{'action':'apn_save'},'result':{'saved_profile_id':'current'}}))
        page.goto(BASE+'/sim/apn',wait_until='domcontentloaded')
        expect(page.locator('#cellular-name')).to_be_enabled(timeout=1000)
        page.locator('#cellular-name').fill('Renamed while refreshing')
        hold[0]=False
        for request in pending:request.fulfill(json={'settings':{**cellular,'username':'fixture-private-updated'},'profiles':[],'blocked':False})
        expect(page.locator('#cellular-name')).to_have_value('Renamed while refreshing')
        page.once('dialog',lambda dialog:dialog.accept());page.locator('#cellular-save').click()
        expect(page.locator('#cellular-result')).to_contain_text('Đã lưu vào danh sách')
        assert len(saved)==1 and saved[0]['username']=='fixture-private-updated'
        assert saved[0]['password_action']=='keep' and saved[0]['password']==''
        assert not page.evaluate('JSON.stringify({...localStorage,...sessionStorage}).includes("fixture-private")')
        browser.close()
    print('PASS: 6 settings restored with failed reads; new-tab Quick; late-read draft and APN credential preservation; mocked mutations only')


if __name__=='__main__':main()

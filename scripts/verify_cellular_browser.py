"""Named APN UI QA with fictional routed responses; no USB/modem operations."""
import json
import uuid

from playwright.sync_api import sync_playwright, expect


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        try:
            page=browser.new_page();errors=[];writes=[];rows=[];last={};blocked=[False]
            page.on('pageerror',lambda e:errors.append(str(e)))
            settings={'available':True,'name':'Fixture current','apn':'fixture.apn','username':'fixture-user',
                      'password_saved':True,'auth':'pap','ip_family':'ipv4','roaming':False}
            page.route('**/api/cellular',lambda r:r.fulfill(json={'settings':settings,'profiles':rows,'blocked':blocked[0]}))
            def save(route):
                body=route.request.post_data_json;writes.append(body);last.clear();last.update(action=body['action'])
                if body['action']=='apn_save':
                    identity=body['profile_id'] if body['profile_id'] not in ('','current') else str(uuid.uuid4())
                    prior=next((p for p in rows if p['id']==identity),None)
                    value={k:v for k,v in body.items() if k not in ('action','profile_id','password','password_action','confirm')}
                    value.update(id=identity,active=False,password_saved=bool(body['password']) or bool(prior and prior['password_saved']))
                    rows[:]=[p for p in rows if p['id']!=identity]+[value];last['saved_profile_id']=identity
                elif body['action']=='apn_apply':
                    for row in rows:row['active']=row['id']==body['profile_id']
                    settings.update(next(p for p in rows if p['active']))
                elif body['action']=='apn_delete':rows[:]=[p for p in rows if p['id']!=body['profile_id']]
                route.fulfill(status=202,json={'accepted':True})
            page.route('**/api/hotspot',save)
            page.route('**/api/hotspot/state',lambda r:r.fulfill(json={'busy':False,'result':last,'error':None,
                       'last_operation':{'action':last.get('action'),'error':None,'at':1}}))
            assert page.goto('http://127.0.0.1:8771/').url.endswith('/overview')
            for width in (320,390,768,1280):
                page.set_viewport_size({'width':width,'height':844})
                assert page.goto('http://127.0.0.1:8771/sim/apn').status==200
                expect(page.locator('#cellular-fields')).to_be_enabled()
                assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth')
                assert page.locator('.app-bottom-nav-item:visible').last.get_attribute('data-nav')=='overview'
                expect(page.locator('#cellular-password')).to_have_value('')
            assert not writes
            page.once('dialog',lambda d:d.dismiss());page.locator('#cellular-save').click();assert not writes
            page.locator('#cellular-new').click();page.locator('#cellular-name').fill('Fixture travel')
            page.locator('#cellular-mode').select_option('manual');page.locator('#cellular-apn').fill('fixture.travel')
            page.locator('#cellular-password-action').select_option('replace');page.locator('#cellular-password').fill('fictional-apn-secret')
            page.once('dialog',lambda d:d.accept());page.locator('#cellular-save').click()
            expect(page.locator('#cellular-result')).to_contain_text('Đã lưu vào danh sách')
            expect(page.locator('#cellular-password')).to_have_value('');assert len(rows)==1
            assert writes[-1]['action']=='apn_save' and not rows[0]['active']
            assert 'fictional-apn-secret' not in page.evaluate('JSON.stringify(sessionStorage)')
            page.locator('#cellular-name').fill('Fixture travel edited')
            expect(page.locator('#cellular-apply')).to_be_disabled()
            page.once('dialog',lambda d:d.accept());page.locator('#cellular-save').click()
            expect(page.locator('#cellular-result')).to_contain_text('Đã lưu vào danh sách')
            assert writes[-1]['password_action']=='keep' and writes[-1]['password']==''
            page.once('dialog',lambda d:d.dismiss());page.locator('#cellular-apply').click()
            assert not any(v['action']=='apn_apply' for v in writes)
            page.once('dialog',lambda d:d.accept());page.locator('#cellular-apply').click()
            expect(page.locator('#cellular-result')).to_contain_text('Đã áp dụng cấu hình')
            expect(page.locator('#cellular-delete')).to_be_disabled()
            blocked[0]=True;page.locator('#cellular-refresh').click()
            expect(page.locator('#cellular-apply-reason')).to_contain_text('Vẫn tạo/sửa/lưu')
            expect(page.locator('#cellular-fields')).to_be_enabled()
            page.locator('#cellular-new').click();page.locator('#cellular-name').fill('Fixture spare')
            page.once('dialog',lambda d:d.accept());page.locator('#cellular-save').click()
            expect(page.locator('#cellular-result')).to_contain_text('Đã lưu vào danh sách');assert len(rows)==2
            expect(page.locator('#cellular-apply')).to_be_disabled()
            page.once('dialog',lambda d:d.accept());page.locator('#cellular-delete').click()
            expect(page.locator('#cellular-result')).to_contain_text('Đã xóa cấu hình');assert len(rows)==1
            assert not errors
            print(json.dumps({'apn_viewports':4,'named_presets_save_edit_apply_delete':'PASS',
                              'consent_and_secret_clear':'PASS','save_while_apply_blocked':'PASS','javascript_errors':0,'hardware_operations':0}))
        finally:browser.close()


if __name__=='__main__':main()

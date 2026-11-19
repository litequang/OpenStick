"""Fictional preview only. Metadata writes are intercepted, never sent to USB."""
import json
from copy import deepcopy
from playwright.sync_api import sync_playwright,expect

BASE='http://127.0.0.1:8771'


def main():
    calls=[];errors=[];fail=[False]
    state={'sites':[{'id':'main','name':'Fixture main','domains':['example.invalid']},
                    {'id':'second','name':'<img src=x onerror=alert(1)>','domains':['second.invalid']}],
           'revision':'r1','routing':{'available':True,'local':'NOT_APPLIED'}}
    def api(route):
        value=route.request.post_data_json;calls.append(value)
        if value['action']=='sites':route.fulfill(json=state);return
        if fail[0]:route.abort();return
        assert value['expected']==state['revision'] and value['confirm'] is True
        if value['action']=='configure':
            item=next(s for s in state['sites'] if s['id']==value['site'])
            item.update(name=value['name'],domains=value['domains']);state['selected']=item['id']
        elif value['action']=='create':
            state['sites'].append({'id':'created','name':value['name'],'domains':value['domains']});state['selected']='created'
        elif value['action']=='publish_domains':state['routing']['local']='CONFIG_SAVED'
        else:raise AssertionError('Unexpected metadata operation')
        state['revision']='r'+str(int(state['revision'][1:])+1);route.fulfill(json=deepcopy(state))
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        try:
            page=browser.new_page(viewport={'width':390,'height':844})
            page.on('pageerror',lambda e:errors.append(type(e).__name__))
            page.route('**/api/websites',api)
            page.route('**/files/**',lambda route:route.fulfill(content_type='text/html',body='<div id="app">FileGator preview fixture</div>',headers={'Content-Security-Policy':"default-src 'self'; frame-ancestors 'self'",'X-Frame-Options':'SAMEORIGIN'}))
            page.goto(BASE+'/website/files');expect(page.locator('#web-site')).to_be_enabled()
            expect(page.frame_locator('#web-filegator-frame').locator('#app')).to_be_visible()
            page.once('dialog',lambda d:d.dismiss());page.locator('#web-site').select_option('second')
            expect(page.locator('#web-site')).to_have_value('main')
            page.once('dialog',lambda d:d.accept())
            page.locator('#web-site').select_option('second')
            expect(page.locator('#web-filegator')).to_have_attribute('href','/files/second/')
            expect(page.locator('#web-filegator-frame')).to_have_attribute('src','/files/second/')
            expect(page.frame_locator('#web-filegator-frame').locator('#app')).to_be_visible()
            # An inventory refresh must not reload an editor/upload already open.
            page.locator('#web-filegator-frame').evaluate('(el)=>el.contentWindow.fixtureMarker=42')
            page.locator('#web-refresh').click();expect(page.locator('#web-refresh')).to_be_enabled()
            assert page.locator('#web-filegator-frame').evaluate('(el)=>el.contentWindow.fixtureMarker')==42
            assert page.locator('img').count()==0
            assert all(v['action']=='sites' for v in calls)
            page.goto(BASE+'/website/domains?site=second')
            expect(page.locator('#web-edit-domains')).to_be_enabled()
            page.locator('#web-edit-domains').click()
            page.locator('#web-site-domains').fill('new.invalid')
            assert all(v['action']=='sites' for v in calls)
            page.locator('#web-site-form button[type=submit]').click()
            expect(page.locator('#web-status')).to_contain_text('Đã lưu website')
            expect(page.locator('#web-domains')).to_contain_text('new.invalid')
            writes=lambda:[v for v in calls if v['action']!='sites']
            assert len(writes())==1 and writes()[0]['site']=='second'
            page.once('dialog',lambda d:d.dismiss());page.locator('#web-apply-domains').click()
            assert len(writes())==1
            page.once('dialog',lambda d:d.accept());page.locator('#web-apply-domains').click()
            expect(page.locator('#web-status')).to_contain_text('Đã lưu cấu hình')
            assert len(writes())==2
            page.goto(BASE+'/website');expect(page.locator('#web-create')).to_be_enabled()
            page.locator('#web-create').click();page.locator('#web-site-name').fill('Created fixture')
            page.locator('#web-site-domains').fill('created.invalid')
            page.locator('#web-site-form button[type=submit]').click()
            expect(page.locator('#web-status')).to_contain_text('Đã lưu website')
            assert len(writes())==3 and writes()[-1]['action']=='create'
            fail[0]=True
            page.locator('#web-configure').click();page.locator('#web-site-name').fill('Uncertain fixture')
            page.locator('#web-site-form button[type=submit]').click()
            expect(page.locator('#web-status')).to_contain_text('Không tự gửi lại')
            page.wait_for_timeout(800);assert len(writes())==4
            # Standalone usage view must read the real schema, retain old values
            # on stale/unavailable samples and never turn missing data into zero.
            usage={'available':True,'today':{'total_bytes':3145728,'download_bytes':2097152,'upload_bytes':1048576}}
            page.route('**/api/overview',lambda route:route.fulfill(json={'system':{'sim_usage':usage}}))
            page.goto(BASE+'/sim/usage')
            expect(page.locator('#usage-values')).to_contain_text('3.00 MiB · ↓ 2.00 MiB · ↑ 1.00 MiB')
            expect(page.locator('#usage-values')).to_contain_text('Chưa có số liệu')
            previous=page.locator('#usage-values').inner_text()
            for changed in ({'available':False},{'available':True,'stale':True},{'available':True,'error':'READ_FAILED'}):
                usage.clear();usage.update(changed)
                page.locator('#usage-refresh').click()
                expect(page.locator('#usage-status')).to_contain_text('không phải 0 byte')
                assert page.locator('#usage-values').inner_text()==previous
            assert not errors,errors
        finally:browser.close()
    print(json.dumps({'preview_metadata':'PASS','usage_schema_and_missing_data':'PASS','mocked_mutation_attempts':4,'automatic_retries':0,'javascript_errors':0,'device_operations':0}))


if __name__=='__main__':main()

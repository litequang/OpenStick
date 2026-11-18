"""Headless dashboard preview with fictional usage; never connects to USB."""
import json
from pathlib import Path
import time

from playwright.sync_api import expect, sync_playwright


def main():
    out=Path('artifacts/sim-usage-browser');out.mkdir(parents=True,exist_ok=True)
    def count(rx,tx):return {'download_bytes':rx,'upload_bytes':tx,'total_bytes':rx+tx}
    usage={'available':True,'status':'connected','stale':False,'error':None,
           'started_at':time.time()-86400,'sampled_at':time.time(),'saved_at':time.time(),
           'today':count(30*1048576,12*1048576),'month':count(1<<30,1<<28),
           'session':count(1024,2048),'total':count(1<<30,1<<28),'undated':count(0,0),
           'continuity_gaps':0}
    data={'system':{'sim_usage':usage},'wifi':{},'services':{}}
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        try:
            page=browser.new_page();errors=[];posts=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            def request(route):
                payload=route.request.post_data_json;posts.append(payload)
                assert payload=={'action':'overview'}
                route.fulfill(json={'accepted':True},status=202)
            page.route('**/api/wifi',request)
            page.route('**/api/state',lambda route:route.fulfill(json={'busy':False,'result':data}))
            for width in [320,390,768,1280]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.goto('http://127.0.0.1:8771/overview').status==200
                expect(page.locator('#metric-sim-usage')).to_have_text('42.00 MiB')
                expect(page.locator('#note-sim-usage')).to_contain_text('1.25 GiB tháng này')
                page.locator('#sim-usage-details summary').click()
                expect(page.locator('#sim-usage-detail')).to_contain_text('Tổng từ lúc bắt đầu')
                expect(page.locator('#sim-usage-detail')).to_contain_text('1.25 GiB')
                assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth'),width
                if width==390:page.screenshot(path=str(out/'overview-390.png'),full_page=True)
            usage['error']='USAGE_SAVE_FAILED'
            page.locator('#overview-refresh').click()
            expect(page.locator('#sim-usage-detail')).to_contain_text('Chưa lưu được')
            expect(page.locator('#metric-sim-usage')).to_have_attribute('data-stale','true')
            usage['error']=None;usage['today']=count(0,0);usage['status']='idle'
            page.locator('#overview-refresh').click()
            expect(page.locator('#metric-sim-usage')).to_have_text('0 B')
            expect(page.locator('#sim-usage-detail')).to_contain_text('lịch sử vẫn được giữ')
            data['system']['sim_usage']={'available':False,'error':'USAGE_STATE_INVALID'}
            page.locator('#overview-refresh').click()
            expect(page.locator('#sim-usage-detail')).to_contain_text('không coi là đã dùng 0 byte')
            assert not errors,errors
            assert all(v=={'action':'overview'} for v in posts)
        finally:browser.close()
    result={'preview_layouts':4,'interactions':'PASS','device_operations':0}
    (out/'report.json').write_text(json.dumps(result));print(json.dumps(result))


if __name__=='__main__':main()

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
            page=browser.new_page();errors=[];posts=[];header_ready=[False];service_reads=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            def request(route):
                assert route.request.method=='GET'
                route.fulfill(json=data)
            page.route('**/api/overview',request)
            def header(route):
                if not header_ready[0]:route.fulfill(status=503,json={'error':'STATUS_PENDING'});return
                route.fulfill(json={'connected':True,'ssid':'Fictional Wi-Fi','ipv4':['192.0.2.2/24'],
                    'modem_status':{'registered':True,'sim_present':True,'signal_percent':75,'signal_recent':True,
                                    'operator_name':'Fixture carrier','access_technologies':16384}})
            page.route('**/api/header',header)
            def services(route):
                service_reads.append(True);route.fulfill(json={'services':{'modemmanager':True}})
            page.route('**/api/services',services)
            page.on('request',lambda request:posts.append(request.url) if request.method=='POST' else None)
            for width in [320,390,768,1280]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.goto('http://127.0.0.1:8771/overview').status==200
                expect(page.locator('#metric-sim-usage')).to_have_text('42.00 MiB')
                if width==320:
                    assert not service_reads,'Closed technical panel must not probe services'
                    header_ready[0]=True
                    expect(page.locator('#overview-wifi')).to_contain_text('Fictional Wi-Fi')
                    page.locator('#overview-services>summary').click()
                    expect(page.locator('#service-list')).to_contain_text('đang chạy (D-Bus)')
                    assert service_reads
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
            assert not posts
        finally:browser.close()
    result={'preview_layouts':4,'interactions':'PASS','metrics_independent_of_pending_header':'PASS','lazy_services':'PASS','device_operations':0}
    (out/'report.json').write_text(json.dumps(result));print(json.dumps(result))


if __name__=='__main__':main()

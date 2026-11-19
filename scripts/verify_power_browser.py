"""Fictional power UI preview. No USB access or real power command."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect


def main():
    out=Path('artifacts/power-browser');out.mkdir(parents=True,exist_ok=True)
    writes=[];failure=[False];state={'available':True,'pending':False,'phase':'IDLE','operation':None,'error':None}
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True)
        try:
            page=browser.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            def api(route):
                if route.request.method=='POST':
                    value=route.request.post_data_json;writes.append(value)
                    if failure[0]:route.abort();return
                    assert set(value)=={'action','operation','confirm'} and value['confirm'] is True
                    state.update(operation=value['operation'],action=value['action'],delay_seconds=5,
                                 phase='CANCELLED' if value['action']=='cancel' else 'QUEUED',
                                 pending=value['action']!='cancel')
                    route.fulfill(status=202,json=state)
                else:route.fulfill(json=state)
            page.route('**/api/device/power',api)
            for width in [320,390,768,1280]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.goto('http://127.0.0.1:8771/settings/system').status==200
                expect(page.locator('#power-reboot')).to_be_enabled()
                assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth'),width
                assert not writes
                if width==390:page.screenshot(path=str(out/'system-390.png'),full_page=True)
            page.once('dialog',lambda dialog:dialog.dismiss());page.locator('#power-off').click()
            assert not writes
            page.once('dialog',lambda dialog:dialog.accept());page.locator('#power-reboot').click()
            expect(page.locator('#power-state')).to_contain_text('Đã lưu yêu cầu')
            expect(page.locator('#power-reboot')).to_be_disabled()
            assert len(writes)==1 and writes[0]['action']=='reboot'
            page.locator('#power-cancel').click();expect(page.locator('#power-state')).to_contain_text('đã được hủy')
            assert len(writes)==2 and writes[-1]['action']=='cancel'
            failure[0]=True
            page.once('dialog',lambda dialog:dialog.accept());page.locator('#power-off').click()
            expect(page.locator('#power-notice')).to_contain_text('không tự gửi lại')
            page.wait_for_timeout(3500);assert len(writes)==3
            assert not errors,errors
        finally:browser.close()
    result={'preview_layouts':4,'confirmation_cancel_unknown':'PASS','real_power_commands':0}
    (out/'report.json').write_text(json.dumps(result));print(json.dumps(result))


if __name__=='__main__':main()

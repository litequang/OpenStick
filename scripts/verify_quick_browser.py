"""Chrome QA on the loopback memory demo, never a USB endpoint."""
import json
import re
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        try:
            page = browser.new_page()
            # HTTP USB/LAN origins do not expose this secure-context-only API.
            page.add_init_script("Object.defineProperty(Crypto.prototype,'randomUUID',{value:undefined,configurable:true})")
            errors = []; actions = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: actions.append(request.post_data_json['action'])
                    if request.method == 'POST' and request.url.endswith('/api/quick') else None)
            for width in [320, 390, 768, 1280]:
                page.set_viewport_size({'width':width,'height':844})
                for path in ['/quick','/overview']:
                    response = page.goto('http://127.0.0.1:8771'+path)
                    assert response.status == 200
                    expect(page.locator('#quick-airplane')).to_be_enabled()
                    expect(page.locator('#quick-data')).to_be_disabled()
                    expect(page.locator('#quick-usb')).to_be_disabled()
                    expect(page.locator('#quick-dialog')).to_have_count(1)
                    assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth')
                    if path=='/overview':
                        assert page.locator('#quick-ap').bounding_box()['height']<=140
            assert actions == [], 'Opening the UI changed state'
            # Reset only the fictional memory backend so this verifier is repeatable.
            assert 'MÔ PHỎNG' in page.locator('body').inner_text()
            token=page.locator('.portal-header').get_attribute('data-status-token')
            for action in ['airplane_off','local_ap_off']:
                response=page.request.post('http://127.0.0.1:8771/api/quick',
                    headers={'X-OpenStick-Token':token},data={'action':action,'operation':str(uuid.uuid4()),'confirm':True})
                assert response.status==202
                page.wait_for_timeout(80)
            page.reload();expect(page.locator('#quick-airplane')).to_have_attribute('aria-pressed','false')
            page.locator('#quick-airplane').click()
            expect(page.locator('#quick-dialog')).to_be_visible()
            page.locator('#quick-dialog button[value=cancel]').click()
            assert actions == []
            page.locator('#quick-airplane').click(); page.locator('#quick-apply').click()
            expect(page.locator('#quick-airplane')).to_have_attribute('aria-pressed','true')
            assert actions == ['airplane_on']
            page.locator('#quick-airplane').click(); page.keyboard.press('Escape')
            expect(page.locator('#quick-dialog')).not_to_be_visible()
            assert actions == ['airplane_on'], 'Escape repeated a previous confirmation'
            page.locator('#quick-ap').click(); page.locator('#quick-apply').click()
            expect(page.locator('#quick-ap')).to_have_attribute('aria-pressed','true')
            expect(page.locator('#quick-airplane')).to_have_attribute('aria-pressed','true')
            page.locator('#quick-airplane').click(); page.locator('#quick-apply').click()
            expect(page.locator('#quick-airplane')).to_have_attribute('aria-pressed','false')
            assert actions == ['airplane_on','local_ap_on','airplane_off']
            assert 'data_on' not in actions
            # Synthetic reboot: a persisted receipt survives a new CSRF token.
            fixture=page.request.get('http://127.0.0.1:8771/api/quick',headers={'X-OpenStick-Token':token}).json()
            fixture['pending_network_trial']=False
            fixture['usb_tethering']={'available':True,'enabled':False,'degraded':False,'desired_enabled':False,'reboot_pending':False}
            simulation={'operation':None,'reads':0,'rotated':False}
            html=page.request.get('http://127.0.0.1:8771/quick').text()
            def reboot_api(route):
                request=route.request
                if request.method=='POST':
                    simulation['operation']=request.post_data_json['operation']
                    route.fulfill(status=202,json={'accepted':True});return
                if '/operation/' not in request.url:
                    route.fulfill(json=fixture);return
                simulation['reads']+=1
                if simulation['reads']==2:route.fulfill(status=403,json={'error':'FORBIDDEN'});return
                applied=simulation['reads']>2
                if applied:
                    simulation['rotated']=request.headers.get('x-openstick-token')=='fixture-after-reboot-token'
                    fixture['usb_tethering']['enabled']=True
                route.fulfill(json={'kind':'usb_tether_on','state':'COMPLETED','busy':False,'error':None,
                    'usb_tethering':{'enabled':applied,'operation':simulation['operation'],'apply_state':'APPLIED' if applied else 'QUEUED'}})
            def reboot_html(route):
                body=re.sub(r'data-status-token="[^"]+"','data-status-token="fixture-after-reboot-token"',html) if simulation['reads']>=2 else html
                route.fulfill(content_type='text/html',body=body)
            page.route('**/api/quick**',reboot_api);page.route('http://127.0.0.1:8771/quick',reboot_html)
            page.goto('http://127.0.0.1:8771/quick');expect(page.locator('#quick-usb')).to_be_enabled()
            page.locator('#quick-usb').click()
            expect(page.locator('#quick-dialog-copy')).to_contain_text('khởi động lại')
            assert 'usb_tether_on' not in actions
            page.locator('#quick-apply').click()
            expect(page.locator('#quick-notice')).to_contain_text('Đã bật chia sẻ USB sau khởi động lại',timeout=20000)
            assert simulation['rotated'] and actions.count('usb_tether_on')==1
            output = Path('artifacts/quick-settings-audit');output.mkdir(exist_ok=True)
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(output/'quick-demo-390.png'),full_page=True)
            assert not errors, errors
            (output/'browser-report.json').write_text(json.dumps({'widths':[320,390,768,1280],
                'actions':actions,'javascript_errors':errors,'hardware_operations':0}),encoding='utf-8')
            print(json.dumps({'layouts':8,'http_without_random_uuid':'PASS','consent_escape_no_sim':'PASS','reboot_token_recovery':'PASS','hardware_operations':0}))
        finally:
            browser.close()


if __name__ == '__main__':main()

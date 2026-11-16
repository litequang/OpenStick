"""Chrome QA on the loopback memory demo, never a USB endpoint."""
import json
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        try:
            page = browser.new_page()
            errors = []; actions = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: actions.append(request.post_data_json['action'])
                    if request.method == 'POST' and request.url.endswith('/api/quick') else None)
            for width in [320, 390, 768, 1280]:
                page.set_viewport_size({'width':width,'height':844})
                response = page.goto('http://127.0.0.1:8771/quick')
                assert response.status == 200
                expect(page.locator('#quick-airplane')).to_be_enabled()
                expect(page.locator('#quick-data')).to_be_disabled()
                expect(page.locator('#quick-usb')).to_be_disabled()
                assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth')
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
            output = Path('artifacts/quick-settings-audit');output.mkdir(exist_ok=True)
            page.set_viewport_size({'width':390,'height':844})
            page.screenshot(path=str(output/'quick-demo-390.png'),full_page=True)
            assert not errors, errors
            (output/'browser-report.json').write_text(json.dumps({'widths':[320,390,768,1280],
                'actions':actions,'javascript_errors':errors,'hardware_operations':0}),encoding='utf-8')
            print(json.dumps({'layouts':4,'consent_escape_no_sim':'PASS','hardware_operations':0}))
        finally:
            browser.close()


if __name__ == '__main__':main()

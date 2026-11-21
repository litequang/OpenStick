"""Headless Chrome QA against the disposable preview, never the USB portal.

Start scripts/preview_portal.py first. Run with a Python that has Playwright.
Screenshots contain only fictional preview data and remain under artifacts/.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from settings_navigation_qa import audit_navigation

BASE = 'http://127.0.0.1:8771'
OUT = Path('artifacts/settings-browser')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        try:
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            client_writes=[];blocked=set();client_failure=[False]
            def client_inventory(route):
                if route.request.method=='POST':
                    payload=route.request.post_data_json;client_writes.append(payload)
                    if client_failure[0]:route.abort();return
                    if payload['action']=='block':blocked.add(payload['mac'])
                    else:blocked.discard(payload['mac'])
                    route.fulfill(json={'saved':True,'filter_applied':True});return
                route.fulfill(json={'ap_active':True,'inventory_available':True,'count':1,
                    'blocked':sorted(blocked),'filter_applied':True,'association_block_supported':False,
                    'clients':[{'mac':'02:00:00:00:00:01','ip':'192.168.8.21',
                      'name':'Fictional <img src=x onerror=alert(1)>','signal_dbm':-52,
                      'rx_bytes':1048576,'tx_bytes':2048,'rx_mbps':72.2,'tx_mbps':65,
                      'internet_blocked':'02:00:00:00:00:01' in blocked}]})
            page.route('**/api/ap/clients',client_inventory)
            navigation = audit_navigation(page, BASE)
            for width in [320, 390, 768, 1280]:
                page.set_viewport_size({'width': width, 'height': 844})
                for path in ['/manage', '/setup', '/internet', '/hotspot', '/modem/network', '/settings/leds']:
                    response = page.goto(BASE + path)
                    assert response.status == 200, (path, response.status)
                    if path == '/manage':
                        expect(page.locator('.settings-category-tree--hub')).to_have_count(1)
                        expect(page.locator('.settings-category')).to_have_count(4)
                    else:
                        expect(page.locator('.settings-category-tree--sidebar')).to_have_count(1)
                        expect(page.locator('.settings-category-item[aria-current="page"]')).to_have_count(1)
                        if width < 760:
                            drawer = page.locator('#settings-submenu-toggle')
                            expect(drawer).to_have_count(1)
                            drawer.locator('summary.settings-navigation-trigger').click()
                            expect(page.locator('.settings-category-tree--sidebar')).to_be_visible()
                            drawer.locator('summary.settings-navigation-trigger').click()
                    page.wait_for_timeout(250)
                    assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth'), (path, width, 'overflow')
                    assert not errors, errors
                    if width in [390, 1280]:
                        page.screenshot(path=str(OUT / (path.strip('/').replace('/', '-') + f'-{width}.png')), full_page=True)
                    results.append({'path': path, 'width': width, 'http': response.status, 'overflow': False})

            page.set_viewport_size({'width': 390, 'height': 844})
            # A late header response must not close a form the user is editing.
            header_ready=[False]
            def delayed_header(route):
                if not header_ready[0]:route.fulfill(status=503,json={'error':'STATUS_PENDING'})
                else:route.continue_()
            page.route('**/api/header',delayed_header)
            page.goto(BASE+'/setup')
            if not page.locator('#setup-ssid').is_visible():
                page.locator('#setup-connect-details summary').click()
            page.locator('#setup-ssid').fill('Draft while status is pending')
            header_ready[0]=True
            expect(page.locator('#setup-wifi-status')).to_contain_text('Đang nhận Wi-Fi')
            expect(page.locator('#setup-connect-details')).to_have_attribute('open','')
            expect(page.locator('#setup-ssid')).to_have_value('Draft while status is pending')
            page.unroute('**/api/header')
            # Default preview models station mode: change Wi-Fi must be usable.
            page.goto(BASE + '/setup')
            expect(page.locator('#setup-submit')).to_be_enabled()
            expect(page.locator('#setup-connect-details')).not_to_have_attribute('open', '')
            page.locator('#setup-connect-details summary').click()
            expect(page.locator('#setup-connect-impact')).to_contain_text('không khởi động lại')
            page.locator('#setup-ssid').fill('Fictional station')
            page.locator('#setup-password').fill('fictional-password')
            writes = []
            def station(route):
                writes.append(route.request.post_data_json)
                route.fulfill(json={'accepted': True}, status=202)
            page.route('**/api/wifi', station)
            page.route('**/api/state', lambda route: route.fulfill(json={'busy': False, 'result': {'connected': True}}))
            page.once('dialog', lambda dialog: dialog.dismiss())
            page.locator('#setup-submit').click()
            assert writes == []
            page.once('dialog', lambda dialog: dialog.accept())
            page.locator('#setup-submit').click()
            expect(page.locator('#setup-connect-notice')).to_contain_text('Đã kết nối Wi-Fi')
            assert [write['action'] for write in writes] == ['connect']
            assert 'confirm' not in writes[0], 'Station backend contract changed'
            expect(page.locator('#setup-password')).to_have_value('')
            page.goto(BASE+'/setup/ap')
            page.locator('#setup-reveal').click()
            expect(page.locator('#setup-credentials')).to_be_visible()
            page.locator('#setup-reveal').click()
            expect(page.locator('#setup-credentials')).to_be_hidden()
            expect(page.locator('#setup-credentials')).to_have_text('')
            page.route('**/api/setup/credentials',lambda route:route.fulfill(status=403,json={'error':'DENIED'}))
            page.locator('#setup-reveal').click()
            expect(page.locator('#setup-notice')).to_be_visible()
            expect(page.locator('#setup-notice')).to_contain_text('Chưa tải được thông tin kết nối')
            page.unroute('**/api/setup/credentials')

            # AP mode must retain the original reboot handoff and explicit consent.
            page.route('**/api/setup', lambda route: route.fulfill(json={
                'enabled': True, 'configured': True, 'setup_active': True, 'busy': False,
                'ssid': 'Fictional setup', 'url': 'http://192.0.2.1:8765/setup', 'networks': [], 'scan_at': 1}))
            page.route('**/api/header', lambda route: route.fulfill(json={
                'connected': False, 'setup_active': True, 'hotspot_active': True, 'ssid': 'Fictional setup'}))
            page.goto(BASE+'/setup')
            expect(page.locator('#setup-submit')).to_contain_text('khởi động lại')
            expect(page.locator('#setup-connect-impact')).to_contain_text('một lần')
            page.goto(BASE+'/setup/ap')
            page.locator('#setup-ap-ssid').fill('Unsaved draft')
            page.wait_for_timeout(5200)
            expect(page.locator('#setup-ap-ssid')).to_have_value('Unsaved draft')
            page.unroute('**/api/setup'); page.unroute('**/api/header')

            # Advanced AP options only stage after explicit confirmation.
            ap_writes = []
            def ap_stage(route):
                if route.request.method == 'POST':
                    payload = route.request.post_data_json
                    ap_writes.append(payload)
                    route.fulfill(status=202, json={'configured': True, 'ssid': 'Fictional AP',
                        'channel': 6, 'setup_active': True, 'enabled': True, 'busy': False,
                        'url': 'http://192.0.2.1:8765/setup', 'ap_options': {
                            'configured': True, 'hidden': payload['hidden'],
                            'isolation': payload['isolation'], 'max_clients': payload['max_clients']}})
                else:route.continue_()
            page.route('**/api/setup', ap_stage)
            page.goto(BASE + '/setup/ap')
            expect(page.locator('#setup-ap-save')).to_be_enabled()
            page.locator('#setup-ap-ssid').fill('Fictional AP')
            page.locator('#setup-ap-hidden').check(); page.locator('#setup-ap-isolation').check()
            page.locator('#setup-ap-max-clients').fill('3')
            page.wait_for_timeout(5200)
            expect(page.locator('#setup-ap-hidden')).to_be_checked()
            expect(page.locator('#setup-ap-max-clients')).to_have_value('3')
            assert not ap_writes
            page.once('dialog', lambda dialog: dialog.dismiss()); page.locator('#setup-ap-save').click()
            assert not ap_writes
            page.once('dialog', lambda dialog: dialog.accept()); page.locator('#setup-ap-save').click()
            expect(page.locator('#setup-ap-options-status')).to_contain_text('tối đa 3')
            assert len(ap_writes) == 1 and ap_writes[0]['hidden'] and ap_writes[0]['isolation']
            assert ap_writes[0]['action'] == 'configure_ap' and ap_writes[0]['max_clients'] == 3
            page.unroute('**/api/setup')

            # Inventory uses literal text, and block/unblock never activates an AP.
            page.goto(BASE+'/setup/clients')
            expect(page.locator('#ap-clients-list .ap-client-card')).to_have_count(1)
            expect(page.locator('#ap-clients-list img')).to_have_count(0)
            page.once('dialog',lambda d:d.dismiss())
            page.locator('#ap-clients-list button').click();assert not client_writes
            page.once('dialog',lambda d:d.accept())
            page.locator('#ap-clients-list button').click()
            expect(page.locator('#ap-clients-list button')).to_have_text('Bỏ chặn')
            assert len(client_writes)==1 and client_writes[0]['action']=='block'
            assert client_writes[0]['confirm'] is True and len(client_writes[0]['operation'])==36
            page.once('dialog',lambda d:d.accept())
            page.locator('#ap-clients-blocked button').click()
            expect(page.locator('#ap-clients-list button')).to_have_text('Chặn Internet')
            assert len(client_writes)==2 and client_writes[1]['action']=='unblock'
            client_failure[0]=True
            page.once('dialog',lambda d:d.accept());page.locator('#ap-clients-list button').click()
            expect(page.locator('#ap-clients-notice')).to_contain_text('kết quả chưa xác định')
            page.wait_for_timeout(500);assert len(client_writes)==3
            client_failure[0]=False

            # Failed and disconnected station requests must not claim success/retry.
            page.goto(BASE + '/setup')
            expect(page.locator('#setup-submit')).to_be_enabled()
            expect(page.locator('#setup-connect-details')).not_to_have_attribute('open', '')
            page.locator('#setup-connect-details summary').click()
            page.locator('#setup-ssid').fill('Fictional station')
            page.locator('#setup-password').fill('fictional-password')
            page.unroute('**/api/state')
            page.route('**/api/state', lambda route: route.fulfill(json={'busy': False, 'error': True, 'error_code': 'WIFI_AUTH_REQUIRED'}))
            page.once('dialog', lambda dialog: dialog.accept()); page.locator('#setup-submit').click()
            expect(page.locator('#setup-connect-notice')).to_contain_text('mật khẩu')
            page.unroute('**/api/state'); page.route('**/api/state', lambda route: route.abort())
            page.once('dialog', lambda dialog: dialog.accept()); page.locator('#setup-submit').click()
            expect(page.locator('#setup-connect-notice')).to_contain_text('không tự gửi lại')
            assert len(writes) == 3

            page.goto(BASE + '/internet')
            expect(page.locator('#policy-fields')).to_be_enabled()
            page.locator('#internet-mode').select_option('sim_only')
            page.once('dialog', lambda dialog: dialog.dismiss()); page.locator('#policy-refresh').click()
            expect(page.locator('#internet-mode')).to_have_value('sim_only')
            expect(page.locator('#policy-mode-help')).to_contain_text('ngắt Wi-Fi')
            page.locator('#internet-mode').select_option('wifi_only')
            expect(page.locator('#policy-cellular')).to_be_disabled()

            page.goto(BASE + '/hotspot')
            expect(page.locator('#hotspot-start')).to_have_count(0)
            expect(page.locator('#hotspot-apn-settings')).to_have_count(0)
            expect(page.locator('#hotspot-pending')).to_be_hidden()
            expect(page.locator('.settings-workspace-content a[href="/sim/apn"]')).to_have_count(1)

            page.goto(BASE + '/settings/access')
            page.locator('#lan-manage').evaluate('(el)=>el.open=true')
            expect(page.locator('#lan-fields')).to_be_enabled()
            page.locator('#lan-password').fill('fictional-password')
            page.locator('#lan-password-repeat').fill('different-password')
            page.locator('#lan-settings button[type=submit]').click()
            expect(page.locator('#lan-status')).to_contain_text('chưa trùng')
            assert not errors, errors
            results.append({'interactions': 'PASS', 'javascript_errors': errors, 'device_operations': 0})
        finally:
            browser.close()
    (OUT / 'report.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps({'layouts': 24, 'navigation': navigation, 'interactions': 'PASS', 'device_operations': 0}))


if __name__ == '__main__':
    main()

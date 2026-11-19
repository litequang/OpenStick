"""Navigation-only browser assertions shared by preview and private device QA.

No screenshots or page contents are recorded here. Callers must block device
mutations when using a real portal. This module only clicks navigation controls.
"""
from playwright.sync_api import expect
from urllib.parse import urlsplit

WIDTHS = [320, 360, 390, 430, 768, 820, 1024, 1280]
PATHS = ['/manage', '/setup', '/quick', '/modem/network', '/sim/apn',
         '/modem/sms', '/modem/ussd', '/internet', '/hotspot', '/website',
         '/settings/leds', '/settings/system', '/overview']
GROUPS = ['connect', 'sim', 'web', 'device']
READ_POSTS = {'/api/wifi': {'status', 'overview'},
              '/api/modem': {'status', 'archive', 'messages'},
              '/api/internet': {'status', 'profiles'},
              '/api/hotspot': {'status'}, '/api/lan': {'status'},
              '/api/websites': {'sites', 'list', 'get'}}


def readonly_guard(page, *, sync_sms=True):
    """Fail closed for actions; optionally withhold SMS import on a real USB."""
    observed = {'mutations_blocked': 0, 'read_posts': 0, 'sms_sync_withheld': 0, 'blocked_routes': []}
    def guard(route):
        request = route.request
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            route.continue_()
            return
        path = urlsplit(request.url).path
        try:
            value = request.post_data_json
        except Exception:
            value = {}
        action = value.get('action') if isinstance(value, dict) else None
        keys = {'action', 'site'} if path == '/api/websites' and action == 'list' else {'action'}
        if request.method != 'POST' or action not in READ_POSTS.get(path, set()) or set(value) != keys:
            observed['mutations_blocked'] += 1
            observed['blocked_routes'].append({'path': path, 'action': action if action in ('status','sites','list','messages','archive','profiles') else 'UNEXPECTED', 'keys': sorted(value) if isinstance(value, dict) else []})
            route.abort()
        elif not sync_sms and path == '/api/modem' and action == 'messages':
            observed['sms_sync_withheld'] += 1
            route.fulfill(status=409, json={'error': 'READ_ONLY_NAVIGATION_QA'})
        else:
            observed['read_posts'] += 1
            route.continue_()
    page.route('**/api/**', guard)
    return observed, guard


def open_menu(page, group=None):
    drawer = page.locator('#settings-submenu-toggle')
    if drawer.count() and not drawer.evaluate('(el)=>el.open'):
        drawer.locator('summary.settings-navigation-trigger').click()
    root = page.locator('.settings-category-tree')
    if group:
        category = root.locator(f'[data-settings-section="{group}"]')
        if not category.evaluate('(el)=>el.open'):
            category.locator('summary.settings-category-header').click()
    return root


def assert_layout(page, width, path):
    assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth'), (path, width, 'overflow')
    expect(page.locator('.portal-header')).to_have_count(1)
    expect(page.locator('#portal-nav')).to_have_count(1)
    expect(page.locator('.settings-nav')).to_have_count(0)
    root = page.locator('.settings-category-tree')
    expect(root).to_have_count(1)
    assert root.locator('.settings-category').evaluate_all(
        '(els)=>els.map(el=>el.dataset.settingsSection)') == GROUPS
    if path != '/manage':
        expect(root.locator('[aria-current="page"]')).to_have_count(1)
        nav = page.locator('.settings-navigation').bounding_box()
        content = page.locator('.settings-workspace-content').bounding_box()
        if width >= 760:
            assert nav['x'] + nav['width'] <= content['x'], (path, width, 'sidebar overlap')
        else:
            expect(page.locator('#settings-submenu-toggle')).not_to_have_attribute('open', '')
            assert content['width'] >= width * .75, (path, width, 'narrow content')


def audit_navigation(page, base, widths=WIDTHS):
    rows = []
    errors = []
    def on_error(error):
        # Only counts/categories are exported; never page text or device values.
        errors.append(type(error).__name__)
    page.on('pageerror', on_error)
    reads, guard = readonly_guard(page)
    try:
        for width in widths:
            page.set_viewport_size({'width': width, 'height': 844 if width < 760 else 900})
            for path in PATHS:
                response = page.goto(base + path)
                assert response.status == 200, (path, width, response.status)
                page.wait_for_timeout(120)
                assert_layout(page, width, path)
                rows.append({'path': path, 'width': width, 'overflow': False})
            # Switch siblings and parents from a child, without visiting the hub.
            for group, item, expected in [('sim', 'ussd', '/modem/ussd'),
                                          ('sim', 'sms', '/modem/sms'),
                                          ('connect', 'usb-tether', '/quick#quick-usb'),
                                          ('device', 'power', '/settings/system')]:
                root = open_menu(page, group)
                root.locator(f'[data-settings-link="{item}"]').click()
                expect(page).to_have_url(base + expected)
                expect(page.locator(f'[data-settings-link="{item}"]')).to_have_attribute('aria-current', 'page')
                expect(page.locator('.settings-category-tree')).to_have_count(1)
            # Hash destinations must select the panel after asynchronous reads.
            for tab in ['uploads', 'domains', 'files']:
                response = page.goto(base + '/website#web-pane-' + tab)
                assert response is None or response.status == 200
                expect(page.locator(f'[data-web-tab="{tab}"]')).to_have_attribute('aria-pressed', 'true')
                expect(page.locator('#web-pane-' + tab)).to_be_visible()
                page.wait_for_timeout(150)
                assert page.locator('body').evaluate('(el)=>el.scrollWidth<=innerWidth'), ('website', width, tab)
                root = open_menu(page, 'web')
                next_tab = 'files' if tab != 'files' else 'domains'
                root.locator(f'[data-settings-link="{next_tab}"]').click()
                expect(page.locator('#web-pane-' + next_tab)).to_be_visible()
                page.locator(f'[data-web-tab="{tab}"]').click()
                expect(page.locator(f'[data-settings-link="{tab}"]')).to_have_attribute('aria-current', 'page')
            # Landscape navigation retains its usable menu and content.
            page.set_viewport_size({'width': width, 'height': 480})
            page.goto(base + '/setup')
            page.wait_for_timeout(120)
            assert_layout(page, width, '/setup')
            root = open_menu(page, 'device')
            root.locator('[data-settings-link="leds"]').click()
            expect(page).to_have_url(base + '/settings/leds')
            assert not errors, ('javascript_errors', len(errors))
        assert reads['mutations_blocked'] == 0, reads
        return {'layouts': len(rows), 'landscape_widths': len(widths),
                'widths': widths, 'navigation': 'PASS', 'website_tabs': 'PASS',
                'javascript_errors': len(errors), **reads}
    finally:
        page.remove_listener('pageerror', on_error)
        page.unroute('**/api/**', guard)

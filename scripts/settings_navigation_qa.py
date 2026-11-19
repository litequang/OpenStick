"""Navigation-only browser assertions shared by preview and private device QA.

No screenshots or page contents are recorded here. Callers must block device
mutations when using a real portal. This module only clicks navigation controls.
"""
from playwright.sync_api import expect
from urllib.parse import urlsplit,parse_qs

WIDTHS = [320, 360, 390, 430, 768, 820, 1024, 1280]
PATHS = ['/manage','/setup','/setup/saved','/setup/ap','/setup/clients',
         '/quick','/quick/usb','/modem/network','/sim/apn','/sim/usage','/modem/sms',
         '/modem/ussd','/internet','/website','/website/files','/website/domains',
         '/settings/leds','/settings/system','/settings/access','/overview']
GROUPS = ['connect', 'sim', 'web', 'device']
READ_POSTS = {'/api/wifi': {'status', 'overview'},
              '/api/modem': {'status', 'archive', 'messages'},
              '/api/internet': {'status', 'profiles'},
              '/api/hotspot': {'status'}, '/api/lan': {'status'},
              '/api/websites': {'sites', 'catalog', 'list', 'get'}}


def readonly_guard(page, *, sync_sms=True):
    """Fail closed for actions; optionally withhold SMS import on a real USB."""
    observed = {'mutations_blocked': 0, 'read_posts': 0, 'filegator_reads':0, 'sms_sync_withheld': 0, 'blocked_routes': []}
    def guard(route):
        request = route.request
        parts=urlsplit(request.url)
        if parts.path.startswith('/files/'):
            actions=parse_qs(parts.query).get('r',['/'])
            if request.method in ('GET','POST') and len(actions)==1 and actions[0] in ('/','/getconfig','/getuser','/getdir','/changedir'):
                observed['filegator_reads']+=1;route.continue_()
            else:
                observed['mutations_blocked']+=1
                observed['blocked_routes'].append({'path':'/files/<site>/','action':'UNEXPECTED_FILE_OPERATION'})
                route.abort()
            return
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
    page.route('**/files/**', guard)
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


def assert_leaf(page, path):
    setup_views = {'/setup': ['setup-connect-pane'], '/setup/saved': ['saved-wifi'],
                   '/setup/ap': ['usb-ap-settings','setup-status-panel','setup-recovery-panel'], '/setup/clients': ['ap-clients']}
    if path in setup_views:
        for panel in ['setup-connect-pane','saved-wifi','usb-ap-settings','ap-clients','setup-status-panel','setup-recovery-panel']:
            assert page.locator('#'+panel).is_visible() == (panel in setup_views[path]), (path,panel,'mixed settings')
    if path == '/quick/usb':
        expect(page.locator('#quick-usb')).to_be_visible()
        for key in ['airplane','data','ap','receive']:
            expect(page.locator('#quick-'+key)).to_be_hidden()
    if path == '/sim/usage':
        expect(page.locator('#usage-values')).to_be_visible()
        expect(page.locator('#card-ram')).to_have_count(0)
    if path.startswith('/website') and page.locator('.website-leaf').count():
        expected={'/website':'web-summary','/website/files':'web-filegator-panel','/website/domains':'web-domain-panel'}[path]
        for key in ['web-summary','web-filegator-panel','web-domain-panel']:
            expect(page.locator('#'+key)).to_have_count(int(key==expected))
        for obsolete in ['#site-upload','#site-text','#web-zip-inspect','[data-settings-link="uploads"]','[data-web-tab]']:
            expect(page.locator(obsolete)).to_have_count(0)
        expect(page.locator('script[src="/static/website.js"]')).to_have_count(0)
    if path == '/manage':expect(page.locator('#lan-settings')).to_have_count(0)


def audit_navigation(page, base, widths=WIDTHS):
    rows=[];errors=[];filegator_seen=False
    def on_error(error):errors.append(type(error).__name__)
    page.on('pageerror',on_error)
    reads,guard=readonly_guard(page)
    try:
        for width in widths:
            page.set_viewport_size({'width':width,'height':844 if width<760 else 900})
            for path in PATHS:
                response=page.goto(base+path,wait_until='domcontentloaded')
                assert response.status==200,(path,width,response.status)
                page.wait_for_timeout(100)
                assert_layout(page,width,path);assert_leaf(page,path)
                filegator_seen=filegator_seen or bool(page.locator('.website-leaf').count())
                rows.append({'path':path,'width':width,'overflow':False})
            for group,item,expected in [('sim','ussd','/modem/ussd'),('sim','sms','/modem/sms'),
                                         ('connect','usb-tether','/quick/usb'),('device','access','/settings/access'),
                                         ('web','files','/website/files'),('web','domains','/website/domains')]:
                root=open_menu(page,group);root.locator(f'[data-settings-link="{item}"]').click()
                page.wait_for_url(lambda value:urlsplit(str(value)).path==expected)
                expect(page.locator(f'[data-settings-link="{item}"]')).to_have_attribute('aria-current','page')
                assert_leaf(page,expected)
            page.set_viewport_size({'width':width,'height':480});page.goto(base+'/setup')
            page.wait_for_timeout(100);assert_layout(page,width,'/setup')
            root=open_menu(page,'device');root.locator('[data-settings-link="leds"]').click()
            expect(page).to_have_url(base+'/settings/leds')
            assert not errors,('javascript_errors',len(errors))
        assert reads['mutations_blocked']==0,reads
        return {'layouts':len(rows),'landscape_widths':len(widths),'widths':widths,
                'navigation':'PASS','isolated_child_screens':'PASS','filegator_layout_seen':filegator_seen,
                'javascript_errors':len(errors),**reads}
    finally:
        page.remove_listener('pageerror',on_error);page.unroute('**/api/**',guard);page.unroute('**/files/**',guard)

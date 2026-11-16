"""UI integration contracts: keep saved Wi-Fi from 76236fd while simplifying navigation."""
from pathlib import Path

from uz801_manager.hosting import create_hosting_app
from uz801_manager.lan_access import LanSettings

BASE = "http://172.16.42.1"
ROOT = Path(__file__).resolve().parents[1] / "uz801_manager"


class Wifi:
    def call(self, action, **values):
        return {"connected": True}


class Saved:
    def __init__(self):
        self.seen = []
    def call(self, action, **values):
        self.seen.append(action)
        return {"profiles": []}


def test_saved_wifi_controls_live_next_to_connection_and_management_links_to_them():
    internet = Saved()
    app = create_hosting_app(backend=Wifi(), usb_portal=True, modem_backend=object(),
                             network_backend=internet, setup_backend=object(), token="fixture-test")
    with app.test_client() as client:
        page = client.get("/manage", base_url=BASE)
        assert page.status_code == 200
        for item in ['id="saved-wifi"', '/setup#saved-wifi',
                     'href="/setup"', 'href="/internet"']:
            assert item in page.text
        assert '/static/manage.js' not in page.text
        assert 'id="saved-wifi-list"' not in page.text
        setup = client.get('/setup', base_url=BASE)
        assert setup.status_code == 200
        for item in ['id="setup-connect"', 'id="saved-wifi"', 'id="saved-wifi-list"',
                     'id="saved-wifi-refresh"', '/static/saved_wifi.js', 'savedWifiActionToken']:
            assert item in setup.text
        assert setup.text.index('id="setup-connect"') < setup.text.index('id="saved-wifi"')
        internet_page = client.get('/internet', base_url=BASE)
        assert internet_page.status_code == 200
        assert '/setup#saved-wifi' in internet_page.text
        assert 'id="saved-profiles"' not in internet_page.text
        assert client.get("/api/wifi/saved", base_url=BASE).status_code == 403
        assert 'id="lan-password"' not in page.text


def test_lan_settings_move_from_wifi_to_management_on_usb_only(tmp_path):
    lan = LanSettings(tmp_path, address=lambda: "192.0.2.2")
    app = create_hosting_app(backend=Wifi(), usb_portal=True, modem_backend=object(),
                             lan_settings=lan, token="fixture")
    with app.test_client() as client:
        wifi = client.get("/", base_url=BASE)
        manage = client.get("/manage", base_url=BASE)
        assert wifi.status_code == 200
        assert 'id="lan-settings"' not in wifi.text
        assert 'href="/manage"' in wifi.text
        assert manage.status_code == 200
        assert 'id="lan-settings"' in manage.text
        assert 'id="lan-password"' in manage.text
        assert 'id="lan-manage"' in manage.text
        assert "const token=" in manage.text
        assert client.get("/manage", base_url="http://wrong.example").status_code == 403


def test_layout_css_preserves_saved_wifi_styles_and_responsive_updates():
    css = (ROOT / "static" / "portal.css").read_text(encoding="utf-8")
    for marker in [".manage-wifi-list", ".manage-wifi-item",
                   ".portal-breadcrumb", ".ux-advanced", ".portal-skip-link",
                   ".app-bottom-nav-item[data-section-active=true]",
                   "@media(max-width:620px)"]:
        assert marker in css
    source = (ROOT / "static" / "manage.js").read_text(encoding="utf-8")
    assert "/api/wifi/saved" in source
    assert "textContent=profile.ssid" in source
    assert "profile.password" not in source
    actions = (ROOT / 'static' / 'saved_wifi.js').read_text(encoding='utf-8')
    assert "textContent = profile.ssid" in actions
    assert "'X-OpenStick-Token': savedWifiActionToken" in actions
    assert 'innerHTML' not in actions


def test_navigation_breadcrumb_and_accessible_current_state():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
    template = env.get_template("portal_chrome.html")
    render = lambda page: template.render(token="fixture", page=page)
    for page in ["internet", "hotspot", "network", "setup", "website"]:
        content = render(page)
        assert 'data-section-active="true"' in content
        assert 'href="/manage"' in content
        assert 'id="portal-content" tabindex="-1"' in content
        assert 'href="#portal-content"' in content
    assert 'aria-current="page"' in render("manage")
    assert 'href="/setup"' in render('wifi')
    assert 'aria-current="page"' in render('wifi')


def test_adaptive_bottom_dock_and_unified_settings_hub():
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=True)
    chrome = env.get_template('portal_chrome.html')
    desktop = chrome.render(token='fixture', page='website', portal_has_website=True)
    for name in ['sms', 'ussd', 'overview', 'wifi', 'sim', 'website', 'manage']:
        assert f'data-nav="{name}"' in desktop
    assert desktop.count('class="app-bottom-nav-item') == 7
    assert 'data-has-website="true"' in desktop
    assert 'data-current-section="website"' in desktop
    missing_site = chrome.render(token='fixture', page='manage', portal_has_website=False)
    assert 'data-nav="website"' not in missing_site
    assert missing_site.count('class="app-bottom-nav-item') == 6
    assert 'data-has-website="false"' in missing_site
    child = chrome.render(token='fixture', page='hotspot', portal_has_website=True)
    assert 'data-current-section="sim"' in child
    assert 'data-nav="sim"' in child
    assert 'data-section-active="true"' in child
    css = (ROOT / 'static' / 'portal.css').read_text(encoding='utf-8')
    for required in ['@media(min-width:390px)', '@media(min-width:700px)',
                     'grid-template-columns:repeat(6,minmax(0,1fr))',
                     'grid-template-columns:repeat(7,minmax(0,1fr))',
                     '.portal-nav-sim', '.portal-nav-website']:
        assert required in css
    app = create_hosting_app(backend=Wifi(), modem_backend=object(), usb_portal=True, token='fixture')
    with app.test_client() as client:
        management = client.get('/manage', base_url=BASE)
        assert management.status_code == 200
        html = management.text
        assert 'class="manage-sidebar"' not in html
        assert 'class="manage-topnav"' not in html
        for name in ['manage-wifi', 'manage-sim', 'manage-device', 'saved-wifi']:
            assert f'id="{name}"' in html
        for href in ['/', '/modem/network', '/overview']:
            assert f'href="{href}"' in html


def test_management_website_shortcut_only_when_backend_is_available():
    app = create_hosting_app(backend=Wifi(), modem_backend=object(), usb_portal=True,
                             token='fixture')
    client = app.test_client()
    page = client.get('/overview', base_url=BASE)
    assert page.status_code == 200
    assert 'data-has-website="false"' in page.text
    assert 'data-nav="website"' not in page.text

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


def test_management_preserves_saved_wifi_widget_and_does_not_show_passwords():
    internet = Saved()
    app = create_hosting_app(backend=Wifi(), usb_portal=True, modem_backend=object(),
                             network_backend=internet, token="fixture-test")
    with app.test_client() as client:
        page = client.get("/manage", base_url=BASE)
        assert page.status_code == 200
        for item in ['id="saved-wifi"', 'id="saved-wifi-list"',
                     'id="saved-wifi-refresh"', '/static/manage.js',
                     '/internet#saved-wifi', 'href="#saved-wifi"']:
            assert item in page.text
        assert "savedWifiToken" in page.text
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

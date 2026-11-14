"""Contract tests for grouped Linux management UX; no hardware or screenshot claims."""

from pathlib import Path
import re

import pytest
from jinja2 import Environment, FileSystemLoader

from uz801_manager.hosting import create_hosting_app
from uz801_manager.lan_access import LanSettings

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "uz801_manager" / "templates"
CSS = (ROOT / "uz801_manager" / "static" / "portal.css").read_text(encoding="utf-8")
BASE = "http://172.16.42.1"


def render(name, page, **values):
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    return env.get_template(name).render(token="fixture-token", page=page,
                                         lan_session=False, **values)


def chrome(page):
    return render("portal_chrome.html", page)


def test_bottom_dock_preserves_fast_sms_ussd_and_goes_to_two_hubs():
    html = chrome("overview")
    links = re.search(r'<nav class="app-bottom-nav"[^>]*>(.*?)</nav>', html, re.S).group(1)
    assert links.count('class="app-bottom-nav-item') == 5
    for route in ("/modem/sms", "/modem/ussd", "/overview", "/connections", "/manage"):
        assert f'href="{route}"' in links
    assert 'href="/overview"' in links and 'aria-current="page"' in links
    assert 'href="/internet"' not in links  # Advanced settings live inside the hubs.


@pytest.mark.parametrize("page,group", [
    ("wifi", "connections"), ("internet", "connections"),
    ("network", "connections"), ("setup", "connections"), ("hotspot", "connections"),
    ("website", "manage"),
])
def test_children_highlight_their_parent_group_without_false_current_page(page, group):
    html = chrome(page)
    match = re.search(r'<a href="/' + group + r'"[^>]*>', html)
    assert match is not None
    assert 'data-section-active="true"' in match.group(0)
    assert 'aria-current="page"' not in match.group(0)
    assert '<div class="portal-breadcrumb">' in html


@pytest.mark.parametrize("page,link", [
    ("connections", "/connections"), ("manage", "/manage"),
    ("sms", "/modem/sms"), ("ussd", "/modem/ussd"),
])
def test_exact_dock_page_is_marked_current(page, link):
    html = chrome(page)
    item = re.search(r'<a href="' + link + r'"[^>]*>', html).group(0)
    assert 'aria-current="page"' in item


def test_connection_hub_lists_correct_grouped_destinations():
    html = render("connections.html", "connections", has_policy=True, has_modem=True,
                  has_setup=True, has_hotspot=True)
    for route in ("/", "/internet", "/internet#saved-wifi", "/modem/network",
                  "/setup", "/hotspot"):
        assert f'href="{route}"' in html
    assert "Wi-Fi cài đặt (không SIM)" in html
    assert "Phát Wi-Fi từ SIM" in html
    assert "không tự đổi Wi-Fi" in html


def test_connection_hub_does_not_show_unsupported_links():
    html = render("connections.html", "connections", has_policy=False, has_modem=False,
                  has_setup=False, has_hotspot=False)
    assert 'href="/"' in html
    assert 'href="/hotspot"' not in html and 'href="/modem/network"' not in html
    assert 'href="/internet"' not in html and 'href="/setup"' not in html


def test_management_hub_separates_site_and_lan_access_settings():
    html = render("manage.html", "manage", has_site=True, has_modem=True,
                  can_manage_lan=True, hostname="example.invalid")
    assert 'href="/website"' in html and 'href="/overview"' in html
    assert 'id="lan-password"' in html and 'id="lan-access"' in html
    assert "const token=" in html
    assert "example.invalid" in html


def test_device_management_only_on_usb_and_does_not_reveal_lan_form_elsewhere(tmp_path):
    settings = LanSettings(tmp_path, address=lambda: '192.0.2.2')
    app = create_hosting_app(backend=object(), modem_backend=object(),
                             lan_settings=settings, usb_portal=True, token="fixture-token")
    with app.test_client() as client:
        management = client.get("/manage", base_url=BASE)
        assert management.status_code == 200
        assert 'id="lan-password"' in management.text
        assert 'type="password"' in management.text
        wifi = client.get("/", base_url=BASE)
        assert wifi.status_code == 200
        assert 'id="lan-password"' not in wifi.text
        assert "Mở trung tâm kết nối" in wifi.text
        assert client.get("/connections", base_url=BASE).status_code == 200
        assert client.get("/connections", base_url="http://other.example").status_code == 403
    private_app = create_hosting_app(backend=object(), token="fixture-token")
    with private_app.test_client() as client:
        assert client.get("/connections", base_url="http://127.0.0.1:8770").status_code == 404
        assert client.get("/manage", base_url="http://127.0.0.1:8770").status_code == 404


def test_skip_navigation_accessibility_and_mobile_layout():
    html = chrome("overview")
    assert 'href="#portal-content"' in html
    assert 'id="portal-content" tabindex="-1"' in html
    assert ".portal-skip-link:focus-visible" in CSS
    assert "text-overflow:ellipsis" in CSS
    assert "@media(max-width:620px)" in CSS
    assert ".portal-feature-grid{grid-template-columns:1fr}" in CSS
    assert "[data-section-active=true]" in CSS

"""UI navigation contract for one canonical four-category OpenStick settings tree.

Only template/HTML/CSS/JS are inspected: device actions are never sent.
"""
from pathlib import Path
import re

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1] / "uz801_manager"
ENV = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=True)
PARAMS = {
    "token": "synthetic",
    "portal_settings_features": {
        "wifi": True, "network": True, "internet": True,
        "hotspot": True, "leds": True,
    },
    "portal_has_power": True,
    "portal_has_quick": True,
    "portal_has_website": True,
    "portal_lan_enabled": True,
    "can_manage_lan": False,
    "lan_session": False,
    "filegator_enabled": False,
    "hostname": "example.invalid",
    "features": {
        "setup": True, "network": True, "hotspot": True,
        "website": True, "leds": True,
    },
}

SETTINGS_SCREENS = [
    ("setup.html", "wifi", "connect"),
    ("internet.html", "internet", "connect"),
    ("hotspot.html", "hotspot", "connect"),
    ("quick.html", "quick", "connect"),
    ("modem.html", "network", "sim"),
    ("modem.html", "ussd", "sim"),
    ("sms.html", "sms", "sim"),
    ("cellular.html", "network", "sim"),
    ("website.html", "website", "web"),
    ("leds.html", "leds", "device"),
    ("device_power.html", "manage", "device"),
    ("overview.html", "overview", "device"),
]


def render(name, page, **extra):
    return ENV.get_template(name).render(
        **{**PARAMS, "page": page, "title": "Mạng SIM", **extra}
    )


def links(html):
    return re.findall(
        r'<a class="settings-category-item" href="([^"]+)" data-settings-link="([^"]+)" data-settings-parent="([^"]+)">',
        html,
    )


def test_hub_shows_the_same_four_parent_cards_as_each_child_screen():
    hub = render("manage.html", "manage")
    assert 'settings-category-tree--hub' in hub
    assert 'class="settings-nav"' not in hub
    assert 'class="settings-submenu-desktop"' not in hub
    assert 'class="manage-sidebar"' not in hub
    assert 'id="manage-wifi"' in hub
    assert 'id="manage-sim"' in hub
    assert 'id="manage-device"' in hub
    assert 'id="manage-services"' in hub

    expected = links(hub)
    assert len(expected) >= 19
    assert set(p for _, _, p in expected) == {"connect", "sim", "web", "device"}

    for template, page, group in SETTINGS_SCREENS:
        html = render(template, page)
        assert 'class="settings-workspace"' in html or 'class="settings-workspace" data-settings-workspace=' in html
        assert 'settings-category-tree--sidebar' in html
        assert 'class="settings-nav"' not in html
        assert 'id="settings-submenu-toggle"' in html
        assert 'class="settings-workspace-content"' in html
        assert f'data-current-group="{group}"' in html
        assert links(html) == expected, template


def test_critical_existing_actions_remain_in_their_original_pages():
    checks = {
        "setup.html": ["setup-connect", "saved-wifi", "usb-ap-settings", "ap-clients"],
        "internet.html": ["policy-form", "internet-manual"],
        "hotspot.html": ["hotspot-status", "hotspot-config"],
        "modem.html": ["radio-mode"],
        "cellular.html": ["cellular-form", "cellular-profiles"],
        "website.html": ["web-pane-files", "web-pane-uploads", "web-pane-domains"],
        "leds.html": ["led-network-form", "led-fixed-panel"],
        "quick.html": ["quick-airplane", "quick-data", "quick-receive", "quick-ap", "quick-usb"],
        "overview.html": ["sim-usage-details", "overview-services"],
        "sms.html": ["sms-app", "sms-new-view"],
        "device_power.html": ["power-open-controls"],
        "manage.html": ["manage-access", "saved-wifi", "lan-manage"],
    }
    assert 'id="ussd-state"' in render("modem.html", "ussd")
    for name, ids in checks.items():
        page = (
            "network" if name in ("modem.html", "cellular.html")
            else "wifi" if name == "setup.html"
            else "manage" if name in ("manage.html", "device_power.html")
            else name[:-5]
        )
        html = render(name, page, can_manage_lan=True)
        for element_id in ids:
            assert f'id="{element_id}"' in html, (name, element_id)


def test_feature_visibility_never_links_to_unavailable_website_or_power():
    view = render("manage.html", "manage",
                  portal_has_website=False, portal_has_power=False,
                  portal_lan_enabled=False, can_manage_lan=False)
    assert 'data-settings-section="web"' not in view
    assert 'href="/website"' not in view
    assert 'href="/settings/system"' not in view
    assert 'href="/manage#manage-access"' not in view
    assert 'id="lan-manage"' not in view
    assert 'href="/modem/sms"' in view
    assert 'href="/modem/ussd"' in view


def test_url_targets_exist_for_every_internal_anchor():
    generated = render("manage.html", "manage")
    by_path = {
        "/setup": ("setup.html", "wifi"),
        "/internet": ("internet.html", "internet"),
        "/hotspot": ("hotspot.html", "hotspot"),
        "/modem/network": ("modem.html", "network"),
        "/modem/sms": ("sms.html", "sms"),
        "/modem/ussd": ("modem.html", "ussd"),
        "/sim/apn": ("cellular.html", "network"),
        "/website": ("website.html", "website"),
        "/overview": ("overview.html", "overview"),
        "/quick": ("quick.html", "quick"),
        "/settings/leds": ("leds.html", "leds"),
        "/settings/system": ("device_power.html", "manage"),
        "/manage": ("manage.html", "manage"),
    }
    for href, _, _ in links(generated):
        path, _, hash_part = href.partition("#")
        assert path in by_path, href
        if hash_part:
            name, page = by_path[path]
            html = render(name, page, can_manage_lan=True)
            assert f'id="{hash_part}"' in html, href


def test_responsive_sidebar_and_static_js_cannot_mutate_usb():
    css = (ROOT / "static" / "settings.css").read_text(encoding="utf-8")
    js = (ROOT / "static" / "settings_sidebar.js").read_text(encoding="utf-8")
    for marker in [
        ".settings-category-tree--hub", ".settings-category-tree--sidebar",
        ".settings-navigation-drawer", "@media(max-width:759px)",
        "grid-template-columns:repeat(2,minmax(0,1fr))",
        ".settings-workspace-content",
    ]:
        assert marker in css
    for marker in ["hashchange", "aria-current", "settings-submenu-toggle",
                   "web-pane-files", "web-pane-uploads", "web-pane-domains"]:
        assert marker in js
    assert "fetch(" not in js
    assert "localStorage" not in js
    assert "XMLHttpRequest" not in js


def test_filegator_keeps_all_three_navigation_tabs_visible():
    view = render('website.html', 'website', filegator_enabled=True)
    tabs = re.search(r'<nav class="web-tabs".*?</nav>', view, re.S)[0]
    assert all(f'data-web-tab="{key}"' in tabs for key in ('files', 'uploads', 'domains'))
    assert 'display:none' not in tabs and ' hidden' not in tabs
    assert 'id="web-filegator"' in view
    assert 'class="web-workspace" style="display:none"' in view

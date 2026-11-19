"""Shared settings parent/child navigation contracts; no device operations."""
from pathlib import Path
import re
from urllib.parse import urlsplit
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1] / 'uz801_manager'
TEMPLATES = ROOT / 'templates'
ENV = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
FEATURES = {'wifi': True, 'network': True, 'internet': True, 'hotspot': True, 'leds': True}
PARAMS = dict(token='synthetic', portal_settings_features=FEATURES, portal_has_power=True,
              portal_has_quick=True, portal_has_website=True, can_manage_lan=False,
              lan_session=False, hostname='example.invalid',
              features={'setup':True,'network':True,'hotspot':True,'website':True,'leds':True},
              filegator_enabled=False)

CASES = [
    ('manage.html','manage', {'/manage','/settings/system'}, 'manage'),
    ('setup.html','wifi', {'/setup'}, 'wifi'),
    ('quick.html','quick', {'/quick'}, 'quick'),
    ('internet.html','internet', {'/internet'}, 'internet'),
    ('hotspot.html','hotspot', {'/hotspot'}, 'hotspot'),
    ('leds.html','leds', {'/settings/leds'}, 'leds'),
    ('cellular.html','network', {'/modem/network','/sim/apn'}, 'network'),
    ('modem.html','network', {'/modem/network','/sim/apn'}, 'network'),
    ('device_power.html','manage', {'/manage','/settings/system'}, 'manage'),
]


def _render(name, page):
    return ENV.get_template(name).render(**PARAMS, page=page, title='Mạng SIM')


def test_every_settings_screen_keeps_parent_tabs_and_sibling_links():
    for name, page, allowed, group in CASES:
        html = _render(name,page)
        assert 'class="settings-nav"' in html, name
        assert 'class="settings-workspace"' in html, name
        assert f'data-settings-group="{group}"' in html, name
        assert 'id="settings-submenu-toggle"' in html, name
        assert '/static/settings_sidebar.js' in html, name
        assert 'class="settings-workspace-content"' in html, name
        # All children remain within their parent group. Cross-parent
        # suggestions are only in page content, not the persistent sidebar.
        links = re.findall(r'<a href="([^"]+)" data-settings-link="[^"]+">', html)
        assert links, name
        assert all(urlsplit(url).path in allowed for url in links), (name, links)
        assert 'aria-label="Menu con' in html


def test_only_network_modem_page_uses_settings_sidebar():
    network = _render('modem.html', 'network')
    ussd = _render('modem.html', 'ussd')
    assert 'class="settings-workspace"' in network
    assert 'class="settings-workspace"' not in ussd


def test_child_link_anchors_exist_in_destination_templates():
    examples = {
        'setup.html': ['connection-title','setup-connect-pane','saved-wifi',
                       'usb-ap-settings','ap-clients','setup-status-panel'],
        'internet.html':['policy-form','internet-manual'],
        'hotspot.html':['hotspot-config','hotspot-pending'],
        'leds.html':['led-theme-picker','led-network-form','led-form'],
        'manage.html':['manage-wifi','manage-sim','manage-device'],
        'quick.html':['quick-airplane','quick-data','quick-receive','quick-ap','quick-usb'],
    }
    for name, anchor_ids in examples.items():
        html=_render(name, 'wifi' if name=='setup.html' else 'manage' if name=='manage.html'
                     else 'internet' if name=='internet.html' else 'hotspot' if name=='hotspot.html'
                     else 'leds' if name=='leds.html' else 'quick')
        for key in anchor_ids:
            assert f'id="{key}"' in html, (name,key)


def test_responsive_workspace_has_real_mobile_and_tablet_modes():
    css=(ROOT / 'static' / 'settings.css').read_text(encoding='utf-8')
    js=(ROOT / 'static' / 'settings_sidebar.js').read_text(encoding='utf-8')
    for value in ['@media(max-width:759px)', 'grid-template-columns:190px minmax(0,1fr)',
                  '.settings-submenu-desktop', '.settings-submenu-mobile',
                  '.settings-workspace-content']:
        assert value in css
    for value in ['hashchange', 'aria-current', 'settings-submenu-toggle']:
        assert value in js
    assert 'fetch(' not in js
    assert 'localStorage' not in js

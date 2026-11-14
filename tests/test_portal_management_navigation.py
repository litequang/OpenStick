"""Contract checks for Linux portal management navigation (not visual screenshot tests)."""

from pathlib import Path
import re

import pytest
from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "uz801_manager" / "templates"
CSS = ROOT / "uz801_manager" / "static" / "portal.css"
SHORTCUTS = {
    "internet": "/internet",
    "hotspot": "/hotspot",
    "setup": "/setup",
    "website": "/website",
}


def render_portal(page="overview"):
    env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=True)
    return env.get_template("portal_chrome.html").render(
        token="fixture-token", page=page, lan_session=False
    )


@pytest.mark.parametrize("page,selected_href", SHORTCUTS.items())
def test_management_links_present_with_exact_selected_page(page, selected_href):
    html = render_portal(page)
    match = re.search(
        r'<nav class="portal-management-links"[^>]*>(.*?)</nav>', html, re.S
    )
    assert match is not None
    links = match.group(1)
    assert links.count('class="portal-management-link"') == len(SHORTCUTS)
    for href in SHORTCUTS.values():
        assert f'href="{href}"' in links
    assert (
        links.count('aria-current="page"') == 1
        and f'href="{selected_href}" aria-current="page"' in links
    )


def test_unselected_overview_does_not_mark_management_subpage_current():
    html = render_portal("overview")
    links = re.search(
        r'<nav class="portal-management-links"[^>]*>(.*?)</nav>', html, re.S
    ).group(1)
    assert 'aria-current="page"' not in links
    assert 'id="portal-management-menu"' in html


def test_skip_link_and_dock_labels_support_small_screens():
    html = render_portal()
    css = CSS.read_text(encoding="utf-8")
    assert 'href="#portal-content"' in html
    assert 'id="portal-content" tabindex="-1"' in html
    assert '<span>Wi-Fi</span>' in html
    assert ".app-bottom-nav-item>span:last-child" in css
    assert "text-overflow:ellipsis" in css
    assert ".portal-skip-link:focus-visible" in css
    assert ".portal-management-details>summary:focus-visible" in css
    assert "@media(max-width:359px)" in css

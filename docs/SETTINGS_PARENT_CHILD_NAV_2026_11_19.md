# OpenStick settings navigation — parent tabs + persistent child menu

## Provenance and scope

Base commit is exactly
`3a459f6ef7252ea2bcd2d611a14e484cd6556c54` on
`codex/uz801-v32-postmarketos`. This redesign is presentation-only:
no changes to the saved Wi-Fi profiles, shared AP/SSID, modem/airplane
workflows, data consent, APN, SIM/USB tethering, LED recipes, Nginx,
Cloudflare Tunnel, power control, auth rules, firmware or Linux services.

The reported defect: `/manage` presented many links in four large cards,
but navigating into a child showed unrelated page controls rather than a
persistent sibling list. The existing top `settings-nav` contained mixed
first-level and child routes; only some screens displayed their own local
subnav.

## New responsive interaction

- **Parent tabs** remain at the top on every settings page: Cài đặt nhanh,
  Cài đặt, Wi-Fi, Internet, Phát Wi-Fi, Mạng SIM, Đèn LED, subject to backend
  availability. They can scroll horizontally on narrow screens rather than
  break into 3+ uneven rows.
- **PC ≥ 960 CSS px**: left sticky child navigation, width 195–230px,
  independent reading/editing content on the right. Long side lists scroll
  within the available viewport. The current item follows the URL/hash.
- **iPad/compact desktop 760–959 CSS px**: left sidebar is reduced to 190px;
  main panel remains fluid.
- **Phone < 760 CSS px**: no sidebar taking half the screen. A compact
  collapsible selector says `Trong Wi-Fi · <current child>`; it opens a
  list of sibling links, closes after selection, and persists on all sibling
  pages. The global bottom dock remains unchanged.
- Source-only UI includes one shared template
  `settings_workspace_start.html` and one tiny
  `settings_sidebar.js` (no API or localStorage).
- Navigating to anchor links keeps the selected form visible below the
  sticky header + parent tabs via CSS scroll margins.
- Switching to another parent deliberately changes the sidebar. Clicking
  sibling links cannot inadvertently switch parent groups.

## Parent-to-child map

- Cài đặt: tất cả, Wi-Fi, SIM & Internet, thiết bị/dịch vụ,
  truy cập quản trị (USB/LAN eligible), hệ thống power (if available).
- Wi-Fi: current Wi-Fi, connect, saved Wi-Fi, USB AP identity,
  attached clients, recovery.
- Internet: source/priority policy, manual connection guidance.
- Phát Wi-Fi: status, shared AP configuration, legacy pending handoff.
- Mạng SIM: status & radio mode, APN profiles. Both share the
  `page='network'` context.
- Đèn LED: initial state, theme packs, per-role rules, fixed LED patterns.
- Cài đặt nhanh: overview plus aircraft, SIM data, receive Wi-Fi,
  broadcast Wi-Fi and USB tethering tiles.

Different workflows cross-link from their **page content** when needed,
rather than incorrectly claiming to be siblings.

The old `/setup`, `/sim/apn`, `/modem/network`,
`/settings/system`, `/settings/leds`, `/manage`,
`/internet`, `/hotspot`, `/quick` and hash IDs stay stable.
`modem.html` only gets this settings workspace when
`page='network'`, not on USSD or SMS pages.

## Quality gates

- Source check: `python -m pytest -q`.
- JS syntax: `node --check uz801_manager/static/settings_sidebar.js`.
- Existing functional fixtures must remain green; this change must not
  trigger POST actions when visiting a settings page.
- Browser review at widths 320, 360, 390, 430, 768, 820, 1024, 1280:
  no horizontal page overflow; top parent scroll independent; iPad left
  menu remains visible; mobile subnav opens/closes; links highlight after
  hash changes; the content form remains interactive; bottom dock / header
  remain accessible; landscape and device Safe Area are not clipped.
- Review on physical PC/iPad/Android before merging; device installation
  requires existing backup/checksum/rollback workflow and separate consent.

## Risk and fallback

Changing only Jinja markup and CSS can affect local form widths and nested
scroll; verify layout on the actual browser rather than inferring from tests.
A browser without CSS `:has` may show a vertically stacked fallback;
the navigation links remain ordinary HTML anchors. No network operation
should be attempted as part of a UI acceptance test.

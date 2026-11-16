# OpenStick — Management and adaptive bottom navigation V2

## Source and intent
Started from `codex/uz801-v32-postmarketos` at
`4c6975bb278b77205715c7de56681eaefe8aa17d`.
The current device code already supports real saved Wi-Fi, one shared USB AP
identity, SIM Internet hotspot/consent, LAN login, LED style gallery, SMS,
USSD, static website and device telemetry. This iteration **only reorders
navigation/presentation**. The existing API handlers and persistent network
or credential settings are unchanged.

## Phone and tablet navigation

| Viewport width (CSS px) | Visible destinations |
| --- | --- |
| below 390 | SMS · USSD · Tổng quan · Wi-Fi · Quản lý (five) |
| 390–699 | SMS · USSD · Tổng quan · Wi-Fi · SIM · Quản lý (six) |
| 700 and above, website backend available | SMS · USSD · Tổng quan · Wi-Fi · SIM · Website · Quản lý (seven) |
| 700 and above, website backend unavailable | Six items, no broken Website link |

The six/seven shortcuts all retain touch-friendly space within the existing
600px maximum rounded dock. They **never** replace the five destinations
required by small screens; hidden entries remain accessible inside Quản lý.
The dock still uses the existing scroll up/down behavior, safe-area inset,
reduced-motion setting and keyboard focus support.

The selected icon is meaningful on child pages. When SIM is visible,
`/modem/network`, `/hotspot` and `/internet` highlight SIM rather than
simultaneously highlighting Quản lý. When Website is visible, `/website`
highlights Website. On smaller screens, those child pages highlight Quản lý
instead. `/setup` highlights Wi-Fi directly.

## Management hub

The previous `/manage` stacked three levels of navigation:
a sticky top category strip, quick-access sidebar, and repeated category
lists, in addition to the global dock. These duplicate link destinations.
It is now one grouped page without a second sidebar or sticky category bar.
A simple responsive 2-column desktop / 1-column mobile grid groups:

- Wi-Fi: connect, saved profiles, USB SSID/password/channel and current state.
- SIM & Internet: cellular registration/radio, SIM APN/hotspot and
  Internet source policy.
- Device & services: website, LED styles, health/metrics.
- Access security: USB-only LAN password form, or read-only explanation
  in authenticated LAN session.

Old `/manage#saved-wifi` opens an in-page link to the real
`/setup#saved-wifi` control. Existing group hash IDs are retained for old
links, and saved Wi-Fi management remains protected.

SIM settings subpages use a single local row with Back to Quản lý and the
three related destinations. The redundant breadcrumb row was removed there.
Dedicated Website and LED pages retain their breadcrumb.

## Safety and compatibility

- No changes to radio, SIM data, APN, modem actions, website content,
  stored LED recipes, Wi-Fi profiles, Wi-Fi recovery/rollback, OpenRC or
  firmware.
- Website shortcut only renders when the website backend exists.
- LAN password management remains visible only on USB; authenticated LAN
  users see a non-editable notice. All API guards are retained.
- `/setup` and `/setup#saved-wifi` remain the primary places to change
  Wi-Fi. The older `/` is retained as the optional Wi-Fi status/speed view,
  avoiding a breaking route removal.
- Opening a link, navigating a card, or changing a tab does not issue network
  operations.

## Verification and handoff

Run `pytest`, Node synthetic UI fixtures, JS syntax and packaging smoke.
Run DOM checks at 320, 360, 390, 430, 768 and 1280 CSS px:
no horizontal scroll; header/popover usable; labels do not truncate badly;
all visible bottom-nav targets 200; active item follows page;
none of the five small-phone actions disappear; forms remain touch-friendly.
Do not infer real Android touch acceptance from a synthetic DOM test.

Deploy to actual USB only after explicitly checking device state and
creating a timestamped backup of `hosting.py`, `portal_chrome.html`,
`manage.html`, `portal.css`. If a network handoff is pending, postpone.
Use the owner’s Codex PC physical USB process; no direct deployment here.

## Outstanding
Manual acceptance needed on phone/tablet for 6/7-item dock width and
tap target sizes, the LAN password panel, and the header vs. subtab scroll.
The prior baseline commit itself had one stale source assertion requiring
`id="saved-wifi"` on `/manage` while the link had been moved to `/setup`.
V2 retains that anchor and fixes its presentation.

# Unified four-group USB management navigation (19 November 2026)

Later on the same day, the owner requested separate child screens and removal
of retired native controls when FileGator is present. The installed result is
documented in [SETTINGS_CHILD_SCREENS.md](SETTINGS_CHILD_SCREENS.md); its canonical
URLs and FileGator-only layout supersede the hash destinations/native-tab
inventory below. The shared four-category tree remains current.

## Baseline / code branch
- Base: `3a459f6ef7252ea2bcd2d611a14e484cd6556c54` on
  `codex/uz801-v32-postmarketos`.
- Implementation: `ui/settings-parent-child-nav-20261119`, draft PR #7.
- Goal: the management landing page and the persistent child-page menu share
  **one server-rendered inventory**, rather than having separate navigation
  structures. All network/configuration operations remain unchanged.

## Inventory grouped by actual source routes

| Parent | Children (existing implementation) |
| --- | --- |
| Kết nối & Internet | Quick Settings (airplane, SIM data, Wi-Fi, USB), Wi-Fi station, saved Wi-Fi profiles, shared AP SSID/PSK/channel, AP client inventory, hotspot status, Internet-source policy, USB tethering |
| SIM & liên lạc | Modem registration and radio mode, SMS threads/composition, USSD sessions, custom APN profiles, passive SIM data usage statistics |
| Website & dịch vụ | Website dashboard and multi-site manager, files, uploads/ZIP, domains; the native file-editor layout is retained |
| Thiết bị & bảo mật | Overview/health/telemetry, LED style/state recipes, safe power controls, USB-only LAN administration credentials |

Data usage is at `/overview#sim-usage-details`; the menu deliberately
has a single canonical destination and no duplicate physical form.
Quick Settings contains shortcuts to both SIM data and USB tethering.
External firmware backup / EDL remains in the **Windows application**,
not a fabricated portal action.

## Screen contract

1. `/manage`: four 2-column cards (desktop) showing the parent title,
   explanatory line and child entries; single column/collapsible on mobile.
2. All child pages: one compact persistent left rail containing these
   **same four parent cards** as an accordion, with current group and child
   highlighted. It never navigates the user out to the hub just to switch
   sibling destinations.
3. iPad portrait and compact screens: narrower sidebar, fluid content.
   Under 760 CSS px: an expandable `Danh mục cài đặt` panel on top of
   the content instead of a narrow column.
4. Global header + existing adaptive 5/6/7 bottom dock remain. The old
   redundant `settings-nav` and breadcrumb row are removed.
5. The same `settings_menu.html` Jinja include creates the hub cards and
   sidebar links; source of truth: `portal_settings_features` and backend
   availability. Password/LAN management is shown only when that backend
   exists and the existing USB/LAN authentication rules remain unchanged.
6. When a Website menu item includes a panel hash, front-end code calls the
   existing web-tab button, not a new publish action; revisiting the page
   must not upload or mutate any file.

## Behavioral safety

- Do **not** auto-toggle airplane, cell data, AP, USB tethering, modem, or LED.
- Do **not** show a green operation result because a menu was clicked:
  menu links only navigate existing GET pages.
- Do not expose SIM IDs, Wi-Fi PSKs, SMS contents, secrets, network logs or
  website file content in CI artifacts.
- No replacement of network interfaces, firewall, DHCP, NCM or boot settings.
- No automatic USB deployment or firmware flashing from CI.

## PC acceptance procedure

1. Confirm real device SSH, USB NCM management route and a fallback path.
   Collect read-only version, state and build markers; do not stop services.
2. On Windows, fetch branch, inspect diff; ensure the branch contains the
   correct source commit and no unrelated modifications.
3. Run `python -m pytest -q`, `node --check
   uz801_manager/static/settings_sidebar.js`, and existing JS fixture tests.
4. Run `scripts/preview_portal.py` locally and
   `scripts/verify_settings_browser.py` against 127.0.0.1:8771.
   Use Chrome widths 320 / 360 / 390 / 430 / 768 / 820 / 1024 / 1280,
   landscape/portrait; test nav on /manage, /setup, /quick, /internet,
   /hotspot, /modem/network, /modem/sms, /modem/ussd, /sim/apn,
   /website, /settings/leds, /settings/system.
5. Check the hub/child list matches; SMS and USSD are under SIM, USB
   tethering under Kết nối, Website under Website, LAN under Device.
   Check Website tab hash, saved Wi-Fi anchor, LAN permissions, no horizontal
   page overflow, sticky menu and touch-size/focus.
6. Only then back up and checksum on-device files that will change,
   follow the repository's device deployment process for **portal source
   only**. Avoid package reinstall/firmware flash/network configuration
   changes unless unavoidable and explicitly approved. Preserve ownership,
   mode, service dependencies, session secrets, and rollback files.
7. Compare UI from USB and LAN (if enabled), validate GET routes and
   unchanged network status, modem, SIM, local AP, USB NCM, tunnel and
   website. Do not submit destructive network actions as part of UX testing.
8. If errors occur, restore just the saved versions, refresh only the
   necessary portal service after checking no live critical operation, then
   verify USB management/SSH again.
9. Report SHA, full commands, pytest counts, browser results, actual USB
   version before/after, changed files, backup location and rollback result.

## Known limits
This is a navigation redesign, not a new Wi-Fi or modem driver capability.
The 4-category source has been reviewed statically and tested in the
project CI; actual physical device + iPad/Android taps are an additional
acceptance gate.

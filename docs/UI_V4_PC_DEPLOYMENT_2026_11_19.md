# UI V4 PC validation and USB deployment — 19 November 2026

Requested source: `d8b6d4a3b32560c00830cc7b99140299cb3422d9`,
branch `ui/settings-parent-child-nav-20261119`, [PR #7](https://github.com/litequang/OpenStick/pull/7).
Base: `3a459f6ef7252ea2bcd2d611a14e484cd6556c54` (documentation over installed
portal source `461e913ca43f87e549a490472f4899a72d5af235`). No main merge is authorized
for this deployment. The two unrelated untracked files remain untouched; no
stash existed, no reset/clean was used, and the standard branch was not moved.

## Defect found before deployment

Opening `/website#web-pane-uploads` initially left Files selected. The new
deferred menu controller clicked a tab while the existing website inventory
loader had disabled every button. Actual Chrome preview reproduced this failure.
Keep pure tab buttons usable during loading; file/configuration controls retain
the original busy gate. Clicking a native website tab also updates the current
menu item through a local hash change. Neither path sends a device action.
The installed source must therefore include the tested follow-up fix, not the
original requested commit alone.

Real USB navigation then exposed the existing FileGator-specific hidden Upload
tab, absent from the default preview configuration. Keep all three native tabs
visible while retaining FileGator and its hidden duplicate native editor. Added
a FileGator-enabled preview option and regression assertion; no uploader,
extraction, file or service behavior is changed by this visibility correction.

## PC validation

- `.venv/Scripts/python.exe -m pytest -q`: **787 PASS, one Windows symlink
  privilege skip, exit 0**. This includes the existing Node fixtures for modem,
  SMS, website, saved Wi-Fi, setup, telemetry, LED and settings actions.
  Bare `python -m pytest -q` initially exited 1 because the Windows default
  interpreter has no pytest; no dependencies or tests were removed.
- `node --check` on `settings_sidebar.js` and `website.js`: exit 0. The new
  settings asset is now also syntax-checked by CI.
- All 19 Jinja templates parsed, exit 0; template/route/asset tests passed.
- `scripts/verify_settings_browser.py` against the disposable localhost preview:
  104 route/width layouts plus eight landscape cases, at 320/360/390/430/768/820/
  1024/1280 CSS px; 24 existing settings layouts and interaction regressions.
  Four shared groups, one menu, sibling/parent navigation, mobile drawer,
  desktop/iPad sidebar geometry, Overview/header/dock, website deep links and
  native tab switching passed, with no horizontal overflow or JavaScript errors.
  Read-only action allowlisting observed zero attempted mutations during menu QA.
- `scripts/verify_power_browser.py`: four preview layouts, header exclusivity,
  Overview menu, confirm/cancel/unknown passed; zero real power commands.
- Screenshots are fictional preview data only and stay ignored. These results
  are automated Chrome checks, not acceptance from a physical iPad/phone.

## Exact device file scope

Only these 19 files under `/opt/openstick/uz801_manager` change:

```text
hosting.py
static/settings.css
static/settings_sidebar.js
static/website.js
templates/cellular.html
templates/device_power.html
templates/hotspot.html
templates/internet.html
templates/leds.html
templates/manage.html
templates/modem.html
templates/overview.html
templates/portal_chrome.html
templates/quick.html
templates/settings_menu.html
templates/settings_workspace_start.html
templates/setup.html
templates/sms.html
templates/website.html
```

`hosting.py` adds only a context flag for LAN-menu visibility. No modem, network,
backup, firmware, gadget, firewall, worker or provisioning implementation changes.
Documentation, tests, preview tools and CI configuration are not installed on USB.

## Preflight and installation gate

Real NCM adapter is Up; pinned SSH and `usb0` work on the existing postmarketOS
device. All target baseline source hashes match, with no pending network/power
operation. USB/LAN portals, setup/hotspot/startup workers, custom `openstick-web`
Nginx service and Cloudflare service run; ModemManager owns its bus name.
Do not use the unrelated stock OpenRC `nginx` service status for this installation:
Nginx processes are owned by the custom web service.

715 protected files were hashed privately, including owner configuration,
network profiles, SSH, website files, SMS and web registry. Live usage checkpoints
and worker runtime state are intentionally not frozen; worker continuity is
verified separately. Private addresses, IDs, configuration hashes and timing
artifacts are not included here. Timestamped source archive, metadata and
checksummed private manifest must exist before replacing files. Deployment is
gated on follow-up source CI; only USB/LAN portal services may restart, with
rollback on failed health/state verification. No firmware flash or device reboot.

Installation and independent hardware acceptance will be recorded below only
after they complete.

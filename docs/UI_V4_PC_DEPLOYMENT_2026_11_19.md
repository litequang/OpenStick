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

## Historical V4 installation and read-only checks

The child-screen and FileGator-only changes requested afterward supersede this
layout. See [SETTINGS_CHILD_SCREENS.md](SETTINGS_CHILD_SCREENS.md). The final
protected-state comparison after `4cca1fa` was interrupted by the owner's
poweroff/unplug/replug; it must not be reported as completed acceptance. The
earlier independent verification of `760a304` passed. Subsequent deployment uses
a new baseline after the owner's power cycle, preserving terminal receipts and
current tethering intent rather than restoring older runtime state.

Source installed at this stage: **`4cca1fa4f4ac042714823c10e64d6de3c848fcd9`**.
The busy-tab fix is `760a30497b86e8f5a219318757d687e90a3509de`; the final source
adds the FileGator visibility correction. Both final-source Windows workflows
passed, including pytest, JavaScript checks, EXE build, EXE self-test and smoke:
[branch CI](https://github.com/litequang/OpenStick/actions/runs/44457866963),
[PR CI](https://github.com/litequang/OpenStick/actions/runs/44457876345).

Initial installation replaced the 19 listed files; the final correction replaced
only `templates/website.html`. Timestamped private backups of the replaced source
and its ownership/modes were made before replacement. Archives and manifest
checksums remain under `/var/lib/openstick/deploy-backups/ui-v4-*`; no backup or
runtime data is in Git. Only `openstick-wifi` and `openstick-lan` restarted and
storage was flushed. Source/asset hashes and existing ownership/modes matched.

The first private deploy attempts stopped before replacing files: querying the
hotspot state while holding the deployer's own network lock made its fallback
report busy. The installer now checks that fallback before acquiring the locks,
keeps persisted-transition/power/job checks inside the protected window and
waits boundedly for existing worker locks. These were installer-only changes;
no product safety gate or device network behavior was removed. No rollback was
needed or executed; do not call the unexecuted rollback path hardware-tested.

Chrome Windows against the **actual USB portal** passed 104 route/width layouts
plus eight landscape cases using the same eight CSS widths. Four groups, one
menu, active child, parent/sibling navigation, sidebar/drawer geometry, header,
dock, website hashes and native tabs all passed with FileGator enabled. No
horizontal overflow or JavaScript error was observed. Opening and navigating
produced 88 legacy **read-only** POSTs (status/archive/list); zero mutating
requests were attempted. The guard permits only fixed read actions and can
withhold modem SMS import. No actual SMS, USSD, APN, radio, data, AP, tethering,
LED, file-write or power action was submitted. No real-page screenshot, trace,
SMS, website text, SSID, MAC or identifier is exported.

Public HTTPS returned 200 before and after installation. The probe used a normal
browser user agent; the initial bare-library request was not a valid success
check. The existing Tunnel and Nginx configuration remain unchanged.

These are read-only navigation checks. A physical phone/iPad touch session,
password re-entry, uploading/extracting/editing actual website files and disruptive
network/power actions are not part of this acceptance.

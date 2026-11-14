# Handoff — 2026-11-14, home machine

## Latest update: state-first LED mixes and stable telemetry

`272777e` is installed on the actual USB. The LED page now follows the owner's
requested model: select a network state, then choose off/on/blink independently
for red, green and blue, with per-color timing. Save enables complete recipes
and retains edits across state selection. A supervised LED worker reads role
metadata and updates only changed outputs. Existing fixed settings and their
baseline remain compatible; no recipe was enabled by deployment itself.

Header/overview retain the last good readings during polling, missing samples
and request failures; stale values are identified. Actual disconnect/no-SIM
and valid zeros still update. The unsupported eMMC health card is hidden:
actual driver health fields are zero/unreported, while write counters work.

Full suite: **436 passed / one Windows symlink skip**, 92.43 s. Real driver
probe on the current disconnected role verified simultaneous red steady,
green 200/800 ms and blue 700/300 ms timers, both brightness phases, no writes
on unchanged polling, and saved recipe replay. Owner configuration and all
LEDs were restored afterward. Other role transitions use injected metadata
tests; new UI visual acceptance/reboot are untested. No SIM data or Wi-Fi
activation was performed for these tests. Latest observed WLAN/cellular are
disconnected; five station profiles remain. Do not reuse the older SIM AP
checkpoint as current state. Detailed file list, backups, rollback and limits:
[LED state rules and dashboard report](LED_STATE_RULES_AND_DASHBOARD_2026_11_15.md).

## Latest follow-up: Android hotspot hostname accepted

The owner reported IP administration worked but Android returned
`DNS_PROBE_FINISHED_NXDOMAIN` for `openstick.local`. Avahi was healthy and
answered on wlan0 with the AP address only, but ordinary hotspot DNS returned
NXDOMAIN. `5660c77` adds the exact name to NetworkManager shared dnsmasq via
`/etc/NetworkManager/dnsmasq-shared.d/54_openstick_local.conf`, using wlan0's
IPv4 address and a local-only zone. The setup DHCP service now also provides
local-only DNS and advertises it to clients; it remains inactive and disabled
under its existing worker policy.

Real validation: temporary staged DNS A/AAAA/HTTPS-type responses, combined
dnsmasq syntax, exact setup service arguments, live hotspot DNS A=192.168.8.1
and empty successful AAAA/HTTPS-type responses, named HTTP through that DNS
200, SIM-bound Internet still passing, PC USB name resolution and HTTP 200.
The owner then reconnected Android and explicitly confirmed the named URL
works. No new Python/JS change or full-suite rerun was needed for these two
configuration files. The prior application full suite remains 424 passed /
one Windows skip.

Backup:
`/var/lib/openstick/deploy-backups/home-20261114/before-hotspot-local-dns-1794676748.tar.gz`.
Only the owned Wi-Fi AP was down/up once under the network lock/checkpoint;
no NetworkManager restart, reboot, WWAN reconnection or credential change.
Protected profile, site, SSH/Tunnel and configuration files compared unchanged.
Latest live status: SIM/AP active, enabled true, no pending trial. The owner
has saved the hotspot mode; reboot/autostart acceptance remains untested.
Setup-mode phone DNS acceptance remains separate and untested; setup was not
activated just to test it. See [local naming](LOCAL_MANAGEMENT_ADDRESS.md).

## Latest update: LED controls, visible APN and corrected SIM probe

Application source through `3bd728a` is installed on the actual USB, including
LED controls (`ca346d7`) and APN/diagnostics (`84b5426`). See
[the detailed LED/SIM report](LED_AND_SIM_HOTSPOT_2026_11_15.md) for exact
backups, real driver/probe evidence, rollback and unverified items.

Use `/settings/leds` for the three binary case LEDs; boot replay is enabled.
A real timer/brightness probe was restored to the original LED state.
`/hotspot#sim-apn` now exposes automatic/manual APN and a separate save action
without changing Wi-Fi keys or enabling SIM data. SIM auto-configuration was
already enabled, with the provider database installed.

An actual trial connected cellular data but not AP. Bound HTTPS returned 204;
the old Internet probe rejected DNS arrays formatted `A | B`. Correct parsing
with BOTH HTTPS and DNS bound to the SIM interface returned 204. The parser
is fixed; this establishes SIM Internet for that observation, not phone
sharing. Last action errors now survive polling, and Keep is disabled until
AP/cellular/trial readiness. Do not confirm phone connectivity for the owner.

Before the final DNS update the pending trial expired, independent recovery
stopped cellular, and no pending job remained. The update then restarted only
the two web services and verified HTTP/status and protected-file equality.
Five station profiles were saved, zero active; setup/policy remained disabled.
The owner is retrying; inspect fresh state rather than assuming this persists.
Full suite before DNS follow-up: 422 passed / one Windows skip; latest focused
hotspot tests: 45 passed. Final full suite for `3bd728a`: **424 passed, one
Windows symlink skip**, 89.23 seconds; self-test, JS syntax and diff check pass.

The owner then explicitly confirmed the phone sees USB Wi-Fi and accesses
Internet after the DNS fix. A fresh device read agreed: cellular/AP active,
Start successful, SIM-bound probe true, 222 seconds left in a pending trial,
enabled false. Phone sharing is accepted for this trial; Keep/autostart/reboot
remain unverified. The agent did not press Keep. Do not restart web services
while a trial is in flight; inspect pending state and network lock first.

## Previous deployment: common local URL, usability UI and signal icons

The actual USB now runs `ea9fcc8`, including the requested `0dda4fc` usability
integration and `c3ca851` local naming. Use **http://openstick.local:8765** on
PC USB, station Wi-Fi or the stick's AP. The PC system resolver, real USB
multicast and named HTTP were verified. Both station and setup-AP named login
were checked on the device; phone visual acceptance remains open. Avahi is
enabled for boot on USB/Wi-Fi only. Existing USB and AP IP fallbacks remain.
The header shows carrier on SIM, and fresh 0–4 signal bars on the network
chip with clickable details. Source tests: **387 passed, one symlink skip**.

See [the deployment report](USB_UI_DEPLOYMENT_2026_11_14.md) for the exact
source, file list, backups, rollback, HTTP and security checks and limitations.
The current observed network role is setup AP, with no pending setup job;
four station profiles remain saved, zero active while AP is running.
The owner reports rejoining their older home router fails although other
networks work after hotspot mode. A private profile comparison found the
target's key/settings unchanged and no stored denylist/BSSID lock. Do not
assume all AP-to-station transitions are broken or infer the password is
wrong solely from the driver errors. This router-specific fault is still open.

Local website HTTP and Tunnel service are healthy, but the public website
returned Cloudflare HTTP 403 in checks from both PC and USB. Public access is
not certified. Responsive browser/phone checks were blocked by unsupported
URL enforcement for the Windows browser and remain unverified.

## Saved Wi-Fi management overview (deployed on the actual USB)

The `/manage` hub now shows a dedicated **Wi-Fi đã lưu** section with a count,
SSID names, an indicator for the connected network and a Refresh button. Its
link opens `/internet#saved-wifi`, where saved profiles can be connected or
forgotten with the existing confirmation workflow. `/internet` now loads its
saved profiles automatically when opened. The new authenticated GET
`/api/wifi/saved` returns only `ssid` and `active`, never profile UUIDs or
secrets. Listing remains available while setup AP is active; network-changing
actions continue to observe the existing station-role guard.

Deployment on 2026-11-14 replaced seven portal files: `network_policy.py`,
`network_web.py`, `templates/manage.html`, `templates/internet.html`,
`static/manage.js`, `static/internet.js`, and `static/portal.css` beneath
`/opt/openstick/uz801_manager`. The installer first verified exact installed
file versions and created a device-side backup at
`/var/lib/openstick/deploy-backups/home-20261114/before-saved-wifi-1794670812.tar.gz`.
Both `openstick-wifi` and `openstick-lan` restarted successfully, without a
device reboot or any Wi-Fi profile changes.

Real USB checks: `/manage`, `/internet`, `/overview`, `/`, and three changed
static assets returned HTTP 200; an authenticated real GET of the new API
returned **4 saved profiles, 1 active** (names deliberately omitted from
handoff). Both portal services were running; the local website on port 8080
returned 200; LAN `/login` returned 200; unauthenticated LAN `/manage` redirected
to login (302). On the Windows development machine the full suite passed
**380 tests**, with **one Windows symlink skip**; focused policy/auth tests
passed 47/47; JS syntax and `git diff --check` passed. A browser-based visual
check on the owner's phone has not yet been performed.

## Portal management navigation (deployed on USB)

The portal now includes `/manage`, grouping existing controls into connectivity,
SIM/modem, and website/system sections. The bottom dock links to this hub; its
previous direct network item remains accessible at `/modem/network`. Feature
links are conditional on registered backends. Existing API handlers, network
policy, credentials, and Wi-Fi recovery behavior were not changed.
The UI was deployed on the actual USB on 2026-11-14 from commit `067d347`.
Only `hosting.py`, `templates/portal_chrome.html`, `templates/manage.html`,
and `static/portal.css` were replaced under `/opt/openstick/uz801_manager`.
The existing CSS was confirmed byte-equivalent to the predecessor after
normalizing CRLF line endings. The backup on the device is
`/var/lib/openstick/deploy-backups/home-20261114/before-manage-ui-1794669809.tar.gz`.
The `openstick-wifi` and `openstick-lan` services restarted successfully.
Checks on the real USB and from the home PC: `/manage`, `/overview`, `/`,
and `/static/portal.css` HTTP 200. The USB's LAN IPv4 was present, LAN `/login`
returned 200, and unauthenticated LAN `/manage` redirected (302). All six
checked OpenStick services were running, and the local website loopback
returned 200. End-to-end authenticated LAN login, public Tunnel access and
visual/mobile acceptance were not retested during this UI-only deployment.
Validation after this change: full suite 379 passed / 1 Windows symlink skip
(including the navigation and route access assertions); focused navigation test
1 passed, self-test assets/API passed. Live hardware HTTP checks are listed
above; interactive/visual acceptance remains pending.

Branch `codex/uz801-v32-postmarketos`. No merge,
release, flash or partition changes. Earlier company shutdown notes are
historical. USB is currently powered and accessible.

**Latest finding:** the owner's second Wi-Fi connected successfully through
the setup page, with DHCP and bound Internet verified. Failures against the
older router must not be generalized to all AP → station transitions. The
exact old-router interoperability/configuration issue remains unresolved.

Save now authorizes exactly one normal reboot. A durable private intent
resumes on the next boot, tries the requested network, restores an older
same-SSID keyfile on failure, then tries saved visible/hidden networks before
starting setup AP. Active SMS/USSD delays reboot. A configuring UUID (NM 50)
is no longer mistaken for a connected LAN (NM 100 plus IPv4). Internet probes
are not required for local management.

Real reboot test passed in about 74 seconds: new boot, correct target profile,
DHCP, Wi-Fi-bound Internet and LAN login HTTP 200. It reused the owner's
already-working derived keyfile privately to test the durable worker; the
owner had previously submitted its password through the actual setup UI.
See [detailed continuation](AI_CONTINUATION.md) for evidence and limits.

Negative live API test also passed: POST a nonexistent SSID, one reboot,
requested profile failure, then successful fallback to saved working Wi-Fi
in about 100 seconds (`SAVED_WIFI_CONNECTED`). No setup transaction remained
pending and there was no reboot loop. Final device state is the working
second Wi-Fi with setup recovery still enabled; no SIM data was enabled.

## Access and installed work

- USB SSH and `http://172.16.42.1` work independently of the company machine.
  Home key/host pin are only in ignored `runtime/usb-ssh/`. Company key retained.
- Existing LAN password, website and Tunnel were preserved. Administration
  remains private; LAN port is 8765 and its station address is DHCP-derived.
- Installer Wi-Fi fix uses stable MAC, powersave disabled, derived PSK,
  preserved UUID and longer timeout. Actual connect API passed. A later drop
  recovered after normal reboot; sustained station stability remains open.
- SMS has separate list/conversation/new composer, private SQLite archive,
  verified deletion/tombstones and uncertain-send protection. Agent did not
  send a real SMS. Synthetic DOM acceptance is not screenshot verification.
- SIM/signal share one header icon; Wi-Fi indicates station/SIM AP/setup AP.
- Four Internet policies, saved Wi-Fi profiles and explicit data-off are
  implemented. Default policy is disabled with no cellular consent. Agent
  never activated SIM data; real failover/Internet sharing is unverified.

## USSD

Old ModemManager QMI path used UCS2 and could return a method error before a
late reply. Comparing cached text missed identical replies. New typed
GI/libqmi owned VOICE client sends ASCII codes as ASCII and consumes fresh
method responses/indications. Device dependency `py3-gobject3` was installed
from official signed APKs. No raw AT or firmware change.

Three prototype, four production-controller and two final web API account
queries passed, including identical replies. Both web API results survived
unrelated status jobs; final web requests took about 13.4 and 5.0 seconds.
per-operation receipt polling prevents status jobs in other tabs replacing
USSD/SMS results. Never resend unknown operations automatically. Interactive
menus, broad operator coverage and prolonged reliability remain unverified.

Earlier old-path tests showed 4G-only failure, 3G success and LTE → UMTS → LTE
during mixed-mode success. Owner chose to set the preference personally.
Last observed current AND saved mode was `[12,8]`; do not restore the obsolete
company handoff's `[8,0]` value. PIN2 alone is not a blocking SIM lock.

## Automatic local setup AP

Owner requested configuration access with only USB power, no SIM Internet,
no known Wi-Fi and no PC. `/hotspot` now links the independent `/setup` mode.
`setup_ap.py`, `setup_web.py` and two OpenRC services are installed. Recovery
is enabled on this unit; generated credentials stay private and stable.
The connection card is also in ignored runtime storage.

After 60 seconds without a connected station, local AP/DHCP/authenticated LAN
administration start. It uses manual IPv4, no advertised router/DNS and an
explicit forwarding drop; it never activates cellular data. Existing active
SIM AP/data is preserved. Wi-Fi handoff is queued durably and reboots once
after the HTTP response; failure tries older saved Wi-Fi before restoring AP.

Real hardware fix: optional PMF tried an unsupported AES-CMAC key (`alg=4`,
index 4, kernel EINVAL), causing AP timeout. `wifi-sec.pmf=1` disabled PMF
while retaining WPA2/CCMP and AP activated. Both generated AP profiles now
include the fix. Do not alter station security or flash firmware for this.

Actual AP, DHCP worker, forwarding filter and LAN login HTTP 200 passed.
**Owner confirmed entering the setup page on a phone through the setup AP.**
Fresh scan found three networks and returned AP in 14 seconds. A nonexistent
network handoff returned AP in 33 seconds. The setup form supports scan-list
selection and manual SSID; selection does not submit until Save. A second
working Wi-Fi and successful reboot handoff are now verified. A full cold
power-only/no-known-network boot remains a separate acceptance check.
The installed driver advertises no concurrent STA/AP combination.

## Validation and next steps

Full suite: 379 passed, 1 Windows symlink-privilege skip. Run appropriate
checks after final refinements, deploy matching source and update results.
Device backups: `/var/lib/openstick/deploy-backups/home-20261114/`.

Keep the owner's working second station/radio choices and setup recovery
enabled. Investigate the older router separately if requested; no known
parameter-level fix is established for it. Remaining acceptance includes a
cold power-only/no-reachable-saved-network boot and sustained operation.
No SIM data activation merely to test local provisioning.

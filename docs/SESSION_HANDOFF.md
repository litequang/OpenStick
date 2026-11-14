# Handoff — 2026-11-14, home machine

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

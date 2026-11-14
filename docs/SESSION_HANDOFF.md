# Handoff — 2026-11-14, home machine

Branch `codex/uz801-v32-postmarketos`. No merge,
release, flash or partition changes. Earlier company shutdown notes are
historical. USB is currently powered and accessible.

**Latest blocker:** correct-credential AP → station handoff failed. A normal
reboot and isolated WLAN/WCNSS resets did not yet resolve HAL join/config-BSS
errors. Do not claim provisioning is complete. The owner now requests a
single reboot after Save, followed by saved-network attempts before AP.
See [detailed continuation](AI_CONTINUATION.md) for evidence and exact work left.
Before push, original station keyfile was restored, setup AP was active and
enabled, and no setup transaction was pending. Station Internet was not active.

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
SIM AP/data is preserved. Wi-Fi handoff is queued durably and processed after
the HTTP response; failure restores AP and a prior same-SSID keyfile.

Real hardware fix: optional PMF tried an unsupported AES-CMAC key (`alg=4`,
index 4, kernel EINVAL), causing AP timeout. `wifi-sec.pmf=1` disabled PMF
while retaining WPA2/CCMP and AP activated. Both generated AP profiles now
include the fix. Do not alter station security or flash firmware for this.

Actual AP, DHCP worker, forwarding filter and LAN login HTTP 200 passed.
**Owner confirmed entering the setup page on a phone through the setup AP.**
Fresh scan found three networks and returned AP in 14 seconds. A nonexistent
network handoff returned AP in 33 seconds. The setup form supports scan-list
selection and manual SSID; selection does not submit until Save. Automatic
fallback/successful handoff and final power-only boot are checked separately.
Driver cannot run simultaneous STA/AP.

## Validation and next steps

Full suite: 374 passed, 1 Windows symlink-privilege skip. Run appropriate
checks after final refinements, deploy matching source and update results.
Device backups: `/var/lib/openstick/deploy-backups/home-20261114/`.

Finish setup fallback/handoff checks, restore the
owner's station/radio choices, leave setup recovery enabled, report remaining
limits. No SIM data activation merely to test local provisioning.

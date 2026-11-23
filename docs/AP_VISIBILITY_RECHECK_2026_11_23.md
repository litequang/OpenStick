# AP visibility and normalized visible-profile validation — 2026-11-23

The owner's phone reacceptance after the SIM recovery fix failed: Wi-Fi was
absent or could not be joined. Do not retain the prior pending phone test as a
PASS, or infer AP reachability from SIM-bound Internet and local AP-active state.

## Physical observations and bounded diagnostic action

Two requested fresh Windows broadcast scans found nearby APs but neither the
USB's saved SSID nor its current BSSID. Comparisons used private values only in
memory; no SSID/MAC/raw scan was logged or committed. The USB still reported the
owned shared AP, wcn36xx driver, supplicant completed, channel 11 / 2462 MHz,
20 dBm, power saving off, hidden disabled, MaxNumSta=10 and isolation=0. Actual
supplicant network settings matched the saved SSID with ignore_broadcast_ssid=0,
mode=2 and frequency=2462; rfkill was unblocked. SIM-bound Internet worked.

Kernel messages were matched on the device against public Linux v6.12 format
strings; only static templates/counts/ages were exported. Recorded categories
included old BSS/STA-context-not-found and several spurious-TX-completion messages.
No firmware-crash, HAL timeout or beacon/start-AP failure was established. These
messages do not identify the cause of missing over-the-air visibility.

One bounded down/up of the existing AP was performed under network/modem locks,
after pending/power checks. The first attempt acquired no lock and stopped with
NETWORK_BUSY before a receipt or mutation; acquisition was then retried, without
retrying a submitted uncertain network operation. AP restart completed, preserving
saved identity/security/configuration/radio, live SIM connection and USB admin.
No modem reset, cellular activation, Windows adapter change or device reboot.

The immediate ordinary scan still did not find the AP. A later directed SSID
scan did; a subsequent ordinary native BSS scan received a fresh Beacon or Probe
Response after the scan request, matching the saved SSID/current BSSID, channel
11, RSSI -38 dBm and beacon interval 100 TU. This proves a current over-the-air
response, not continuous beaconing, phone association or DHCP/Internet acceptance.
No radio power-cycle was needed or performed. Phone reacceptance is pending.

Microsoft documents the native BSS [host receive timestamp and frame source](https://learn.microsoft.com/en-us/windows/win32/api/wlanapi/ns-wlanapi-wlan_bss_entry).
The returned network list alone may contain cached entries; compare receive time
against scan request before claiming a new frame. Do not add blind periodic AP
restarts based on local active state, zero associated clients or one missed scan.

## Separate confirmed software defect

The real NM-rewritten AP keyfile had no hidden key, while the saved setting and
effective supplicant both selected visible SSID. OpenStick required an explicit
hidden key before AP activation and therefore rejected this legal normalized
profile with AP_OPTIONS_INVALID. Copying a normalized setup profile into the
shared AP or replaying it could consequently fail before any AP activation.

NetworkManager defines [hidden as default FALSE](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html).
Validation now treats an omitted hidden key as false. A saved hidden=true with
the key absent still fails closed; malformed values, mode/UUID mismatches and
isolation validation remain rejected. Activation does not rewrite profiles or
weaken saved security, client-limit or consent checks. No automatic AP restart,
firmware/kernel change or new polling thread is introduced.

Regression tests cover both owned AP types, saved visible/hidden choices and
adoption of a normalized setup profile while preserving the cellular profile.
This is a correction for repeat activation/boot compatibility, not proof that
the missing default key caused the already active AP to become invisible.
CI, installation and final observations are recorded only after execution.

Final local complete suite: **907 PASS, two Windows skips, exit 0**. The first
run had one new-test fixture failure (no existing cellular profile had yet been
created); its setup was corrected to establish that profile before testing its
preservation. No product assertion or existing test was removed.

## Installed result and remaining acceptance

Source **`0026828298f76085de86120c7b6daa63d525be65`** was installed after
[push CI](https://github.com/litequang/OpenStick/actions/runs/45098027481) and
[PR CI](https://github.com/litequang/OpenStick/actions/runs/45098034225) passed,
including Windows EXE checks. One reviewed Python file was replaced, with a
private checksum-verified source backup. Only both portals and the existing
startup worker restarted; no additional AP transition, firmware/kernel update,
radio power-cycle, modem reset, reboot or package removal during installation.

Installed validation accepted the real normalized visible-AP keyfile (hidden
absent). The validation probe replaced activation/firewall transports in its
short-lived process; this is validation against the real file, **not** another
physical AP activation or cold-boot acceptance. Unit tests establish rejection
of the missing key when saved hidden=true. Do not conflate these results.

Three ordinary native scans about 20 seconds apart each received a new matching
Beacon or Probe Response after its request, RSSI between -37 and -54 dBm. Another
ordinary scan after source installation still received a fresh matching frame
at -38 dBm. This is a short observation window, not long-term AP stability.

Read-only follow-up observed one authenticated/authorized/associated station,
no blocked client, shared DHCP lease records and a successful fixed public-name
query through the AP DNS. These are not proof that the owner's phone successfully
opened a public site with its own mobile data disabled. The owner has not yet
answered the new phone reacceptance question; the earlier phone result was FAIL.

Final 14 installed-source hashes, permissions and 721 protected owner files
matched; network/routes/firewall/DNS/gadget/services matched this installation's
snapshot. SIM-bound Internet, USB admin, live modem-counter usage, valid v2 usage
checkpoint and idle operation gates passed; storage synced. No runtime/private
identity/credentials were committed. The cause of intermittent AP invisibility
remains **UNVERIFIED**; do not describe this compatibility fix or manual diagnostic
restart as a permanent firmware/driver fix.

## Owner follow-up: association succeeds, administration and Internet FAIL

The owner answered the new test: the phone can join Wi-Fi, but neither the
administration page nor Internet works. This explicitly supersedes the pending
acceptance above; **phone end-to-end acceptance is FAIL**.

Further diagnosis preserved the running AP/session, without source deployment,
network/firewall mutation or another AP restart. One authenticated/authorized
station had an unexpired matching lease in the expected AP subnet. The actual
Wi-Fi-bound listener answered GET /login with HTTP 200 from an interface-bound
local probe. That tests the listener, not traversal of the phone's Wi-Fi link.
Input rules allow wlan0 DHCP, TCP/UDP DNS and TCP 8765 (wildcard interface matches
were evaluated, not mistaken for missing rules); forwarding/NAT rules are present,
no client is blocked, and the AP DNS answers a fixed public-name query.

A 35-second passive header-only observation saw SIM traffic and 22 outbound AP
ARP requests, but no incoming AP frames/client IP traffic and no change in that
station's RX/TX byte counters. No packet/content/identity file was saved. Two
bounded local ICMP probes to the matching leased client did not receive replies;
the route selected wlan0, but ARP did not resolve to the associated station.
An existing lease and an associated row consequently do not prove usable IP
connectivity. The limited capture did not overlap a confirmed user action.

The phone's current actual IP/gateway and the exact result of opening
http://192.168.8.1:8765/overview have been requested. Without those observations,
the negative traffic result cannot distinguish a stale/offline association,
client IP/routing behavior and a stalled Wi-Fi data path. Do not label a modem,
firewall or driver root cause, weaken rules, or add blind resets from this alone.
The first diagnostic helper failed before capture because minimal BusyBox ip
lacks JSON neighbor output; it was corrected to use the existing safe text
fallback, then the 35-second observation completed. No product code was changed.

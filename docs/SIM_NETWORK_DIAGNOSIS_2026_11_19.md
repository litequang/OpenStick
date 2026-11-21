# SIM data and misleading serving-network display — 2026-11-19

## 2026-11-21 AP visibility follow-up: restarted existing AP

The owner then reported that the USB Wi-Fi network was absent from the phone's
network list. Fresh device reads still showed AP mode, channel 6 / 2437 MHz,
20 dBm, power save off, supplicant completed and hidden SSID disabled. The
current profile SSID matched the saved owner SSID. These local states alone
did not prove over-the-air visibility.

A fresh Windows WLAN scan was explicitly requested through Native Wi-Fi APIs,
without changing the Windows connection or network settings. It found 13 nearby
networks but not the USB SSID (compared privately in memory; no SSID/BSSID or raw
scan output logged). The earlier cached `netsh` list was not treated as fresh
scan evidence. This reproduced the visibility issue on a second client.

One bounded down/up of the existing owned AP profile completed under the normal
network/modem locks, after power/pending-trial checks. No new profile, password,
radio preference, cellular activation, reboot or service/package change was
introduced. Existing SSID/security/channel settings and saved configuration
hashes matched after the restart; the cellular connection and bound SIM Internet
check were preserved, and USB administration remained available.

A subsequent fresh Windows scan found 9 nearby networks **including the USB
AP**. Thus the restart restored Windows scan visibility. The owner subsequently
confirmed the phone could see the AP and access the Internet, in response to
the instructed test with phone mobile data disabled. This is owner-confirmed
physical phone acceptance of SIM-to-Wi-Fi Internet after the restart, not a
synthetic test. The cause of the stalled visibility and its recurrence remain
unverified. Do not call the restart a permanent driver fix or introduce automatic
AP restart merely because a local AP status says active.

An additional advanced-settings discrepancy remains separate: the saved client
limit is 10, whereas the running supplicant reports MaxNumSta=128. This restart
preserved the existing profile rather than applying/retesting advanced options.
Do not claim physical enforcement of hidden/client-limit/isolation from this
visibility test. No product code was deployed; USB source remains `747f49c`.

## Follow-up: 2026-11-21, read-only device inspection

The owner reported that SIM data plus hotspot still did not provide Internet.
Fresh reads in this session found home MobiFone LTE registration and an active
cellular bearer. Both fixed HTTPS endpoints returned 204 using provider DNS and
system DNS; two public IP ping checks succeeded. The default route used the SIM.

The shared AP and IPv4 forwarding were active. Its DNS answered the fixed public
query; a valid shared-network DHCP lease existed. No client was blocked. The
base firewall explicitly permits `wlan*` and established return traffic; do not
mistake its default DROP policy for a missing AP allow rule. NetworkManager's
AP NAT/forward rules and the separate USB-sharing rules were present. No
forwarding/firewall repair was justified by these reads.

Initially one station was associated; a later read found none. A bounded raw
packet counter (no capture file, addresses, names or payload exported) observed
SIM input/output and AP output but no client IPv4 request in that window.
That does not establish successful client Internet access or explain why the
phone disconnected. The owner was asked to reconnect and test the management
page and a public website with phone mobile data disabled. No network/radio,
package, service or persistent device change was made in this follow-up.

Additional 19 November evidence exposed an important inconsistency: core modem
State=11 (connected), but 3GPP registration=2 (searching) and another carrier code.
Thus checking the core state alone is insufficient. The source correction now
cross-checks 3GPP registration in both modem status and Quick Settings, including
unknown/failed reads. It blocks falsely registered status and action readiness
without changing radio preferences, retrying registration or opening data.

Final local suite: **815 passed, 2 Windows platform skips**, exit 0. The focused
modem/Quick Settings/header suite passed 106 tests. The earlier full-suite
MemoryError was a Windows host test-run failure, not a USB hardware result;
the later complete run passed. These source corrections are **not installed**
on the USB at this checkpoint; installed source remains `747f49c`.

## Observed on the connected UZ801 V3.2

- Local SIM home operator was MobiFone. Saved and actual radio modes both
  remained LTE-only. No band mask or saved radio preference was changed.
- Initially the modem was home-registered on LTE, but NetworkManager had no
  cellular IP, gateway or DNS. The AP remained active.
- One explicit data activation succeeded and passed a small HTTPS check bound
  to the cellular interface. It subsequently disconnected. This was not a
  successful sustained restoration or phone acceptance test.
- During loss of registration the modem reported other carrier names, including
  Viettel, with an empty operator code and idle/searching registration states.
  These observations do **not** demonstrate successful roaming registration.
- A later read exposed network rejection error 14, without a rejecting operator
  identifier. ModemManager defines it as packet service not allowed in that
  PLMN; the legacy GPRS name also applies to LTE. It does not identify the cause
  of the earlier disconnect or establish an account/coverage problem.
- A bounded explicit home-operator registration request had an unknown result;
  it was not repeatedly submitted. A subsequent request restoring automatic
  home registration completed and returned to MobiFone. No persistent network
  lock was added. One data request stopped before transmission with NETWORK_BUSY;
  a later explicit attempt completed.
- Later the modem had a connected, non-suspended bearer, cellular IPv4 and DNS,
  with no reported bearer error or kernel link error. Nevertheless, two small
  HTTPS endpoints timed out using both provider DNS and system DNS; two public
  IP ICMP checks also failed. Registration and a bearer alone are not Internet
  acceptance. End-to-end Internet remained unverified/unreliable at this point.
- Forwarding, the AP shared-network NAT and DHCP processes were present.
  NetworkManager, ModemManager and the radio worker were running. No reboot,
  modem service restart, package removal, firmware change, SMS or USSD was used.

Raw probes, receipts, addresses and runtime configuration stay in ignored local
artifacts or private device storage. This report contains no subscriber identity,
real SSID/MAC, password, message content or owner website details.

## Optimization comparison

The installed optimization from `06d151a` to `747f49c` did not remove services or
packages. Modem transport, quick data operations and network-policy logic were
unchanged. The startup loop gained bounded fixed-log retention; setup passive
reads and LED polling were reduced. Deployment restarted the portal and the
necessary setup/LED/startup workers. That comparison does not by itself rule out
all software defects, nor prove that the optimization caused this incident.

Startup recovery is a bounded boot replay. After its `done` receipt it does not
continuously reconnect a subsequently dropped cellular session. No new automatic
activation/retry loop is introduced by the display correction below.

## Display correction

Only publish `operator_name` as a serving carrier while the modem is registered,
cross-checking 3GPP registration rather than trusting core State=connected alone.
The header independently rejects carrier names from unregistered samples,
including cached samples from older servers. It labels that state **Chưa đăng
ký / Tìm mạng**, keeps previous signal readings explicitly stale, and does not
show an active 4G connection merely because an older sample used LTE. Confirmed
registered carrier changes still invalidate previous signal readings.

Validation: targeted modem/header suite **60 passed**, full suite **804 passed,
2 Windows platform skips**, both exit 0. Fixtures test stale/scanned carrier names
and navigation cache; they are not visual or physical-device UI acceptance.

## Remaining isolation work

Confirm whether this same SIM has working data in a phone at the same location,
with its actual Local plan/APN. Preserve the existing APN until there is evidence
to replace it; do not copy another carrier's APN or enable roaming as a guess.
If the SIM works there, compare one controlled USB data attempt and sanitized
registration/bearer/route counters. Investigate reconnection separately from
carrier-name presentation. Do not claim a permanent fix from a single 204 reply.

Primary references:

- [ModemManager network error definitions](https://raw.githubusercontent.com/linux-mobile-broadband/ModemManager/1.24.2/include/ModemManager-enums.h)
- [ModemManager 3GPP registration](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.Modem3gpp.html)
- [NetworkManager GSM settings: home-only and network-id differ](https://networkmanager.dev/docs/api/latest/settings-gsm.html)

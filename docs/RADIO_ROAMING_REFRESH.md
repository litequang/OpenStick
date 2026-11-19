# Roaming, LTE bands and background refresh — 2026-11-19

## Behavior

`/modem/network` places roaming and band selection beside 3G/4G modes.
Roaming OFF reads `Sim.OperatorIdentifier` (never IMSI or serving operator),
sets the owned GSM profile's `home-only=true` and `network-id`, then explicitly
registers that home PLMN. ON removes the PLMN restriction and requests automatic
registration. SIM home codes remain private in the existing root-owned NM profile,
not the API, logs or repository. A SIM/MVNO requiring another host PLMN may lose
service with this lock; allow roaming to recover. Changing SIM requires checking
and resaving the lock with data off before enabling data on the replacement SIM.

Roaming mutation requires idle cellular data, no setup/hotspot trial or automated
policy, ready unlocked SIM and idle USSD. It holds network then modem locks.
It never stops AP, Wi-Fi, USB or an active bearer. Registration failure/timeout
restores the profile and reports unknown; no registration retry/automatic data-on.
APN application and profile recreation preserve an existing home lock.
The existing radio watcher attempts boot/airplane replay at most three times;
active data can defer replay. NM's persisted network-id also applies on activation.

Bands use typed `SetCurrentBands(au)` only. Automatic is MM BAND_ANY (256);
manual LTE filters retain supported non-LTE bands so existing mode fallback is
preserved. The Việt Nam group intersects B1/B3/B7/B8/B28/B41 with modem support;
it is a candidate filter, **not** a nationwide per-carrier deployment database,
band priority order, speed guarantee or live serving-cell readout. Other supported
LTE bands can be tried individually. Automatic remains recommended for coverage.
No mode/roaming/band selection is applied simply by opening a page or deploying.
Band choice is saved separately in private `radio-bands.json`, leaving radio.json
and the owner's current 3G/4G choice untouched. Watcher replays it after boot or
airplane cycles with a bounded attempt count.

## Refresh

Modem display now uses authenticated GET `/api/modem/status` with bounded
single-flight snapshots, instead of POSTing a shared action job every refresh.
Read-only modem status does not take the action mutex; mutations still take locks
and read fresh capabilities/SIM/USSD before acting. No display cache authorizes
an action. All existing Host/Origin/token/LAN login and power activity gates apply.

Header, Overview, Quick, setup and modem pages refresh at 60 seconds while visible;
setup/modem defer interval reads while editing a form, and Quick while a dialog
is open. Initial load, manual refresh, tab return (header/Quick) and action
completion still refresh. Receipt/operation polling remains fast during actual
operations, and SMS opt-in polling and the original Windows backup UI are unchanged.
Retained server samples render immediately; initial pending GETs use 1/2/4-second
backoff within the existing bounded read window, and the header schedules at most
one delayed follow-up. Transient GET failures also use that bounded window. Previously
known Quick/setup/modem values remain usable and marked old on failure; Quick
does not close the dialog or disable all controls just because a GET failed.
First visit with no trustworthy state still waits for a first sample. Real
mutations/pending trials/unknown previous-operation receipts still block conflicts.

## Evidence and limits

Read-only real USB observations before install: initial Quick HTTP 200 sample age
15.05 seconds (stale), then fresh after about one second; six GETs took 7–38 ms.
This does not establish the cause of every prior lockup. Code inspection identified
whole-panel invalidation after a failed/stale read, a persistent error banner after
successful recovery, and modem status reads sharing the action busy flag.
Actual supported band enums read: 5,10,31,33,35,37,38,50,68,70,71. No radio command
was used for that read. The original vendor firmware's UI source is absent from
this checkout; its exact refresh implementation has not been compared.

`verify_radio_refresh_browser.py` exercises four preview widths, editing while GET
is pending, draft preservation and opening Quick confirmation after a failed read,
with zero POST mutations. Synthetic tests cover typed calls, validation, private
home lookup, profile preservation, rollback/no retry and independent status jobs.
These are not physical acceptance of registration, roaming rejection, LTE
throughput, boot replay, mobile-device visuals or all past intermittent failures.

## Installation

Installed ten source/UI files on the real USB. The reviewed installed baseline
included the deployed UI branch's stale-display/backoff/header-follow-up changes
and settings-workspace wrappers beyond this checkout's development HEAD. Those
changes were preserved. The wrappers are conditional on the existing portal_asset
context, retaining compatibility with the development checkout's older shell.
No unrelated UI-branch file, FileGator or asset-cache infrastructure was replaced.
Before/after SHA-256 verified all ten installed files and served changed assets;
fresh modem/Quick GETs passed. Owner configuration/site/SSH/Tunnel hashes, network,
routes, firewall and boot ID compared unchanged. Only USB/LAN portal services
restarted; sync completed. Existing radio watcher was not restarted; new watcher
boot replay remains untested and will load on its next normal start.

Backup: `/var/lib/openstick/deploy-backups/radio-refresh-1795088058/source.tar.gz`.
Its private manifest records original and installed hashes. To roll back, restore
the archived files at `/opt/openstick`, remove the newly added `radio_network.py`,
and restart only openstick-wifi/openstick-lan. Do not remove owner runtime policy.
Final real Chrome verification: eight page/width combinations (Overview and SIM
network at 320/390/768/1280), zero POST requests, no JS errors or horizontal
overflow; new controls/options ready and existing settings workspace retained.
No real registration, band mutation, data activation, reboot or poweroff was sent.

Full suite before the final reviewed baseline integration: 792 PASS / one Windows
symlink skip; final affected modem/policy/telemetry tests 32 PASS. Settings preview:
24 layouts/interactions PASS, zero device operations. Focused radio/refresh preview:
four widths PASS with mocked data and zero mutations. Self-test, pip check, JS
syntax and diff whitespace checks passed. Source and reports are recorded together
on `codex/uz801-v32-postmarketos`; see Git history for the commit ID. No main merge
or release was performed. GitHub CI status must be checked separately.

Official references:
- [NetworkManager GSM settings](https://networkmanager.dev/docs/api/latest/settings-gsm.html)
- [ModemManager registration](https://www.freedesktop.org/software/ModemManager/doc/latest/ModemManager/gdbus-org.freedesktop.ModemManager1.Modem.Modem3gpp.html)
- [ModemManager frequency bands](https://www.freedesktop.org/software/ModemManager/doc/latest/ModemManager/gdbus-org.freedesktop.ModemManager1.Modem.html)
- [ModemManager enum values](https://github.com/linux-mobile-broadband/ModemManager/blob/main/include/ModemManager-enums.h)
- [VinaPhone 1800 MHz launch](https://baochinhphu.vn/nha-mang-dau-tien-chinh-thuc-cung-cap-dich-vu-4g-102211728.htm)
- [Viettel 2500–2600 MHz](https://v3.viettelfamily.com/news/thoi-su/viettel-dau-gia-thanh-cong-quyen-su-dung-tan-so-vo-tuyen-dien-bang-tan-2500-2600-mhz)

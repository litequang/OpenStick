# Handoff — 2026-11-14, home machine

## 2026-11-19 latest: consolidated AP and embedded FileGator installed

Installed source **`06d151aacec526ef9acf7562365b62a7b33d3bd5`**, same UI branch/PR
#7, no merge/release. Read [AP_AND_FILEGATOR_UI.md](AP_AND_FILEGATOR_UI.md).
One Phát Wi-Fi menu at `/setup/ap` now combines identity, fallback, connection
card, hotspot status and guidance. Old `/hotspot` and `/setup/recovery` redirect;
software without setup retains its standalone hotspot page. Legacy pending-trial
completion/rollback and all action APIs/confirmations remain. Embedded status
reads on open/refresh and polls only pending trials, avoiding another idle poll.

File manager automatically loads FileGator in a same-origin frame; optional
Mở riêng remains. Site changes require confirmation; inventory refresh preserves
the current frame. Only FileGator responses permit same-origin ancestors and
only wrapper URLs permit self frames; other portal pages keep DENY. Existing
LAN/Host/Origin/session/CSRF/fixed-root/chunk/ZIP guards are unchanged. No package
or FileGator upstream source was replaced. Read-only QA includes a FileGator
action allowlist and blocks file mutations before sending them.

790 local tests PASS/one Windows symlink skip, exit 0; Node/pip/self-test PASS.
Both final-source Windows workflows PASS, including EXE build/self-test/smoke:
[push](https://github.com/litequang/OpenStick/actions/runs/44485344869),
[PR](https://github.com/litequang/OpenStick/actions/runs/44485355793).
Preview navigation: 160 layouts/eight landscape/24 interaction checks PASS;
fictional metadata tests retain cancellation/no-replay and test delayed iframe
mount/site switching/no iframe reload on inventory refresh. These are fixtures.

Real USB at initial consolidated source `90a8cae`: 160 layouts/eight landscape
PASS, no JS error or attempted mutation. Final installed source: actual upstream
FileGator navbar loaded inside the frame at eight widths, no second login,
same-origin headers verified, both old AP URLs redirect correctly; nine FileGator
read requests, zero writes/power/network actions, no screenshot or trace saved.
Candidate browser asset override was tested before CI, then repeated against the
installed asset with override explicitly OFF. Vue replaces its initial root and
mounts after document load; early tests caught a false loading-error notice.
The final controller observes mounted DOM boundedly without HTTP/action replay.
Do not claim the two failed readiness checks were full device PASS.

Thirteen portal files then two one-asset corrections installed with private
checksummed source/metadata backups. Final independent verification: all 32 V4
source hashes/assets, 717 protected owner files, ownership/modes, network/routes/
firewall/DNS/gadget and service state match. Worker and usage advance, checkpoint
private/valid, 20 authenticated WLAN-bound GET routes and existing auth/USB-only
permissions PASS; no operation pending, sync done. No rollback/reboot, real file
write/upload/unzip, radio/data/AP/tethering/LED/SMS/USSD action or phone acceptance.
Public Tunnel's separately recorded 530 problem was not repaired or declared
working by this UI change. Unrelated untracked files remain untouched.

Owner now requests a whole-device performance/redundancy audit. Measure current
CPU/PSS/RAM/swap, daemons, polling and real read latencies, then propose savings
and tradeoffs; do not silently remove services or owner data for an audit.

## 2026-11-19 latest: dedicated child screens installed

Installed source: **`61125aa3dab81001232ab862679fe9bba669645e`** on
`ui/settings-parent-child-nav-20261119`, PR #7. No merge or release. Remote main
and development remain `3a459f6`. Read
[SETTINGS_CHILD_SCREENS.md](SETTINGS_CHILD_SCREENS.md). This supersedes V4's
hash-only child links and temporarily restored native website tabs.

Each Wi-Fi child, USB tethering, SIM usage and LAN administration has its own
URL and visible screen. FileGator mode renders only website metadata, a file
manager entry or domains; retired native upload/ZIP/editor controls and their
controller are absent. Native fallback without FileGator remains supported.
Shared network controllers retain hidden required DOM; unrelated saved-Wi-Fi/
client scripts are loaded only on their matching page. Existing action APIs,
locks, consent, revision checks, confirmation and uncertain-result rules remain.

788 tests PASS/one Windows symlink-permission skip, exit 0; pip/Node/self-test
PASS. Both exact-source Windows workflows passed, including EXE build/self-test/
smoke: [branch CI](https://github.com/litequang/OpenStick/actions/runs/44479868249)
and [PR CI](https://github.com/litequang/OpenStick/actions/runs/44479878037).
Chrome preview in each FileGator/native mode passed 176 layouts/eight landscape
cases and 24 existing interaction checks. Additional fictional metadata browser
fixtures cover four intercepted writes, cancel/no replay and usage schema/stale/
unavailable/missing data; these are not device mutation acceptance.

Chrome against the actual USB at `66b5850` passed 176 layouts/eight landscape cases at
320/360/390/430/768/820/1024/1280 CSS pixels: isolated child panels, one tree,
active links, no obsolete FileGator controls, no overflow or JS error. It sent
112 allowlisted read-only POSTs and no attempted mutation, power or file write.
No real screenshot, trace, SMS, private website/network content or identifier
was exported. No physical phone touch session or file operation was tested.

Final `61125aa` moves the shared Wi-Fi notice outside hidden child panels so
credentials/read/scan errors remain visible. This one-template correction passed
50 affected tests and the full CI. Preview navigation/interactions passed again,
including a denied-credentials fixture. On real USB HTML, all five Wi-Fi children
passed at 320/1280 pixels (ten layouts); an intercepted HTTP 403 produced a visible
error, no credentials were read from the device and no write was attempted.

Only USB/LAN portal services restarted; 20 source/template/asset files were
replaced, then the one-template correction, with checksummed private source/metadata backups under
`/var/lib/openstick/deploy-backups/ui-v4-*`. Independent verification matched all
28 V4 source hashes/assets, ownership/modes, 717 protected files and the active
network/routes/firewall/DNS/gadget. Source backup members verified. Power worker
heartbeat and usage samples advanced, private checkpoint remained valid, no
operation pending and storage flushed. WLAN-bound authenticated GETs reached
all 22 routes and preserved login and USB-only credential-management guards.
QA signed an ephemeral session in device memory using the existing key; this
is not password re-entry or a real phone login test. Temporary local QA cookies
are removed after verification; owner password/session keys remain unchanged.

The owner powered off/unplugged/replugged during final comparison of the older
`4cca1fa` installation. Its interrupted final comparison is not claimed PASS.
This install uses a new stable post-owner-action baseline, preserving current
tethering intent and terminal power receipts; no receipt or journal was cleared.
The owner's action is not our physical power-button acceptance. No reboot,
firmware/network/radio/AP/profile/data/tethering/LED/SMS/USSD or website mutation
was issued for this UI deployment; no rollback was needed or executed.

**Separate pre-existing connectivity issue:** public HTTPS returned Cloudflare
530 before and after this child-screen install, whereas the local Nginx website
returned HTTP 200. The recent Tunnel log contains `network is unreachable` and
no registration line in the sampled tail; this is not proof of a permanent
failure or a complete diagnosis. Service process running does not prove a
working Tunnel. Preserve current choices/configuration; do not silently enable
SIM data or switch Wi-Fi to make this unrelated check pass. Direct PC-to-WLAN
login probe is still unreachable from this PC; device WLAN-bound GETs work.

The sections below are historical and do not name the current installed source.

## 2026-11-19 latest: nonblocking telemetry installed and measured

Owner said to implement the performance improvements. Read
[PORTAL_TELEMETRY.md](PORTAL_TELEMETRY.md). Added single-flight asynchronous,
age-bounded display snapshots, GET Overview independent of the shared action
job, lazy services, independent connection updates, browser request coalescing,
bounded GET waits and refresh invalidation on enqueue/completion. Live backend
preflights/locks/consent/receipts are unchanged. Four HTTP threads per listener;
no new daemon, runtime dependency, interface or provisioning change.

781 tests PASS/one Windows symlink skip, exit 0; pip/self-test/JS PASS. Additional
browser checks include pending header vs independent metrics, lazy services and
editing before a late Wi-Fi response. Existing Quick/usage/power preview checks
are separate from real hardware acceptance. Installed source is
`461e913ca43f87e549a490472f4899a72d5af235`. Both
[development CI](https://github.com/litequang/OpenStick/actions/runs/44447183373)
and [main CI](https://github.com/litequang/OpenStick/actions/runs/44447183537)
passed, including EXE build/self-test/smoke. No real reboot/poweroff command is tested.

Five real pre-install Chrome runs: first data 7.640/17.951/21.103/12.766/14.359s,
median 14.359s; DOM median 0.281s. Five post-install runs: first data
1.752/0.156/0.148/0.157/0.155s, median 0.156s; DOM median 0.121s. Quick controls
median 14.371s before vs 0.168s after; first post-install run took 3.636s. Median
requests until ready fell from 16 to nine. Later runs reuse server samples fresh
within five seconds; these are not cold boots or fresh hardware reads in 0.156s.
No browser JavaScript errors. See the telemetry report for every run and limits.

Deployment plus independent verification matched all 13 source/UI hashes and
served assets, live GETs/age metadata, independent Overview metrics and running
ModemManager. Power was ready/IDLE, no queue/receipts; worker heartbeat and SIM
samples advanced, private checkpoint remained valid. Protected owner hashes,
active network, routes and firewall matched before/after; services ran and sync
completed. Only USB/LAN portal services restarted; startup/usage/power worker kept
running. No network/radio/data/AP/profile/gadget change, SMS/USSD, reboot or
poweroff. Rollback sources: `deploy-backups/portal-performance-*` privately.

Five groups of six concurrent GETs took 0.334–2.503s; Manage/CSS reached 2.478s.
Telemetry 503 denotes a pending sample. Do not claim every real response is under
one second; the blocked-producer sub-second result is a fixture. Samples became
fresh again after load. Ten-second resource sample: no swap-in/out/major faults,
about 165 MiB used zram, other swap zero; ten Python processes about 149 MiB summed
RSS (shared pages included), 5.2% of one CPU core. No RAM reduction claim.
Private timing/SSH helpers stay ignored; unrelated untracked files stay intact.
The sections below record earlier states, not the current installed source.

## 2026-11-19 latest: header power, service truth and performance audit

Owner requests correct ModemManager status, a power/reset menu on the status bar,
then a source audit of slow portal entry. The service is running/owns D-Bus even
though OpenRC status is false. Read-only `NameHasOwner` on the bus daemon now
drives this service's display; unavailable/failed bus reads are distinct from
stopped. No service start/restart is needed for this correction.

Header **Nguồn** exposes confirmed normal reboot/poweroff, with outside/other
icon/Escape close behavior. System keeps instructions and a shortcut; there is
one controller/ID set per page. No power action on opening, and no polling load
until the menu opens or a request is being observed. No factory reset.
772 PASS/one Windows symlink skip, exit 0; pip/JS checks PASS; preview Chrome at
four widths plus Overview/menu exclusivity/confirmation/cancel/unknown PASS.
**Installed source `045ff7e602dae886f9d14740ff32295aef1089f9`.** Both Windows CI
runs passed, including EXE build/self-test/smoke:
[development CI](https://github.com/litequang/OpenStick/actions/runs/44443159562),
[main CI](https://github.com/litequang/OpenStick/actions/runs/44443160070).
Deployment and independent verification matched all seven source/UI hashes,
real Overview header power controls and served assets. The real read-only
Overview job reports `services.modemmanager=true`. Power is ready/IDLE with
advancing heartbeat, no queue/receipts or real power commands. SIM samples still
advance and the private checkpoint remains valid. Owner file hashes, active
network, routes and firewall matched; services run and storage was flushed.
Only USB/LAN portal services restarted; existing startup/usage/power worker kept
running. No physical reboot/poweroff acceptance. Private rollback source backup
is under `deploy-backups/header-status-power-*`; preview process was stopped.

Read [PORTAL_PERFORMANCE_AUDIT.md](PORTAL_PERFORMANCE_AUDIT.md). Real USB and
headless Chrome baseline found DOM 0.123s vs first Overview data 9.157s; header
8.727s, overview job 11.158s; concurrent status calls delayed CSS/Manage ~3.7s.
Two synchronous HTTP threads, repeated header reads in header/Quick/Overview,
subprocess overhead and overlapping polling are evidence-backed bottlenecks.
Ten-second sample had no swap-in/out/major faults; used swap was zram, other
used swap zero. This is point-in-time evidence, not a p95/load certification.

Performance architecture experiments have been archived privately and removed
from the source for now. No cache/collector/HTTP-thread redesign is installed.
Do not confuse this update with implementing the proposed performance phases.
No radio/profile/data/route/gadget or board power change was made for the audit.
Private timings/resources/rollback helpers stay ignored; unrelated untracked
files remain untouched. Timing artifacts are private and not included in Git.

## 2026-11-19 latest: normal device power buttons installed

**Installed source `1d479fac99ffb11e7960d58e32f53d015378394f`; both branch/main
Windows CI passed.** [Development CI](https://github.com/litequang/OpenStick/actions/runs/44438576639)
and [main CI](https://github.com/litequang/OpenStick/actions/runs/44438576764).
Read [DEVICE_POWER.md](DEVICE_POWER.md). `/manage` links to `/settings/system`:
explicitly confirmed normal reboot/poweroff, five-second grace/cancel, deadline,
boot/worker-generation binding, durable receipts and no uncertain-command replay.
Existing API/file and background Wi-Fi/modem/quick jobs share a transition gate;
final preparation takes network/modem/site locks and checkpoints SIM usage under
its mutex. No force flags or arbitrary command endpoint. No power action on GET.
Windows backup app remains separate. Poweroff is OS shutdown, not cutting USB 5 V.

766 tests passed / one Windows symlink skip, exit 0; pip check/self-test/JS passed.
Four headless preview layouts and confirm/dismiss/cancel/disconnect passed.
Real init support and private temporary Linux file-lock/mock-dispatch fixture
passed. **No real power command has been run; no physical power-cycle PASS.**

The first transactional install failed its short HTTP-readiness window and
restored previous source/services. A second deployment with a longer readiness
window succeeded. Independent verification checked all 12 source/asset hashes,
Manage link, real System HTML/buttons/JS and authenticated GET-only power status:
ready, IDLE, heartbeat advancing. No live power queue or operation receipts exist.
SIM accounting samples still advance and its root-private checkpoint is valid.
Protected owner files, active network, routes and firewall matched before/after;
services are running and storage was flushed. Only portal/startup services were
restarted; no board reboot, radio/data/AP/profile or USB gadget action was made.
Private rollback source backup is under `deploy-backups/device-power-*`.

Physical reboot/shutdown completion, LED behavior and network restoration after
these buttons remain NOT_TESTED. Do not infer poweroff completion from HTTP loss,
do not test power automatically and do not replay unknown commands. No private
runtime receipts, backups or owner identifiers/credentials belong in Git.
Two unrelated untracked files (`docs/HYBRID_COMPATIBILITY_MATRIX.md`,
`hosting_launcher.py`) stay untouched. Preview process has been stopped.

## 2026-11-18 latest: SIM data accounting and Overview metric

**Installed source `69111ce`; both Windows branch/main CI passed.** Independent
source hashes, served card and real authenticated Overview API usage passed.
Collector timestamps advanced with no browser open; root-private checkpoint
validated, baseline identifiers excluded from public projection. Passive Linux
counter/atomic persistence fixture also passed and was cleaned. Deployment kept
owner hashes, network, routes, firewall and services; storage flushed. No reboot,
profile/data/AP change or deliberate SIM traffic generated. Cold-power replay,
real traffic byte accuracy and carrier billing comparison remain NOT_TESTED.
Private rollback source backup is under `deploy-backups/sim-usage-*`; runtime
results remain ignored. No owner identifiers or credentials belong in Git.

Owner requests passive SIM usage history and a metric beside existing Overview
statistics. See [SIM_DATA_USAGE.md](SIM_DATA_USAGE.md). One thread reuses the
startup worker process, independent of modem/network locks; one private writer,
RAM snapshot and fsynced minute checkpoints. No network/radio/probe action.
Counts aggregate all SIMs, not carrier accounts; no SIM identity is queried.
Today/month/session/lifetime counters expose only sanitized amounts/times; failure
and uncertain continuity remain explicit. Do not promise billing accuracy or
complete abrupt-power-loss accounting. No quota/data-off action implemented.
737 tests passed / one Windows symlink skip, exit 0; pip check/self-test and
headless preview at four widths passed. Real read-only preflight found a modem
with a connected NM data binding and readable counters, not SIM Internet PASS.
The installation record above supersedes the earlier source-only preflight.

## 2026-11-18 latest: AP client feature installed and API/filter fixture verified

Owner accepts Internet blocking while retaining Wi-Fi association/admin access.
Open `/setup#ap-clients` for inventory, block/unblock and the saved offline list.
Source/assets and protected owner hashes matched after deployment; real USB
authenticated API save/apply/readback/unblock with a fictional MAC passed.
Its temporary policy/filter were removed and base firewall verified restored.
Startup worker was restarted; final HTTP inventory read passed with it running.
Storage flushed; no reboot or AP/profile change. Final station count was zero;
**no real client packet enforcement, association-deny or SIM Internet PASS**.
See [AP_CLIENTS.md](AP_CLIENTS.md) for limits and physical acceptance still needed.
BusyBox lacks `ip -j`: bounded plain-neighbor fallback is installed. Read-only
inventory no longer waits on the no-SIM modem lock; writes retain that lock and
role races invalidate the sample. Full suite: 707 passed / one Windows symlink
skip, exit 0. Browser fixture preview 24 layouts/interactions passed previously.
Runtime policy, receipts, backups and private hashes stay off GitHub. Source
changes and CI must be handed off with actual commit/status, not implied by
this deployment record. Earlier source-only/deployment-pending notes are history.

## 2026-11-18 latest: AP inventory / Internet-by-MAC implementation

Owner authorizes implementation and installation. See [AP_CLIENTS.md](AP_CLIENTS.md).
This is connected-station inventory and routed Internet filtering, not association
ACL. Real read-only probe: AP active, iw available/readable, zero stations; no
expected supplicant control socket. Kernel NF_TABLES_NETDEV disabled, so netdev
was rejected after an actual dry check. Dedicated inet-forward rules passed dry
check. No base network/firewall changes were made during research. Saved filters
replay through the existing network-startup worker and shared AP hook; AP scan
rollback now also uses the common hook. Preserve previous installed state until
deployment verification is recorded; physical packet/client tests remain pending.
705 tests passed / one Windows symlink skip, exit 0. Browser preview 24 layouts
and client confirmation/cancel/block/unblock/disconnect interactions passed.

## 2026-11-18 latest: AP option code installed after explicit authorization

Owner explicitly requested install now and SIM testing later. Deployed source
`393ead1` after both branch/main Windows CI passed. Nine source/UI files installed;
independent SHA-256/protected-content/HTTP controls/API/served-assets/service checks
passed. Existing AP remains active, advanced settings remain not configured;
read-only new-module access to MaxNumSta/ApIsolate succeeded without property writes.
No manual SIM/AP/radio action, reboot, base firewall or network profile changes.
Existing saved data/radio/network choices retained. NM data-interface presence is
not a SIM Internet acceptance test. Do not claim physical Hidden SSID, client cap
or isolation PASS: no client association/peer tests have run.

USB transport stopped responding during staging; owner performed normal replug.
Small inline source transfers then succeeded. First installer HTTP readiness
failed and rolled back; subsequent guarded installation and separate verification
passed. Private backups: `/var/lib/openstick/deploy-backups/ap-options-*`.
Storage synced. Read [AP_ADVANCED_SETTINGS.md](AP_ADVANCED_SETTINGS.md); older
source-only notes below are historical. No Computer Use was used.

## 2026-11-18 latest: advanced AP options, source only, not deployed

Owner requests Hidden SSID, client limit and AP isolation completed and pushed
before installing anything on USB. Implemented `/setup` shared AP controls,
durable optional settings, profile propagation, pre-AP string MaxNumSta setter
and readback, bounded DBus errors/rollback and legacy-autoconnect bypass guards.
Every owned AP activation path uses the common hook, including new boot replay.
Legacy clients preserve previously saved options; polling does not erase drafts.
See [AP_ADVANCED_SETTINGS.md](AP_ADVANCED_SETTINGS.md) for implementation,
upstream evidence and physical acceptance. All three are software supported,
NOT HARDWARE VERIFIED. No USB connection, command, configuration, service,
installation, radio action, network change or reboot in this task. Installed
USB is still the previous network-startup fix; its cold-boot acceptance remains
separately pending. Do not mistake Git HEAD for installed device source.
680 pytest passed, one Windows symlink skip, exit 0. Chrome headless 24 layouts
and interactions PASS, including advanced settings draft/cancel/stage; Node,
self-test, pip check and diff check passed. All evidence here is offline/preview.

## 2026-11-18 latest: persist Quick Settings network choice, installed, cold boot untested

Owner reports unplug/replug reconnects station despite selecting SIM data + AP.
Read-only USB inspection confirmed active SIM/AP + saved data consent, but both
NM managed profiles had autoconnect=no and there was no manual Wi-Fi role replay.
Implemented [NETWORK_STARTUP.md](NETWORK_STARTUP.md): durable explicit selection,
new bounded boot worker, AP-first/delayed-SIM behavior, airplane/data vetoes,
existing locks, setup fallback guard and explicit setup-handoff precedence.
Successful Quick Settings actions save automatically; read/status/scan do not.
Full suite: 652 passed, one Windows symlink-privilege skip, exit 0; JavaScript
syntax and whitespace checks passed. Physical reboot acceptance remains pending.

Installed source SHA-256 matches; saved the currently working SIM/AP under its
existing consent and enabled the service at boot. Existing profile/website/Tunnel/
LAN/SSH/radio contents checked unchanged; storage synced. Owner needed to unplug,
so told them it was safe and did NOT reboot. **Cold-power/reboot replay remains
NOT_TESTED on hardware.** Do not claim full physical acceptance. Current live
AP/data before removal were confirmed; waiting/failure combinations are fixtures.

Private source/config backup: `network-startup-1794978346134489169/before.tar.gz`
under `/var/lib/openstick/deploy-backups/`. Transport stalled during staging;
some client operations ended with SSH/SFTP errors. Installation eventually
completed; final source/protected hashes and enabled/running service were checked
independently. Do not rerun the initial installer as if nothing was installed.
At next plug, test AP DHCP/admin and SIM-bound Internet before calling this PASS.
The older MM/cold USB DHCP issues and FileGator visual acceptance remain open.

## 2026-11-17 latest: installed upstream FileGator

Owner requested an existing GitHub panel. Installed stable FileGator 7.16.9
(MIT), source commit 40f29bf7b0bf2193cc111334a7ee17ce3413d2af. Read
[FILEGATOR.md](FILEGATOR.md). `/website` selects the site and opens FileGator;
the old file/upload controls are hidden while installed. Domains still use
OpenStick. Unzip uses the existing bounded publisher/journal internally after
upstream CSRF validation; no manual inspect step or second upload.

Pinned official 4 MB build + PHP 8.3 FPM on-demand/one worker + independent
Nginx loopback 127.0.0.1:8788. Dedicated non-login account has ACLs only on
public roots, original owners/content retained; old ACLs backed up privately.
The /files/<site>/ proxy inherits LAN login and Host/Origin guards, forwards
only the `filegator` cookie, retains upstream CSRF, and resolves roots server-side.
No backend admin APIs/arbitrary upstreams. Initial Alpine default group mismatch
was repaired; installer now explicitly creates/selects the dedicated group.

637 PASS / one Windows skip, exit 0. Actual private fixtures: 28,311,916 bytes
uploaded in 28 chunks, hash matched; unzip/download passed, unrelated file
retained; missing CSRF/traversal blocked. Fixture removed. No owner archive
published. Aggregate service RSS 26,036 KiB busy / 14,008 KiB idle.

Chrome reached FileGator without a second login; full four-layout/back-navigation
run did not pass. Website sometimes remained waiting for API; Windows ran out
of virtual memory too. Do not claim phone/LAN/full visual acceptance. No reboot
or cold-boot test. See remaining limits and boot status in FILEGATOR.md.

Only openstick-wifi/openstick-lan restarted. Source hashes/protected state/network
checked; no reboot, SIM/Wi-Fi/firewall/gadget/public Nginx/Tunnel changes.
Backup: `/var/lib/openstick/deploy-backups/web-panel-1794887804034494053`.
Earlier source: `web-panel-1794887567131205592` in the same parent. Two unrelated
untracked files remain untouched. MM/cold USB lease issues remain open.

## 2026-11-17 latest: fix false ZIP size error on 27 MiB uploads

Owner's 27 MB ZIP was reported as exceeding 128 MiB. Reproduced on the real
USB with a generated 28,311,692-byte ZIP: HTTP 413 before inspection. The
multipart decoder read buffer is 65,536 bytes; max_form_memory_size had been
set to that same value. A partial boundary retained from a binary chunk made
the next buffer exceed the bound, even for a small valid ZIP. A deterministic
128 KiB regression with a retained CR failed 413 before the patch.

Raised only multipart decoder/field headroom to 256 KiB; the streamed request
spill threshold remains 64 KiB, request envelope 129 MiB, ZIP cap 128 MiB and
file/site quotas unchanged. Transfer 413 now returns UPLOAD_REQUEST_REJECTED;
the browser reports a request rejection rather than claiming the selected ZIP
exceeds 128 MiB. True ZIP size checks still have their own ZIP_TOO_LARGE code.
625 pytest PASS / one Windows privilege skip, exit 0. New tests cover carry,
bounded form metadata/request envelope, true ZIP size error, and UI 413 wording.
Chrome demo's complete hosting interactions and twelve layouts still pass.

Installed and verified source hashes, protected owner state/network unchanged,
no reboot. Backup `/var/lib/openstick/deploy-backups/web-panel-1794885793308617038/`.
After installation the same generated 27 MiB ZIP returned HTTP 200 on the real
USB browser, inspection passed and extract button enabled. Cancelled extraction;
no fixture was published into the owner's website. Actual owner archive was not
read or published. Testing used only generated data and inspection.

## 2026-11-17 latest: fix ZIP picker routing and missing feedback

Owner reported ZIP upload had no visible response/extract button. The normal
picker previously queued ZIP as a regular static upload (blocked by extension),
while the dedicated ZIP card was below the normal uploader and errors were
only at the page top. Both pickers now route a single ZIP directly to automatic
inspection, never automatic publication. ZIP card is first, a toolbar shortcut
opens it, progress/error feedback stays by the upload workflow and the extract
button becomes enabled only after inspection. Changing destination invalidates
the preview. Mixed ZIP/regular selections are explicitly rejected. Blocked ZIP
paths return their entry name to the authenticated UI via textContent.

622 pytest PASS / one Windows privilege skip, exit 0. Chrome demo regression
passed normal-picker .ZIP, native ZIP error, cancelled extraction, HTTP 413 and
disconnect feedback/no automatic retry, plus the original twelve layouts and
multisite/file/upload/ZIP/download interactions. Synthetic Node fixture runs
the real asset's picker routing and confirms inspection-only and disabled
extract after errors. New API regression proves blocked-entry reporting and
no publication on rejection.

Installed web sources with hashes checked; protected state/active connections
unchanged, no reboot, only portals stopped/started after taking the site lock.
Backup: `/var/lib/openstick/deploy-backups/web-panel-1794882746777416009/`.
Real USB Chrome selected a tiny fixture ZIP in the normal picker: HTTP
inspection passed, extract enabled, cancellation sent no extraction request.
A blocked-entry ZIP showed its filename and disabled extraction. No owner
site file or domain was published, and no real ZIP extraction was requested.

## 2026-11-17 latest: multi-site web file manager installed

Pulled the standard branch fast-forward from a6e7754 to 1954eb2 (three commits),
then implemented the owner's new priority: multiple static websites/domains,
larger streaming uploads and ZIP extraction. See [panel guide](WEB_HOSTING_PANEL.md).
Website page now uses the website navigation section. New roots are independent;
main's directory and primary hostname are protected. Up to eight sites, ten
hostnames/site, 32 MiB/file, 128 MiB/ZIP, 256 MiB/site, 2,000 entries. JSON text
editor capped at 2 MiB; legacy /api/site remains compatible. Both USB/LAN
Waitress listeners now accept the upload envelope and spill request input to disk.

File manager supports folder navigation/search, create/edit/copy/move/rename,
confirmed file/subtree delete, streamed upload and download, folder ZIP export.
ZIP inspect is separate from publish, with archive hash and tree revision checks,
bounded metadata/data decompression, private staging/backups, I/O rollback and
durable interruption journal. Recovery requires explicit confirmation and refuses
later external edits. Multi-file publish is not atomic from Nginx's perspective.
Batch upload reports partial completion and never automatically retries unknowns.

Domain save changes private registry only. Explicit Apply generates a narrow
Nginx include and marked local-managed Tunnel ingress, preserves the default
server and original hostname, validates both, reloads Nginx/restarts Tunnel,
and rolls back on failure. Unsupported existing schema is blocked. DNS remains
UNVERIFIED and manual in Cloudflare; no DNS token or credentials exported.
No domain configuration was applied or DNS changed in this session.

Validation: 621 pytest PASS / one Windows symlink-privilege skip, exit 0;
Node syntax, packaged self-test and pip check PASS. Chrome memory demo passed
12 layouts and file/multisite/upload/ZIP/download/cancel interactions. Actual
USB Chrome read-only passed 12 layouts, no JS errors/overflow/mutating requests.
Actual USB temporary private fixtures passed independent roots, 2,097,169-byte
streamed upload, ZIP inspect/publish/export, copy/move; fixtures removed and
protected owner state unchanged. These are not maximum-size stress tests,
real power-cut tests, public DNS acceptance, or actual domain service reload.

Installed exactly eleven web-panel source/assets, verified all hashes; restarted
only openstick-wifi/openstick-lan. No network-worker restart, radio change, SIM
data, Wi-Fi switch, firmware operation or reboot. Website/Tunnel/Nginx/SSH/LAN/
APN/radio config hashes and active connections unchanged, source backup under
`/var/lib/openstick/deploy-backups/web-panel-1794880552473939180/`; sync completed.
Only web-panel files were deployed: do not assume the separately pulled
1954eb2 Quick Settings mode-cycling change was also installed on the USB.
Original unrelated untracked files remain untouched. Earlier MM and cold-replug
DHCP limitations remain open; owner asked to prioritize the hosting panel.

## Latest: named APN presets and conflicting legacy button cleanup

See [action audit](UI_ACTION_AUDIT_2026_11_16.md). Named APN save/edit/delete
is private metadata only; Apply separately updates the owned GSM keyfile,
under old active-data/AP/policy guards, never activates it. No SIM matching.
Registry is root-only, never exported with passwords. Do not overwrite it.
Legacy combined activation/APN form/data-off and setup start/restore-old-Wi-Fi
buttons removed. Pending trial keep/rollback remains conditional. USSD sends
through the confirmed form only, RAT selection lives in SIM settings.
Fallback setting has a new save-only action; existing setup reboot handoff
and original Windows backup UI are preserved. No network changes/reboot are
authorized merely by opening these pages. 580 tests pass / one Windows skip;
fixture browser checks passed. Multiple carrier/SIM data tests remain unverified.

## 2026-11-16 latest: Quick Wi-Fi, advanced APN and Overview entry installed

See [current report](QUICK_WIFI_APN_2026_11_16.md), including the new cold-replug
USB DHCP limitation. Root redirects to Overview; home is rightmost at all
dock widths. Popup handles automatic saved Wi-Fi, choosing saved/new networks,
explicit scans and disconnect. AP-down first scan returned empty on hardware;
bounded cache warm-up fixed two actual AP → saved-station tests. Final Wi-Fi
bound HTTPS passed. No new password login was exercised on the device.

Advanced APN lives at `/sim/apn`, linked from SIM/Manage. It saves only, with
auth, credential keep/replace/clear, IP family and roaming. Secrets are never
returned; NM keyfile parsing preserves normalized trailing password spaces.
20 offline NM roundtrips passed on USB, not SIM authentication. Owner removed
SIM mid-test; don't report subsequent SIM cases as hardware PASS. 573 pytest
passed / one Windows privilege skip; demo and actual read-only browser checks
passed. Actual root/dock/popup/APN tested at four viewport widths, no writes.

Final checkpoint: station Internet, data intent OFF, tether desired ON, no
network trial pending; critical site/Tunnel/LAN/SSH/radio hashes unchanged.
Windows retained an old 42-day management lease after the owner's replug:
no USB gateway/DNS and source-bound HTTPS failed despite active owned DHCP/NAT.
This is a new known limitation, not covered by earlier on/off reboot PASS.
Read the report before promising automatic cold-boot sharing. No PC reset,
manual renew, firmware/initramfs/gadget edits or reboot in this update.

Latest private deployment backup: `quick-validation-1794821201506118600`,
28 files, under `/var/lib/openstick/deploy-backups/`. Do not restore all
protected config blindly or overwrite the owner's later changes. Unrelated
untracked `hosting_launcher.py` and `docs/HYBRID_COMPATIBILITY_MATRIX.md` stay untouched.

## 2026-11-16 latest: installed Quick Settings, SIM and USB sharing tested

This supersedes the historical source-only/no-SIM checkpoint below. Owner
authorized real network changes and SIM data, then chose saved USB tethering
plus one normal reboot per toggle instead of any PC companion. No Windows
assistant was installed. Five shared tiles appear on Overview and `/quick`;
AP/data are independent and there is no separate SIM-sharing tile. AP-off
does not restore station Wi-Fi. Data-off keeps the AP, IPv4, credentials and
DHCP process; actual second-cycle continuity check passed.

Real SIM DNS/HTTPS bound to the cellular interface passed. Two data off/on
cycles, AP on/off and a mobile-disable/enable cycle passed; mobile enable alone
left data off, explicit data-on then passed 204. Owner confirmed phone AP
Internet and management with phone mobile data disabled. SMS/USSD were excluded
by the owner's latest choice. Saved/current RAT remains [8,0]; no APN guess.

USB sharing via both station Wi-Fi and SIM passed Windows source-bound HTTPS
204 and USB DNS. Final UI on/off now saves a durable intent and reboots once;
both actual reboot tests automatically added/removed Windows gateway/DNS,
without ipconfig renew, adapter reset or PC software. A boot worker and the
vendor-supported `/etc/unudhcpd.conf` hook select the owned DHCP/DNS service.
No vendor-dispatcher edit, gadget change or SIM activation at boot. Website
HTTP 200, Tunnel/portal services and Wi-Fi Internet returned. Only USB profile
connection.timestamp changed on reboot; functional settings were preserved.

Do not call the original ModemManager InProgress / “Bearer already being
disconnected” fault conclusively fixed. It was observed and one MM-only service
restart was performed with no active data; later radio recovery worked for
the owner. Recent cycles passed, but no upstream/root-cause patch is claimed.
DATA_CONNECT_FAILED is now explicit and fail closed, never a silent retry,
APN/RAT change or automatic modem reset. AP/data/tethering were enabled at the
successful test checkpoint; the owner continues testing. Read fresh state.

519 pytest passed, one Windows symlink-privilege skip, exit 0. Eight Chrome
demo layouts, HTTP without randomUUID, consent/Escape and cross-reboot token
renewal passed. Real Chrome handled the earlier actions; host virtual-memory
exhaustion crashed Chrome before the airplane-off POST. Finished that action
and explicit data-on through the same token/UUID API, not visual acceptance.

See [hardware report](QUICK_SETTINGS_HARDWARE_VALIDATION_2026_11_16.md) and
[usage/boot design](USB_TETHERING.md) for backup locations, boundaries and
unverified cases. No main merge/release/firmware change. Keep unrelated
untracked `docs/HYBRID_COMPATIBILITY_MATRIX.md` and `hosting_launcher.py` untouched.

## 2026-11-16: Quick Settings source only — NOT deployed

Owner first requested read-only audit, then explicitly asked to develop the
features and test with a SIM later. Owner confirms no SIM is currently fitted.
Read-only hardware evidence: six requested module hashes match USB baseline
`c704264`; station/USB management work; NCM gadget and Windows DHCP confirmed.
USB forwarding is zero, no NAT/default host route: management, not tethering.
Installed USB-sharing dispatcher rebinds UDC; do not blindly use NM shared.
Supplicant has MaxNumSta=128 and ApIsolate=0; neither is hardware acceptance.
Saved/current radio mode is now [8,0], not the older [12,8] observation.

New source adds `/quick`, explicit radio/data/local-AP actions, durable intent
and operation IDs, shared watchdog/legacy vetoes and data-off AP fallback.
498 pytest passed / 1 Windows symlink skip; Chrome memory-demo consent/Escape,
no-SIM and four viewport checks passed. Physical modem toggles, role changes,
SIM data and cold boot are untested. No install, service restart or network
change on the USB was performed. Source HEAD after this work is ahead of
installed baseline: do not assume `/quick` exists on the device. Review the
two Quick Settings reports before any deployment. Runtime evidence is sanitized
and ignored. Existing unrelated untracked files were preserved.

## 2026-11-16: settings UX review installed on the physical USB

Owner prioritized all settings and explicitly declined Computer Use. Used
source audit, Node behavior fixtures and Playwright/Chrome headless instead.
See [settings UX review](SETTINGS_UX_REVIEW_2026_11_16.md) for the source
references, actual bugs, changes and reproduction commands.

Added shared settings navigation and form styling; station Wi-Fi now uses the
existing direct-connect API in `/setup`, while setup AP retains the existing
one-reboot durable handoff. Added current Wi-Fi status, nearby feedback,
explicit transition confirmation, locked-button reasons, hide credentials,
policy draft protection and LAN duplicate-submit prevention. No backup,
firmware, modem/radio or network-worker logic was changed. New navigation
uses backend availability flags from the Flask context.

Validation: baseline 468 PASS / 1 SKIP; final 469 PASS / 1 Windows symlink
privilege SKIP, exit 0. Node syntax, packaged self-test and pip check exit 0.
Chrome preview: 24 layouts (six settings pages, widths 320/390/768/1280), no
horizontal overflow or JavaScript errors. Interaction tests cover rejected
consent, password error, disconnected polling/no POST replay, credential hide,
draft preservation and LAN mismatch/duplicate protection. These are synthetic
network tests, not proof of real network switching.

Eleven installed source/assets matched baseline `5ceead5` before deployment.
First install was rolled back automatically because the immediate HTTP probe
ran before the restarted server had opened its socket. Confirmed the old UI
was healthy, added readiness retries to the private deploy helper, then
installed successfully. Restarted only `openstick-wifi` and `openstick-lan`.
Eight USB HTTP checks and four service checks passed; all eleven installed
file hashes match. Protected configuration/profile/site/SSH hashes, active
connections and boot ID stayed unchanged. No reboot, Wi-Fi switch, SIM data,
SMS/USSD, hotspot trial or credential change was performed.

Post-install Chrome headless against the physical USB opened six settings
pages at 390 px with no overflow or JavaScript errors. Station connect and
policy/LED forms loaded successfully. Interception allowed only read-only
`status`/`profiles` POSTs; no mutating request was generated. A separate
numeric Wi-Fi LAN request still redirected to the login form, and the saved
LAN password configuration hash was unchanged. No phone login was repeated.

Successful deployment backup:
`/var/lib/openstick/deploy-backups/settings-ui-1794794151267590617/before.tar.gz`
SHA-256 `e82a9c305cd277a4aaa19bfe3ac2491aa03d7f0194ab714d15810838aee29fba`.
No real passwords, identifiers or messages are included in committed evidence.
Physical-phone visual acceptance and actual network-changing form acceptance
remain for the owner; do not perform them automatically.

## 2026-11-16: fix incoming mDNS query filtering on the real USB

Owner confirmed that the numeric station-IP management URL opened on a phone
while `openstick.local` failed DNS. Source-bound LAN HTTP reached the login
redirect for either exact Host. Avahi was registered as `openstick.local`;
LAN/USB/Avahi services were running and no setup/hotspot transition was pending.

Reproduced the server defect from the PC's Wi-Fi interface: multicast A queries
with TTL 1 and 64 timed out, while TTL 255 returned the correct station address.
The original `53_openstick_mdns.nft` required TTL 255 even for incoming queries.
Added a WLAN-only, exact `224.0.0.251`/UDP5353 accept rule without a query TTL
condition, retaining the old stricter rule. Repeated wire probes for all three
TTLs returned RCODE 0, matching transaction IDs and the correct WLAN address.

Backed up the original file under
`/var/lib/openstick/deploy-backups/mdns-query-1794792297396710055/`.
Installed file SHA-256:
`1324de292c0c1f0a68ae55889ba2c21dc60f29ef2d1b2e91b4641049d423c320`.
Full persistent nftables syntax check passed. Added only one live rule,
without flushing firewall state or restarting services. No radio, SIM data,
credentials, Wi-Fi profile, website, Tunnel or reboot change was made.

Focused LAN/auth/firewall regression tests: 11 passed, exit 0. Full suite:
468 passed, one Windows symlink-privilege skip, exit 0 (17.12 seconds). After
reconnecting phone Wi-Fi, the owner confirmed that
`http://openstick.local:8765/setup` opens by name on the LAN. Source fix:
`9cfc64648ba35df0d2d6974f21f2d57b7d724be4`. A client that uses only
ordinary router DNS remains a separate case; the current router rejected the
local name request. See [local management addressing](LOCAL_MANAGEMENT_ADDRESS.md).

## 2026-11-16: navigation and management UI V2 deployed on the physical USB

Commit `fddda78c51ad7f3f63167181a68eb18e486574f5` was fast-forwarded
onto the local `codex/uz801-v32-postmarketos` branch and deployed to the
physical device. Source validation: **467 pytest passed, 1 Windows symlink
skip**; JavaScript syntax and Python compilation passed.

Before installing, the four prior files were backed up as
`/var/lib/openstick/deploy-backups/home-20261114/before-portal-v2-fddda78-1794788421.tar.gz`
(SHA-256 archive: `07478bdeeb9ed90a6380c7666029e8399bbdd0f2c70c0575c158c0c3ed840952`).
Installed only `uz801_manager/hosting.py`, `static/portal.css`,
`templates/manage.html`, and `templates/portal_chrome.html`. Every
installed checksum matched the package manifest. Restarted only
`openstick-wifi` and `openstick-lan`, which remained started alongside
`openstick-hotspot` and `avahi-daemon`. Saved station connection,
station IP and no-pending-trial state remained unchanged. No device reboot
or SIM/hotspot/Wi-Fi mode operation was performed.

Physical USB listener responded HTTP 200 at `/manage`, `/setup`,
`/overview`, `/hotspot` and `/static/portal.css`. The deployed
`/manage` HTML contains the saved-Wi-Fi link, SIM group, LED shortcut
and preserved legacy `saved-wifi` anchor. Actual Wi-Fi LAN IPv4 access
redirected unauthenticated `/manage` and `/hotspot` to `/login`
(HTTP 302), while `/login` returned HTTP 200. Authentication password
was not used or changed.

**Local-name diagnosis:** On the PC with the USB cable connected, normal
`openstick.local` resolution selects the USB-only address, so that test
does not prove the Wi-Fi path. From the PC's actual Wi-Fi interface, a
proper mDNS query with TTL 255 received an answer from the device's WLAN
IPv4 address and did not include the USB address. The home router's
ordinary unicast DNS returned `NXDOMAIN` for `openstick.local`.
Consequently clients using only that router DNS may still fail; either
client mDNS support or a router-side local DNS record is required.
Android phone acceptance on the home LAN remains unverified. No router
DNS or client settings were changed.

## 2026-11-15: Wi-Fi setup management UI redesigned and deployed

The real USB `/setup` portal now has two prominent Wi-Fi panels: **USB joins
a Wi-Fi network** and **USB broadcasts Wi-Fi**. The latter edits the one
shared SSID, password and channel for both recovery/setup AP and SIM Internet
sharing. Form labels, scan action, password reveal controls, save actions,
warnings and recovery guidance are grouped clearly; advanced setup-AP
controls are collapsed. Existing routes, HTML IDs and backend operations are
preserved. Desktop has two columns, and small screens stack the panels.

Source checks: **465 passed, 1 skipped** (Windows symlink privilege); focused
setup checks **36 passed**; JavaScript syntax, fixture and diff checks passed.
Local Chrome previews at 1280, 390 and 320px had no horizontal overflow; those
mock previews do not constitute Android/iOS physical acceptance.

Live deployment installed only `templates/setup.html`, `static/setup.js` and
`static/portal.css` after verifying baseline SHA-256 and staged checksums.
Automatic rollback and a three-file archive were prepared:
`/var/lib/openstick/deploy-backups/home-20261114/before-setup-ui-1794751001.tar.gz`.
Restarted `openstick-wifi` and `openstick-lan` portal services only. Checks on
the real USB passed for installed hashes, five HTTP 200 endpoints (`/setup`,
`/hotspot`, `/overview`, and the two static assets), and all four OpenRC
services (Wi-Fi, LAN, hotspot, LED) started. `wlan0` stayed connected to the
same NetworkManager profile, and neither hotspot nor setup had a pending
trial. No reboot, SIM activation or Wi-Fi configuration change was made.
Owner phone visual/touch acceptance is still pending.

The follow-up advanced-control UI was installed on the USB in a second
deployment. Instead of four large always-present buttons, the expanded section
shows two compact control rows: automatic recovery AP and manual setup AP.
Each row has a live status badge and only the action applicable to that state.
The synthetic JavaScript fixture exercised enable/disable/start/stop, including
badge transitions and button visibility; suite remained 465 passed, 1 skipped.
The second deployment validated installed SHA-256, successful portal service
restarts and `/setup` and static assets with the new control selectors. It
checked that the Wi-Fi profile did not change and no trial was pending. A
transient connection refusal immediately after restarting the portal cleared
within the script's retry window. Backup before this second deployment:
`/var/lib/openstick/deploy-backups/home-20261114/before-setup-ui-1794751697.tar.gz`.
Physical phone visual/touch confirmation remains pending.

## 2026-11-15: LED style gallery deployed without changing saved LED rules

Merged `ui/led-style-gallery-20261115` into the active
`codex/uz801-v32-postmarketos` branch. The `/settings/leds` page now offers
12 three-channel binary LED styles and four draft-only theme packs for all six
network roles. Previewing or selecting a style never writes to the device;
the existing explicit Save action is required. Current saved LED rules were
left intact, as was the existing `openstick-led` worker implementation.

Source verification: **465 passed, 1 skipped** (Windows symlink privilege)
across the full suite; **34 LED tests passed**. Real USB deployment installed
only `static/leds.js`, `static/portal.css`, `templates/leds.html`, after checking
all three old-file SHA-256 hashes. Backup archive (three files):
`/var/lib/openstick/deploy-backups/home-20261114/before-led-gallery-1794748543.tar.gz`.
Only the Wi-Fi and LAN portal services restarted; LED worker did not restart.
LED, Wi-Fi, LAN, hotspot OpenRC services all reported started after deployment;
installed file hashes all matched the staged manifest. The LED page, both
new static assets, `/setup`, `/hotspot` and `/overview` each returned HTTP 200.
The WLAN active connection, saved LED configuration hash and absent pending
network trial state were unchanged. There was no radio/SIM change or reboot.

Visual/optical verification of the style cards and actual blink timings on
the owner's phone/USB remains open. Three independent `max_brightness=1`
channels cannot provide smooth 24-bit RGB effects. Refer to
[LED Style Gallery](LED_STYLE_GALLERY_2026_11_15.md) for full behavior and
device limitations.

## 2026-11-15: one shared Wi-Fi identity deployed to the real USB

Installed the single Wi-Fi identity control for both setup/recovery AP and
SIM-backed Internet hotspot. `/setup#usb-ap-settings` edits the shared SSID,
password and 2.4 GHz channel; `/hotspot` links to that control and retains the
separate SIM APN settings. Saving the identity stages it for the next AP
activation, including when a SIM hotspot is currently active; it does not
disconnect the running AP or activate cellular data. A pending network handoff
blocks this edit to preserve rollback state. The hotspot start flow uses the
shared identity and the existing explicit SIM consent/confirmation.

Deployment source validation previously completed: **465 pytest PASS, 1 SKIP**
(Windows symlink privilege), plus JavaScript syntax and `git diff --check`.
Seven modified portal files were checksum-verified against the live predeploy
baseline and installed under `/opt/openstick/uz801_manager/` with backup
`/var/lib/openstick/deploy-backups/home-20261114/before-shared-wifi-1794707861.tar.gz`
(archive contains all seven prior files). Restarted only the `openstick-hotspot`,
`openstick-wifi` and `openstick-lan` OpenRC services; all reported started.
Installed SHA-256 checks passed for all seven files. USB Ethernet HTTP `/setup`,
`/hotspot`, `/overview`, `/static/setup.js` and `/static/portal_nav.js` returned
200. `wlan0` remained on the same predeploy NetworkManager connection,
`openstick-64c2ad14edc821c1`; there were no hotspot/setup pending trials.
No reboot, radio-mode change or cellular activation was performed. Browser
visual acceptance and changing shared Wi-Fi credentials on a physical phone
remain for owner testing; HTTP status does not prove end-to-end Internet.

See [shared Wi-Fi deployment](SHARED_WIFI_2026_11_15.md) for file hashes,
deployment details and a minimally disruptive manual acceptance sequence.

## 2026-11-15: setup AP → SIM Internet sharing without changing Wi-Fi credentials

Installed the smart hotspot handoff in the actual UZ801 V3.2 USB portal. The
owner's existing setup AP stays up until a consented `/hotspot` Start operation
has verified SIM-bound Internet access; the portal then uses the setup AP's
SSID, key and radio configuration for the SIM-backed AP, preserving
`192.168.8.1:8765` and the `openstick.local:8765` management URL. Wi-Fi may
briefly disconnect as the AP changes mode. The user must reconnect and Keep
the session within five minutes, or the NetworkManager checkpoint/worker tries
to recover the setup AP. Stop also restores the previous private SIM hotspot
configuration and setup-AP services. No simultaneous station/AP is attempted.

The change also makes read-only state available after reconnection to another
portal listener, without interpreting an interrupted Start POST as success or
automatically resending it. It keeps the explicit SIM charge warning/consent.
The source suite passed **448 tests, 1 Windows symlink privilege skip**, plus
JS syntax and diff checks. Hardware deployment backed up the previous three
files to `/var/lib/openstick/deploy-backups/home-20261114/` as
`before-smart-hotspot-1794703089.tar.gz`, installed only `hotspot.py`,
`hotspot_web.py`, `templates/hotspot.html` in `/opt/openstick/uz801_manager`,
and restarted only `openstick-hotspot`, `openstick-wifi`, `openstick-lan`.
Each restarted service was healthy; `/hotspot`, `/overview`, `/setup` returned
HTTP 200; WLAN still used the setup UUID and no trial was pending. No reboot,
Wi-Fi mode change or SIM data activation was used for this deployment check.
**The complete phone → SIM Internet → Keep → Stop flow is NOT yet verified.**

See [smart hotspot report](SMART_SIM_HOTSPOT_2026_11_15.md) for installed
hashes, recovery boundaries, rollback and the owner test sequence. Continue
to preserve website, Tunnel, credentials, saved Wi-Fi and radio choice.

## 2026-11-15: keep status strip and Overview readable across page navigation

Installed the display-only session cache on the real USB. Every page restores
the most recently measured header Wi-Fi, carrier and signal readouts before its
first asynchronous `/api/header` fetch. Overview likewise restores measured
system, Wi-Fi, SIM and service readouts before refreshing in the background.
Both still update periodically, preserve the last reading on transient errors,
and mark restored data as stale until the next successful sample. Initial
visits without a cached sample may still show waiting placeholders.

Cache entries live in the browser's `sessionStorage`, expire after eight hours,
are scoped by the LAN session where present, and include only explicitly
selected display fields. No raw modem payload, subscriber ID, Wi-Fi password,
session credential or CSRF token is persisted in the cache. Signing out clears
the relevant display entries. This does not convert document navigation to
client-side routing; a live browser/mobile visual acceptance check remains.

Source verification: **436 pytest passed / 1 Windows symlink permission skip**;
the synthetic full-page navigation test checks that values are already restored
while both API requests are pending. The USB initially had no pending hotspot
or setup trial; both installed source files matched their expected baseline
hashes. Deployment updated **only** `static/portal_nav.js` and
`templates/overview.html` under `/opt/openstick/uz801_manager`, with a network
lock and no reboot or network-mode change. `openstick-wifi` and `openstick-lan`
restarted successfully; real USB HTTP subsequently served the expected JS
content and `/overview` after a brief service-start delay. Backup:
`/var/lib/openstick/deploy-backups/home-20261114/before-dashboard-cache-1794680646.tar.gz`.
Restore that archive at `/opt/openstick` and restart the two portal services to
roll back. Phone visual inspection remains for the owner.

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

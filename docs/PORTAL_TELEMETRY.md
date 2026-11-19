# Nonblocking portal telemetry — 2026-11-19

Opening Overview now uses read-only GET snapshots instead of creating an
`/api/wifi` job and polling its shared operation result. The original job APIs
remain for existing clients and explicit actions. Windows backup behavior is
unchanged. See [the performance audit](PORTAL_PERFORMANCE_AUDIT.md).

## Display data and actions

- `telemetry.py` maintains one in-flight producer per source, per portal process.
  Header, Overview and Quick Settings have a five-second freshness window and
  30-second maximum retained age. Services use 30/120 seconds and are only read
  when the technical services panel is open. Expired reads return 503 with
  `STATUS_PENDING` and `Retry-After: 1`; retained results have explicit age/stale
  metadata. A failure never resets the old sample's timestamp or becomes zero.
- All authentication, Host/Origin/token and LAN-session checks run before cache
  access. No global HTTP cache, identity export, new daemon or persisted telemetry
  file is introduced. The source callbacks remain bounded read-only operations.
  One blocked source cannot create an unbounded queue or occupy an HTTP thread.
- Dashboard system metrics do not wait for Wi-Fi, modem or service inspection.
  Connection/signal rows update independently through the shared header result.
  The header and mode chooser share the same browser request; duplicate status
  subprocesses are coalesced briefly in `LocalWifi` with separate data/run locks.
- Browser retries apply only to four allowlisted display GET endpoints. Each
  request has a five-second timeout and the pending/stale wait has a nominal
  15-second deadline. It never retries a mutation, credential endpoint, receipt,
  SMS, USSD or power request. Existing consent and operation IDs remain intact.
- Successful action enqueue and worker completion invalidate display generations;
  a pre-mutation read finishing late cannot refill the invalidated local cache.
  Invalidating data does not wait for the subprocess lock. Action backends still
  acquire their original locks and inspect live hardware/network state. A cached
  switch state does not authorize an operation or prove Internet access.
- Caches are separate between USB/LAN processes. A change made through the other
  listener is observed through the normal freshness window, not an IPC push.
  Snapshot fields are observations, not an atomic hardware transaction. Live
  checks at execution remain mandatory even when the display appears fresh.
- Quick Settings refresh requests are coalesced and an action schedules a further
  refresh if one is already running. Mode telemetry does not hold up the other
  tiles. Wi-Fi polling is reduced from five to 15 seconds with in-flight guards;
  a late initial response does not collapse a form the user has begun editing.
- Both existing USB/LAN listeners use four HTTP threads instead of two. No
  listener/interface/port, route, firewall, gadget or service startup policy is
  changed. No UI framework or additional runtime dependency is installed.
- Network/hotspot background jobs now retain the existing power activity gate
  after HTTP acknowledgement, like Wi-Fi/modem/Quick jobs. Power dispatch and its
  actual hardware acceptance remain separate from this performance work.

## Baseline and validation

Five sequential Chrome contexts on the real USB, before installation:

| Run | DOM ready, seconds | First Overview data, seconds |
| --- | ---: | ---: |
| 1 | 0.190 | 7.640 |
| 2 | 0.298 | 17.951 |
| 3 | 8.040 | 21.103 |
| 4 | 0.245 | 12.766 |
| 5 | 0.281 | 14.359 |
| Median | 0.281 | 14.359 |

These are page-load observations with a new browser context, not cold boots,
controlled radio conditions or p95 claims. No network mutation or power command
was sent. Private timing/resource artifacts do not belong in Git.

Regression coverage includes blocked producers with concurrent HTML/CSS/power
GETs, single-flight/TTL/max-age/backoff, late result invalidation, unchanged
operation state, live action execution, LAN/cross-origin access, subprocess
coalescing, browser GET deadlines and no action retransmission. Mocked power
commands never execute on the host or USB. Chrome preview verifies independent
metrics while header is pending, lazy services, Wi-Fi editing, Quick Settings
consent/receipt/reboot-token recovery and header power controls.

## Installed results on the real USB

Installed source: `461e913ca43f87e549a490472f4899a72d5af235`.
Both [development CI](https://github.com/litequang/OpenStick/actions/runs/44447183373)
and [main CI](https://github.com/litequang/OpenStick/actions/runs/44447183537)
passed, including Windows EXE build/self-test/smoke. Local suite: 781 passed,
one Windows symlink-privilege skip, exit 0; pip check, self-test and JavaScript
syntax checks passed. Headless preview checks passed for Overview/usage (four
widths), Quick Settings (eight layouts), power controls (four widths) and settings
(24 layouts). Preview interactions use fixtures, not physical radio/power tests.

Five sequential new Chrome contexts after installation:

| Run | DOM ready, seconds | First Overview data, seconds | Quick controls ready, seconds |
| --- | ---: | ---: | ---: |
| 1 | 0.386 | 1.752 | 3.636 |
| 2 | 0.124 | 0.156 | 0.168 |
| 3 | 0.114 | 0.148 | 0.160 |
| 4 | 0.121 | 0.157 | 0.168 |
| 5 | 0.121 | 0.155 | 0.170 |
| Median | 0.121 | 0.156 | 0.168 |

| Measure | Before | After |
| --- | ---: | ---: |
| Median DOM ready | 0.281 s | 0.121 s |
| Median first Overview data | 14.359 s | 0.156 s |
| Slowest first Overview data in these five runs | 21.103 s | 1.752 s |
| Median Quick controls ready | 14.371 s | 0.168 s |
| Median requests until ready | 16 | 9 |

Later runs reuse server samples still fresh within five seconds. The 0.156 s
median is time to display a valid sample, not time to reread every hardware
source. First measured post-install data took 1.752 s; Quick controls took
3.636 s. These are five observations on an already-running USB, not cold boots,
phone visual acceptance, p95 or a guarantee for every network condition.

Five groups of six simultaneous display/asset/page/power-status GETs took
0.334–2.503 s per request. Manage/CSS/power status returned 200; telemetry could
return 503 while a background sample was pending. Manage/CSS reached 2.478 s.
Real hardware therefore does not establish a sub-second maximum under load;
the sub-second blocked-producer check is a fixture result only. The earlier
audit used five concurrent requests, so it is not an identical-load comparison.
Fresh samples became available again after this load check.

A ten-second post-install resource sample recorded zero swap-in/out and major
faults. Used zram was about 165 MiB, other used swap zero. Ten Python processes
totalled about 149 MiB RSS and 5.2% of one CPU core; RSS sums include shared pages.
This does not establish reduced RAM use or absence of pressure at other times.

Deployment and independent verification matched all 13 source/UI hashes and
served assets. Real GET Overview/header/Quick/services returned bounded display
metadata; Overview metrics were independent of Wi-Fi/services, and ModemManager
reported running. Power stayed ready/IDLE with advancing worker heartbeat and
no queued requests or receipts. SIM accounting samples advanced and the private
checkpoint remained valid. Protected owner file hashes, active network, routes
and firewall matched before/after; services ran and storage was flushed. Only
the existing USB/LAN portal services restarted; startup/usage/power workers kept
running. Private rollback sources are under `deploy-backups/portal-performance-*`.

No radio/data/AP/profile/gadget change, SMS/USSD, reboot or poweroff was performed.
Physical radio transitions, cold boot and the new power buttons remain separate
acceptance work. Read the [session handoff](SESSION_HANDOFF.md) before USB work.

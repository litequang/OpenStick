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

Read the latest [session handoff](SESSION_HANDOFF.md) for test counts, installed
source, real-device verification and measured results after installation. Do not
represent passing mocks, preview screenshots or source hashes as a physical
radio, SIM data, reboot or poweroff test.

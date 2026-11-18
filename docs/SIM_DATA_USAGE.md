# SIM data usage — 2026-11-18

The Overview metric **Dung lượng SIM** shows today's download/upload/total and
the current calendar month's total. Expand **Dung lượng SIM · chi tiết thống kê**
for monthly download/upload, the observed session, lifetime total, start time and
continuity warnings. Days and months use Vietnam time (UTC+7). This is aggregate
usage across all SIMs used on this USB, not a per-SIM account or carrier balance.
No SIM identity is needed or read. There is no automatic quota/data-off action.

## Accounting and persistence

`sim_usage.CounterSource` only runs fixed, bounded, read-only `nmcli device status`
and `nmcli device show` queries. It requires exactly one GSM device connected to
a `wwan*` or `rmnet*` data interface. Other interface families remain unsupported
instead of guessing from the default route. It reads sysfs RX/TX byte counters,
checks interface index and rechecks the NM binding before accepting a sample.
Wi-Fi/USB/Ethernet counters are never summed. Traffic that traverses the SIM
interface is counted once, including the USB's website/Tunnel and traffic routed
for hotspot or tethered clients. IP version does not create another accounting
layer. Interface statistics are not an invoice or a SIM Internet health check.

See the [Linux kernel statistics documentation](https://docs.kernel.org/networking/statistics.html)
for sysfs and RX/TX semantics. The implementation uses Python's standard library
only; it does not depend on BusyBox JSON output, packet capture, modem identities,
AT/QMI operations, a firewall rule or a new daemon.

One collector thread in the existing `openstick-network-startup` process samples
approximately every ten seconds, independently of network/modem readiness locks.
It never enables radio/data, sends network probes, changes AP/route/NAT or creates
a bearer. Opening or refreshing Overview only reads its sanitized snapshot.
A dedicated nonblocking lock permits one collector writer. Graceful worker exit
stops the collector and attempts a final checkpoint.

The first valid observation is a baseline; bytes that predate tracking are not
claimed. Subsequent monotonic deltas accumulate by day and lifetime. Repeated
reads add nothing. Interface recreation, reboot or counter decrease starts a new
baseline without subtracting history or adding an unknown initial counter value.
Process restarts can resume a persisted baseline from the same boot/interface.
Session means the continuously observed data-interface session, not carrier billing.
At most 400 daily buckets are retained; the lifetime total survives pruning.

Live telemetry is atomically replaced on RAM-backed `/run/openstick/sim-usage.json`.
Root-private `/var/lib/openstick/sim-usage.json` checkpoints use atomic replacement,
file/directory fsync and mode 0600, approximately once a minute while changed,
also on observed disconnect and graceful shutdown. The file retains only counts,
time buckets and the minimum local baseline (boot/interface/index/counters), never
IMSI/ICCID/IMEI, phone number, APN credentials, MAC/SSID, SMS or packet contents.
Baseline metadata is stripped from the authenticated Overview response and the
browser display cache. Runtime telemetry and backups must stay ignored by Git.

## Limits and failures

- Sudden power loss can lose traffic since the last checkpoint (normally around
  60 seconds plus sampling/query latency). A damaged state file is reported and
  preserved; it is not silently reset. Save failure retains live RAM totals with
  a visible warning; this does not make them durable.
- Fast disconnect/reconnect, modem resets, counter/driver behavior and time spent
  without an observable interface may cause undercounting. Old history is never
  reconstructed from current absolute counters. A counter may reset and exceed
  the prior value between samples without being detectable.
- Samples crossing midnight are assigned to the interval's ending day. A detected
  large wall-clock adjustment or a restart spanning different dates keeps the
  delta in the lifetime/undated total rather than inventing a calendar split.
  Before a usable clock (2020 or later), day/month are unavailable.
- Source errors keep known totals as stale/unknown, not healthy zero. A first
  failed observation creates no zero-usage claim or permanent baseline. More
  than one modem, unsupported interface types and incomplete replies are errors.
- The totals include interface overhead/control traffic as reported by the
  driver; they can differ from the carrier's charging rules. No hard billing
  limit or guaranteed complete traffic measurement is claimed.

## Validation

Local suite: **737 passed, one Windows symlink-privilege skip, exit 0**.
Coverage includes counter deltas/repeat sampling, restart/checkpoint recovery,
boot/interface/reset boundaries, disconnect/no SIM, source timeout/malformed
replies, initial probe failure, day/month/NTP changes, corrupt state, failed saves,
bounded history, identity filtering and passive Overview/worker integration.
Headless Chrome preview: 320/390/768/1280 widths, no overflow, details, save-failure,
idle zero and unavailable/stale states passed. Node fixture verifies the actual
template, cached display and private-field exclusion. Preview data is fictional;
this is not phone visual acceptance or a real SIM traffic measurement.

Read-only USB preflight confirmed one modem, an NM data-interface binding and
readable sysfs counters/index. It did not verify SIM presence, Internet or byte
accuracy. Installation and further hardware observations are recorded separately
in the latest [session handoff](SESSION_HANDOFF.md).

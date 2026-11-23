# BAM-DMUX cellular usage accounting — 2026-11-23

The real USB's BAM-DMUX netdev returns zero RX/TX byte counters despite working
SIM traffic. The old collector and UI were live but accumulated zeros. Cached
ModemManager bearer statistics contained actual RX/TX bytes; a read-only typed
probe on the real device observed them increasing within the same connection.
No counter reset, SIM identity, packet capture or radio/data mutation was used.

For this driver, the existing collector now uses individual read-only DBus
properties from the unique connected bearer matching the confirmed NM cellular
interface. ReloadStatsSupported and valid byte/connection statistics are required;
missing/ambiguous/changing statistics report unknown, preserving history rather
than silently falling back to broken zeros. Other drivers retain netdev counters.
The total DBus-read budget is three seconds. No extra daemon, thread, signal
setup, QMI command or network-changing method is introduced.

The private connection epoch combines bearer object number, attempt count and
connection start timestamp. Only same-source, same-epoch monotonic deltas count.
Reconnect/source/boot changes establish a new baseline, so a new connection with
larger counters cannot be counted as continuation of the old one. Epoch, boot,
interface and modem object paths stay private; the public API adds only the fixed
source category. No APN/credential/identity/USSD/SMS fields are requested.

Version 1 checkpoints migrate to version 2 while preserving lifetime/day/month
totals and start date. No existing statistics file is deleted or reset. The new
source's pre-existing byte count is not backfilled: historical zeros cannot be
reconstructed as accurate calendar usage. The continuity-gap indication explains
that history may be incomplete. Modem values update periodically; the page's
60-second refresh is not a real-time quota or the carrier's billing counter.

[ModemManager Bearer Stats](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Bearer.html)
defines ongoing RX/TX, connection attempts/start date and periodic reload support.

Regression checks cover read-only methods/field privacy, interface matching,
missing stats, reconnect/daemon epochs, source migration, malformed/ambiguous
state, disconnect/flush, restart, day/month/time changes and all earlier tests.
Full local suite before the final epoch recheck: 902 PASS/two Windows skips;
final focused accounting group: 52 PASS, exit 0. CI and installed acceptance are
recorded after execution; the candidate read is not installed-worker acceptance.

Rollback must preserve newly accumulated totals: stop the collector, archive its
current private checkpoint, convert a valid v2 checkpoint to v1 with last=None
and a continuity gap, then restore old source. Never restore an older total or
allow old source to mistake modem counters for zero-valued netdev continuity.

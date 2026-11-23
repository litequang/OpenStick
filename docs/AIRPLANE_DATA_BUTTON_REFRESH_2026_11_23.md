# Data button after airplane-off — 2026-11-23

## Problem and correction

The owner reported that Data SIM remained unavailable after disabling airplane
mode, apparently requiring USB removal/reconnection. The button correctly requires
a ready SIM and current network registration, but the UI had no fast readiness
follow-up when data was off. After its immediate post-operation read, it normally
waited 60 seconds for another status read. An enabling/searching sample could
therefore keep the button disabled after the modem became ready. The old text
could say merely Off, obscuring the actual waiting condition.

Quick Settings now follows radio/SIM registration with read-only status requests
every two seconds, bounded to two minutes. It stops fast reads when ready and
does not run them on hidden pages, while an operation/dialog is active, or as a
permanent polling loop. The ordinary slow refresh remains. Explicit Read Again
and completed operations rearm the bounded wait, including a queued forced read.
The tile states why it is unavailable: airplane mode, waiting for modem/SIM, SIM
not ready, or waiting for registration. It becomes clickable when fresh readiness
arrives. None of these reads enables a radio, bearer, data, AP or reboot.

Backend registration/SIM checks, confirmation, cellular consent, receipts, locks
and data-off veto are unchanged. Airplane-off still leaves data off until an
explicit click. No speculative changes to PIN handling, APN, radio mode, driver
reset or saved network selection were added.

## Physical and browser evidence

The latest fix request authorized investigating the normal airplane toggle. One
controlled cycle used the actual overview UI and its confirmation/receipt paths:
airplane-on, airplane-off and explicit data-on each completed once. On this cycle,
registration and the old button were ready about **2.1 seconds** after the off
receipt; the owner's persistent lock did not reproduce. No USB unplug/reboot was
used. The driver was suspended/auto after radio-off and safely active/on again
after explicit data activation. An initial helper hit a transient status-pending
response after all three completed receipts; a separate read-only check confirmed
the final state without resending any action.

That check verified registered/connected SIM, bound SIM HTTPS, AP active, NAT
matching the SIM interface, USB administration, saved AP+data-on and unchanged
saved radio choice. BAM was active/on with zero new resume errors. This is actual
hardware evidence of this one successful cycle, not reproduction of every prior
lock or a new independent phone Internet test.

A separate browser comparison used the real USB page with **synthetic GET-only
readiness**, keeping actual hardware/network state unchanged. It delayed SIM
readiness and registration for eight seconds. The old script made one read and
was still locked after the 12-second observation. The candidate made five reads,
unlocked automatically at **8.6 seconds**, then stopped fast polling. Four widths
(320/390/768/1366 px) had no overflow; no JS error or mutating request occurred.
This delayed-readiness result is a fixture test, not physical registration timing.

Local full suite: **943 PASS, two Windows platform skips, exit 0**, 30.98 seconds.
Affected Quick Settings/recovery/telemetry group: **81 PASS**; JS syntax PASS.
New deterministic UI regression covers delayed readiness, status staleness,
airplane/data-off veto, bounded reads, explicit rearm, hidden pages/dialogs and
no automatic activation. Deployment and installed verification follow below.

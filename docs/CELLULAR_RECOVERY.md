# Cellular session recovery — 2026-11-21

## Problem and resulting behavior

On the real UZ801 the AP remained visible while the previously working SIM
bearer disconnected (`MobileEquipment.Unknown`, generic call failure). The
modem remained home-registered on LTE, but there was no cellular IP/DNS. The
old boot replay had finished and did not maintain the selected connection.
This is distinct from the earlier AP visibility stall. The exact radio/network
cause of the bearer disconnect is not established.

The existing startup worker now also observes the owner's explicit SIM-data
selection every 20 seconds. After observing a registered, working connection,
two successive positive disconnect samples can trigger one bounded activation
of the owned cellular profile. Both NM (disconnected, no active profile) and MM
(registered, idle) must agree; searching, connecting and stale connected states
do not grant another activation. The saved radio mode must also match.

AP identity, DHCP, USB administration and the modem's radio mode are not changed.
After successful recovery the existing AP sharing guard and USB uplink rules are
updated for the current interface. No first connection, modem reset, AP restart,
operator selection, APN change or unbounded NM boot autoconnect is introduced.

## Consent, ownership and retry barriers

- Both the saved network selection and current private data intent must allow
  SIM data. Airplane/data-off vetoes win; reads never grant consent.
- Pause for power/USB transitions, network trials, active USSD, foreign cellular
  profiles, another Wi-Fi role or a separately enabled network policy/legacy
  hotspot controller. The UI's network/modem locks serialize operations.
- Persist a receipt and ATTEMPTING state **before** submitting activation. An
  exception, timeout, interrupted worker or unverifiable result stops automatic
  activation for that saved selection. Never replay an uncertain operation.
- Maximum three recovery activations in a failure burst. Ten minutes of
  continuously observed stable connection resets the successful-attempt budget;
  a worker restart alone does not. Three short-lived recoveries stop at
  LIMIT_REACHED. Unknown outcomes do not get this automatic reset.
- A new explicitly confirmed data selection can rearm valid stopped state.
  Corrupt recovery state fails closed and needs local inspection.
- Initial or failed boot activation is not retried by this mechanism. A real
  connection must first be observed in the current boot/selection.

Only a small private state file and fixed-category operation receipts persist.
Public status exports phase, attempt count and fixed errors, not boot IDs,
revision IDs, modem identities, credentials, operator identifiers or messages.
No extra process or polling thread is created; the 20-second interval bounds
the additional reads in the existing worker.

## UI

Data requested ON and actual connected data are separate states. A dropped
session no longer appears as an intentional OFF. The tile displays waiting,
reconnecting or stopped recovery and keeps **turn off** available even when the
SIM loses registration. Confirmation explains the recovery behavior. A bearer
alone is never presented as measured Internet success.

The serving-network correction from `df55e36` is also needed on installed
systems: core MM State=connected must not override 3GPP searching/unregistered
status. The previously installed `747f49c` does not contain that correction.

## Validation and deployment status

Local full suite: **842 passed, 2 Windows platform skips**, exit 0. Existing
worker-lifetime/usage tests remain and now also verify the recovery tick. Node
syntax, UI behavioral fixture, dependency check and whitespace check pass.
Regression coverage includes consent/radio vetoes, mode changes, USSD, foreign
profiles, pending transitions, unknown/connecting states, worker interruption,
corrupt state, finite attempts, stable-budget reset and user data-off at the
last submission barrier. Fixtures are not physical acceptance.

This commit is the candidate source. Push and CI precede any installation.
Hardware results will be recorded separately: observe initial connection,
simulate one owned bearer disconnect with AP preserved, verify the real worker
reconnects, test explicit data-off suppresses recovery, then restore the owner's
selected state. No reboot, SMS/USSD, firmware or SIM-identity collection is part
of that validation. AP beacon-stall recurrence remains a separate driver issue;
do not claim this cellular recovery restarts or permanently fixes AP beacons.

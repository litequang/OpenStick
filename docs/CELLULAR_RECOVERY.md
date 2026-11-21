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

## Physical deployment and validation — 2026-11-21

Installed **`eaa747125f3d365c968308a6cccfcab055cdfe3d`** from the UI branch/PR #7.
Both Windows workflows passed, including tests, EXE build/self-test/smoke:
[push](https://github.com/litequang/OpenStick/actions/runs/44890209911),
[PR](https://github.com/litequang/OpenStick/actions/runs/44890214053).
Integration with the newly pushed saved-settings/radio controls was necessary
before the PR workflow could run; its earlier merge conflict was resolved on the
UI branch. No merge into main/development, release or firmware operation.

Read-only source inventory found a **mixed installed baseline**: optimization/UI
code plus previously installed saved-settings/radio changes. `747f49c` alone did
not describe the actual installed files. Only six reviewed files were replaced;
actual installed hashes were pinned before replacement. Other settings/cache,
radio controls and owner choices were preserved. Source/served asset hashes,
ownership/permissions, 721 protected owner files, network/routes/firewall/DNS/USB
gadget, services and sync passed. Only the two portal services and the existing
startup worker restarted. Private source backup/checksum remains on the device;
no owner data or backup archive was added to Git.

Real worker tests, with SIM/data consent already granted:

- Explicit data activation completed and the real background worker armed.
- One controlled disconnect of only the owned cellular profile recovered in
  **47.3 s**, one recorded activation; SIM-bound HTTPS Internet passed.
- Product data-off completed. After **45 s**, no cellular reactivation and
  recovery remained paused. Explicitly restoring data-on completed, the worker
  armed again and SIM-bound Internet passed.
- A follow-up controlled disconnect recovered in **31.7 s**, again one attempt
  for the newly selected configuration. SIM-bound Internet passed; AP active,
  saved LTE-only choice and USB administration retained.
- The first test's whole-profile-byte equality check was **false**. Do not call
  it a PASS: activation updates profile files. The follow-up captured every
  parsed field before/after: only cellular `connection.timestamp` changed; no AP
  fields or other cellular settings changed. Both profile permissions were 0600.

These tests prove bounded recovery of an observed, explicitly selected session,
not the cause of the original modem call failure or long-term network stability.
No new phone Internet, cold-boot, airplane cycle or AP-driver recovery acceptance
is claimed. The earlier owner-confirmed phone success followed a separate AP
restart. The recovery never restarts that AP.

## Candidate source validation (before integration)

Local full suite: **842 passed, 2 Windows platform skips**, exit 0. Existing
worker-lifetime/usage tests remain and now also verify the recovery tick. Node
syntax, UI behavioral fixture, dependency check and whitespace check pass.
Regression coverage includes consent/radio vetoes, mode changes, USSD, foreign
profiles, pending transitions, unknown/connecting states, worker interruption,
corrupt state, finite attempts, stable-budget reset and user data-off at the
last submission barrier. Fixtures are not physical acceptance.

After integrating the saved-settings/radio source, the full suite passed
**855 tests, 2 Windows platform skips**, exit 0. No test was removed. Physical
results above followed both successful CI runs. No reboot, SMS/USSD, firmware
or SIM-identity collection was part of validation. AP beacon-stall recurrence
remains a separate driver issue; do not claim permanent AP-beacon repair.

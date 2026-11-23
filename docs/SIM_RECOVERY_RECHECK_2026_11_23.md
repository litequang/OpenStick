# SIM Internet recheck — 2026-11-23

## Actual failure captured before changing the device

The installed seven-file recovery/band source still matched `9e78ce7`. The SIM
was home-registered on MobiFone LTE, with the saved LTE-only choice unchanged,
but NM positively reported disconnected (30), no owned active cellular connection
or data interface, and MM had no bearer. Bound Internet testing consequently had
no interface to use. Registration and the requested data-on flag were not data
connectivity. No SMS, USSD, identity/credential export or radio change.

The selected configuration requested AP+SIM data, radio/data intent allowed it,
and the existing AP matched that role. No automated policy, legacy hotspot,
network trial or pending gate explained the failure. The real startup worker
was alive. Recovery reported WAITING_CONNECTION; its persisted state had no
observed connection proof for the current saved revision. The most recent
completed explicit actions included data-on followed by AP-on. Older boot-replay
state recorded WIFI_RESTORE_FAILED for a different selection; it is not evidence
that the current saved AP should be torn down or the old failure blindly replayed.

The AP administration/DHCP profile and NM sharing table existed. The selected
data state had no live uplink, and the existing AP guard dropped forwarded traffic.
Do not remove that guard or weaken the base firewall to conceal missing SIM data.
USB tethering was separately selected off. No associated phone was observed in
this read, so it is not a phone-through-Wi-Fi acceptance test.

Today's thermal observations were approximately 48–52 C, CPU cooling state 0/3.
The 21 November observation of 79–86 C and a 200 MHz thermal cap is historical;
it does not explain today's missing bearer.

## Software gap and correction

Previously only the 20-second background sample could establish connection
proof. Every saved AP/Wi-Fi selection changed the configuration revision. A
successful explicit data-on followed by AP-on and a disconnect before the next
sample could therefore lose the recovery eligibility of a connection that had
actually worked. The worker intentionally does not open an unobserved first
connection or retry an uncertain failed boot, leaving this case waiting forever.
Its newly initialized WAITING_CONNECTION state also was not persisted when no
other field changed, making the current revision difficult to diagnose.

The explicit transaction now records verified registration/IP connection proof
under its existing network/modem locks before its successful receipt returns.
An AP/Wi-Fi save transfers same-boot proof and the existing attempt budget to
the new revision. The boot worker records successful restoration too. A fresh
WAITING_CONNECTION state is persisted without initiating any network operation.

AP saves preserve ATTEMPTING/UNKNOWN/LIMIT_REACHED and cannot grant a new retry
budget. Only a successful, explicitly confirmed data-on rearms it. Missing,
corrupt, unconsented or never-connected state still grants no activation. All
existing radio, data-off, power/USB, USSD, role, ownership and finite-retry gates
remain. No AP restart, APN/operator/band change or modem reset is added.

The data tile keeps its requested on/off semantics but uses amber when data was
requested and no registered/IP session exists. A blue connected tile still says
Internet is unverified; signal bars are not an Internet measurement.

This corrects a demonstrated state-management hole. It does not establish what
initially dropped the physical modem session or prove the UI optimization caused
that drop. The optimization did not remove networking services/packages or alter
the saved profile/firewall in its recorded deployment. Longer-term modem/AP
stability, initial failed boot recovery and cold-power acceptance remain separate.

## Validation

Focused network/Quick/recovery tests: 84 PASS, exit 0. Regression coverage now
includes data-on proof before the first worker poll, disconnect during AP save,
transfer to the new selection, boot proof, and preservation of stopped retry
budgets. The never-connected case remains tested without manufacturing a prior
successful explicit activation. No test was discarded.

Full local suite: **880 PASS, 2 Windows platform skips**, exit 0. The final
additional stopped-state/boot assertion is checked in the affected suite too.
CI and physical installation results are recorded after execution.
No new code was installed or network state changed during the initial diagnosis.
The separate unfinished BAM-DMUX usage-accounting work is preserved locally and
is not part of this network patch or its installed-source claim.

# SIM off/on: connected bearer with failed BAM-DMUX transport — 2026-11-23

## Captured physical failure

After the owner's data-off/data-on sequence, both receipts were COMPLETED, NM
reported 100/connected on the owned profile, MM reported connected/non-suspended
bearer and home LTE registration. Requested data and saved AP+data selection
were enabled. Recovery proof matched the current boot/revision; this was not the
previous missing-revision-proof case. Installed network source hashes matched.

Actual SIM-bound testing failed all four HTTPS probes across two public endpoints
and provider/system DNS, both public-IP pings, and a separate DNS-independent
HTTPS/ping probe. IP/prefix, route source/interface/gateway and DNS matched the
current bearer. rp_filter=0 and forwarding=1. AP/NAT/forward rules existed; no
client was blocked. This is failure on the USB's own SIM path, not merely phone
DNS or Wi-Fi forwarding. No AP restart, airplane toggle or modem reset was used.

The BAM-DMUX device had power/control=auto and runtime_status=error. During a
35-second bounded test the same bearer reported zero RX/TX byte delta. Kernel
messages matched public static templates: 12 older inactive-channel messages
and one **Failed to resume: -22**. No modem/remoteproc crash was established.
No raw identifiers, network addresses, credentials, packet contents or kernel
lines containing runtime identifiers were exported or committed.

This establishes a failed kernel data-transport runtime-PM state for this
incident. It does not prove every historical drop has this cause, nor that the
portal optimization introduced it. Linux v6.12's [BAM-DMUX source](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/refs/tags/v6.12/drivers/net/wwan/qcom_bam_dmux.c)
uses runtime PM in transmit and emits that error when its wake-up work cannot
resume. A [15 November 2026 proposed upstream patch](https://lists.openwall.net/linux-kernel/2026/11/15/602)
addresses power/DMA lifetime serialization; it is research evidence, not proof
that this precise race occurred here or that an installed kernel contains a fix.
No patch from another board/firmware is assumed applicable or installed.

## Correction and bounded mitigation

Read-only status detects the BAM-DMUX power error and stops treating a connected
NM/bearer as a usable SIM interface. Quick Settings shows an explicit driver
error requiring a normal restart, instead of implying that another APN or blind
airplane/data retry is the remedy. Opening a page does not write sysfs, enable a
bearer or queue a restart.

Before an existing, consented owned cellular activation, the common Network.up
path requests power/control=on only on the single positively identified BAM-DMUX
controller. It verifies active state and readback, and fails closed on an error,
ambiguous/out-of-sysfs device, invalid ownership record or bounded resume timeout.
Other drivers and AP/station activation are untouched. The hold remains through
data-off so the next data-on does not depend on idle autosuspend/resume. Data-off
still ends the session; the hold does not enable SIM data. Radio-disable releases
only a hold this feature owns; it never overrides an external pre-existing hold,
and release errors never prevent the owner's radio-off veto.

This is a userspace mitigation of idle resume exposure, **not a kernel repair**.
Keeping the data controller awake can increase power/temperature. Thermal
protection remains enabled; no CPU, thermal, Wi-Fi, USB or modem-firmware tuning.
No driver unbind/rebind, remoteproc reset, flash, reboot or repeated activation
is added. An already errored kernel transport is not declared repaired by merely
writing a policy flag. A normal restart and real off/on cycles are required to
validate prevention; do not claim physical PASS before performing them.

## Validation record

Synthetic tests cover read-only status/privacy, owned versus external holds,
sticky/resume errors, bounded timeout, corrupt/ambiguous/out-of-sysfs targets,
common activation ordering, no AP changes and rejecting a false connected tile.
CI/deployment/restart/off-on hardware results are recorded after execution.

Local full suite: **920 PASS, two Windows platform skips, exit 0**. Final affected
transport/recovery/UI fixture group: **43 PASS**, exit 0; quick.js syntax PASS.
These are software results, not restarted-device/off-on acceptance.

## Installed, awaiting normal-restart validation

Four reviewed source files from **`fb7ece27a438fd203a7097275aed2f4771b56683`**
were installed after [push CI](https://github.com/litequang/OpenStick/actions/runs/45104629790)
and [PR CI](https://github.com/litequang/OpenStick/actions/runs/45104636126) passed,
including Windows EXE checks. Source/served-asset hashes, permissions and private
source-backup checksum passed. Both portals and the existing startup worker
restarted; no reboot, firmware, kernel, driver rebind, modem/airplane/AP reset.

The candidate read-only probe and installed code both positively identified the
actual errored BAM-DMUX controller. Preparation failed closed before writing.
Installed status now rejects the existing NM-connected bearer as a usable data
interface. Real Chrome on the USB overview at 320/390/768/1366 px displayed the
specific driver error and amber data state, with no horizontal overflow, JS error
or mutating browser request. This is not a phone test or physical proof that the
hold prevents recurrence.

Final 16 source hashes, 721 protected owner files, network/routes/firewall/DNS/
gadget/services and BAM power policy matched installation baseline. AP and USB
administration remained, usage checkpoint was valid, gates idle, storage synced.
The pre-existing power/control=auto and runtime_status=error remained; no hold
was installed by merely loading the UI or restarting the workers.

The owner subsequently approved one normal reboot and three real data-off/on
cycles. DevicePower dispatched the normal reboot with checkpoint/receipt; boot
restored AP+SIM, actual bound HTTPS passed and BAM was active/on with its owned
hold. All three cycles completed (24.3/35.5/35.7 seconds), retained the AP and USB
administration, stayed off during the six-second veto observation, and passed
bound SIM HTTPS after enabling again. No new resume errors occurred. Saved radio,
USB descriptors and 16 installed-source hashes matched; usage history remained
valid/nondecreasing. Chrome showed connected/blue at four widths without JS
errors, mutations or overflow. This is short-cycle hardware mitigation evidence,
not a kernel fix, long soak or physical phone acceptance. Peak sampled thermal
zone rose from 56 to 73 C by the final check; causal power cost is not isolated.

**The owner's subsequent phone Internet test FAILS.** Separate diagnosis found
missing AP sharing NAT while the USB's own SIM path still works; see
[the downstream NAT report](AP_NAT_RESTORE_2026_11_23.md). Do not represent the
three USB uplink cycle results as resolution of this downstream failure.
The proposed upstream kernel patch has not been installed; no further reboot,
airplane toggle, APN change, driver rebind or modem reset has been performed.

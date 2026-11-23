# AP sharing after normal reboot — 2026-11-23

## Separate the two observed failures

The owner approved one normal reboot and three SIM data-off/on cycles after the
BAM-DMUX runtime-PM failure described in [the transport report](SIM_DATA_TOGGLE_BAM_PM.md).
The reboot used DevicePower's existing checkpoint, durable receipt and normal
shutdown. Saved AP+SIM selection restored; BAM was active/held awake with zero
new resume errors. All three real off/on cycles completed, kept AP/USB management,
and passed HTTPS bound to the SIM after data-on (24.3, 35.5 and 35.7 seconds).
One initial preflight Internet sample failed before either cycle receipt existed;
a later read-only sample passed before the first actual cycle was submitted.

These are **USB uplink** results, not phone Internet acceptance. The owner then
reported no Internet through Wi-Fi and slow administration. Preserve that FAIL.

## Physical evidence of lost NAT

The pre-reboot private baseline contained NM's shared AP NAT table and one
masquerade rule. After reboot, AP remained active with IPv4 shared mode, a valid
lease and an authorized station. Forwarding=1, rp_filter=0; no client was blocked.
The AP DNS answered a public-name query. SIM-bound HTTPS still passed and BAM
remained healthy. However, the entire current ruleset had **zero NAT chains and
zero masquerade rules**; no legacy iptables backend was present. NM's effective
backend was nftables. The three data-on operations removed the AP deny guard but
did not recreate sharing NAT on an already active AP.

A bounded 35-second header-only observation counted 847 incoming client IPv4
frames, 43 DNS requests/44 replies, 123 administration TCP frames/143 replies,
569 public SYNs and 561 matching outgoing SIM SYNs, without matching public
SYN-ACKs back. MACs/addresses/destinations/payloads were not exported or saved.
This establishes a downstream sharing failure distinct from the cleared BAM
error; Wi-Fi association, DHCP and a connected bearer did not prove Internet.

The exact event that removed NM's table is **UNVERIFIED**. Base nftables startup
contains a global flush, but service timestamps are distorted by clock correction
and do not establish a causal boot sequence. Do not claim that a particular
optimization/service removal caused it. The [NM manual](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/NetworkManager.conf.html)
describes shared-mode masquerading; the [installed-version upstream implementation](https://github.com/NetworkManager/NetworkManager/blob/1.52.2/src/core/nm-firewall-utils.c)
does not make an active AP proof that external firewall state remains present.

## Durable correction

OpenStick owns one separately marked NAT table, restricted to the fixed AP IPv4
subnet and the already connected owned SIM interface. It requires positive saved
cellular consent, radio permission, the owned AP/shared IPv4 configuration and a
usable SIM transport. It neither opens a bearer nor changes the AP, route, base
firewall, USB tethering, client block/isolation rules, DNS or credentials.

Before opening the existing forwarding gate, data-on/startup/AP activation checks
syntax, atomically installs the scoped rule and verifies readback. Data-off closes
the guard first and removes only owned NAT. Existing connected-state recovery
also reconciles missing NAT at its existing 20-second cadence and under the same
locks; there is no new thread, browser-triggered write, Internet polling loop or
blind AP/modem reset. A matching table causes reads only. A foreign/malformed
table fails closed rather than being overwritten. If NM's own NAT exists, the
scoped table runs first; conntrack applies one translation, not double NAT.

## Installed validation

Source **`ec5a7523dd1d50934c5728b084b37889d5a03bb6`** passed **942 tests/two
Windows platform skips, exit 0**, the 106-test affected group and JavaScript
syntax checking. A check-only probe using the actual USB nftables accepted the
generated rule without applying it. [Push CI](https://github.com/litequang/OpenStick/actions/runs/45108582638)
and [PR CI](https://github.com/litequang/OpenStick/actions/runs/45108587656) passed,
including the Windows EXE.

Four source files were installed with checksum-verified private source backup.
The existing startup worker restored the missing owned NAT table automatically;
readback matched the actual connected SIM interface. No AP/data toggle, second
reboot, route change, radio mode/APN change or modem/driver reset was needed.
17 installed source hashes and 722 protected owner files matched. The base
network/routes/firewall/DNS/gadget remained unchanged when excluding only the
deliberately added owned NAT table. Saved AP+SIM, radio choice, usage history and
valid checkpoint were retained; services were running and storage synced.

USB-bound SIM HTTPS still passed and BAM stayed active/on with zero new resume
errors. Real Chrome at 320/390/768/1366 px showed connected/blue without overflow,
JS error or mutation. A Windows-to-USB GET /overview returned HTTP 200 in 56 ms;
an earlier device-local GET was 14 ms. These isolated page timings do not prove
phone latency or benchmark the entire UI. Peak sampled thermal zone at this
check was 75 C; power/thermal effects of the BAM hold need longer observation.

The owner has been asked to repeat the phone Internet/admin check. The previous
result was FAIL; successful NAT restoration and USB HTTPS are **not** fresh
phone acceptance. A subsequent 35-second passive window had zero associated
stations and only SIM traffic, so it supplies no new phone-path result. Long
soak, another cold-power test and an independently
confirmed explanation of NM table removal remain unverified.

## Owner reacceptance after installation: FAIL

The owner answered the post-installation phone test: **still no Internet**.
This supersedes the pending phone result above. NAT restoration is a verified
correction of missing state, not a completed resolution of phone access.

Read-only follow-up again passed the 17 source hashes/722 protected owner files,
unchanged base network/firewall/gadget, valid/nondecreasing usage history, owned
NAT matching the actual SIM interface, SIM-bound HTTPS and healthy BAM active/on.
No new resume errors occurred; peak sampled zone was 76 C. No additional code,
profile/network/route/firewall change, restart, radio toggle or reboot was made.

One 35-second window saw only two incoming client IPv4 frames, no station TX
byte delta and nine outgoing AP ARPs. The associated client had a current lease;
two bounded local pings failed and ARP did not resolve. A later 45-second
header-only observation saw 44 AP IPv4 inputs/45 outputs and one new public TCP
SYN correctly translated to the actual SIM source IP. Its matching SYN-ACK
returned on SIM and was sent onto AP. NAT matched before/after. This proves that
at least that new TCP path traversed NAT both ways, not a completed page load or
delivery acknowledged by the phone. A single additional untranslated AP-subnet
packet was observed; its origin/connection age was not established, so stale
conntrack is a hypothesis, not an established remaining cause.

AP and SIM MTU are both 1500 and AP power saving is off. One kernel warning
matched the public WCN36xx template `Spurious TX complete indication`; no firmware
crash/HAL timeout was established. The warning alone does not prove a permanent
driver failure. Device station inactivity was later about 42 seconds, and none
of these captures overlapped a separately confirmed phone page-open action.

The phone has been asked to open http://neverssl.com and https://1.1.1.1 with
mobile data off. Those results are pending; they help separate name resolution,
TLS/content transfer and intermittent Wi-Fi delivery. Do not infer that another
APN change, blind AP restart or kernel/firmware replacement is justified yet.
Minimal BusyBox ip rejected one diagnostic JSON-address request before capture;
the helper was corrected to parse text and then completed. The device has no
conntrack tool/proc listing; a fixed read-only CT_GET netlink request returned
EINVAL. No conntrack deletion/reset was attempted, and no diagnostic identities
or packet payloads were exported or committed.

A final 45-second TCP-stage observation still had one associated station and
matching NAT, but zero AP IPv4 frames at all (SIM background traffic continued).
It cannot diagnose a page-open failure without a simultaneous phone attempt.

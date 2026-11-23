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

Validation/deployment and fresh phone acceptance are recorded after execution.
The owner's current phone Internet result remains FAIL until retested.

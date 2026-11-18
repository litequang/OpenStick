# AP clients and Internet filtering — 2026-11-18

## Scope

`/setup#ap-clients` lists devices currently associated with the USB AP and lets
the owner block/unblock **routed Internet traffic** by MAC. No SIM is needed to
manage this. It does not remove a device from Wi-Fi, implement an association
deny ACL, replace AP isolation, or restrict access to services on the USB itself.
The local admin page and DHCP/DNS remain available. Local proxies/services can
still communicate externally on their own behalf; this is not an authorization
boundary against a hostile client. MAC randomization/spoofing can bypass a list.

Only driver station entries establish current presence (`iw dev wlan0 station
dump`); DHCP lease history never creates a connected device. IP/name enrichment
comes from bounded, fixed-path DHCP files and the current wlan0 neighbor cache.
Missing fields remain unknown, and failure is distinct from an empty list.
TX/RX counters and link rates are from the USB's perspective, not speed tests.
No external vendor/OUI lookup or device history is performed.

The new authenticated API uses existing USB/LAN login, token and Host/Origin
guards. Block/unblock require explicit confirmation and a UUID receipt; opening
the page, polling or cancelling does not mutate anything. Inventory, client MACs,
IP addresses and names remain on the private admin interface. Only the necessary
block list is durably stored in root-private `ap-clients.json`; receipt files
contain operation/outcome categories, not MAC/name/IP or command output.

## Actual backend findings

- The real USB is running an AP and can read `iw` station inventory. It returned
  zero associated devices during the initial read-only probe. This verifies the
  empty read, not phone association/leave detection or per-client counters.
- wpa_supplicant 2.11 source contains `DENY_ACL` control commands, but its expected
  Unix control socket is not available in this installed NM-managed setup.
  Association ACL remains **UNVERIFIED / unavailable in the panel**; no supplicant
  restart, backend replacement or interface recreation was attempted.
- Live `/proc/config.gz` reports `CONFIG_NF_TABLES_NETDEV` disabled. A netdev dry
  check failed; it was not installed or represented as working. The implementation
  uses a dedicated **inet forward** table whose generated rules passed
  `nft --check` on the USB. No rules changed during syntax research.

## Filtering, state and limits

The only owned firewall object is `inet openstick_ap_clients`. Its forward chain
runs before the existing sharing rules. Client-originated routed packets are
matched by wlan0 and source MAC, for both IPv4 and IPv6. Reply guards use current
neighbor IPs correlated to a blocked MAC. These IP guards are refreshed by the
existing network-startup worker every five seconds; neighbor churn can delay or
invalidate reply matching. Do not present neighbor correlation as authenticated
identity, a measured packet-denial guarantee, or association blocking.

No input/output chain, NAT, conntrack mark, gadget/USB DHCP, base firewall flush,
profile, radio, APN, SIM-data grant, public website or Tunnel is changed. Foreign
flowtable/offload rules cause a fixed unsupported error rather than accepting a
filter that fast-path traffic could bypass. Unknown objects at the owned table
name are not overwritten. Rules are validated then applied as an nft transaction.

Successful changes are saved with fsync before acknowledgement. On failure,
previous private policy and owned rules are restored; uncertain/failed rollback
is reported explicitly. The shared network lock serializes all portal/worker
mutations. Read-only inventory does not acquire that lock: a no-SIM modem wait
must not prevent viewing clients. A concurrent Wi-Fi role change invalidates
the sample rather than reporting a false empty AP. Before an owned AP start
the saved filter is prepared. AP scan/role
rollback uses the same activation hook, and entering station/off removes only
this filter. Boot reconciliation reuses the existing worker; no extra Python
daemon is added. Corrupt policy is not silently replaced with an empty list.

Up to 128 normalized unicast MAC entries can be stored. That storage bound is
not an AP hardware capacity claim. API errors never return raw subprocess output.
The UI supports online rows, an offline block list, manual MAC input, confirmation,
timeouts, no automatic mutation retry, draft-safe polling and text-only names.

## Validation and remaining acceptance

705 pytest passed, one Windows symlink-privilege skip, exit 0. Chrome headless
24 layouts and interactions passed, including the client widget and aborted
mutation without automatic retry. Syntax, self-test, dependency and whitespace
checks passed. These are fixture/preview results, not physical-client acceptance.

Offline tests cover parser/lease separation, enrichment, input/auth gates,
atomic save, uncertain-save recovery, firewall failure rollback, unknown/offload
tables, orphan-filter reporting, boot replay, station cleanup, pre-AP hook,
receipt replay rejection and malformed inventory. Browser fixtures cover layout,
text-only untrusted names, confirmation/cancellation, block/unblock and disconnect
without automatic resend. Fixture MACs are fictional.

## Installed-device checks

Installed on the real USB after owner authorization. Independent source and
served-asset hashes, HTTP controls/API and inventory access passed. At final
verification the AP had zero associated stations. A fictional, non-associated
MAC was saved through the authenticated API, applied to the real nftables table,
read back and unblocked successfully. The temporary policy and owned table were
removed; the original absence of policy, base firewall and protected owner
configuration hashes were verified unchanged. Storage was flushed. No reboot,
AP/profile change, SMS/USSD request or SIM-data test was performed.

The first filter check exposed BusyBox `ip` without JSON support. The backend
now falls back to a fixed, bounded plain-neighbor parser; regression and installed
API checks passed. The existing startup worker was temporarily stopped during
the fixture mutation check to avoid its no-SIM readiness lock, then restarted.
The final inventory GET also succeeded with that worker running.

Full local suite: **707 passed, one Windows symlink-privilege skip, exit 0**.
Browser fixture validation previously passed 24 layouts and confirmation,
cancel/block/unblock/disconnect interactions. These are automated previews, not
visual or physical packet acceptance. A pre-existing ZIP test timestamp race
found by CI was fixed using deterministic fixture metadata, without removing
the rollback test or changing the ZIP publisher.

Real client enforcement is **NOT_TESTED** until a phone is connected and the
owner chooses its MAC to test. Required acceptance: join/leave count is correct;
block stops new IPv4/IPv6 Internet requests and established traffic as intended;
admin and DHCP remain available; unblock restores access; saved policy survives
AP mode changes and cold boot; private website/Tunnel/radio state remains intact.
SIM Internet acceptance is separate and deferred at the owner's request.

References: [official wpa_supplicant 2.11 source](https://w1.fi/releases/wpa_supplicant-2.11.tar.gz)
(`ctrl_iface.c`, `ap.c`, source hash in [AP options](AP_ADVANCED_SETTINGS.md));
[nftables project manual](https://www.netfilter.org/projects/nftables/manpage.html).

# One local administration URL

Use **http://openstick.local:8765** on clients with local-name resolution: a PC connected by USB, a phone or PC
on the same Wi-Fi as the stick, or a phone connected to its setup/SIM AP.
This is a local name supplied by mDNS and, on the stick's hotspots, local DNS.
It is not a public Tunnel hostname. Wi-Fi still requires
the existing LAN login. The physical USB listener retains its USB-only trust
boundary and its original http://172.16.42.1 URL.

The stick continues using DHCP on station networks. Avahi follows interface
address changes and advertises the current address separately on `usb0` and
`wlan0`. No home-network address, gateway or password is embedded in source.
IPv6 publication is disabled because the administration listeners use IPv4.
Host authorities are explicitly allowlisted; an Origin must match the exact
Host used for that request, even when both names are allowed.

## Installation on postmarketOS / Alpine

1. Deploy the matching Python package and templates under `/opt/openstick`.
2. The device needs the distribution's `avahi` and `avahi-openrc` packages.
   Back up `/etc/avahi/avahi-daemon.conf` and confirm that no existing Avahi
   deployment or name registration will be overwritten unexpectedly.
3. Install `scripts/avahi/avahi-daemon.conf` as
   `/etc/avahi/avahi-daemon.conf` (root-owned, mode 0644).
4. Install `scripts/nftables/53_openstick_mdns.nft` into `/etc/nftables.d/`.
   Syntax-check with `nft -c -f` first. Add its rule to the running firewall
   only once; do not flush the ruleset or disrupt USB recovery. Existing USB
   ingress rules also permit mDNS and the additional USB-bound port 8765.
5. Start `avahi-daemon` and add it to OpenRC's default runlevel with
   `rc-update add avahi-daemon default`. Restart only `openstick-wifi` and
   `openstick-lan` to load the updated application.
6. Verify the actual Avahi FQDN is `openstick.local`, multicast A responses
   on the physical link, and HTTP through that name. Check LAN login and
   rejected cross-origin requests. Keep a timestamped backup and rollback
   manifest for all files and any new service/firewall configuration.
7. For Android clients using ordinary DNS, install
   `scripts/dnsmasq-shared.d/54_openstick_local.conf` as
   `/etc/NetworkManager/dnsmasq-shared.d/54_openstick_local.conf`. Syntax-check
   the combined shared configuration with dnsmasq. NetworkManager reads this
   when its shared hotspot starts; SIGHUP does not reload dnsmasq config.
   When no transition/trial is pending, reactivate only the owned AP profile
   to load it, keeping USB recovery and the cellular connection intact.
   Do not restart NetworkManager. Keep a configuration backup and checkpoint.
8. Install the matching `scripts/openrc/openstick-setup-dhcp` as well. Its
   local-only DNS advertises itself via DHCP and resolves the same name from
   `wlan0`'s IPv4 address, without an upstream resolver or a default gateway.
   Leave the setup service under the setup worker's control; do not enable
   it at boot or start it alongside the SIM AP's DHCP server.

Avahi alone needs no reconnection or radio change. Adding the hotspot DNS
fallback requires one AP reactivation and may require clients to reconnect
to clear negative DNS caches. It does not require a SIM data activation,
SMS/USSD, device reboot or a change to station credentials. The same Avahi
interface allowlist covers station and hotspot mode; no simultaneous
station/AP support is required.

## Using and troubleshooting the name

### Incoming query TTL compatibility fix (2026-11-16)

The original firewall required IP TTL 255 on **every** incoming mDNS packet.
That incorrectly filtered link-local multicast queries using TTL 1 or the
client OS default. RFC 6762 section 11 recommends TTL 255 on **responses**;
it does not require that TTL on all queries. Avahi already handles the
protocol's responder/source checks.

The rule now additionally accepts UDP destination port 5353 addressed to
`224.0.0.251`, arriving only on `wlan0`, without imposing a query TTL.
The existing TTL-255 rule for other mDNS ingress remains. This does not open
ordinary DNS on new interfaces, enable a reflector, alter WWAN/forwarding,
or weaken HTTP Host/Origin/login checks.

This was reproduced on the physical USB from the PC's actual Wi-Fi interface:

| Query IP TTL | Before | After |
|---|---|---|
| 1 | Timeout | Correct WLAN A record |
| 64 | Timeout | Correct WLAN A record |
| 255 | Correct WLAN A record | Correct WLAN A record |

Each successful reply had RCODE 0 and the matching transaction ID. Source-bound
LAN HTTP with both the numeric and named Host returned the login redirect.
The owner independently confirmed numeric-IP access from the phone before
the fix. Phone acceptance using the name after this change is still pending.
This demonstrates a real firewall defect; it does not prove that every
Android/browser DNS failure has the same cause.

Only the persistent mDNS file and one live multicast accept rule were added;
the old rule was retained. The entire firewall was not flushed. Configuration
validation passed; no service restart, Wi-Fi reconnection, radio operation,
SIM data activation or reboot was performed. The original file is backed up
locally under `/var/lib/openstick/deploy-backups/mdns-query-1794792297396710055/`.

Clients that bypass mDNS and ask a router/public resolver still need working
local name resolution on that client/router. The observed LAN router rejected
an ordinary DNS request for this name. A server-side mDNS fix cannot make
that router answer. Numeric IP remains a valid fallback; do not redirect
ordinary LAN DNS traffic or expose administration publicly to work around it.

Protocol basis: [RFC 6762 section 11](https://www.rfc-editor.org/rfc/rfc6762.html#section-11).
Android's resolver behavior and exclusions are described in
[AOSP mDNS .local resolution](https://source.android.com/docs/core/ota/modular-system/dns-resolver#mdns-local-resolution).

### Client and network checks

- On a phone connected to the setup AP, keep the Wi-Fi connection when it
  reports no Internet. Allow time for name caches to update after a change.
- Both peers must share the local link. Guest isolation or blocked multicast
  can prevent `.local` resolution. A VPN, proxy or older client resolver may
  also interfere; use the IP fallback in that situation.
- The setup/SIM AP fallback is http://192.168.8.1:8765. The station IP fallback
  remains visible through USB management. DHCP reservation on a router is an
  alternative if a fixed numeric IP is required on that particular network.
- Another device already using `openstick.local` can cause Avahi to choose a
  suffixed name. Diagnose a collision rather than forcing two devices to
  claim the same name. This deployment checks the name after startup.
- On Android, `DNS_PROBE_FINISHED_NXDOMAIN` may mean the browser used ordinary
  DNS rather than mDNS. The hotspot DNS fallback must return its own WLAN
  IPv4 for the exact name, never the USB-only address. Reconnect the phone
  after installing it. Private DNS/VPN settings can bypass hotspot DNS.
  On someone else's station Wi-Fi, the stick cannot configure that router's
  DNS; that case still depends on working client mDNS or router configuration.

After the DNS fallback deployment from `5660c77`, the owner confirmed Android
could open `http://openstick.local:8765/hotspot`. Actual hotspot DNS returned
192.168.8.1, named HTTP through that resolver returned 200, and the PC retained
USB resolution and named HTTP 200. Setup service arguments passed actual
dnsmasq syntax validation; its new DNS behavior has not been phone-tested in
setup mode. Real Wi-Fi switching remains a separate hardware check; an HTTP
test with a Host header is not a DNS or phone acceptance test.

Configuration semantics: [Avahi's official configuration reference](https://github.com/avahi/avahi/blob/master/man/avahi-daemon.conf.5.xml.in).
DNS fallback: [NetworkManager shared DNS configuration](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html),
[dnsmasq interface-name, local and SIGHUP semantics](https://dnsmasq.org/docs/dnsmasq-man.html).

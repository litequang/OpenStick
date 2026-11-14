# One local administration URL

Use **http://openstick.local:8765** on a PC connected by USB, a phone or PC
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

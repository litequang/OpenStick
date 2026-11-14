# One local administration URL

Use **http://openstick.local:8765** on a PC connected by USB, a phone or PC
on the same Wi-Fi as the stick, or a phone connected to its setup/SIM AP.
This is a local mDNS name, not a public Tunnel hostname. Wi-Fi still requires
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

No reconnection, radio change, SIM data, SMS/USSD or device reboot is needed.
The same Avahi interface allowlist covers station and hotspot mode; no
simultaneous station/AP support is required.

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

Phone hotspot acceptance and real Wi-Fi switching are separate hardware
checks; an HTTP test with a Host header is not a DNS or phone acceptance test.

Configuration semantics: [Avahi's official configuration reference](https://github.com/avahi/avahi/blob/master/man/avahi-daemon.conf.5.xml.in).

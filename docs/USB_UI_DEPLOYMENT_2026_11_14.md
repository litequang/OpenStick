# USB deployment — local address, usability UI and status icons

## Source and backups

The deployed application matches `ea9fcc8` on
`codex/uz801-v32-postmarketos`. This includes the requested UI integration
`0dda4fcc698e78dbdfdc5cbbfc34e63ba89eb59b`, local-address support in `c3ca851`,
and the status-icon update in `ea9fcc8`. The saved-Wi-Fi implementation from
`76236fd` remains present, including its API, assets and both anchor links.

Before replacement the installer verified installed source hashes against
`76236fd`, accepting only its LF/CRLF variants. It also verified the unchanged
saved-network backend and script. The first deployment backed up all affected
files, preserving their metadata, to:

`/var/lib/openstick/deploy-backups/home-20261114/before-local-address-ui-1794672659.tar.gz`

The subsequent status-icon backup is:

`/var/lib/openstick/deploy-backups/home-20261114/before-status-icons-1794673143.tar.gz`

An earlier icon attempt rolled back successfully when the saved-network smoke
check encountered transient `NETWORK_BUSY`/HTTP 503. The retry accepts only a
bounded number of temporary 503 responses; it then verified the saved list.
Its rollback backup ends in `before-status-icons-1794673100.tar.gz`.

## Files installed

Under `/opt/openstick/uz801_manager`:

- `hosting.py`, `hosting_device.py`, `lan_access.py`, `lan_device.py`, `setup_web.py`
- `static/portal.css`, `static/portal_nav.js`, `static/setup.js`
- `templates/hotspot.html`, `templates/internet.html`, `templates/lan_login.html`
- `templates/lan_settings.html`, `templates/manage.html`, `templates/modem.html`
- `templates/overview.html`, `templates/portal_chrome.html`, `templates/setup.html`
- `templates/website.html`

Configuration added/replaced:

- `/etc/avahi/avahi-daemon.conf` from `scripts/avahi/avahi-daemon.conf`
- `/etc/nftables.d/53_openstick_mdns.nft` from the corresponding source file

The existing distribution Avahi service was started and enabled for boot.
Only the new mDNS rule was added to the live firewall; no ruleset flush or
NetworkManager restart was performed. Only the two administration web services
were restarted. The device was not rebooted by this deployment.

## Resulting behavior

**http://openstick.local:8765** is the common management URL on physical USB,
local station Wi-Fi, and the stick's setup/SIM hotspot. Avahi publishes IPv4
addresses on `usb0` and `wlan0` only, tracks changes, and does not reflect
discovery onto other links. The legacy USB port 80 and AP IP fallbacks remain.
The USB application has a second USB-bound socket on port 8765. The Wi-Fi
listener keeps its own interface binding, login, CSRF and token protections.
Host aliases are explicit and each request still requires its exact Origin.

The requested usability integration is installed. LAN password configuration
is in USB `/manage`, with advanced settings collapsed. It is absent from
the main Wi-Fi page and remains unavailable through the Wi-Fi management API.

The SIM chip now labels the carrier; long names truncate in the header and
remain available in its details. The network chip shows the radio technology
and 0–4 filled signal bars based on fresh modem percentage buckets. Clicking
it opens registration/technology/signal details. Missing, old, locked-SIM or
unregistered readings do not display fresh filled bars. Modem and Wi-Fi chips
and the existing popover close/Escape behavior are retained.

## Validation

- Full suite after the final source change: **387 passed, 1 skipped**. The skip
  is Windows symlink permission. Self-test assets/API/export checks passed;
  JavaScript syntax and diff checks passed. DOM fixtures are synthetic.
- On real USB hardware all ten routes returned HTTP 200 through the named
  Host: `/overview`, `/`, `/manage`, `/internet`, `/setup`, `/hotspot`,
  `/modem/network`, `/modem/sms`, `/modem/ussd`, `/website`.
- The Windows system resolver resolved `openstick.local` to the USB address;
  the PC fetched `/manage` using the actual name with no hosts-file override.
  A multicast query from the PC's physical USB interface received an A reply
  from the device. The original USB address also returned HTTP 200.
- On the station listener, named `/login` returned 200 and unauthenticated
  named/numeric `/manage` returned 302. An unapproved Host returned 403.
- On-device multicast queries received the station address initially and
  `192.168.8.1` while the setup AP was later active. The named setup-AP login
  returned HTTP 200. These are server/network checks, not phone acceptance.
- The saved-list API returned four station profiles with only `ssid` and
  `active` fields. Initially one was active. Later the setup AP was active,
  so zero saved station profiles were active, which is expected for AP mode.
- Eight checked services were running: Avahi, both portals, website,
  Cloudflare Tunnel, modem, policy and setup recovery. The local website on
  loopback port 8080 returned HTTP 200.
- Initial deployment compared protected configuration/website/SSH files and
  confirmed no content changes, no reboot, and the same station connection.
  The deployment did not submit a Wi-Fi switch, send SMS/USSD, activate SIM
  data, alter radio settings, or publish/delete website content.

## Remaining observations and acceptance

The public website returned **HTTP 403 from Cloudflare** from both the PC and
the device while station Internet was available. The origin and Tunnel
service checks passed, but public end-to-end website access is not marked
passed. No public access policy was changed to bypass this response.

Computer Use stopped before visual inspection because URL policy enforcement
is not supported for the current Windows browser (Coc Coc). Visual checks at
360, 390, 430, 768 and 1280 pixels, dock occlusion, actual detail expansion,
browser console errors and direct phone acceptance remain **unverified**.

During later checks the stick was in setup AP mode, with no pending setup
transaction. The owner reports a particular previously working home router
cannot be rejoined, while other Wi-Fi networks can be joined after hotspot
mode. A private comparison found the target's saved key and connection
parameters unchanged from its backup: autoconnect enabled, key present, and
no saved BSSID lock or MAC denylist. The last cached scan saw WPA2 and a
strong signal. Kernel join/config errors with code -5 remain observable;
they do not by themselves establish a wrong password or a blacklist.
The underlying router-specific connection fault is not resolved by this UI
deployment. Do not retest already unsuccessful radio-driver reloads or
security overrides as if they were new findings; see the continuation notes.

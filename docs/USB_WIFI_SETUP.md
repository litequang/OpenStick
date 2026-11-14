# OpenStick USB Wi-Fi setup

Status on the tested FY_UZ801_V3.2 unit: installed. USB HTTP, Wi-Fi status
and scan, public HTTPS through the fixed Cloudflare hostname, and NTP
synchronization passed live checks. Visual browser testing is UNVERIFIED:
Windows Computer Use stopped because it could not confidently determine the
browser URL. See the [execution record](UZ801_V32_INSTALL_SOURCE.md) for
restart verification and remaining limits.

After installation, connect the dongle to a computer and open
`http://172.16.42.1` in a browser. Select **Tìm mạng Wi-Fi**, choose a WPA/WPA2
Personal network, enter its password and select **Kết nối**. Profiles are
saved per SSID with autoconnect enabled. Passwords are never returned by the
API or stored in job history.

For subsequent use on a saved network, a suitable USB power supply is enough;
a computer provides power and management access but is not the Internet
upstream. A different, unsaved network requires USB management to enter its
credentials. This configuration does not create a Wi-Fi hotspot.

The portal listens on `172.16.42.1:80` and binds its socket to Linux interface
`usb0` using `SO_BINDTODEVICE`; failure to bind stops the service. Its API
requires a random same-origin token, strict Host/Origin checks and rejects
cross-site requests. USB access is the administrative trust boundary. The
portal must never be added to Cloudflare Tunnel ingress.

Public static content is served separately by Nginx on `127.0.0.1:8080` from
`/var/www/openstick`. The tunnel routes only the configured public hostname
to that listener. Tunnel credentials, SSH keys, Wi-Fi profiles and device
identifiers remain local and must not be committed.

Nginx runs in the foreground under the OpenRC service
[`openstick-web`](../scripts/openrc/openstick-web). The stock daemon service
is disabled to avoid two services managing the same listener. On this image,
NetworkManager can report started before loopback receives `127.0.0.1`;
stock Nginx then exited with `Address not available`. The foreground service
retries a failed process after three seconds. The portal and tunnel are also
supervised. None of these services changes firmware or partition layout.

For maintenance over the local pinned SSH key, the account is `user` at
`172.16.42.1`. Upload website files using SFTP into `/var/www/openstick`;
Nginx serves changes directly. SSH password authentication and root login
are disabled; authentication is restricted to the USB subnet. SSH listens
without requiring the USB IP to exist at daemon startup, and its default
runlevel is explicitly enabled. Keep the management private key locally.

Chronyd starts automatically; the NetworkManager Wi-Fi-up dispatcher also
restarts it to refresh time after reconnection. An initial clock correction
was needed during first provisioning. A running chronyd process alone is
not proof of synchronization: verify `chronyc tracking` reports a nonzero
stratum and `Leap status: Normal` after startup. Tunnel startup can take
longer while Wi-Fi, DNS and time synchronization become available.

The optional Windows launcher uses key-pinned USB SSH and `sudo -n` against
the Linux account. It requires the local `pmos_known_hosts` pin and
`manager_ed25519` key. The browser portal is intended to work without this
launcher after device installation.

The read-only Android backup Manager retains its existing safety gates.
The Linux Wi-Fi modules contain no flash, erase, restore or firmware APIs.

The installed USB portal also links to `/modem` for SMS/USSD and 3G/4G mode
selection. The inserted SIM is registered and the modem exposes Messaging
and USSD interfaces. A secondary PIN2 report is displayed without treating
it as a primary SIM lock. End-to-end SMS/USSD transactions remain unverified;
see [SMS/USSD readiness and usage](UZ801_SMS_USSD.md). This does not enable
Internet data over the SIM or expose SMS through the public website.

# OpenStick USB Wi-Fi setup

Status: application code tested; device deployment and browser smoke testing
are pending USB SSH recovery. The addresses below describe the configured
target, not an assertion that the service is already running.

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

The optional Windows launcher uses key-pinned USB SSH and `sudo -n` against
the Linux account. It requires the local `pmos_known_hosts` pin and
`manager_ed25519` key. The browser portal is intended to work without this
launcher after device installation.

The read-only Android backup Manager retains its existing safety gates.
The Linux Wi-Fi modules contain no flash, erase, restore or firmware APIs.

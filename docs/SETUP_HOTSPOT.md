# Automatic Wi-Fi setup without SIM

`/hotspot` offers local setup and optional SIM Internet sharing. They use
one physical radio with separate owned profiles. Setup needs no SIM/APN/data.
The installed driver does not advertise simultaneous station/AP operation.

## Prepare once

1. Enable LAN administration and set the manager password over USB.
2. Open `http://172.16.42.1/setup`, enable automatic recovery and select
   **Xem thông tin kết nối** or **Tải thẻ kết nối**.
3. Save the generated SSID/password and local URL on the phone. Wi-Fi and
   manager passwords are separate; there is no public default password.

Recovery is enabled on this particular unit. Its card remains private.

## Use with only power

USB tries saved station networks. After 60 seconds without a connected IPv4
station, the worker makes bounded attempts at up to five available/hidden
autoconnect profiles before broadcasting setup SSID. Join on the phone, accept staying
connected without Internet, and open `http://192.168.8.1:8765/setup`. Log in
with the manager password and enter a 2.4 GHz WPA/WPA2 Personal SSID/password.
Captive-portal auto-opening is not implemented.

Choose a network from the cached scan list or type the name manually for a
hidden SSID. Selection alone never changes the connection. **Quét mạng Wi-Fi**
queues a fresh scan; AP may stop briefly and is restored automatically with
the same credentials. Reconnect the phone to see the new list. Only **Lưu &
khởi động lại để kết nối** submits the entered name/password and starts handoff.

An independent OpenRC worker saves/processes the request after the HTTP
response. It saves a root-private intent and requests one normal reboot,
waiting for any SMS send/active USSD first. New-boot recovery never requests
another reboot: it tries the submitted profile, restores any older same-SSID
profile on failure, and tries other saved autoconnect networks. If none works,
the same setup AP returns, normally within about 1–3 minutes. On success join the same LAN on
the phone; find USB's new DHCP address in the router. Association alone does
not establish Internet. Wrong credentials/unreachable networks restore the
same setup AP when no saved network works. An interrupted request recovers
through saved Wi-Fi or setup AP. A failed reboot request times out without
a reboot loop and restores local setup. The USB page reloads its token after boot.

Existing active SIM hotspot/data is preserved; stop it before changing to
local setup. Setup never grants data consent, creates a bearer or changes
radio preference. A connected station without Internet does not trigger AP.

## Deployment and actual checks

Install the package plus `scripts/openrc/openstick-setup` and
`openstick-setup-dhcp` into `/etc/init.d`, mode 755. Add **only openstick-setup**
to the default runlevel; its worker manages DHCP. Dependencies: NetworkManager,
nftables, dnsmasq, existing authenticated LAN portal.

Setup uses manual `192.168.8.1/24`, WPA2/CCMP, no autoconnect. DHCP binds wlan0,
advertises no router/DNS and runs no DNS resolver. A separate nftables table
drops forwarding through wlan0. USB management stays available.

The tested wcn36xx firmware rejected the optional PMF AES-CMAC management key,
preventing AP initialization. Generated AP profiles set `pmf=1` (disabled)
while retaining WPA2/CCMP. Actual AP, DHCP worker, forwarding filter and login
HTTP 200 were checked. **Owner confirmed entering the setup page on a phone.**
A live fresh scan found three networks and restored AP in about 14 seconds.
A nonexistent-network handoff restored the same AP in about 33 seconds.
The owner's second Wi-Fi connected through the actual setup form. An actual
normal reboot then returned to that Wi-Fi in about 74 seconds, with DHCP,
bound Internet and LAN login HTTP 200. That worker test privately reused the
existing derived keyfile. The older router still fails independently; its
exact compatibility/configuration cause is not established. Full cold
power-only/no-known-network acceptance is recorded separately.

A negative live HTTP test saved an unreachable SSID, rebooted once and
reconnected to another saved working network in about 100 seconds. The
invalid profile was removed, the pending intent cleared and no second reboot
was requested. Normal operation was left on the working second Wi-Fi with
automatic setup recovery enabled.

Credentials/state are root-private. Normal status omits the password; explicit
card/credential endpoints require portal token and LAN authentication and are
never public Tunnel targets.

References: [NetworkManager settings](https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html),
[dnsmasq options](https://dnsmasq.org/docs/dnsmasq-man.html).

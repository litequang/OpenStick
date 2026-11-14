# Opt-in SIM Internet → Wi-Fi hotspot

## Scope and current evidence

This is a standalone 2.4 GHz AP using SIM Internet, not a Wi-Fi repeater.
The physical FY_UZ801_V3.2 running postmarketOS v26.06,
kernel `6.12.1-msm8916`, reports `wcn36xx` AP support and NetworkManager
1.52.2 reports `WIFI-PROPERTIES.AP=yes`. NetworkManager Wi-Fi/WWAN and
dnsmasq are installed. The driver reports no supported interface
combinations, so concurrent STA+AP is not offered.

On 2026-11-14 the installed implementation passed ten live prerequisite
checks: AP capability; initially unconfigured; cellular and AP inactive;
both generated keyfiles accepted by `nmcli --offline`; native checkpoint
creation/extension/destruction; original active connections unchanged;
recovery worker running. Synthetic profile files were deleted afterward.
These checks did **not** activate a bearer or AP.

**End-to-end hotspot remains UNVERIFIED** until a real SIM data session,
phone DHCP/Internet, manager login, public Tunnel and rollback trial pass.
There is no claim of hardware hotspot PASS, throughput, thermal stability,
or power-cycle persistence yet. Windows fixtures: 298 passed, one Windows
symlink-privilege skip, exit 0. The skipped path protection was separately
verified on the Linux device during website-editor testing.

## Use from the panel

1. While still connected over USB or the existing Wi-Fi, open **Wi-Fi & Web
   → Phát Wi-Fi từ SIM 4G**, or `/hotspot`.
2. Set the SSID, WPA2 password (8–63 ASCII characters), channel 1/6/11 and
   APN. An empty APN uses NetworkManager's installed provider database.
   A manually entered APN must come from the operator. Manual APN
   username/password configuration is not offered in this version.
3. **Chỉ lưu cấu hình** writes private profiles with autoconnect disabled;
   it does not start data or replace the current Wi-Fi.
4. To test, explicitly accept cellular data charges and the Wi-Fi role
   change, then choose **Bật thử SIM → Wi-Fi**. The SIM must already be
   unlocked and registered, with no active USSD session. No SIM PIN is sent.
5. The controller first connects SIM data and tests bounded HTTPS over the
   actual modem IP interface, binding DNS to the same interface. Only after
   a successful probe does it replace STA with AP.
6. Connect the phone to the new SSID. Open
   `http://192.168.8.1:8765/hotspot` and log in with the separately configured
   **manager password**. USB management remains at
   `http://172.16.42.1/hotspot`.
7. Check phone Internet and the existing public hostname. If satisfied,
   choose **Tôi đã kết nối được — giữ chế độ này** before the trial expires.
   This enables both profiles' autoconnect for future power-ups. The stored
   AP priority is higher than the saved STA profiles.
8. **Tắt hotspot & dữ liệu SIM** disables those profiles' autoconnect,
   disconnects only OpenStick's data/AP profiles, and attempts the previous
   Wi-Fi profile. SMS/USSD radio is not intentionally disabled. If the old
   Wi-Fi is unavailable, continue through USB.

Enable LAN administration and its password through USB first if phone
management is desired. Its firewall rule, login and Host/Origin checks
also apply in AP mode. Port 8765 is private administration, not a public
Tunnel target. Nginx stays on loopback port 8080; the existing Tunnel
continues to serve the static website when the selected upstream has Internet.

## Trial recovery and limits

Before connecting data, NetworkManager creates a 300-second checkpoint for
only the Wi-Fi and GSM devices. USB is excluded. The local recovery deadline
is 285 seconds, leaving a margin before native rollback. Neither new profile
autoconnects during a trial. Without **keep**, native rollback and the
independent OpenRC recovery worker restore prior device connections.

Pending state includes boot identity and monotonic deadlines locally, never
in public reports. A reboot during an unconfirmed trial causes the worker
to disable trial autoconnect and restore the saved Wi-Fi profile. A failed
partial keep also remains recoverable. A live checkpoint must be extended
before committing persistent autoconnect settings. These failure paths have
fixture coverage; disruptive hardware rollback/power-loss tests remain pending.

Wi-Fi scan/connect/speed operations in the Manager are blocked while a trial
or saved hotspot mode is active; stop hotspot first. The same process lock
serializes these operations with hotspot transitions. Existing SMS/USSD
operations use a separate shared modem lock during transitions. Existing
third-party cellular sessions are refused rather than taken over.

WPA2 credentials are stored only in root-only NetworkManager profiles, using
a derived PSK rather than a plaintext passphrase. No password is returned
by status or placed in command arguments/logs. Only fixed bounded probe
URLs are allowed. Roaming is disabled in the generated cellular profile.
Starting/keeping the mode authorizes data use; it is not enabled on install.

Saved Wi-Fi roaming, selectable Wi-Fi/SIM failover, phone-style SMS threads
and SMS archive/delete are separate unfinished work. This feature does not
claim those functions are implemented.

## Primary references

- [NetworkManager IPv4 settings](https://networkmanager.dev/docs/api/latest/settings-ipv4.html):
  `shared` belongs on the downstream interface and provides forwarding;
  the AP profile explicitly selects its subnet and has no default route.
- [NetworkManager checkpoints](https://networkmanager.dev/docs/api/latest/gdbus-org.freedesktop.NetworkManager.html):
  timed automatic rollback and checkpoint methods. The installed 1.52.2
  instance was checked for create/extend/destroy compatibility.
- [GSM settings](https://networkmanager.dev/docs/api/latest/settings-gsm.html):
  provider-database auto-configuration and home-only operation.
- [Wi-Fi settings](https://networkmanager.dev/docs/api/latest/settings-802-11-wireless.html):
  AP mode and 2.4 GHz configuration. Actual board evidence above is required
  in addition to these generic API descriptions.

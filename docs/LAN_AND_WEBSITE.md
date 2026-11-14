# Wi-Fi administration and static website editor

## Open the manager from a phone

Connect through USB first at `http://172.16.42.1/`. Under **Quản trị từ
điện thoại qua Wi-Fi**, set and repeat a password of 12–128 characters.
There is no default password. Open the displayed Wi-Fi address, port 8765,
on a phone on the same LAN. The address comes from DHCP and can change.
Guest/client isolation on the access point can prevent access.

The Wi-Fi listener is bound to `wlan0`, separate from USB, Nginx and Tunnel.
Install [the narrowly scoped firewall rule](../scripts/nftables/52_openstick_lan.nft)
in `/etc/nftables.d/52_openstick_lan.nft`; validate with
`nft --check --file /etc/nftables.nft` before applying. The OpenRC
[LAN service](../scripts/openrc/openstick-lan) needs NetworkManager and
nftables. Without this rule, the stock postmarketOS input-drop policy
silently blocks the port despite a healthy listener. Do not open WWAN
ingress or change forwarding for administration.

Passwords are PBKDF2 hashed in a root-only local configuration. Sessions
expire after eight hours; disabling LAN or changing credentials invalidates
them. Requests retain strict Host/Origin checks, CSRF on forms and random
API tokens. Login throttles apply globally and per client. This listener
uses HTTP on the trusted local Wi-Fi; it does not provide TLS encryption.
Never add it to Cloudflare Tunnel or forward it through a router.

Native login/logout forms need `Referrer-Policy: same-origin`. Under
`no-referrer`, browsers can send `Origin: null` for form POSTs, which the
strict origin guard correctly rejects. This behavior is specified in
[Fetch's Origin-header algorithm](https://fetch.spec.whatwg.org/#append-a-request-origin-header).
Opaque/null and foreign origins remain blocked. USB retains `no-referrer`.

On 2026-11-14 the real unit returned HTTP 200 for LAN `/login`, unauthenticated
private routes redirected to login, and the owner confirmed successful login
from a phone after the firewall and form-policy fixes. No owner password
was read or reset during verification.

## Manage the static website

Choose **Wi-Fi & Web → Quản lý website**, or open `/website` in the private
manager. It supports:

- Selecting and editing UTF-8 HTML, CSS, JavaScript, JSON, SVG and text files.
- Creating files and directories through paths such as `assets/style.css`.
- Uploading static images/fonts and replacing an explicitly selected file.
- Deleting a selected file after confirmation.
- Opening the public hostname in a separate tab.

**Lưu và xuất bản** changes the Nginx-served file immediately; Cloudflare or
browser caches can delay its public appearance. The initial website is not
modified by installing the editor. Limits: 1 MiB per file, 500 managed files,
64 MiB total. Stale edits are refused using SHA-256 versions. Directory
traversal, hidden paths, symlinks and non-static extensions are rejected.
No arbitrary shell, PHP, Node.js, WordPress, Nginx configuration, Tunnel
credential or system-file editor is exposed. Uploaded HTML/JS runs only on
the public website origin, never as a manager preview.

The editor is a single-site file manager, not a multi-site/domain hosting
control panel. There is no ZIP deployment, version history or undo yet.

## Hotspot evidence and current limits

Read-only `iw phy` on this FY_UZ801_V3.2 unit with kernel
`6.12.1-msm8916` reported the `wcn36xx` driver, `managed`, `AP`, `AP/VLAN`
and monitor modes, on 2.4 GHz channels. It also reported **interface
combinations are not supported**. This is evidence for trying a standalone
AP, not proof of a working Internet-sharing hotspot or simultaneous
Wi-Fi STA+AP. Do not promise concurrent upstream Wi-Fi and hotspot.

SIM Internet, DHCP/NAT hotspot clients, throughput, stability and actual
LTE-to-AP routing remain **UNVERIFIED**. No hotspot was activated, no Wi-Fi
connection was switched, and no cellular data session was started in this
check. A standalone hotspot trial would replace the current STA role and
needs a working, explicitly selected cellular upstream first.

An opt-in [SIM → Wi-Fi implementation](SIM_WIFI_HOTSPOT.md) is now installed.
Its prerequisite checks passed, but the end-to-end cellular/AP trial is still
unverified. Installation did not activate either data or the hotspot.

## Validation of this update

Windows: 267 tests passed, one OS symlink-creation test skipped because the
local account lacks that privilege, exit code 0. The same symlink rejection
was tested successfully on the Linux USB, alongside binary-exact upload.
The rendered editor script was also executed with synthetic DOM/API fixtures;
this is not a screenshot or visual browser test.

Live checks: 13/13 LAN/editor checks and 18/18 existing Wi-Fi/website/Tunnel
checks passed. The original index remained byte-identical; the temporary
public test file was deleted. The modem stayed registered, 4G-only, and the
operation journal did not gain any SMS/USSD send attempts. No cellular data
or hotspot was activated. The owner confirmed LAN login, but has not yet
confirmed the new editor's visual layout.

One older modem verifier checked only the text `unmanaged-devices=type:wwan`
and labelled it `wwan_unmanaged`. That assertion is not runtime evidence:
NetworkManager's actual GSM device `Managed` property is **true**, state 30
(disconnected). No SIM data profile has been configured here. Future Internet
policy work must use runtime device/profile state and must not claim that
the existing configuration text isolates NetworkManager from the modem.

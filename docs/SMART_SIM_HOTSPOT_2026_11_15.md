# OpenStick UZ801 V3.2 — smart SIM hotspot deployment, 2026-11-15

## Requested behavior

When an isolated setup Wi-Fi hotspot is already running, the owner should be
able to enable SIM-backed Internet without first stopping that setup hotspot.
The phone reconnects to the **same SSID and password**; admin remains at
`http://192.168.8.1:8765/hotspot` or
`http://openstick.local:8765/hotspot` when name resolution works. A PC on
USB Ethernet can manage the same portal; backup route is
`http://172.16.42.1:8765/hotspot`.

## Implementation and safety

- The normal `Start` action requires the owner's existing data/charge consent
  and confirmation. Merely loading the page or checking state never activates
  the modem. The driver does not support simultaneous Wi-Fi station + AP.
- If setup AP is running, the backend snapshots prior hotspot configuration
  and profiles, creates a NetworkManager checkpoint, copies the setup AP
  Wi-Fi identity into the SIM-sharing AP profile, and verifies that Internet
  access is bound to the SIM interface before changing the Wi-Fi AP mode.
- The setup AP's isolated DHCP/firewall services are handed over to shared
  Internet mode at the transition. The browser may lose its request during
  handoff: it polls read-only status; it does not replay a possibly successful
  POST. A separate Wi-Fi/USB listener can recover real state by backend status.
- A pending trial is recoverable on failure or timeout. The owner has about
  five minutes to reconnect and press **Keep**. Stop restores the previous
  local setup service and the pre-handoff hotspot configuration, including
  retained APN profile. Modem access remains governed by the shared locks.
- The private snapshot/receipt files live on the device under
  `/var/lib/openstick/` and are never tracked in Git.

## Validation and hardware installation

- Source validation: `python -m pytest -q`: **448 PASS, 1 SKIP** (Windows
  symlink privilege), no failures. JavaScript syntax, Python compilation and
  `git diff --check`: PASS. The tests include backend handoff/rollback,
  reconnect to another listener and a busy lock.
- USB accessed over its existing USB Ethernet/SSH administration path; only
  these files were installed under `/opt/openstick/uz801_manager/`:

  | File | SHA-256 installed |
  | --- | --- |
  | `hotspot.py` | `7abbc733c66022a45c4863e0d55916e6c1675075b6dd0cda017460103f1e3fdf` |
  | `hotspot_web.py` | `0f7700f68eef608094a4b45f56504f13fc07406ecb1b1ba6a61909a59c5497b5` |
  | `templates/hotspot.html` | `3263f3807f04341420bc8ee4b6a5d958c66e64009ab87da29d344ca3d402f962` |

- Existing file backup:
  `/var/lib/openstick/deploy-backups/home-20261114/before-smart-hotspot-1794703089.tar.gz`.
  The prior hashes were respectively:
  `54609fc64cbf45e97dbc90d1088934843c26c76e9514b7f00ce76586f`,
  `b9587420cbafed23f3227876f3b758de2d1a0e2a300328740045b436c4fd3059`,
  `0f1339e77b45e1a36ba2b10b0214aadd17cd9ad94347346d8cbe7c598d10cd41`.
- Restarted `openstick-hotspot`, `openstick-wifi`, `openstick-lan` only; all
  started. HTTP `/hotspot`, `/overview`, `/setup` returned 200 from USB.
  WLAN was still on the setup UUID, with no pending hotspot/setup trial.
  No NetworkManager restart, reboot, SIM activation or actual AP handoff was
  made during the deployment smoke test.

## Owner acceptance on phone (not yet run)

1. Join the USB's currently running setup Wi-Fi on the phone, visit
   `http://openstick.local:8765/hotspot` (fallback IP above), and check the
   existing network name. The admin password is separate from Wi-Fi password.
2. If the SIM plan should be used, tick the data/cost consent and select
   **Bật thử SIM → Wi-Fi**. Observe whether the phone disconnects briefly;
   reconnect to the **same Wi-Fi** without changing its saved password.
3. Confirm the phone receives a local IP, can browse an external website,
   and can still open the OpenStick admin portal. Then press **Tôi đã kết nối
   được — giữ chế độ này** before the five-minute trial expires.
4. Select **Tắt hotspot & dữ liệu SIM** and verify the setup AP is restored
   without changing its SSID/password; the admin portal stays accessible.
   If the SIM test fails, report the exact status text and use USB Ethernet.

**Not accepted yet:** Live SIM-backed Internet through the setup-origin AP,
physical phone reconnect/Keep/Stop and reboot persistence. Simulation, HTTP
200 and an advertised AP capability do not establish those results.

## Rollback

Use the private on-device backup archive above to restore the three package
files to `/opt/openstick/uz801_manager/`, then restart the three listed
OpenRC portal services. Verify management over USB and check the setup AP
state before attempting any network changes. Do not roll back runtime
credentials, NetworkManager secrets, APN or the owner's saved radio choice.

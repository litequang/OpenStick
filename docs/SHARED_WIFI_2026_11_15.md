# OpenStick UZ801 V3.2 — shared setup/SIM hotspot Wi-Fi, 2026-11-15

## User-visible change

There is one editable SSID, Wi-Fi password and 2.4 GHz channel for the USB's
setup/recovery Wi-Fi and SIM-backed hotspot. Edit these on
`http://openstick.local:8765/setup#usb-ap-settings`; from `/hotspot`, follow
the "Cài đặt Wi-Fi USB" link. APN remains configurable separately on
`/hotspot#sim-apn`. Saving shared Wi-Fi parameters changes the next activation;
it does not interrupt the current AP. The UI explains this delay. Changes are
rejected while a network handoff is waiting for user confirmation.

This is the Wi-Fi **transmitted by** the USB, not a saved household Wi-Fi the
USB connects **to**. This adapter does not advertise simultaneous STA and AP.
The existing SIM data-charge consent and 5-minute Keep/rollback remain in place.

## Source verification

`python -m pytest -q`: 465 passed, 1 skipped (Windows symlink privilege).
Python/JavaScript syntax and `git diff --check`: passed. Includes backend
configuration, staged changes while hotspot is active, pending-handoff guard,
SSID escaping, UI identity and header signal retention test coverage.

## Real-device deployment

Target: existing `user@172.16.42.1` USB Ethernet SSH administration path.
Seven staged files were SHA-256 checked against the current installation before
replacement. Previous files were archived on USB at:

`/var/lib/openstick/deploy-backups/home-20261114/before-shared-wifi-1794707861.tar.gz`

Archive verified to contain seven files. Installed file SHA-256:

| Relative to `/opt/openstick/uz801_manager/` | SHA-256 |
| --- | --- |
| `hotspot.py` | `901dac2ffd6aa3327ff6fdfcbbc0c12a8351e7d6327867fa6850296165b253c8` |
| `setup_ap.py` | `62a83027ee64153e6d7e6d933e7c6f7ca5f7231bdf5e80729c419e3424fa2004` |
| `setup_web.py` | `f5a71a87f5b18bf0fdf0e382b7d2707c4b68fa553fc4c0d1a896b03bff2b80ae` |
| `static/portal_nav.js` | `37c4c17284f300e80faf884151f7c6b32283d04f341732d0e744720e48958402` |
| `static/setup.js` | `9c84abe8cead7b723b062c35e737e1fd752342c992ccc4168cc8694de91a2011` |
| `templates/hotspot.html` | `f071178580a1392b7321889dd79987bf5e1249fb27a2bb60debd594860063fe9` |
| `templates/setup.html` | `2b2cbae326b7a5ec9352549bf7d4682afdc37106d7f9bd45f19bbb3f46a6385b` |

Only `openstick-hotspot`, `openstick-wifi` and `openstick-lan` were restarted;
all were started after deploy. All seven installed hashes matched the manifest.
USB Ethernet HTTP `/setup`, `/hotspot`, `/overview`, `/static/setup.js` and
`/static/portal_nav.js` returned status 200, and expected page/JS markers were
present. `wlan0` still used the same NetworkManager connection
`openstick-64c2ad14edc821c1` before and after deployment. No setup or SIM
trial was pending. No router changes, modem activation, reboot or Wi-Fi mode
switch was made during installation. The owner's website, Tunnel, LAN password,
SSH authorization and saved radio profile were not intentionally changed.

## Owner acceptance on a phone

1. With the phone connected to the USB's current Wi-Fi, open
   `http://openstick.local:8765/setup#usb-ap-settings`. Confirm that editing
   the transmitted SSID, password and channel happens in one form.
2. Open `/hotspot` and verify it shows that shared Wi-Fi configuration and a
   link to edit it, without a second password/SSID form. APN remains separate.
3. Only when ready to reconnect, change the transmitted SSID or password and
   save. Confirm the **current** active AP stays reachable, and that the change
   appears at the next manually initiated AP activation. Connect with the new
   credentials and confirm `openstick.local:8765` plus Internet access as
   appropriate for SIM-backed operation.
4. If performing a SIM hotspot trial, accept the existing data-charge consent,
   reconnect and press Keep within five minutes. If network management is
   unavailable, USB Ethernet management remains at `172.16.42.1:8765`.

No phone browser visual test, actual Wi-Fi credential change, reactivation,
full SIM Internet trial, reboot persistence or Keep/Stop hardware workflow was
performed as part of this deployment. The source tests and HTTP 200 do not
replace those physical checks.

## Recovery

The deployment archive above contains the seven previously installed files,
relative to `/opt/openstick/`, under `uz801_manager/`. Restore these files
only when necessary from a working USB Ethernet session, and restart only the
three portal services, verifying login and the existing Wi-Fi role afterward.
Never overwrite `/var/lib/openstick` owner state or NetworkManager profiles
with the source tree.

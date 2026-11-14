# LED settings and SIM hotspot diagnostics on the actual USB

## Installed source and access

Branch: `codex/uz801-v32-postmarketos`. The application now includes
`ca346d7` (LED settings), `84b5426` (visible APN settings and persistent errors),
and `3bd728a` (NetworkManager DNS array parsing and trial confirmation gating).
The common management address remains `http://openstick.local:8765`.

- LED controls: `/settings/leds`, linked from `/manage`.
- SIM APN: `/hotspot#sim-apn`, outside the advanced disclosure.
- Existing USB and AP numeric address fallbacks remain available.

## LEDs: verified capabilities and limitations

The actual driver exposes three binary case LEDs: `red:power`, `green:wlan`,
and `blue:wan`, each with maximum brightness 1. `mmc0::` is excluded. The UI
offers only supported triggers: default, off, on, timer blink, heartbeat,
Wi-Fi radio/link/RX/TX. Blink on/off durations are 100–5000 milliseconds.
Wi-Fi triggers indicate radio activity, not working SIM Internet.

Settings use a separate LED lock and an atomic private settings file.
Opening the page or selecting values does not write to the driver. Save
applies supported choices, rolls back on failure, and persists the baseline
needed for Default. The enabled `openstick-led` OpenRC service reapplies saved
choices at boot; absent settings cause no writes.

Actual driver verification used a temporary private configuration: blue on,
then timer 250 ms on / 750 ms off, sampled brightness values 0 and 1, and a
new backend instance replaying the saved temporary settings. All original
case LED states were restored, `mmc0::` remained unchanged, and the owner's
LED settings file was preserved. This verifies driver behavior, not optical
inspection or an actual reboot of the new boot service.

## APN and the actual SIM Internet fault

The real cellular profile used `auto-config=true`, no explicit APN, and an
installed provider database. The UI previously hid APN under Advanced.
It now shows automatic/manual selection and the saved mode directly.
**Chỉ lưu APN** updates only the managed GSM profile and APN metadata, retaining
the hotspot's Wi-Fi key and other cellular profile settings. It neither
activates data nor changes radios. Live hotspot/trial/cellular and enabled
policy states block this edit. A load/persistence failure restores the
previous profile and metadata. There is no guessed carrier preset.

While a real trial was pending, the device had a cellular link but no active
AP. A bounded HTTPS request bound to that SIM interface returned HTTP 204.
The application's stricter probe failed because this NetworkManager version
rendered multiple IPv4 DNS servers as `A | B` on one line. The old parser
expected one address per line and rejected that value. Passing the unsplit
value to curl also returned argument error 43. Splitting and validating the
addresses, while binding BOTH HTTPS and DNS to the SIM interface, returned
HTTP 204 on the actual device. Thus automatic APN worked for that observed
trial; signal registration alone was not used as proof.

`3bd728a` accepts newline and pipe-separated DNS arrays, validates every
address used, and keeps interface-bound DNS/HTTPS checks. The AP still starts
only after that probe passes. After deployment the owner retried and explicitly
confirmed the phone saw the USB Wi-Fi and could access the Internet. A fresh
device check also showed AP active, cellular connected, a successful Start
result, and the corrected SIM-bound Internet probe passing. This is now actual
phone acceptance for that trial, not merely an outbound device probe.

## Trial and error presentation

Last mutating action errors persist separately from status refreshes, shared
between USB/LAN app instances. Only action, allowlisted error code and time
are stored; raw modem errors, APNs, profile IDs and credentials are excluded.
The UI distinguishes cellular connection, Internet probe and AP start errors.

The owner's screenshot showed an unready AP but an enabled Keep button.
Keep now requires a pending, unexpired trial, an active AP and a cellular
link. An unready AP displays a recovery countdown instead of suggesting
confirmation. The five-minute trial rollback design remains; removing it
was not requested explicitly. Do not press Keep on the owner's behalf:
phone connectivity is for the owner to confirm.

A trial was observed during the first diagnostics web-service update. Its
origin was not attributed; it may have overlapped the service restart, so
do not claim that trial's interrupted progress solely proves the DNS bug.
The DNS parser defect and successful corrected probe were verified
independently on its active SIM link. The independent recovery service later
cleared pending state and stopped trial cellular data. The DNS update waited
for that recovery before restarting web services.

## Deployment and checks

Version-checked backups, on the actual USB:

- `/var/lib/openstick/deploy-backups/home-20261114/before-led-settings-1794657473.tar.gz`
- `/var/lib/openstick/deploy-backups/home-20261114/before-hotspot-diagnostics-1794658111.tar.gz`
- `/var/lib/openstick/deploy-backups/home-20261114/before-hotspot-dns-1794658418.tar.gz`

Device time was observed to differ from the PC's date; backup names above
are exact observations. LED deployment installed its app assets and OpenRC
script. Diagnostics changed four package files; DNS follow-up changed only
`hotspot.py` and `templates/hotspot.html`. Only `openstick-wifi` and
`openstick-lan` were restarted; no reboot, NetworkManager restart, firmware,
partition, radio-mode, SMS or USSD operation was initiated by these updates.

Real checks: management/static endpoints and LED/APN pages HTTP 200, LED
discovery, authenticated hotspot status API, services running. Protected
website, SSH, Tunnel, network profile and selected settings files compared
unchanged across the APN and DNS deployments. Five station profiles remained
saved, zero active at those checkpoints. No owner SSID or secret is recorded
here. Setup and network policy remained disabled by the owner.

Tests before DNS follow-up: full suite **422 passed, one Windows symlink
skip**; after DNS/UI follow-up, focused hotspot tests **45 passed**, and
hotspot/policy tests including DNS changes **70 passed**. Self-test, JS
syntax and diff whitespace checks passed. These are synthetic checks;
actual hardware evidence is described separately above. Final full-suite
for `3bd728a`: **424 passed, one Windows symlink skip**, 89.23 seconds.

Deployment checkpoint: cellular disconnected, hotspot inactive, no pending
trial. The owner's subsequent retry succeeded: phone Wi-Fi and Internet were
confirmed by the owner. Latest read: cellular/AP active, pending trial with
222 seconds remaining, enabled false, last action Start with no error, and
SIM-bound probe true. The owner was told to use Keep if they want persistence;
the agent did not press it. Persistent autostart and a fresh phone test after
reboot are not verified. The local common URL over the phone's actual network
stack was not separately accepted in this test. Read fresh state before any
service update, and never restart web services during an in-flight trial.
The older home-router station incompatibility and public website Cloudflare
403 remain separate unresolved investigations.

References: [Linux LED class](https://docs.kernel.org/leds/leds-class.html),
[NetworkManager GSM APN and auto-config](https://www.networkmanager.dev/docs/api/latest/settings-gsm.html).

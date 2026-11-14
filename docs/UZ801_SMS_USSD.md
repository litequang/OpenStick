# SMS and USSD readiness on the installed UZ801 V3.2

Checkpoint: 2026-11-14. The user requested research and installation of suitable
SMS/USSD tools while retaining the working static site and Wi-Fi Internet.
Initial discovery ran without a SIM. The owner subsequently inserted one;
the same device now reports a present SIM and state `registered`. SMS/USSD
transactions still require an explicitly chosen destination or USSD code.

## Results on the real USB

| Check | Result |
|---|---|
| Linux modem remoteproc | Running after starting the packaged RMTFS service |
| Original modem firmware | Loaded from the existing read-only modem partition |
| Modem revision | `UZ801_V3.0_21_V01R01B10`, dated September 2015 |
| Control ports | `/dev/wwan0at0`, `/dev/wwan0at1`, `/dev/wwan0qmi0` present |
| ModemManager | Initially `failed/sim-missing`; after insertion, one modem `registered` |
| QMI control query | PASS through qmi-proxy; WMS 1.10 and Voice 2.1 advertised |
| SMS send and receive | Messaging interface present; end-to-end send/receive UNVERIFIED |
| USSD | MobiFone account response received via NetworkNotification; method result still unreliable |
| Mobile data | No bearer/APN configured; NetworkManager WWAN remains unmanaged |

Installed from the configured official repositories: ModemManager
`1.25.95_git20260527-r1`, its OpenRC service, qmi-utils/libqmi
`1.38.0_git20260414-r0`, RMTFS `1.3-r0` and its OpenRC service.
RMTFS and ModemManager were added to the default runlevel.

The installed RMTFS configuration has `rmtfs_avoid_writing="true"`; its actual
process arguments were checked as `-s -P -r`. In this mode RMTFS reads original
NV partitions and services changes using RAM shadows instead of persisting
them to those partitions. No modem firmware, GPT, calibration or bootloader
was flashed. No SIM unlock, PIN guess, AT initialization, SMS deletion, message
forwarding or cellular data connection was attempted.

RMTFS read-only mode does not prove SMS storage survives a reboot. SMS storage,
host-side persistence, multipart/Unicode handling, delivery behavior and USSD
session handling still require tests with this unit and its SIM/operator.

## Evidence and limits

- The [first-hand FY_UZ801_V3.2 SMS report](https://alastair.d-silva.org/sending-receiving-smses-using-cheap-4g-lte-modems)
  describes working SMS using stock modem firmware and SMStools3 through an AT
  port. It is supporting evidence for this board revision, not a test of this
  unit or proof of USSD support. No attached third-party firmware was installed.
- [ModemManager's Qualcomm layout documentation](https://modemmanager.org/docs/modemmanager/wwan-device-types/)
  identifies the WWAN AT/QMI control-port model used by MSM8916. A control port
  alone does not establish SMS or USSD functionality.
- The official [Messaging interface](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.Messaging.html)
  requires a valid unlocked SIM before listing or sending messages. The
  [USSD interface](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.Modem3gpp.Ussd.html)
  has the same prerequisite. Their current absence while SIM is missing is
  not evidence that this modem cannot support them.
- [RMTFS 1.3 storage implementation](https://github.com/linux-msm/rmtfs/blob/v1.3/storage.c)
  implements RAM shadows for `-r`; the
  [packaged OpenRC configuration](https://github.com/alpinelinux/aports/blob/3.24-stable/community/rmtfs/rmtfs.confd)
  defaults to avoiding storage writes. Both the installed configuration and
  running arguments were inspected on this device.

WMS/Voice service versions are necessary discovery evidence, not proof that
every SMS/USSD request is implemented or accepted by a particular operator.
The initial SIM-missing state did not justify a firmware change.

After insertion, `UnlockRequired` was `SIM_PIN2` (3), while the modem was
already registered. The initial manager incorrectly treated every value
except `NONE` as blocking. It now follows the
[upstream ModemManager lock handling](https://github.com/linux-mobile-broadband/ModemManager/blob/main/src/mm-iface-modem.c):
`NONE`, `SIM_PIN2` and `SIM_PUK2` allow operation; a modem explicitly in the
`locked` state remains blocked. Primary PIN/PUK and unknown lock values still
block actions. No PIN/PUK was entered, and no retry counter was decremented
by this manager. Regression tests cover both secondary and primary locks.

## When a SIM is available

1. Shut down Linux normally, remove USB power, then insert the SIM in the
   correct orientation. Do not insert/remove the SIM while powered.
2. Boot normally and verify modem/SIM state, required lock, registration and
   exposed Messaging/USSD interfaces. Do not guess a PIN or collect SIM/device
   identities into a public report. Enable only the control plane if needed;
   keep mobile data unmanaged and the web's default route on Wi-Fi.
3. Have the owner send an ordinary test SMS to the SIM. Verify reception
   locally without forwarding SMS/OTPs or publishing message contents.
4. Send a test SMS only to an explicitly selected destination, and initiate
   only an explicitly selected USSD code. Record actual success/failure and
   possible carrier limitations; do not automatically retry an uncertain send.
5. Test restart, receive persistence and private browser access separately.

## Installed USB manager

Open `http://172.16.42.1/overview`. The bottom dock separates **SMS**
(`/modem/sms`), **USSD** (`/modem/ussd`), **Wi-Fi & Web** (`/`) and
**Mạng SIM** (`/modem/network`). `/modem` redirects to SMS for old bookmarks.
Header icons show modem, SIM, network and signal; click each for details.
The enable button appears only on Mạng SIM when the modem is actually disabled.
Outgoing actions require explicit confirmation. Missing or
primary-locked SIMs disable network actions and mode changes in both the UI
and backend. With the inserted SIM registered, SMS/USSD controls are now
available. Stored SMS reads do not delete messages from the modem.

The device advertised the following `SupportedModes` pairs on the real bus:

| Allowed / preferred | Meaning |
|---|---|
| 4 / 0 | 3G only |
| 8 / 0 | 4G only |
| 12 / 8 | 3G/4G, prefer 4G |
| 12 / 4 | 3G/4G, prefer 3G |

`CurrentModes` initially was `8 / 0`. The owner subsequently saved 4G-only,
then explicitly authorized one temporary `12 / 8` comparison and restoration.
Both mode changes succeeded, and current and saved modes were verified back
at `8 / 0`. The modem reported LTE during the mixed-mode comparison; this was
not a 3G registration test. A mode change must exactly
match an advertised pair and uses the documented
[SetCurrentModes method](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.html#gdbus-method-org-freedesktop-ModemManager1-Modem.SetCurrentModes).
The selected pair is saved in root-private `/var/lib/openstick/radio.json`
and re-applied on a later boot only if still supported. 4G-only excludes 3G;
it does not choose a specific LTE frequency band. Reboot persistence with a
working SIM, 3G coverage and interactive USSD menus remain UNVERIFIED.

## Authorized MobiFone USSD test

The owner requested a live test and separately approved a temporary mixed-mode
comparison followed by restoration to 4G-only. The agent issued one `*101#`
account query in each mode. No service subscription code or SMS was sent.
The method calls returned errors/unknown outcomes; later a nonempty 96-character
MobiFone account notification appeared, whereas earlier reads were empty.
Its contents and subscriber identifiers remain local. Current and saved modes
are back at 4G-only, registered, with the USSD session idle.

This verifies receipt of an operator account response on this unit. It does
not prove the mode switch fixed the problem: access technology remained LTE
during the mixed-mode test, and asynchronous notification timing is a separate
issue. Initiate/Respond now allow 115 seconds instead of abandoning a QMI
operation at 60 seconds; the
[upstream QMI implementation](https://github.com/linux-mobile-broadband/ModemManager/blob/main/src/mm-broadband-modem-qmi.c)
uses a 100-second operation timeout. Extending the timeout alone does not fix
an immediate method error.

The UI displays pending/idle/user-response state, retains the last method
result in RAM across status refreshes, and shows NetworkNotification separately
as the modem's last notification, with no invented receipt timestamp or promise
that it belongs to the latest request. Error categories are fixed/redacted;
the persistent journal records no code, reply, number or balance. Unknown
outcomes never trigger automatic retransmission. Interactive replies and
reliable Cancel method completion remain UNVERIFIED.

The `openstick-modem` OpenRC service checks readiness every 30 seconds. It may
enable the radio when a valid unlocked SIM is ready, and restore the saved
radio-mode choice. Each automatic mutation has a bounded retry count. It never
enters a PIN, initiates SMS/USSD or creates/connects a packet-data bearer.
Device operations share a nonblocking Linux file lock across the UI and this
service; an active USSD session prevents radio-mode changes.

SMS/USSD attempts write an exclusive, fsynced UUID receipt before transmitting.
Receipts contain action type, time and outcome, not destination, text, USSD
code or reply. A repeated UUID is refused even after a process restart.
Unknown send results are not automatically retried. A successful SMS Send
method means submission, not verified delivery to the recipient.

The manager reads only whitelisted DBus properties for status. It discovers
paths by introspection rather than exporting GetAll/GetManagedObjects data.
Message contents and replies stay in the private USB UI, not application logs
or the public static root. The same USB-interface binding, token and Host/Origin
guards used by Wi-Fi management protect all modem routes. Plain HTTP USB
operation does not depend on the secure-context-only `crypto.randomUUID()`.

Wi-Fi remains the Internet upstream. Internet over the SIM, APN setup and
failover are not implemented in this manager and were not enabled.
NetworkManager has an official
[gsm.auto-config option](https://networkmanager.dev/docs/api/latest/settings-gsm.html)
to obtain APN settings from its provider database; enabling that setting is
different from activating a data connection. A future SIM-data option needs
real APN/bearer/route/HTTPS tests on this unit.

The public Cloudflare hostname routes only to the static Nginx site and must
not expose modem administration or SMS content.

## Validation boundaries

- Automated backend/API and synthetic JavaScript UI fixtures cover no-SIM,
  lock and registration gates, unsupported radio modes, active USSD sessions,
  typed DBus calls, durable duplicate prevention and uncertain sends, input
  validation, confirmation reset, private-HTTP UUID generation, and safe text
  rendering. Fixture SMS/USSD results are not network tests.
- Live USB HTTP checks passed first with no SIM, then with the SIM registered
  and the PIN2 report correctly handled. Messaging and USSD interfaces were
  present, with USSD idle. Checks cover advertised modes, security guards,
  rejection of raw/data commands, absence
  of identity fields, running services, read-only RMTFS and no additional
  transmissions during the read-only audit. Typed DBus dictionary/tuple encoding was checked offline without
  sending those messages.
- An earlier Windows Computer Use attempt could not determine the browser
  URL. The latest Edge capture failed twice with channel/capture timeouts.
  The owner later confirmed the dark dashboard, bottom navigation and header
  popovers work on the real portal. This is owner-observed acceptance;
  automated screenshot inspection and independent narrow-window visual
  acceptance remain unverified.
- Sending/receiving SMS, interactive USSD, actual 3G registration and mobile
  data remain UNVERIFIED. An account response was received as described above.
  No outgoing cellular test runs merely by opening a page. The local suite
  passed 238 tests (exit 0); 25 live modem checks, 14 dashboard/Wi-Fi metric
  checks and 18 hosting checks passed (each exit 0).

Raw hardware observations stay under ignored private directories. This report
contains no IMEI, IMSI, ICCID, phone number, SMS content or calibration data.

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
| USSD | USSD interface present and idle; operator transaction UNVERIFIED |
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

Open `http://172.16.42.1/modem`, or select **SMS / USSD và trạng thái 4G**
from the Wi-Fi page. The installed interface includes modem/SIM status, an
inbox, SMS composition, USSD initiation/reply/cancellation and a radio-mode
selector. Outgoing actions require explicit confirmation. Missing or
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

`CurrentModes` was `8 / 0`; this was read, not applied by this installation.
No radio preference has yet been saved or changed. A mode change must exactly
match an advertised pair and uses the documented
[SetCurrentModes method](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.html#gdbus-method-org-freedesktop-ModemManager1-Modem.SetCurrentModes).
The selected pair is saved in root-private `/var/lib/openstick/radio.json`
and re-applied on a later boot only if still supported. 4G-only excludes 3G;
it does not choose a specific LTE frequency band. Actual selection, persistence
with a working SIM, coverage behavior and SMS/USSD in LTE-only remain UNVERIFIED.

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
  of identity fields, running services, read-only RMTFS and empty attempt
  journal. Typed DBus dictionary/tuple encoding was checked offline without
  sending those messages.
- A Windows Computer Use attempt stopped because it could not confidently
  determine the browser URL. Visual browser layout remains UNVERIFIED; a
  synthetic DOM fixture and HTTP checks are not a real-browser visual PASS.
- Sending/receiving SMS, operator USSD, switching radio technologies and mobile
  data remain UNVERIFIED pending actual operator tests. No outgoing network
  test is run merely by opening the page. The local suite passed 212 tests
  (exit 0); 20 live modem checks and 18 hosting checks passed (each exit 0).

Raw hardware observations stay under ignored private directories. This report
contains no IMEI, IMSI, ICCID, phone number, SMS content or calibration data.

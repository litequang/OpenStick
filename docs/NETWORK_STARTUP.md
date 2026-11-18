# Saved network selection — 2026-11-18

Quick Settings now saves successful manual choices for Wi-Fi station/AP/off and
SIM data on/off. No additional Save button is needed. `/overview` and `/quick`
show the saved startup choice. Opening a page or scanning Wi-Fi never saves a
choice or starts a connection. USB tethering retains its independent saved mode.

## Root cause on the real USB

Read-only inspection found SIM data and AP active, with explicit data consent
already saved in `quick-settings.json`. However, both managed AP/cellular
profiles had `connection.autoconnect=no`. Manual Quick Settings stopped the
older automation but did not persist the Wi-Fi role or replay data-on at boot.
The setup fallback could consequently choose an old station profile again.
This was missing replay of a saved selection, not loss of the saved Wi-Fi
password, APN, radio preference or SSID.

## Behavior

- Successful manual changes atomically save `network-startup.json`, fsync the
  file and parent directory, before reporting success. Private revision/profile
  references and boot IDs stay local. Public API returns only the selected role
  and data flag. Failure to save is reported explicitly, not as a successful save.
- The new `openstick-network-startup` OpenRC service replays only after a new
  boot. A service restart or page load cannot replay an already applied manual
  action in the current boot. Runtime receipts prevent repeated bearer activation
  after an uncertain result in the same boot.
- For AP + SIM, it restores the existing shared AP first. Missing SIM, delayed
  registration or waiting radio-mode replay leave the AP available without Internet;
  it waits for a ready, registered SIM before requesting the saved bearer once.
  The existing modem worker restores the owner's saved radio choice. Startup does
  not change RAT/APN, send SMS/USSD or reset ModemManager.
- SIM data additionally requires a valid explicit `quick-settings.json` consent
  with airplane off. Missing/corrupt intent, a newer data-off veto or airplane-on
  cannot grant data. Airplane-off still leaves data off. AP forwarding remains
  blocked until the owned cellular profile has a data interface. Registration
  alone is not reported as Internet access.
- Unknown activation results are not blindly retried. Wi-Fi restoration has up
  to three delayed attempts. Busy SMS/USSD, missing modem/SIM and mismatched saved
  radio mode cause waiting, not a radio reset or a fallback to receiving Wi-Fi.
- The setup fallback respects a saved AP/off choice. An already-authorized setup
  Save/handoff has priority and, after success, saves station mode with data off.
  An enabled separate Internet policy or legacy kept hotspot retains ownership;
  the new service does not compete with it.

All replay/manual transitions use the existing network lock followed by the modem
lock. Wi-Fi STA/AP still cannot operate simultaneously on this driver. No gadget,
VID/PID, USB driver, base firewall, public Nginx/Tunnel, website, LAN password,
SSH authorization, saved Wi-Fi credentials or saved RAT is replaced by this fix.
The existing AP forwarding guard and tethering-uplink refresh are reused.

## Deployment and acceptance

Full automated suite: **652 passed, 1 skipped, exit 0**. The skip is the Windows
account's unavailable symlink privilege. JavaScript syntax and diff whitespace
checks passed. These results do not establish physical reboot acceptance.

Installed five source/UI files and the new service on the real USB. Its working
SIM + AP selection was saved under the existing valid consent. It was already
active, so the worker made no live replay. Verified installed SHA-256 values,
OpenRC default-runlevel registration, running services, existing AP/data state
and protected file contents against a private before-install archive. Synced
storage and told the owner it was safe to remove the USB.

The owner needed to unplug before a reboot acceptance test. **Actual reboot /
cold power-cycle restoration is NOT_TESTED.** Do not label the fix hardware PASS
based on source tests, saved JSON or a running service alone. At next connection:

1. Keep the SIM fitted and power the USB normally, without reset/test points.
2. Confirm the saved AP appears and a phone obtains an address and reaches
   `http://192.168.8.1:8765/overview`.
3. With the phone's mobile data off, confirm a public website opens through SIM.
4. Inspect the private startup receipt: RESTORED, AP role, owned data interface;
   verify saved RAT and private website/Tunnel configuration remain intact.
5. Separately test saved data off, AP off, station mode, and delayed/missing SIM
   when the owner has time. These combinations currently have fixture evidence.

Automated tests cover power-loss/new-boot simulation, no same-boot replay, AP-first
ordering, delayed SIM/mode/USSD readiness, data/airplane vetoes, invalid state,
pending handoff/policy precedence, bounded failure, station/off, read-only status,
failed actions and a save failure preserving the newer data-off veto. These tests
do not operate real USB or establish cold-boot, DHCP-client or public Internet PASS.

Before-install backup remains private:
`/var/lib/openstick/deploy-backups/network-startup-1794978346134489169/before.tar.gz`.
Large SSH/SFTP transfers stalled during staging; verified no installation had
started before stopping that attempt. A later transfer/install completed; final
source hashes and protected contents were independently rechecked after transport
errors. Do not infer rollback or retry the installer blindly from the client error.

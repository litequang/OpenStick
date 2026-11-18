# Advanced AP settings — 2026-11-18

**Installed on the USB after the owner explicitly authorized deployment.**
Source commit `393ead1` was published first; Windows CI passed on both main and
the development branch. Installed nine source/UI files with a private rollback
archive, verified SHA-256 and served assets, HTTP controls/API, running services,
protected owner content and unchanged active connections/base firewall/boot ID.
Storage was synced. No manual AP/radio/SIM operation or reboot was performed.

Advanced options remain **not configured/enabled** on the USB; existing choices
were preserved. The installed backend's `MaxNumSta` and `ApIsolate` properties
were readable through the new module, without setting either property. This is
backend availability evidence, not client-limit or isolation hardware acceptance.
The AP was still active after installation; SIM Internet was not tested.

USB transport temporarily lost reachability while staging; a normal owner
replug restored access. Small inline transfers completed. The first install
failed HTTP readiness and rolled back; a subsequent guarded install passed,
then independent source/protected-content/HTTP/asset/service checks passed.
Private backups remain under `/var/lib/openstick/deploy-backups/ap-options-*`.
Do not infer installed state from an earlier transfer/health error alone.

## User flow

`/setup` → **Mạng USB phát** → **Điểm phát nâng cao**:

- Hidden SSID: hide the broadcast name; phones must add the exact network name
  manually. WPA2/password remains required. Hiding a name is not authentication.
- Client limit: an integer from 1 to 32. This is an application configuration
  range, not measured UZ801 V3.2 capacity or a promise that 32 clients work.
- AP isolation: request client-to-client isolation while retaining client access
  to the USB/admin and the authorized Internet uplink.

Save confirms these settings and stages them without disconnecting a running AP,
starting SIM data, or rebooting. They apply on the next AP activation, including
boot restoration. To apply manually, use Quick Settings to turn Phát Wi-Fi off
then on. A Wi-Fi admin client disconnects during this transition; keep USB
administration available. Download the connection card before hiding/changing
the AP. The card now explains how to join a hidden network.

Polling preserves unsaved drafts. Opening a page and reading status never save or
activate anything. The interface distinguishes saved settings from hardware
verification; it does not display backend acceptance as physical PASS.

## Implementation and compatibility

One optional `ap_options` object in private `setup-ap.json` stores `hidden`,
`max_clients`, and `isolation`. The existing durable profile/config save and
rollback remain in use. Legacy configurations lacking this object retain their
existing behavior. The form initially suggests 10 clients but only saving opts
in. An older API caller omitting all three new fields preserves existing options;
partial groups, unknown fields, non-booleans, fractions and invalid caps fail
before writes. The shared AP copies the same Wi-Fi/security sections and options
when changing between management AP and SIM-backed AP; credentials/APN remain
private and unchanged unless the owner explicitly edits the AP identity.

- NetworkManager keyfiles use `wifi.hidden` and `wifi.ap-isolation` (0/1).
- NetworkManager 1.52.2 has no client-limit setting. Do not invent a
  `max-clients` key or equate DHCP leases with Wi-Fi association limits.
- The pre-activation hook sets wpa_supplicant's **string** `MaxNumSta` property
  on its existing `wlan0` interface, verifies readback, then activates the AP.
  wpa_supplicant copies `max_num_sta` into the AP BSS at creation. After activation
  it checks the limit and `ApIsolate` again. Every owned explicit AP start,
  setup scan restoration, Quick Settings handoff and new boot replay uses this
  hook. It never creates/removes a supplicant interface or starts hostapd.
- Missing backend, changed interface path, profile mismatch, denied/timed-out
  property set or wrong readback raises a fixed error. It does not silently start
  a new AP without the requested pre-activation limit. On failure it stops a
  newly activated owned AP and attempts to restore the prior limit, reporting
  rollback failure separately. Callers retain their existing recovery behavior.
- Saved legacy hotspot autoconnect is blocked from accepting advanced settings;
  use a manual Quick Settings action first to stop that old automation. Legacy
  trial Keep is also blocked with advanced settings, since native autoconnect
  bypasses the pre-activation hook. Pending trial/handoff guards remain intact.
- No changes to gadget, USB DHCP/tethering, base firewall, station Wi-Fi policy,
  website, Tunnel, LAN login, SSH authorization, APN or saved radio mode. Existing
  locks serialize profile save and AP transitions across portal processes.

The supported configuration and backend readback are **software evidence only**.
Firmware/driver may reject AP isolation or enforce a smaller station limit.
Backend/interface restarts can invalidate the property path and cause activation
to fail safely; this must be tested with the actual installed NM/supplicant.
External/manual AP activation outside OpenStick is outside this hook's guarantee.

## Evidence

The prior read-only hardware audit found NM 1.52.2, wpa_supplicant 2.11 and
string read/write `MaxNumSta`/`ApIsolate` properties. It did not test their effects.
See [Phase 0 evidence](QUICK_SETTINGS_PHASE0_AUDIT_2026_11_16.md).

- [NetworkManager wireless settings](https://www.networkmanager.dev/docs/api/1.46.0/settings-802-11-wireless.html)
  describes hidden AP SSID and client isolation.
- [NetworkManager 1.52.2 supplicant configuration source](https://github.com/NetworkManager/NetworkManager/blob/1.52.2/src/core/supplicant/nm-supplicant-config.c)
  is the installed-version reference for NM integration.
- [Official wpa_supplicant 2.11 source archive](https://w1.fi/releases/wpa_supplicant-2.11.tar.gz),
  SHA-256 `912ea06f74e30a8e36fbb68064d6cdff218d8d591db0fc5d75dee6c81ac7fc0a`:
  `wpa_supplicant/dbus/dbus_new.c` dynamically exposes global properties as strings;
  `dbus_new_handlers.c` parses their setters; `wpa_supplicant/ap.c` selects the
  smaller of driver-reported `max_stations` and configured `max_num_sta`.

## Remaining hardware acceptance

Offline validation: **680 pytest passed, 1 skipped, exit 0**. The single skip
is the Windows account's unavailable symlink privilege. Includes 28 AP-option
regressions for input/auth gates, save/rollback, property signatures/readback,
backend failure, profile adoption and boot replay without granting SIM data.
Chrome headless: 24 layouts and interaction checks PASS, no JavaScript errors or
horizontal overflow; advanced-option confirmation/cancellation and draft polling
passed. Screenshots inspected locally. Node syntax, package self-test, dependency
and whitespace checks passed. Preview/fixtures only, no device operations.

All three features are **SUPPORTED BY SOFTWARE, NOT HARDWARE VERIFIED**.
No physical client test has run for this source change.

1. Keep USB administration and a private config/profile rollback copy. First
   verify ordinary AP, DHCP and admin before changing advanced options.
2. Hidden on: saved settings do not change the running AP; after explicit AP
   restart the broadcast name is absent on a fresh scan, but manual join works
   and DHCP/admin/authorized Internet remain usable. Hidden off reverses this.
3. Cap 1: client A can join, B cannot associate; after A leaves, B can join.
   Cap 2: both can associate. Test reconnection and AP/boot replay. Do not call
   a missing DHCP lease evidence that the association cap worked.
4. Isolation off/on with two clients: test bidirectional client TCP, IPv4 ARP
   and IPv6/ND where enabled. With isolation on, neither client can reach the
   other; both still reach USB/admin and authorized Internet. With isolation
   off, allowed peer traffic works again. Inspect effective driver behavior;
   successful property readback alone is insufficient.
5. Repeat management AP ↔ SIM-backed AP and delayed/missing SIM. Verify same
   saved SSID/password/options and no automatic data grant. Test a cold boot,
   supplicant/interface interruption and recovery without exposing an uncapped
   replacement AP. Check protected website/Tunnel/LAN/SSH/radio state unchanged.

Do not advertise isolation as a security guarantee or a measured maximum client
count until these tests pass. An unsupported driver is a deployment No-Go for
the affected option; do not silently replace isolation with a partial IP filter.

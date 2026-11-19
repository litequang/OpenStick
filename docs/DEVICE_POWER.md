# Device power controls — 2026-11-19

The **Nguồn** icon on the header/status bar opens **Khởi động lại USB** and
**Tắt USB an toàn**, including directly on Overview. **Quản lý → Hệ thống**
(`/settings/system`) keeps instructions and a shortcut to this menu. Reset here
means normal reboot, never factory reset. Each requires a click and explicit confirmation. Website,
Tunnel, Wi-Fi, tethering and modem sessions will be interrupted. Finish uploads,
unzip and editing first. Opening the page/status polling never requests power.
The power menu reads status only when opened or observing an accepted request;
clicking outside, opening another status icon or pressing Escape closes it.
Cancel is available during the five-second queue window and while waiting for
busy operations, until command preparation takes the exclusive transition lock.

Poweroff means normal Linux shutdown, not removal of the USB port's 5 V supply.
LED behavior and board poweroff completion have not been physically accepted.
Unplug/replug is required to start again after shutdown. Loss of the admin page
alone does not prove shutdown finished. Reboot may return through USB or the
saved network; the browser only polls for status and never repeats the POST.

## Execution and safety

Only the real Linux USB/LAN portal injects `DevicePower`. Windows backup UI has
no power endpoint. The disposable preview has an unavailable fake backend, never
a system executor. The live endpoint inherits Host/Origin/token guards and LAN
login. Payload keys and actions are allowlisted; confirmation must be literal
true and operation a canonical UUID. There is no arbitrary command/argument API.

The dispatcher uses only `/sbin/reboot` or `/sbin/poweroff`, without force flags,
through the existing BusyBox init/OpenRC shutdown integration. Availability
requires root, BusyBox PID 1, an OpenRC shutdown hook and executable commands.
See [OpenRC's user guide](https://github.com/OpenRC/openrc/blob/master/user-guide.md#shutdown)
for normal service shutdown. Availability is software readiness, not proof that
this board has completed a physical power cycle.

One thread in the existing startup worker is protected by a private singleton
lock and volatile heartbeat. A request is bound to its current boot and worker
generation; it expires after 60 seconds. A service restart cancels queued work
and never replays it; already-dispatching work becomes unknown. A new boot never
executes an old request. UUID receipts and dispatch intent are fsynced before
execution. The same UUID cannot dispatch again, including after a timeout or
unknown result. A returned command exit status is not hardware completion.

An exclusive transition lock rejects overlap with active API/file requests and
asynchronous Wi-Fi/modem/Quick Settings jobs. New API/file POSTs are blocked while
a power request is pending. Preparation also acquires existing network, modem
and website locks; active network configuration trials/reboot handoffs are
rejected. Network-startup replay pauses while power is pending. The SIM collector
uses a separate mutex so preparation can checkpoint its latest trusted totals,
then sync storage before dispatch. A failed checkpoint stops preparation.
Deadline/service-stop checks run again after checkpoint and sync: a delayed
request must not unexpectedly dispatch later. No forced fallback is provided.

Queue/receipt/baseline metadata is private under `/var/lib/openstick`; heartbeat
and lock files are under `/run/openstick`. Public status omits boot and worker
identifiers and never includes command output, passwords or modem identities.
Malformed queue state is preserved and reported; it is not converted into a new
power request. Unknown results require inspection, not automatic retries.

## Validation and installation status

- Local suite: **766 passed, one Windows symlink-privilege skip, exit 0**.
  Tests cover confirmation, authentication including LAN login, passive GETs,
  duplicate IDs, cancel/expiry, boot/worker changes, command timeout, durable-write
  failures before/after dispatch, usage checkpoint, deadline/service-stop checks,
  and asynchronous activity after HTTP acknowledgement. All commands are mocked.
- Chrome headless preview: four widths (320/390/768/1280), no overflow;
  dismiss/confirm/cancel/disconnect do not cause automatic command resubmission.
  Browser fixtures and screenshots use fictional data, not hardware acceptance.
- Real USB read-only preflight supports the installed init configuration.
  A temporary private Linux fixture verified real shared/exclusive file locking
  and at-most-once dispatch through a **mock executor**, then was removed.
  **Zero real reboot/poweroff commands were executed.**

- Installed source **`1d479fa`**, development/main CI PASS. Independent USB
  verification matched all 12 source/UI hashes, served the Manage link and System
  page/JS, and read an available, IDLE power API with an advancing worker heartbeat.
  No live power request/receipt was created. SIM samples still advance, checkpoint
  is valid/private, protected owner files/network/routes/firewall are unchanged,
  services run and storage was flushed. No real power command was sent.

Read the latest [session handoff](SESSION_HANDOFF.md) for installation evidence.
Physical shutdown/reboot, LED behavior and post-power-cycle network restoration
remain NOT_TESTED for these new buttons. Do not test them automatically during
deployment or represent a disconnected HTTP request as successful shutdown.

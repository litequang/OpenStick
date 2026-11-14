# State-first LED recipes and stable dashboard updates

## Installed behavior

Application source `272777e`, branch `codex/uz801-v32-postmarketos`, is installed
on the real USB. Open `/settings/leds` from `/manage`.

The main LED workflow is **choose a state, then configure all three colors**.
Each red/green/blue channel can be off, steady, or blink with independent
on/off durations of 100–5000 ms. A recipe may combine multiple steady and
blinking channels simultaneously. Switching the state selector retains local
edits but neither applies LEDs nor changes networks. Save persists all edited
recipes and enables automatic selection; no automatic recipe was enabled
merely by this deployment.

States, in precedence order: setup hotspot, SIM hotspot, station Wi-Fi,
cellular data without Wi-Fi, disconnected, and unknown. One complete recipe
wins; overlapping states do not merge conflicting color settings. The SIM AP
recipe therefore wins over its simultaneously active cellular connection.
Station requires connected state and IPv4, not Internet. Cellular data requires
an actual activated data link, not LTE registration. If Wi-Fi metadata is
unknown, a cellular-only role is not inferred. The setup state reports the
active owned setup AP, not a failed Internet probe.

An OpenRC-supervised LED worker polls role metadata approximately every three
seconds when automatic recipes are enabled. It reads NetworkManager only;
there is no scan, network/modem lock, connection activation, SIM Internet
probe, SMS/USSD, or radio preference change. Metadata is read outside the LED
lock. It applies only changed outputs, preserving timer phase across identical
polls. `python3 -m uz801_manager.leds --once` remains available for one-time
replay. Boot replay is implemented, but a new physical reboot was not tested.

The private settings file accepts existing version-1 per-color configuration.
Saving recipes writes version 2 while retaining old fixed settings and the
original baseline. The advanced fixed-mode form disables automatic selection
without discarding recipes. Disabling automation restores old fixed settings,
or the original baseline for colors without fixed settings. Every recipe,
including inactive ones, is validated before any hardware write. Failed
application or persistence restores prior hardware. Only the three allowlisted
case LEDs are touched; the storage activity LED is excluded.

## Header and overview

Refreshes keep current values in place until new values arrive. Missing modem
snapshots and failed HTTP requests no longer reset chips to waiting or erase
signal bars. Retained values are marked as the last reading in details/title.
A fresh no-SIM, locked SIM, unregistered modem, or disconnected Wi-Fi still
replaces the previous status. Valid zero readings remain valid updates.

Overview updates usable metrics individually and retains previous values for
missing readings. Service nodes are updated in place, with actual stopped
states replacing running states; missing service data retains the old value.
The page reports when values are retained. Pending requests do not replace
the displayed numbers. UI tests cover delayed polling, partial snapshots,
request failure, recovery, real disconnection/no-SIM, and zero values.

The real eMMC driver returns `0x00 0x00` for `life_time` and `0x00` for
`pre_eol_info`. The health card is hidden when neither provides usable data;
these zeros are not interpreted as healthy or zero wear. If a device actually
provides health data, it is displayed. A previously valid health reading is
retained and marked stale if one later read is missing. The separate write
counter still works on this device and remains visible. No low-level MMC
utility was installed and no flash/NV/partition operation was performed.

## Actual deployment and evidence

Seven installed files: `leds.py`, `static/leds.js`, `static/portal.css`,
`static/portal_nav.js`, `templates/leds.html`, `templates/overview.html` beneath
`/opt/openstick/uz801_manager`, plus `/etc/init.d/openstick-led`.

Successful backup:
`/var/lib/openstick/deploy-backups/home-20261114/before-led-recipes-1794678694.tar.gz`.
An earlier attempt restored all seven files from
`before-led-recipes-1794678558.tar.gz` when its smoke check incorrectly assumed
the previously observed SIM AP was still active. Fresh metadata showed WLAN
and cellular disconnected; no active trial existed. The check was corrected
to accept the actual current role rather than activate a network to satisfy
the check. Do not attribute this offline state to the update or enable SIM data
without the owner's choice.

Deployment used version checks and network/LED locks, restarted only the two
web services, and replaced the old LED oneshot with the supervised worker.
No Wi-Fi, WWAN, NetworkManager restart or reboot was performed. Protected
profiles, website, SSH/Tunnel files, selected private configuration and initial
LED states compared unchanged. Real management/static HTTP checks and the
authenticated role API passed. Five station profiles remained saved, zero
active. The API recognized the actual disconnected role, and the worker ran.

A subsequent real-driver probe used temporary private settings with the
actual disconnected role: red steady, green timer 200/800 ms, blue timer
700/300 ms simultaneously. Both timer channels sampled brightness 0 and 1.
An unchanged role poll performed no writes, and a new backend instance
replayed the saved temporary recipe. All original LED states, the owner's
settings file and unrelated storage LED were restored, then the worker was
restarted successfully. This proves actual concurrent driver control and
replay, not optical color mixing or real Wi-Fi/SIM/setup transitions. Those
role changes are covered by injected metadata tests; real role-transition
acceptance and visual phone acceptance of the new LED editor remain open.

Validation: **436 passed, one Windows symlink skip**, 92.43 seconds. Focused
LED/modem/UI checks: 47 passed. Self-test, JS syntax and whitespace checks pass.
The fixtures are synthetic, not visual acceptance. Latest observed network
role is disconnected; inspect fresh state before changing services.

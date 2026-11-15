# OpenStick LED Style Gallery — hardware-grounded options (2026-11-15)

## Actual hardware (UZ801 V3.2)

The three case channels are `red:power`, `green:wlan`, `blue:wan`,
each with `max_brightness=1` on the installed driver. All are independent,
binary LEDs, NOT a confirmed multicolor/PWM addressable RGB package.

The existing `/settings/leds` UI supports fixed off/on and kernel `timer`
blink with on/off intervals of 100–5000 ms. The OpenRC worker already switches
one complete recipe among six network roles approximately every 3 seconds.
This feature introduces a **client-side preset catalog and draft-only
gallery**, with no new driver operations or background scheduler.

Names such as *Violet*, *Aurora* and *Ocean* are artistic descriptions of
three physical case LEDs operating together. Actual optical mixing depends
on the enclosure; the LED indicator may show three separate light sources.
True smooth fades, 24-bit color, rainbow gradients and variable brightness
are **not implemented**, and a web animation is only a conceptual preview.

## Twelve presets

Numbers after blink are time ON / time OFF in milliseconds. “on” is steady,
“off” is dark. Each style can be assigned independently to any network state.

| Style | Red | Green | Blue | Intent |
| --- | --- | --- | --- | --- |
| Emerald Calm | off | on | off | Quiet, unmistakable connected state |
| Ocean Beacon | off | blink 250/1750 | on | Steady blue with occasional green beacon |
| Aurora Drift | off | blink 650/1350 | blink 1250/750 | Two gentle overlapping pulses |
| Ice Pulse | off | on | blink 900/1100 | Stable green + blue accent |
| Starlight | off | blink 120/2880 | blink 120/1880 | Sparse short flashes |
| Violet Neon | on | off | on | Two bright steady colors, no dimming |
| Cyber Pulse | blink 200/1000 | off | blink 550/650 | Alternating red/blue motif |
| Triad Rhythm | blink 200/800 | blink 500/500 | blink 800/200 | Rhythmic three-channel combination |
| Sunrise | on | blink 1300/700 | off | Steady red with pulsing green |
| Blue Link | off | off | on | Clear minimal blue indication |
| Alert Crimson | blink 250/250 | off | off | Recognizable high-attention warning |
| Silent Night | off | off | off | All indicators off |

These patterns use existing hardware timers, not a userspace per-frame RGB
loop. They don't require new API actions, register writes or network polling.

## Four one-click theme packs

| State | OpenStick Signature | Aurora Calm | Cyberpunk | Silent Night |
| --- | --- | --- | --- | --- |
| Setup hotspot | Sunrise | Starlight | Triad Rhythm | Silent Night |
| SIM hotspot | Ocean Beacon | Aurora Drift | Cyber Pulse | Silent Night |
| Wi-Fi station | Emerald Calm | Ice Pulse | Violet Neon | Silent Night |
| Cellular data only | Blue Link | Ocean Beacon | Ice Pulse | Silent Night |
| Offline | Alert Crimson | Sunrise | Alert Crimson | Silent Night |
| Unknown | Starlight | Silent Night | Starlight | Silent Night |

**Recommended first try: OpenStick Signature**. It distinguishes roles
with familiar visual cues and avoids repeated flashy motifs for normal Wi-Fi.
The Silent Night pack disables *all* visible warnings as well as decorative
lights. Select it only if intentional.

These are recommendations, not automatically applied defaults. The user
can select a theme, then override one particular state with an individual
style or manual per-channel settings before saving.

## Safety and UX contract

1. Reading the page, selecting an individual preset, selecting a pack,
   browsing categories, and switching network state are strictly draft-only
   JavaScript updates. **No POST** before explicit `Lưu quy tắc`.
2. The existing `POST /api/leds` with `configure_network` remains the
   *only* route to persist the six complete state recipes. The backend
   allowlist enforces exactly three channel modes (off/on/blink) and
   bounded timing. Existing lock, hardware rollback, atomic storage and
   boot replay remain unchanged.
3. The fixed-mode editor, restore-default action and per-channel manual
   editor remain available. Selecting a pack never changes Wi-Fi,
   cellular data, APN, radio mode, modem registration, SMS or USSD.
4. Visual cards use semantic buttons with `aria-pressed`, focus indicators,
   status copy, two columns on mobile, and reduced-motion preview.
5. App preview blinks are schematic, not phase-accurate with the Linux
   timer trigger. There is no claim of real-device optical acceptance.

## Current state predicates

Precedence: setup hotspot > SIM hotspot > Wi-Fi station > cellular data only
> offline > unknown. Station requires IPv4, NOT Internet reachability.
Cellular data means an activated data link, NOT just LTE registration.
If a state is unknown it stays unknown; no invented online status.

## Phase 2 ideas (NOT implemented)

- True `RGB rainbow`, `breathing`, `fade` and `gradient` require a
  separately verified PWM/multicolor control interface or external hardware.
- On this binary device, a carefully bounded three-channel sequential chase
  could be emulated in software if the owner approves after **real**
  timing, CPU, power and rollback checks. It would still be discrete colors,
  not smooth 24-bit RGB.
- Do not assume a `multi_intensity` interface exists simply because three
  colored LEDs are present.

## Verification and deployment

Run full `pytest`, Node synthetic LED UI fixture and app self-test.
Verify catalog has exactly 12 styles, the four packs map six full recipes,
and selecting them produces zero write requests until Save.

Deploy only with owner authorization, device-version checks, a timestamped
backup, the `openstick-led` worker safe-state check, and rollback. Never change
the owner's existing LED preferences automatically.
Acceptance on the actual USB should first preview and review the cards
on mobile with the LED state unchanged, then test an explicitly consented
style on a non-critical role and restore the original saved configuration.

References:
- https://docs.kernel.org/leds/leds-class.html
- https://www.kernel.org/doc/html/latest/leds/leds-class-multicolor.html

## Actual USB deployment, 2026-11-15

The owner requested updating LED functionality on the USB. The LED feature
branch was merged into `codex/uz801-v32-postmarketos`, retaining the shared
Wi-Fi setup/SIM hotspot configuration previously installed there.

The full source suite passed **465 tests** with **1 Windows symlink privilege
skip**; the LED test subset passed **34/34**. The deploy verified the current
USB SHA-256 hashes before copying only three UI files:

| File relative to `/opt/openstick/uz801_manager` | Installed SHA-256 |
| --- | --- |
| `static/leds.js` | `3993e3f9aaecfb35702db1f9079b5026db8880d352d63527cee168264eb86a0b` |
| `static/portal.css` | `59edab4c13aa62213a87a51f8bb1ad4d6e6144670ce2d4e4ea4fb405688980a4` |
| `templates/leds.html` | `80e91a879842a2308e45310f97651e032bed7b8fbe00e0efe14406249a67bf13` |

The previous three files were backed up to
`/var/lib/openstick/deploy-backups/home-20261114/before-led-gallery-1794748543.tar.gz`;
the archive was subsequently verified to contain exactly those three files.
Only `openstick-wifi` and `openstick-lan` restarted, briefly interrupting portal
HTTP while restarting; all four `openstick-led`/Wi-Fi/LAN/hotspot services were
started after deployment. The LED page, `leds.js`, `portal.css`, `/setup`,
`/hotspot` and `/overview` returned HTTP 200. The WLAN connection did not
change; no network handoff was pending, and the saved LED configuration hash
remained identical. No LED rules were applied by the installer and no reboot
or network-mode change was made.

Physical LED pattern timing and the appearance of cards on the owner's Android
browser are still unverified. To accept the feature, the owner can preview
styles safely at `/settings/leds`; applying any style to real LEDs requires
pressing the existing Save button. Keep a copy of current selections before
changing a working pattern.

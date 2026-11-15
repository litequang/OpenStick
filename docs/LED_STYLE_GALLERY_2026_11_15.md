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

Deploy only with device-version checks, a timestamped backup, the
`openstick-led` worker safe-state check, and rollback. **Do not deploy from
ChatGPT or change the owner's current LED preferences automatically**.
Acceptance on the actual USB should first preview and review the cards
on mobile with the LED state unchanged, then test an explicitly consented
style on a non-critical role and restore the original saved configuration.

References:
- https://docs.kernel.org/leds/leds-class.html
- https://www.kernel.org/doc/html/latest/leds/leds-class-multicolor.html

# Installed USB portal

Checkpoint: 2026-11-14. Open `http://172.16.42.1/overview`; use Ctrl+F5 after
an update. The public static website and Cloudflare ingress remain separate.

The owner supplied UFI Panel screenshots as the dashboard reference. The dark
two-column mobile cards use actual Linux telemetry, not the screenshot's
numbers or Debian branding. This unit runs postmarketOS v26.06.

The bottom dock adapts `MobileBottomNav.tsx`, `bottomNavScroll.ts` and the
navigation CSS from the owner's
[thophuongpro commit 83adf488](https://github.com/litequang/thophuongpro/commit/83adf488f12a36a54b180960c187c764ff0e17b8).
It retains the rounded glass dock, emphasized center destination, active icon,
safe-area spacing, reduced-motion fallback, fast-down hide and upward reveal.
It uses ordinary private local links and lightweight JavaScript, without React.

| Screen | Location | Behavior |
|---|---|---|
| Tổng quan | `/overview` | RAM, root-filesystem storage, modem signal, sensor temperature/CPU load, SMS submission counts, eMMC health/writes, swap, connections and service state |
| Wi-Fi & Web | `/` | Current SSID/IP/signal/TX-RX rates, change network, explicit 2 MiB download sample, public website link |
| SMS | `/modem/sms` | Conversation list → full thread/reply → separate new message, private durable archive |
| USSD | `/modem/ussd` | Initiate/respond/cancel, show session state and last modem notification separately |
| Mạng SIM | `/modem/network` | Actual advertised 3G/4G choices; explain SIM-data/APN readiness |
| Wi-Fi cài đặt | `/setup` | Enter SSID/password, save and connect autonomously, recover AP on failure; no SIM needed |

Header icons open native keyboard-accessible details for modem, combined
SIM/signal, network and Wi-Fi station/hotspot. An already registered modem is labeled operational rather than
showing an unexplained disabled activation button. Only a disabled modem offers
activation on Mạng SIM. Details contain no IMSI, ICCID, IMEI or own-number fields.

## Interpretation of metrics

- RAM uses MemTotal minus MemAvailable. Storage is the mounted root filesystem,
  not the entire physical eMMC. Temperature is the highest valid exposed
  sensor reading; it is not presented as a board-specific thermal limit.
- Signal is ModemManager's 0–100 quality with its freshness flag. Radio access
  technology is read separately from the allowed/preferred mode setting.
- eMMC lifetime and Pre-EOL come only from exported sysfs fields. This unit
  did not supply usable values through those fields, so the dashboard reports
  unavailable. It does not fabricate the reference image's 10–20% health.
- [Block-device write sectors](https://docs.kernel.org/block/stat.html) use
  512-byte units. The daily figure extrapolates
  the counter since boot over uptime; it is not an observed full-day total.
- Swap separates zram and other swap entries. No eMMC swap file was observed
  in the live check. Missing memory metrics are unknown, not healthy zeroes.
- SMS counts include only completed Manager submission receipts, not confirmed
  carrier delivery or messages sent by other tools. Unknown outcomes are
  counted separately. Vietnam UTC+7 calendar boundaries are used. Until an
  owner-defined tariff is saved, the cost estimate is unavailable, not zero.

No login/logout, cellular bearer, APN mutation, port forwarding, public modem
administration, shell console, flash or restore capability was added by this UI.
The image's unseen menus are not evidence that those functions are compatible.

## Validation

238 local tests passed, including synthetic DOM execution of the actual Wi-Fi,
SMS, USSD, SIM-network and overview scripts, read-only telemetry fixtures,
duplicate-send protection and navigation scroll behavior. Live USB checks:
25 modem/API, 14 dashboard/Wi-Fi telemetry and bounded-download checks, and
18 existing hosting checks all passed with exit 0. The public site, Wi-Fi
default route, NTP and Tunnel remained healthy.

The owner subsequently confirmed seeing the dark dashboard, bottom navigation
and working header detail icons on the real portal. This is owner-observed UI
acceptance. The native Edge screenshot helper timed out twice (`FrameArrived`
and window capture channel timeout), so automated screenshot acceptance and
independent narrow-window visual inspection remain unverified. Cold power
cycle of this final portal configuration has not been tested.

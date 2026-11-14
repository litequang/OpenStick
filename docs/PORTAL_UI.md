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

The navigation has been reorganized by task. The five-item dock now holds **SMS**, **USSD**, **Tổng quan** (center), **Kết nối**, **Quản lý**. SMS/USSD remain one tap away; Kết nối and Quản lý open real hubs rather than a dropdown of miscellaneous shortcuts. Detail pages show a small breadcrumb to their hub. The active parent is visually highlighted, without using false aria-current="page" on a parent route. Keyboard users retain skip navigation and visible focus, and the grouped hub cards form a single column on narrow phones. This is source-only UX work pending visual inspection on the USB and phone.

Header icons open native keyboard-accessible details for modem, combined
SIM/signal, network and Wi-Fi station/hotspot. An already registered modem is labeled operational rather than
showing an unexplained disabled activation button. Only a disabled modem offers
activation on Mạng SIM. Details contain no IMSI, ICCID, IMEI or own-number fields.

## Function inventory and navigation

| Group / screen | URL | Responsibilities |
|---|---|---|
| Tổng quan | `/overview` | Read-only telemetry, connection states, service health |
| Liên lạc / SMS | `/modem/sms` | Conversations, private archive, tariff and draft/send controls |
| Liên lạc / USSD | `/modem/ussd` | USSD initiate, reply, cancel; manual radio mode fallback |
| Kết nối | `/connections` | Navigation hub only; no network mutation on open |
| Wi-Fi nhận Internet | `/` | Scan/select/connect to upstream Wi-Fi, status, bounded speed sample |
| Wi-Fi đã lưu, Nguồn Internet | `/internet#saved-wifi`, `/internet` | Saved profiles, Wi-Fi/SIM priority/failover, cellular data off |
| Mạng SIM | `/modem/network` | Select modem radio modes, SIM registration and readiness |
| Wi-Fi cài đặt | `/setup` | Local setup AP (no SIM data), Wi-Fi provisioning and connection card |
| Phát Wi-Fi từ SIM | `/hotspot` | APN and tethering; explicit cellular data consent, confirmation/rollback |
| Quản lý | `/manage` | Site/system/admin access hub, LAN administrator password when on USB |
| Website | `/website` | Static site editor/upload/delete/public link |

The Windows backup/EDL/compatibility GUI is **separate from this Linux portal**.
The `/manage` LAN password controls were moved from the crowded Wi-Fi page,
but `/api/lan` retains its existing permission and confirmation rules. A
Wi-Fi-authenticated LAN session may view the management hub but must use the
USB port to change LAN access. The old page URLs remain available and no
modem, network, site or setup action is triggered by visiting either hub.
Capabilities omitted from an installation are omitted from its hub links.

## Navigation changes — verification

- Structural tests: route availability, old URL preservation, allowed links,
  group highlighting, keyboard focus and presence of the existing LAN form.
- GitHub CI provides Python/Node/Windows package checks, **not** a visual
  acceptance on actual USB, phone, tablet or desktop viewport.
- On-device check before deployment: open both hubs via USB, inspect narrow
  phone layout and 5 dock items, then revisit SMS, USSD, Wi-Fi, saved profiles,
  Internet policy, setup AP, SIM AP, Website, and LAN password forms.
- Do **not** trigger a network change merely to test navigation. Preserve
  saved Wi-Fi secrets, AP state, radio mode, LAN password, and Tunnel.

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

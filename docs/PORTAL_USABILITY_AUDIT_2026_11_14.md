# OpenStick portal — UX consolidation audit (2026-11-14)

## Provenance and scope

Integration base: `codex/uz801-v32-postmarketos` at commit
`76236fdc08f3f8079ad052463effc876425af892`.
This is the commit that introduced the read-only saved Wi-Fi overview
(`GET /api/wifi/saved`, `static/manage.js`, management list, and navigation
to actionable saved-network settings). All these parts remain in this branch.
The older `ui/management-navigation-20261114`/PR #3 branch is not the
source of truth for this integration.

Changes here are template/CSS/route presentation and test updates.
No flash, radio setting, APN, SIM data, network policy, credentials,
SMS archive, private web content, or USB deployment is performed.
The Windows backup/EDL application is out of scope.

## Function-by-function review

| Screen | Primary action | Secondary or advanced | Safety |
| --- | --- | --- | --- |
| `/overview` | Actual device metrics and connection health | Service/port details folded away | Data are read-only and may be unavailable |
| `/` | Current Wi-Fi, scan/connect | Optional bounded download test; management moved out | Do not activate alternate network just to inspect |
| `/manage` | Task groups for connectivity, SIM, services | Read-only saved Wi-Fi list including active profile; LAN settings folded away | LAN admin password can be configured only over USB |
| `/internet` | Source policy and saved Wi-Fi profile actions | Technical policy explanation | SIM data off has distinct warning/confirmation; no implicit data enable |
| `/setup` | Select Wi-Fi then explicit save/reboot | Setup AP enable/start/stop folded away; credentials card visible | Reboot, AP/station handoff and fallback untouched |
| `/hotspot` | Configure and explicitly test SIM AP | Channel/APN folded away | SIM charges, Wi-Fi interruption and 5-minute confirmation visible |
| `/modem/network` | Choose advertised 3G/4G radio mode | Internet/APN help as links rather than duplicate cards | Radio mode change does not activate SIM Internet |
| `/modem/ussd` | Enter code/read response/reply | Manual 3G/4G recovery folded away | Send/answer/cancel retains explicit controls and receipt handling |
| `/modem/sms` | Conversations, compose and search | Existing SMS sync/deletion/tariff options under details | Archive and uncertain-send protections unchanged |
| `/website` | Select file/edit/explicitly publish | Optional upload under details; delete visually distinct | Existing confirmation, ETag guard and limits unchanged |
| `/login` | Log in on local Wi-Fi | Help copy updated to point to USB management | Same-origin/session/CSRF unchanged |

Common design: compact mobile cards, responsive one-column management
cards, safe area and scroll-aware bottom dock, keyboard skip link,
visible focus, breadcrumb on management child pages, parent-section
highlight instead of erroneous `aria-current="page"` on child routes.

## Compatibility constraints

- Keep `/api/wifi/saved` protected; SSIDs are rendered with `textContent`,
  never HTML. Never expose Wi-Fi passwords or stored PSK.
- Keep `/manage#saved-wifi` and `/internet#saved-wifi` working.
- Keep all existing URLs, form IDs, token propagation and button wiring.
- Keep the LAN management form only in the USB administration view.
  The existing /api/lan permission and consent requirements remain.
- Avoid touching or re-testing SIM data/hotspot/radio or a new
  Wi-Fi switch without owner instruction and an active USB recovery path.
- Existing station and setup AP recovery must continue unchanged.

## Validation and handoff

GitHub CI verifies Python tests, JavaScript syntax checks, self tests
and packaging. CI does not verify real phone layout, physical UZ801
operation or the live website/Tunnel.

Codex PC should fetch this integration, compare to the USB's deployed
source and make a timestamped backup before deploying. Live acceptance:
view at 360/390/430/768/1280 CSS px, check sticky header and dock,
open/collapse details, navigate to each page, observe saved Wi-Fi
list (active label, no passwords), open LAN UI over USB only,
test unauthenticated LAN redirect and check HTTP 200 for the existing
website and main routes. Do not send SMS/USSD, trigger mobile data,
reboot, reconnect saved networks or publish/delete live files simply
to test the visual UX.

No claim of successful live USB or phone validation should be made
until Codex PC and the owner have performed it.

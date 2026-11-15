# OpenStick settings grouping — 2026-11-15

## Screen map

- **Wi-Fi (`/setup`)**: scan and join a network, show saved networks beside the
  connection controls, reconnect or forget a saved network, and edit the one
  shared USB access point identity (SSID, password and channel) used for setup
  access and SIM Internet sharing.
- **SIM & Internet (`/internet`)**: choose the preferred Internet source,
  configure automatic Wi-Fi/SIM fallback, and turn off SIM data. Links lead to
  SIM radio/network status, APN and SIM Wi-Fi sharing where those controls
  remain in their dedicated screens.
- **SIM Wi-Fi (`/hotspot`)**: configure APN, review SIM Internet status and
  consent to starting or stopping the shared Wi-Fi access point with SIM data.
- **Management (`/manage`)**: navigation hub for the screens above, device
  health, website, LED settings and LAN access security.
- **SMS, USSD and Overview** remain direct primary navigation destinations.

Old `/internet#saved-wifi` and `/manage#saved-wifi` links now lead to the saved
network list in `/setup`. The global Wi-Fi navigation opens `/setup` so the
connection flow and saved network list stay together.

SIM subpages (`/modem/network`, `/hotspot`, `/internet`) retain a local
“SIM & Internet” navigation bar with all three sibling destinations and the
current page selected. The Wi-Fi setup screen likewise keeps quick links to
connection, saved networks and the shared USB access point settings.

## Implementation and verification

The saved network view uses the existing token-protected network policy
operations. SSIDs are inserted as text, never interpreted as HTML. Connect and
forget require explicit confirmation; active profiles cannot be forgotten.
Network switching retains the backend's Internet verification and rollback
behavior. The shared access point settings are presented in the Wi-Fi screen;
APN and SIM consent remain in the SIM-specific screen.

Source checks on 2026-11-15: **465 pytest passed, 1 skipped** because the
Windows account cannot create symlinks. The setup and saved Wi-Fi browser
fixtures passed, along with JavaScript syntax and `git diff --check`.

The actual USB deployment backed up the prior portal files to
`/var/lib/openstick/deploy-backups/home-20261114/before-saved-wifi-1794756550.tar.gz`,
then installed the changed portal files atomically and restarted only
`openstick-wifi` and `openstick-lan`. SHA-256 checks, HTTP checks for
`/manage`, `/setup`, `/internet`, `/overview`, `/`, and the relevant static
assets passed. The protected saved Wi-Fi API returned six profiles with one
active. After deployment the SIM data policy remained off, neither Wi-Fi AP
was active, and no trial was pending; all three checked portal services were
running.

Physical phone visual review and a user-driven reconnect/forget operation have
not been performed. No network switch, reboot, SIM activation or saved profile
mutation was part of deployment verification.

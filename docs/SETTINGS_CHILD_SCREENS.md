# Separate settings screens — 2026-11-19

The owner reported that child menu items merely scrolled to a section while
unrelated settings remained on the same page. Child items now have dedicated
URLs and show only their corresponding panels. The four parent categories and
the shared sidebar/mobile drawer remain the single navigation tree.

| Screen | URL |
| --- | --- |
| Connect to Wi-Fi | `/setup` |
| Saved Wi-Fi | `/setup/saved` |
| Broadcast Wi-Fi configuration | `/setup/ap` |
| Connected/blocked Wi-Fi clients | `/setup/clients` |
| Automatic setup AP fallback and access card | `/setup/recovery` |
| USB Internet sharing | `/quick/usb` |
| SIM data usage | `/sim/usage` |
| LAN administration and password | `/settings/access` |
| Website list and metadata | `/website` |
| Website file manager | `/website/files` |
| Website domains | `/website/domains` |

Existing SMS, USSD, SIM network, APN, Internet policy, LED and system pages keep
their existing URLs. Overview retains its summary metrics and Quick Settings.
Legacy section-hash bookmarks redirect to the corresponding child URL without
submitting an action. Site selection is preserved in website child links.

## FileGator and obsolete controls

When FileGator is enabled, the website templates render only the website
metadata, FileGator entry or domains appropriate to the current screen. They do
not render the retired native upload, ZIP checker/extractor, editor or tab/menu
controls and do not load the old file-manager controller. The old upload URL
redirects to FileGator's entry screen. File operations remain in FileGator;
OpenStick retains the existing create/configure/domain publication API and its
revision/confirmation checks. Page load performs only a website inventory read.

The native fallback is retained for environments without FileGator; its child
panes are also separated. Shared Wi-Fi/Quick controllers still require certain
hidden DOM elements, so those templates retain hidden nonselected sections.
Only the selected screen is visible and saved-Wi-Fi/client controllers are
loaded only on their own pages. No new network daemon or dependency is added.

## Validation and deployment scope

Full Windows suite: **788 PASS, one Windows symlink-permission skip, exit 0**.
Chrome preview with FileGator enabled: 176 route/width cases (22 pages at
320/360/390/430/768/820/1024/1280 CSS pixels), eight landscape cases and 24
existing interaction checks passed without JavaScript errors. Assertions cover
isolated visible child screens and absence of retired FileGator-mode controls.
Metadata create/configure/publish, cancellation and uncertain-response handling
are tested with intercepted fictional data: four mocked writes, no automatic
retries, no USB writes. The standalone usage screen is tested against upload/
download/total fields, missing fields and stale/unavailable/error samples; it
retains previous values rather than replacing a failed read with zero.

Browser fixtures are not physical phone acceptance. Real-device checks must
remain navigation-only: no SMS/USSD, radio/data/AP/profile, tethering, LED, website
file writes, Nginx/Tunnel reload or power command is needed for this UI change.
Only portal source/templates/assets are installable; restart only the USB/LAN
portal services after exact-source CI passes. Preserve owner data/configuration,
network/gadget/firewall, usage checkpoint and existing power/operation receipts.

The owner's poweroff/replug occurred between earlier V4 checks. A new read-only
preflight found SSH/USB administration and expected services ready, no pending
operation and the installed `4cca1fa` source matching. Protected-file and network
comparisons for this installation use this post-owner-action baseline. Terminal
power receipts from a different boot are preserved, not deleted to make a gate
pass. Installed source and final real USB results are recorded in the handoff
after deployment. Branch remains `ui/settings-parent-child-nav-20261119`; no
merge to main or release is authorized for this deployment.

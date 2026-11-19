# Immediate settings restoration — 2026-11-19

The owner requested last-known controls immediately on every page revisit, across
all USB settings, rather than repeatedly showing disabled loading placeholders.

## Behavior

`portal_nav.js` provides shared, explicit per-screen projections. Quick Settings,
modem/network, receiving/transmitting Wi-Fi, saved Wi-Fi, AP clients, APN, LED,
Internet policy, LAN administration, power status, SIM usage and the deployed
website metadata screen restore their most recent successful snapshot before
starting background reads. A successful live read updates the screen, preserving
active drafts. Read failures retain the restored screen. Manual read controls and
normal background updates remain; this is not a browser cache of private HTTP.

Snapshots have a version, timestamp and eight-hour lifetime, are isolated by the
existing USB/LAN browser-session scope and origin, and carry an explicit old-data
notice. Sanitized settings also use localStorage so a newly opened tab can restore
them. AP-client inventory stays session-only. Logging out clears settings snapshots.
An entirely new browser/origin, expired cache or unavailable browser storage still
requires an initial read; no state is invented before the first successful sample.

Schemas allow individual display/configuration fields, never raw API responses.
Passwords, APN usernames, CSRF/session secrets, modem/subscriber identities,
SMS/USSD contents, file contents and operation IDs are excluded. Existing private
operation-receipt recovery remains separate: Quick checks an unresolved operation
before restoring enabled controls, then polls that receipt without replaying POST.
Cached power state never supplies an operation ID or authorizes cancellation;
power commands re-read state when invoked from a restored snapshot.

Writes still use existing confirmations, receipts, fresh backend preflight,
network/modem/power gates and revision checks. Active trials, permissions and actual
connection restrictions may disable particular actions; a display refresh alone
does not disable an otherwise usable form. APN edits from a restored snapshot
retrieve/preserve the current username at save time unless the owner edited it,
so omitting credentials from browser storage cannot silently erase them. Late
responses cannot overwrite a newer accepted settings mutation. LED and policy
reads do not occupy the page's mutation busy flag; active drafts remain intact.

New authenticated GET `/api/internet/status` and `/api/wifi/profiles` use bounded
single-flight snapshots instead of claiming the old shared POST action job for a
display read. All Host/Origin/token/LAN login guards remain. No credential GET,
file operation, SMS/USSD, network activation or radio write is cached/retried.

The current development checkout is older than parts of the installed UI branch.
Preserve the previously reviewed navigation/asset/stale-read changes. The deployed
`website_filegator.js` and `sim_usage.js` were brought from the matching UI branch
before adding restoration; unrelated UI/hosting/FileGator backend files were not
replaced. This does not merge the UI branch into development or publish a release.

## Verification and installed checkpoint

793 pytest PASS / one Windows symlink skip; the final affected settings, LED, APN,
policy and power group passed 115 tests. Self-test, pip check and all portal JS
syntax checks passed. Chrome preview: 24 layouts/interactions PASS; six settings
screens restore with every API read deliberately failing, including a new tab.
Mocked late-read/APN-save checks prove draft and username preservation. Projection
tests cover credentials exclusion, expiry, auth scope and session-only clients.
These are synthetic/browser checks, not physical radio or network acceptance.

21 files are installed. An initial verification window timed out; the attempted
source rollback could not acquire the busy network gate. A subsequent install
attempt stopped at baseline checks because the new files were already present.
Independent verification then confirmed all 21 intended hashes, changed served
assets and fresh modem/Quick/policy/profiles GETs. Protected owner files, network,
routes, firewall and boot ID exactly matched the pre-install checkpoint. Preserve
this independently verified installed state; do not assume a rollback completed.
Private helpers and diagnostics remain under ignored runtime storage.

Pre-install archive:
`/var/lib/openstick/deploy-backups/settings-cache-1795089926/source.tar.gz`.
Restore its 21 members beneath `/opt/openstick` and restart openstick-wifi and
openstick-lan to roll back code. Keep all owner/runtime files and network choices.
No network/radio/band/data/AP/source selection, SMS/USSD, file publication or power
command was invoked for installation. Source and reports are recorded together
on `codex/uz801-v32-postmarketos`; see Git history for the commit ID. No main merge
or release was performed. GitHub CI status must be checked separately.

Final live Chrome checks used actual USB HTML/API responses to warm each screen,
then deliberately blocked API reads on revisit: 14 settings routes restored their
known controls/data, with no JS errors, horizontal overflow or mutating requests.
A newly opened tab restored Quick Settings too. This failure injection verifies
browser restoration, not network/radio acceptance. A connection action may still
be disabled by the actual saved AP role; edit fields remain available.

The live check caught the SIM-usage first-visit path rejecting retained server
samples without recording a display snapshot. Two focused static-script followups
now render known/unavailable samples immediately, retain prior readings on error,
and schedule at most one delayed read. Missing readings are never synthesized as
zero. Focused cache/usage regressions: two PASS. The final followup hash, served
script/status APIs, protected files, network/routes/firewall/boot and sync passed.
Followup archives are `settings-cache-1795090513/source.tar.gz` and
`settings-cache-1795090618/source.tar.gz` in the same deployment-backup directory;
the 21-file archive above remains the complete pre-feature rollback.

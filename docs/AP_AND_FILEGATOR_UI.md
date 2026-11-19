# One broadcast Wi-Fi screen and embedded FileGator — 2026-11-19

The owner asked to combine setup fallback, hotspot and broadcast identity, and
to open FileGator without a second click. There is now one **Phát Wi-Fi** menu
item at `/setup/ap`. It contains SSID/password/channel/advanced AP configuration,
setup fallback controls, connection card, SIM hotspot status and usage guidance.
`/setup/recovery` and `/hotspot` redirect there when the setup backend exists.
Software with a hotspot backend but no setup backend retains the standalone
hotspot screen. Existing API routes, confirmations, pending-trial completion and
rollback controls are retained; navigation never activates AP, SIM data or radio.

Setup fallback is the same saved AP identity, with local administration when
there is no Internet. SIM data plus broadcast shares Internet through that AP.
This grouping does not add simultaneous station/AP support. Fallback settings
remain explicit and separately saved; changing identity still stages the next
AP activation. The embedded legacy-status panel reads on open/explicit refresh
and polls only a pending trial, avoiding an extra permanent heavy status poll.

## File manager

`/website/files` reads the site inventory then opens `/files/<selected-site>/`
in a same-origin iframe immediately. There is no intermediate launch button.
The site selector changes the frame after explicit confirmation; cancelling
preserves the current site. Refreshing the inventory does not reload the same
frame, so it does not interrupt its editor/upload. **Mở riêng** is an optional
new-tab shortcut for more space. FileGator remains the only file UI.

FileGator mounts Vue asynchronously after document load and replaces its initial
root. The loading notice observes the mounted navbar for at most 20 seconds;
changing site cancels the old observation. This is a browser DOM check only,
not an HTTP retry or replay of a file action. The preview fixture mounts after
load too, so an early load event cannot falsely mark the working frame failed.

Only FileGator bridge responses allow same-origin embedding (`SAMEORIGIN` and
`frame-ancestors 'self'`). Only the file-manager wrapper URLs allow `frame-src
'self'`; other portal pages keep their DENY/no-ancestor policy. The parent page
itself still cannot be embedded. LAN authentication, Host/Origin validation,
credential-version checks, scoped FileGator sessions, CSRF, fixed upstream/root,
chunk limits, ZIP recovery and website/Tunnel boundaries are unchanged. No
external iframe origin or credentials in URLs is introduced. The upstream
FileGator package is not patched or reinstalled.

Read-only browser checks must block any FileGator mutation as well as portal
mutations. Opening FileGator can establish its existing scoped PHP session and
read directory metadata; it must not modify owner files. No real upload, unzip,
delete, rename, network or power action is required to accept this UI change.
The handoff records exact installed source, CI, test counts and real-device
acceptance separately from mocked browser interactions.

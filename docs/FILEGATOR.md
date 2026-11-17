# FileGator for static websites — 2026-11-17

The installed file manager is upstream **FileGator 7.16.9** (MIT), not a newly
written replacement. OpenStick keeps the website registry, domain/Nginx/Tunnel
controls and existing LAN login. FileGator supplies file navigation, chunked
uploads, editing, folders, rename, copy, move, delete, ZIP creation and download.
Its unzip button uses OpenStick's existing bounded ZIP publisher internally;
there is no separate inspection screen or second upload to extract.

## Use

1. Open `/website`, choose the website, then **Mở trình quản lý file**.
2. In FileGator upload a ZIP. After upload finishes, select its ZIP action and
   confirm **Unzip**. There is no manual source-code checking step.
3. Extraction replaces matching paths and preserves unrelated old files. It
   does not remove a wrapping project directory. Put `index.html` at the ZIP
   root to publish it at the website root.
4. Use **← Website** to return to website selection and domain management.

FileGator uploads in 1 MiB chunks, one at a time, with a 128 MiB file limit.
The bridge accepts at most 2 MiB/request. ZIP publication keeps the existing
128 MiB archive / 32 MiB entry / 256 MiB website / 2,000-entry limits, path/type
checks, interruption journal and rollback. The stored ZIP itself counts toward
website disk usage; delete it after extraction if no longer needed. Other
FileGator file operations are upstream operations, not multi-file transactions;
they do not have OpenStick's ZIP rollback or a trash bin. Keep an independent
copy before deleting or editing files.

## Selection evidence

| Candidate | Decision |
| --- | --- |
| [FileGator 7.16.9](https://github.com/filegator/filegator/releases/tag/v7.16.9) | Selected stable release; chunked upload, editor, ZIP tools; PHP 8.3 available in the device's package repositories. |
| [FileGator 8](https://github.com/filegator/filegator/releases/tag/v8.0.0-rc4) | Go binary exists for ARM64, but this release is explicitly a release candidate. Not installed. |
| [File Browser original](https://github.com/filebrowser/filebrowser) | Archived 2026-08-31. Not selected for a new permanent installation. |
| [FileBrowser Quantum](https://github.com/gtsteffaniak/filebrowser#comparison-chart) | README lists 512 MB minimum; USB Linux exposes about 376 MiB. Not installed or hardware benchmarked. |
| [Tiny File Manager](https://github.com/prasathmani/tinyfilemanager) | README advises removing the script after use; not chosen as the permanent portal. |

This is a file manager for existing static hosting, not an all-purpose cPanel.
It does not install databases, PHP websites, WordPress, Node applications, mail,
or DNS accounts. The PHP worker executes only the FileGator application in its
separate public directory, never uploaded website PHP files.

## Reproducible installation

Upstream source tag: `v7.16.9`, commit
`40f29bf7b0bf2193cc111334a7ee17ce3413d2af`.
Download [the versioned official build](https://github.com/filegator/static/blob/master/builds/filegator_v7.16.9.zip)
to a private staging folder, alongside all files from `deploy/filegator/`.
Expected size: **4,136,684 bytes**. Expected SHA-256:

```text
304d979f646ec9db4e6a38452b796a269fa97016460aa3f8e458abc7bfe559e1
```

The official Git blob is `bca5b80be660bc61280717628539a959f82907d0`.
The installer checks size and SHA-256 before executing or extracting anything.
No curl-to-shell installer, Docker, frontend build, default admin password or
downloaded programmer is used. The original upstream MIT LICENSE stays installed.

On postmarketOS, as root, run `python3 install.py /private/path/to/build.zip`.
This installs PHP 8.3 dependencies, a dedicated `openstick-files` account, the
unchanged upstream bundle under `/opt/openstick-filegator`, separate configuration
and two OpenRC services. Existing or partial installations are refused rather
than overwritten. A failed installation may leave packages/files for diagnosis;
repair or uninstall those explicitly before retrying. The account does not get
SSH, modem, network configuration or system administration permissions.

Only public website directories receive named ACL permissions for this account;
content and original owners are preserved. Before-install ACLs are saved privately
in `/var/lib/openstick-filegator/before.acl`. New website creation grants the same
ACL to that new root. No network worker or public web-server configuration changes.

The FileGator PHP pool has one worker, starts on demand and exits after 10 seconds
idle, with a 96 MiB PHP allocation limit. This is not a hard process RSS limit.
An independent Nginx instance listens only on `127.0.0.1:8788` and talks to a private
FPM socket. Do not expose that listener: the backend guest account deliberately
has file permissions because authentication is at OpenStick's `/files/<site>/`
bridge. LAN requests require the existing portal session; USB uses the existing
USB administration boundary. The bridge forwards only the FileGator cookie,
keeps upstream CSRF validation and selects the site root from the server registry.
Private files, admin/user APIs and arbitrary upstream URLs cannot be proxied.

Website, Tunnel, LAN password, radio choice, SSH authorization, firewall, gadget
and active network connections remain unchanged. Only the two portal services
restart when portal source is installed. The new services have separate configs,
socket and PIDs; the public Nginx and Tunnel are not reloaded/restarted.

After successful health/fixture checks, enable `openstick-filegator-php` and
`openstick-filegator-http` in OpenRC's default runlevel. No real reboot has been
performed to validate boot persistence in this session.

## Hardware evidence

On the actual ARM64 postmarketOS USB, isolated private fixtures exercised the
real PHP/FPM/HTTP backend and bridge:

- Generated **28,311,916-byte ZIP**, uploaded in 28 chunks; SHA-256 matched.
- Extraction replaced a fixture index, published 27 MiB PDF/CSS and retained an
  unrelated fixture file. Download matched its bytes.
- Missing CSRF rejected extraction; traversal ZIP rejected without escape.
- Fixture directory cleaned; no owner archive, website or domain published.
- Aggregate service RSS: **26,036 KiB busy**, **14,008 KiB after worker idle exit**;
  this sum counts shared RSS repeatedly and is not PSS or a maximum-load guarantee.
  Device MemAvailable after the fixture was 125,440 KiB.

Regression suite: **637 PASS / 1 Windows symlink-privilege skip**, exit 0.
Tests cover LAN login/credential rotation, Origin guard, scoped cookie forwarding,
fixed upstream, forbidden routes, chunk bounds, interrupted ZIP lock and safe unzip.
Do not treat synthetic tests or private fixture extraction as publication of the
owner's real archive, a power-cut test, or DNS/Cloudflare acceptance.

## Disable / uninstall

For a manual rollback, stop and remove only the two `openstick-filegator-*`
services from the default runlevel, restore saved source for the two portals,
and restart those portals. Leave site files and website registry intact. Restore
ACLs from the saved file only after checking for websites/files created since
installation; do not overwrite newer ACL changes blindly. Keep private service
state until this comparison is complete. Do not stop/reconfigure public Nginx,
Tunnel, SSH, NetworkManager, modem or USB gadget for this rollback.

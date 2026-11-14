# Mini Hosting Single on this postmarketOS unit

Audit date: 2026-11-14. This is an installation feasibility check, not an MHS
hardware acceptance result. MHS has not been installed or modified on the USB.

Source reviewed: [Mini-Hosting-Single](https://github.com/litequang/Mini-Hosting-Single/tree/c464e0b26e05ffa85b031b2e500ff506f85774b4),
commit `c464e0b26e05ffa85b031b2e500ff506f85774b4`, version `2.1.0-rc.20`.
Its README describes static, Node, PHP and WordPress site management. WordPress
is served through PHP-FPM and MariaDB, not executed by Node.js.

## Measured device state

The running FY_UZ801_V3.2 unit is AArch64 postmarketOS with OpenRC and apk.
`MemTotal` was 385324 KiB (about 376 MiB), `MemAvailable` 251856 KiB (about
246 MiB), with compressed swap enabled. The root filesystem reported 2.0 GiB
total and approximately 1.3 GiB available. These are a snapshot, not guaranteed
capacity for another application or a load benchmark.

The configured repositories offer AArch64 Node.js 24.22.3, PHP 8.4/8.5 and
MariaDB 11.8.9. Package availability is not proof that MHS hosting works.
The existing Nginx/static website and Cloudflare Tunnel have passed live HTTP
and normal-reboot checks separately from MHS.

## Direct installation: BLOCKED

- [`scripts/bootstrap.sh.in`](https://github.com/litequang/Mini-Hosting-Single/blob/c464e0b26e05ffa85b031b2e500ff506f85774b4/scripts/bootstrap.sh.in)
  requires the exact Termux prefix `/data/data/com.termux/files/usr`, and uses
  `pkg`, `dpkg-query`, termux-services and Termux:Boot. Those are not this OS's
  package/service/boot interfaces.
- [`tools/install.mjs`](https://github.com/litequang/Mini-Hosting-Single/blob/c464e0b26e05ffa85b031b2e500ff506f85774b4/tools/install.mjs)
  refuses a native install unless the exact Termux prefix and at least 3072 MiB
  free space are present (`MHS_FRESH_TERMUX_3GIB_REQUIRED`). The current root
  filesystem cannot meet that gate. This is MHS's installer policy, not a claim
  that every WordPress installation inherently needs 3 GiB free.
- `panel/src/config.mjs` and `system.mjs` resolve binaries under `PREFIX/bin`
  and services through `sv` and `PREFIX/var/service`. Setting `PREFIX=/usr`
  alone does not adapt the installer, services or Alpine executable locations.
- MHS owns its Nginx listener at `127.0.0.1:8080`, where the working OpenStick
  static service already listens. A migration must explicitly coordinate that
  listener and the existing tunnel, rather than start a competing instance.

No installer, database initialization, package installation or MHS service was
run on the USB for this audit. No guard was bypassed with fixture mode or fake
Termux paths. No firmware work is required to investigate an application port.

## Feasibility by workload

| Workload | Evidence and conclusion |
|---|---|
| Existing static site + Tunnel | VERIFIED on this unit, including normal reboot |
| MHS static-site management | CONDITIONAL: platform/service migration and private administration needed |
| Small Node application | CONDITIONAL: compatible package available; actual runtime, memory and restart tests NOT RUN |
| MHS PHP / WordPress | UNVERIFIED: PHP extensions, SQL provisioning, platform adaptation and load tests needed |
| Full all-services MHS installation | BLOCKED by the current installer and storage policy |

Prefer a port that preserves the original MHS Panel and its authentication,
site ownership, upload, path, secret and operation guards. Introduce explicit
Linux platform adapters for package paths and supervision; do not fake Termux
or merely remove its free-space check. Keep the Wi-Fi portal USB-only and do
not expose MHS's local password listener through the public website tunnel.

A resource profile with static hosting and one small Node application is a
reasonable first test. WordPress additionally needs PHP-FPM and MariaDB; their
combined resource use with Panel and Tunnel must be measured on this unit.
The existing MHS configuration already limits PHP to one child below 2 GiB RAM
and sets a 64 MiB MariaDB buffer pool, but that alone is not a memory acceptance
test. Building large Node dependency trees on-device and production WordPress
with heavy plugins are not justified by the current evidence.

# Handoff — 2026-11-14

Branch: `codex/uz801-v32-postmarketos`. Do not merge main or create a release
without the owner's approval. No firmware/partition work belongs to the
remaining task.

## Owner can unplug the device

The owner requested shutdown to leave. `/bin/sync` completed, normal
`/sbin/poweroff` was requested, and USB SSH stopped afterward. No flash,
partition write, pending hotspot trial or cellular data activation was
running. The last installed connection remained the original saved Wi-Fi.
The source push proceeds on Windows independently of the USB.

## Completed and deployed

- Dark dashboard, bottom navigation and exclusive header popovers.
- Password-protected Wi-Fi administration, with the stock nftables ingress
  fix and form Referrer-Policy correction. The owner confirmed LAN login.
  The Wi-Fi IP is DHCP-derived, not fixed; see `/` over USB for its URL.
- Static website manager at `/website`: text edit/create, asset upload and
  delete; original website retained. Thirteen live editor/LAN checks passed.
- Opt-in `/hotspot` UI/controller and independent recovery service. Ten live
  prerequisites passed, including offline NM keyfile validation and native
  checkpoint create/extend/destroy. Neither cellular nor AP was activated.
- Current web and Cloudflare Tunnel were verified before shutdown. No
  administrative endpoint was added to public Tunnel ingress.

The main LAN/editor commit is `1448e4c93553c9fdae4a44b3633e056dabde605c`.
Its [Windows CI](https://github.com/litequang/OpenStick/actions/runs/43582477054)
passed tests, packaging, EXE self-test and smoke test.
The hotspot source is in the subsequent branch commit. Final wording and a
minor recovery no-op avoidance change were made after poweroff; deploy the
latest branch source before final acceptance. Do not assume every final
source hash already matches `/opt/openstick`.

## Next safe steps

1. Plug in normally. Check pinned USB SSH, `172.16.42.1`, saved Wi-Fi, NTP,
   Nginx and Tunnel. Do not enter fastboot/EDL or flash anything.
2. Deploy the latest portal/controller files and OpenRC service with the
   existing local private tooling. Keep website, SSH identities, Tunnel
   credentials and NetworkManager profiles. Deployment scripts and host
   pins/keys are intentionally ignored locally, not in GitHub.
3. In `/hotspot`, the owner must set SSID and password locally; do not ask
   for passwords in chat. Empty APN selects the provider database. Saving
   alone must not start data. See [hotspot usage](SIM_WIFI_HOTSPOT.md).
4. The owner must explicitly select the cellular-data/role-change consent
   and start a trial. Check actual QMI/IP interface, bound Internet probe,
   AP, phone DHCP/Internet, manager login at `192.168.8.1:8765`, public site
   and Tunnel. Only then keep the mode. Real rollback, power-cycle behavior,
   throughput/temperature and sustained operation are still UNVERIFIED.
5. If trial fails, preserve fixed error categories and local evidence;
   recover via checkpoint/USB. Never guess SIM PINs or expose raw modem
   errors, phone identifiers or SMS/USSD contents in GitHub.

## Still unfinished — do not claim delivered

- Phone-style SMS conversations, persistent received/sent archive and
  deletion. Current SMS UI still uses the earlier modem-message list.
- Four selectable Internet policies (Wi-Fi only, SIM only, either preferred
  with fallback/failback).
- Saved Wi-Fi profile list, optional Internet-aware switching among known
  available Wi-Fi networks, with hysteresis/cooldown. Saved credentials and
  basic NetworkManager autoconnect already exist.
- Independent visual acceptance of the website/hotspot screens. Previous
  Edge capture failed twice; existing dashboard acceptance came from owner.

Keep hotspot and Wi-Fi-client roles mutually exclusive with this driver.
Do not promise Wi-Fi repeater operation. Do not confuse LTE registration
with proven Internet or successful data routing.

## Known modem facts to retain

MobiFone SIM is registered on LTE, saved radio mode 4G-only. PIN2 is a
secondary lock and does not prevent SMS/USSD operation. Never enter PIN/PUK.
`*101#` produced a late operator notification despite an earlier DBus method
error. The mixed 3G/4G experiment still used LTE and was restored to 4G-only;
it did not prove 4G-only caused the USSD issue. Never automatically resend an
uncertain SMS or USSD request.

An old verifier's `wwan_unmanaged` label checks configuration text only.
Actual NetworkManager GSM `Managed=true`, state 30 was read before data
configuration. Runtime state, not `type:wwan` text, is authoritative.
The RMTFS `-r` safety configuration remains unchanged.

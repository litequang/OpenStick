# Continuing OpenStick work

Read [docs/AI_CONTINUATION.md](docs/AI_CONTINUATION.md) and
[docs/SESSION_HANDOFF.md](docs/SESSION_HANDOFF.md) before changing the installed
USB portal. They distinguish tested behavior from unfinished hardware work.

- Current development branch: `codex/uz801-v32-postmarketos`.
- The Linux portal is separate from the original Windows read-only backup UI.
- Preserve the owner's website, Tunnel, LAN password, SSH authorization and
  saved radio choice. Do not mistake LTE registration for working SIM data.
- Never commit runtime credentials, host keys, device identifiers, SMS/USSD
  contents or network passwords. `runtime/` is intentionally ignored.
- Keep USB administration working during Wi-Fi changes. The hardware does
  not support simultaneous Wi-Fi station and AP.
- Main open issue: successful AP → station handoff is not yet verified.
  Phone access to setup AP and failed-network rollback are verified.
- Do not represent synthetic tests as physical-device or visual acceptance.

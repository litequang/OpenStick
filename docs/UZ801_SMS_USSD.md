# SMS and USSD on the installed UZ801 V3.2

Checkpoint 2026-11-14. Private administration: USB `http://172.16.42.1`, or
password-protected LAN on port 8765. Public website/Tunnel stay separate.

## SMS

`/modem/sms` has a conversation list, a full conversation with bubbles/reply,
and a separate new-message screen. Search and drafts stay local to the page;
sender numbers are not placed in URLs. Visible-page refresh imports messages
into root-private SQLite under `/var/lib/openstick/sms`.

Deletion creates tombstones and clears archived plaintext. Optional modem
deletion verifies the live fingerprint. Outgoing UUID receipts are durable;
unknown outcomes are not automatically resent. Modem submission does not
prove recipient delivery. Agent tests did not send real SMS.

SMS/USSD need registration but do not need an active packet-data bearer.
Explicit data-off leaves the modem available for them. Primary SIM locks
block actions; PIN2/PUK2 alone do not block a registered modem. No PIN guesses.

## USSD

`/modem/ussd` provides explicit initiate/reply/cancel and a `*101#` shortcut.
Busy/interactive sessions block radio-mode changes. Unacknowledged cancel
closes the owned local session and enforces 30 seconds of cooldown; it does
not claim confirmed network cancellation. Unknown requests never auto-resend.

Supported allowed/preferred pairs: `[4,0]` 3G, `[8,0]` 4G, `[12,8]` mixed
prefer 4G, `[12,4]` mixed prefer 3G. Owner chooses/saves a pair on
`/modem/network`; no silent per-query mode switching. Last current and saved
mode was mixed/prefer 4G. Earlier old-path controlled tests showed 4G-only
failure, 3G success, and LTE → UMTS → LTE during mixed-mode success. This is
specific to the tested SIM/operator/path, not a universal LTE claim.

`ussd_qmi.py` uses typed GI/libqmi and its own VOICE client through qmi-proxy.
ModemManager still owns radio/SMS/data. Linux needs `py3-gobject3`, libqmi's
Qmi typelib and qmi-proxy. Non-QMI installations retain the DBus fallback.
No raw AT commands or firmware changes.

Old ModemManager QMI used UCS2 and sometimes returned an error before a late
response. Comparing cached text lost identical replies. The new client sends
ASCII codes as ASCII and accepts fresh method responses/own indications.
Session state is root-private RAM. Persistent journals contain no codes,
numbers, contents or balances. Per-operation API polling protects results
against unrelated status refreshes in other tabs.

Three prototype, four production-controller and two final web API queries
passed, including identical consecutive responses. Both web result receipts
survived unrelated status refreshes. Additional checks are recorded in
[the handoff](SESSION_HANDOFF.md). Interactive menus and long-term/operator
coverage remain unverified. Fixtures do not substitute for network tests.

RMTFS remains `-s -P -r` with RAM shadows. No firmware, NV, calibration,
partition or bootloader writes were made. Readiness automation restores only
the saved radio preference; it never sends SMS/USSD or activates data.

Primary references:

- [ModemManager QMI source](https://github.com/linux-mobile-broadband/ModemManager/blob/main/src/mm-broadband-modem-qmi.c)
- [Typed libqmi VOICE definitions](https://gitlab.freedesktop.org/mobile-broadband/libqmi/-/blob/main/data/qmi-service-voice.json)
- [ModemManager USSD API](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.Modem3gpp.Ussd.html)
- [RMTFS RAM shadows](https://github.com/linux-msm/rmtfs/blob/v1.3/storage.c)

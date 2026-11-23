# Serving LTE band display

The network header now shows `4G · B3` when actual serving-channel information
is available. Opening **Mạng & sóng** adds the nominal band, exact downlink
frequency and EARFCN. These are radio-channel details, not throughput or proof of
Internet connectivity. The SIM/carrier chip continues to identify the carrier;
its details also show the serving band.

The optional read uses the typed ModemManager `GetCellInfo` method only for an
unlocked, registered LTE modem with no active USSD session, with a three-second
DBus timeout. Missing methods, unsupported responses, malformed data and timeouts
leave the other status usable and display **chưa đọc được**. No RF/PLMN/APN
configuration, signal polling setup, data connection or QMI/AT write is sent.
Existing snapshot workers provide the read; no new service, thread or timer.

Only LTE entries explicitly marked `serving=true` are used. Neighbor cells,
`CurrentBands` (allowed filters), `SupportedBands`, modem names and operator
names never establish the current band. Multiple known serving carriers may be
shown without claiming which is primary. No previous serving band is retained
as current after a fresh unavailable/unregistered response. Browser session
header snapshots retain only the sanitized channel fields, with the existing
stale indicator on restoration.

The parser exports only band number, nominal MHz, downlink MHz and EARFCN. It
does not export or persist raw cell info, cell IDs, tracking area, PCI, network
IDs, subscriber/device identity or messages. Unknown channel ranges are omitted;
the initial explicit table covers B1/B3/B5/B7/B8/B20/B28/B38/B40/B41. This table
is not a claim that all these bands are supported by this hardware.

Sources:

- [ModemManager GetCellInfo contract](https://www.freedesktop.org/software/ModemManager/api/latest/gdbus-org.freedesktop.ModemManager1.Modem.html#gdbus-method-org-freedesktop-ModemManager1-Modem.GetCellInfo)
  distinguishes serving and neighboring cells, cell type and channel data.
- [ETSI TS 136 101 V17.14.0](https://www.etsi.org/deliver/etsi_ts/136100_136199/136101/17.14.00_60/ts_136101v171400p.pdf),
  section 5.7.3/table 5.7.3-1 supplies DL EARFCN ranges and the frequency formula.

On the actual USB, a read-only probe returned one serving LTE EARFCN 1501 and
one neighbor. The serving channel maps to **B3, nominal 1800 MHz, DL 1835.1 MHz**;
the neighbor was not treated as the active band. This is physical read support,
not visual acceptance or a band-selection test. Installation/served UI validation
is recorded separately after CI. Regression coverage tests boundary channels,
neighbor exclusion, malformed data, unavailable status, USSD/registration gates,
read-only DBus methods, field privacy and the header/cache behavior.

Full local suite after integration: **877 PASS, 2 Windows platform skips**,
exit 0. An initial run caught a separator-encoding error in the new header;
it was fixed and all existing tests retained. Final SIM-popover addition is
also covered by the affected UI test before pushing.

## Installed validation — 2026-11-21

Installed three files from **`9e78ce766f1a442229701b8568d8b65276d3c4d2`** after
both [push CI](https://github.com/litequang/OpenStick/actions/runs/44890967912)
and [PR CI](https://github.com/litequang/OpenStick/actions/runs/44890971880) passed,
including Windows EXE checks. Six-file cellular recovery from `eaa7471` remains
in place. No merge to main/development, release or firmware change.

The actual installed decoder returned B3/1800 MHz, EARFCN 1501, DL 1835.1 MHz;
the complete status read took 0.686 s in one sample (not a latency benchmark).
Real Chrome opened the USB's actual `/overview` at 320, 390, 768 and 1366 px:
`4G · B3` appeared, both SIM and network details contained MHz/EARFCN, popovers
stayed within the viewport, another icon closed the previous popover and an
outside click closed the active one. Zero JS errors or unexpected mutations;
read-only request guard active, no screenshots/trace or phone acceptance.
The first harness outside-click targeted a heading covered by the open popover;
the corrected pointer target was genuinely outside and the full check passed.

Installation independently verified source/served asset hashes, permissions,
721 protected owner files and unchanged network/routes/firewall/DNS/gadget;
services healthy, sync complete. Only the two portal services and existing
startup worker restarted. The source backup/checksum stays private on the USB.
No band/operator/data/AP/power change was needed for this display deployment.

Final independent read after browser QA: all seven combined recovery/display
source hashes matched, 721 protected owner files and network/routes/firewall/
DNS/gadget/services still matched the deployment snapshot, recovery CONNECTED
with one attempt and no error, SIM-bound Internet PASS, sync complete.

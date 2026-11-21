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

"""Sanitize serving LTE channels; never export cell/location identifiers.

MM GetCellInfo uses MMCellType.LTE=5 and downlink EARFCN. CurrentBands is
an allowed-band filter, not serving-band evidence. Mapping: 3GPP TS 36.101
V17.14.0, 5.7.3 table 5.7.3-1 (only explicitly listed ranges below).
https://www.etsi.org/deliver/etsi_ts/136100_136199/136101/17.14.00_60/ts_136101v171400p.pdf
"""
from numbers import Integral

# band, nominal MHz, first/last DL EARFCN, first DL frequency in tenths MHz.
RANGES = ((1,2100,0,599,21100), (3,1800,1200,1949,18050),
          (5,850,2400,2649,8690), (7,2600,2750,3449,26200),
          (8,900,3450,3799,9250), (20,800,6150,6449,7910),
          (28,700,9210,9659,7580), (38,2600,37750,38249,25700),
          (40,2300,38650,39649,23000), (41,2500,39650,41589,24960))


def serving_lte(cells):
    """Return only serving carriers with known channel mappings, at most 8.

    Neighbors and unknown/malformed entries never become an active band.
    No inference from modem model, operator, signal or allowed bands.
    """
    if not isinstance(cells, (list, tuple)) or len(cells) > 128:return []
    result = []
    for cell in cells:
        if not isinstance(cell, dict) or cell.get('serving') != True:continue
        kind, channel = cell.get('cell-type'), cell.get('earfcn')
        if (not isinstance(kind, Integral) or isinstance(kind, bool) or kind != 5
                or not isinstance(channel, Integral) or isinstance(channel, bool)):continue
        for band, nominal, first, last, base in RANGES:
            if first <= channel <= last:
                row = {'band':band, 'nominal_mhz':nominal, 'earfcn':int(channel),
                       'downlink_mhz':(base+int(channel)-first)/10}
                if row not in result:result.append(row)
                break
        if len(result) == 8:break
    return result

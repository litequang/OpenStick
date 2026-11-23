import pytest

from uz801_manager.serving_lte import RANGES, serving_lte


@pytest.mark.parametrize('band,nominal,first,last,base', RANGES)
def test_known_lte_channel_boundaries(band, nominal, first, last, base):
    for channel in (first, last):
        assert serving_lte([{'cell-type':5,'serving':True,'earfcn':channel}]) == [
            {'band':band,'nominal_mhz':nominal,'earfcn':channel,
             'downlink_mhz':(base+channel-first)/10}]


def test_serving_filter_deduplication_and_location_exclusion():
    serving = {'cell-type':5,'serving':True,'earfcn':1501,
               'ci':'private-cell','tac':'private-area','operator-id':'private-network'}
    assert serving_lte([{'cell-type':5,'serving':False,'earfcn':1874},serving,serving]) == [
        {'band':3,'nominal_mhz':1800,'earfcn':1501,'downlink_mhz':1835.1}]


@pytest.mark.parametrize('cells', [None, {}, [{}]*129, [None],
    [{'serving':True,'cell-type':5,'earfcn':'1501'}],
    [{'serving':True,'cell-type':5,'earfcn':True}],
    [{'serving':True,'cell-type':5,'earfcn':-1}],
    [{'serving':True,'cell-type':5,'earfcn':5000}],
    [{'serving':True,'cell-type':6,'earfcn':1501}],
    [{'serving':False,'cell-type':5,'earfcn':1501}]])
def test_unknown_or_malformed_cells_never_guess_a_band(cells):
    assert serving_lte(cells) == []

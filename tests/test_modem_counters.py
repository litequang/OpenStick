import copy

import pytest

from uz801_manager.modem_counters import bearer_counters
from uz801_manager.modem_device import ROOT, MODEM, PROPS, INTRO, SERVICE


class Bus:
    def __init__(self):
        self.calls=[];self.closed=False;self.paths=['0'];self.bearers=[ROOT+'/Bearer/7']
        self.values={'Connected':True,'Interface':'wwan0','ReloadStatsSupported':True,
                     'Stats':{'rx-bytes':10000,'tx-bytes':20000,'attempts':3,'start-date':1795000000,
                              'private-field':'not-exported'}}

    def call_blocking(self, service, path, interface, method, signature, args, **kwargs):
        assert service==SERVICE and 0 < kwargs['timeout'] <= 1
        self.calls.append((path,interface,method,args))
        if method=='Introspect':
            assert interface==INTRO and path==ROOT+'/Modem'
            return '<node>'+''.join(f'<node name="{n}"/>' for n in self.paths)+'</node>'
        assert interface==PROPS and method=='Get' and signature=='ss'
        if args==[MODEM,'Bearers']:return self.bearers
        assert args[0]==SERVICE+'.Bearer' and args[1] in self.values
        return copy.deepcopy(self.values[args[1]])

    def close(self):self.closed=True


def test_typed_bearer_read_has_only_readonly_properties_and_private_epoch():
    b=Bus();v=bearer_counters('wwan0',bus_factory=lambda:b)
    assert v=={'rx':10000,'tx':20000,'epoch':'7:3:1795000000'}
    assert 'not-exported' not in repr(v) and b.closed
    assert all(v[2] in ('Get','Introspect') for v in b.calls)


@pytest.mark.parametrize('key,value', [('Connected',False),('Interface','wlan0'),
    ('ReloadStatsSupported',False),('Stats',{}),
    ('Stats',{'rx-bytes':True,'tx-bytes':0,'attempts':1,'start-date':1795000000}),
    ('Stats',{'rx-bytes':-1,'tx-bytes':0,'attempts':1,'start-date':1795000000}),
    ('Stats',{'rx-bytes':2**64,'tx-bytes':0,'attempts':1,'start-date':1795000000}),
    ('Stats',{'rx-bytes':0,'tx-bytes':0,'attempts':0,'start-date':1795000000}),
    ('Stats',{'rx-bytes':0,'tx-bytes':0,'attempts':1,'start-date':0})])
def test_missing_or_invalid_modem_stats_never_become_a_zero_sample(key,value):
    b=Bus();b.values[key]=value
    with pytest.raises(ValueError,match='^MODEM_COUNTERS_UNAVAILABLE$'):
        bearer_counters('wwan0',bus_factory=lambda:b)
    assert b.closed


def test_ambiguous_or_changing_connection_never_counts_twice():
    for change in ('modems','bearers','attempt','start'):
        class Changing(Bus):
            count=0
            def call_blocking(self,*args,**kwargs):
                value=super().call_blocking(*args,**kwargs)
                if args[3]=='Get' and args[5][-1]=='Stats':
                    self.count+=1
                    if self.count==2:value['start-date' if change=='start' else 'attempts']+=1
                return value
        b=Changing() if change in ('attempt','start') else Bus()
        if change=='modems':b.paths=['0','1']
        if change=='bearers':b.bearers=[ROOT+'/Bearer/7',ROOT+'/Bearer/8']
        with pytest.raises(ValueError):bearer_counters('wwan0',bus_factory=lambda:b)
        assert b.closed


def test_bus_failures_have_no_private_error_text():
    def fail():raise RuntimeError('private bus/device info')
    with pytest.raises(ValueError,match='^MODEM_COUNTERS_UNAVAILABLE$'):
        bearer_counters('wwan0',bus_factory=fail)


@pytest.mark.parametrize('interface',['usb0','wlan0','../wwan0',None])
def test_noncellular_interface_is_rejected_without_opening_bus(interface):
    def fail():raise AssertionError('must not open bus')
    with pytest.raises(ValueError):bearer_counters(interface,bus_factory=fail)

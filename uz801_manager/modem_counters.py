"""Read cached modem bearer counters when BAM-DMUX netdev stats are missing.

Only introspection and individual DBus property reads. No subscriber/device
identity, bearer Properties/APN credentials, radio or connection operations.
Private epoch prevents mixing modem connections; never export it in telemetry.
"""
from numbers import Integral
import re
import time
import xml.etree.ElementTree as ET


def bearer_counters(interface, *, bus_factory=None):
    from .modem_device import SERVICE, ROOT, MODEM, PROPS, INTRO, system_bus
    if not isinstance(interface,str) or not re.fullmatch(r'(?:wwan|rmnet)[A-Za-z0-9_.-]{0,26}',interface):
        raise ValueError('MODEM_COUNTERS_UNAVAILABLE')
    bus = None
    try:
        deadline = time.monotonic()+3
        bus = (bus_factory or system_bus)()
        def invoke(path, method, signature='', args=()):
            remaining = deadline-time.monotonic()
            if remaining <= 0:raise ValueError()
            return bus.call_blocking(SERVICE,path,INTRO if method=='Introspect' else PROPS,
                                     method,signature,list(args),timeout=min(1,remaining))

        def get(path, owner, key):return invoke(path,'Get','ss',(owner,key))

        tree = ET.fromstring(str(invoke(ROOT+'/Modem','Introspect')))
        paths = [ROOT+'/Modem/'+n.get('name') for n in tree.findall('node')
                 if re.fullmatch('[0-9]+',n.get('name',''))]
        if len(paths) != 1:raise ValueError()
        bearers = get(paths[0],MODEM,'Bearers')
        if len(bearers) > 32:raise ValueError()
        rows = []
        for path in bearers:
            path = str(path)
            if not re.fullmatch(re.escape(ROOT)+r'/Bearer/[0-9]{1,10}',path):raise ValueError()
            owner = SERVICE+'.Bearer'
            if not get(path,owner,'Connected') or str(get(path,owner,'Interface')) != interface:continue
            if not get(path,owner,'ReloadStatsSupported'):raise ValueError()
            stats = get(path,owner,'Stats')
            values = {}
            for key in ('rx-bytes','tx-bytes','attempts','start-date'):
                value = stats.get(key)
                if not isinstance(value,Integral) or isinstance(value,bool) or not 0 <= value < 2**64:
                    raise ValueError()
                values[key] = int(value)
            if not values['attempts'] or not values['start-date']:raise ValueError()
            fresh = get(path,owner,'Stats')
            if (not get(path,owner,'Connected') or str(get(path,owner,'Interface')) != interface
                    or any(int(fresh.get(key,-1)) != values[key] for key in ('attempts','start-date'))):
                raise ValueError()
            rows.append({'rx':values['rx-bytes'],'tx':values['tx-bytes'],
                         'epoch':f"{path.rsplit('/',1)[1]}:{values['attempts']}:{values['start-date']}"})
        if len(rows) != 1:raise ValueError()
        return rows[0]
    except Exception:
        raise ValueError('MODEM_COUNTERS_UNAVAILABLE') from None
    finally:
        if bus is not None:
            try:bus.close()
            except Exception:pass

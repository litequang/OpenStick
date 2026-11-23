"""BAM-DMUX runtime-PM guard; never resets a modem, driver or USB gadget.

Only an explicit/previously consented cellular activation calls prepare(). GETs
only read status. Keep the host data transport awake across data off/on; release
our own hold before airplane-offline transitions. This mitigates idle resume
failures on the validated kernel, not a substitute for a corrected kernel.
"""
import json
from pathlib import Path
import re
import time

ERRORS = {'CELLULAR_TRANSPORT_POWER_ERROR', 'CELLULAR_TRANSPORT_UNAVAILABLE'}


class TransportPower:
    def __init__(self, root=Path('/'), *, clock=time.monotonic, sleep=time.sleep):
        self.root = Path(root);self.clock = clock;self.sleep = sleep
        self.marker = self.root/'run/openstick/cellular-pm-hold.json'

    def device(self):
        devices = set()
        base = self.root/'sys/class/net'
        if not base.exists():return None
        allowed = (self.root/'sys/devices').resolve()
        for item in base.iterdir():
            if not re.fullmatch(r'(?:wwan|rmnet)[A-Za-z0-9_.-]{0,26}',item.name):continue
            driver = item/'device/driver'
            if not driver.exists() or driver.resolve().name != 'bam-dmux':continue
            device = (item/'device').resolve()
            if not device.is_relative_to(allowed):raise ValueError()
            devices.add(device)
        if len(devices)>1:raise ValueError()
        return next(iter(devices),None)

    def status(self):
        try:
            device = self.device()
            if device is None:return {'state':'not_applicable','error':None}
            value = (device/'power/runtime_status').read_text().strip()
            control = (device/'power/control').read_text().strip()
            if value=='error':return {'state':'error','error':'CELLULAR_TRANSPORT_POWER_ERROR'}
            if value not in ('active','suspended','suspending','resuming') or control not in ('auto','on'):
                raise ValueError()
            return {'state':value,'held_awake':control=='on','error':None}
        except (OSError,ValueError):
            return {'state':'unknown','error':'CELLULAR_TRANSPORT_UNAVAILABLE'}

    def owned(self, device):
        if not self.marker.exists() and not self.marker.is_symlink():return False
        if self.marker.is_symlink() or self.marker.stat().st_size>4096:raise ValueError()
        value=json.loads(self.marker.read_text())
        if value!={'version':1,'device':str(device),'previous':'auto'}:raise ValueError()
        return True

    def prepare(self):
        """Called under the existing network/modem transaction locks, before NM up."""
        value=self.status()
        if value['error']:raise RuntimeError(value['error'])
        if value['state']=='not_applicable':return
        try:
            device=self.device();control=device/'power/control'
            self.owned(device)  # Invalid ownership must not be overwritten.
            if control.read_text().strip()=='auto':
                from .sim_usage import atomic
                atomic(self.marker,{'version':1,'device':str(device),'previous':'auto'})
                control.write_text('on\n')
            deadline=self.clock()+3
            while True:
                current=self.status()
                if current['error']:raise RuntimeError(current['error'])
                if current['state']=='active' and current.get('held_awake'):return
                if self.clock()>=deadline:raise RuntimeError('CELLULAR_TRANSPORT_UNAVAILABLE')
                self.sleep(.1)
        except RuntimeError:raise
        except (OSError,ValueError,TypeError,AttributeError):
            raise RuntimeError('CELLULAR_TRANSPORT_UNAVAILABLE') from None

    def release(self):
        """Release only our hold before radio disable; never restore external policy."""
        try:
            device=self.device()
            if device is None or not self.owned(device):return
            control=device/'power/control'
            if control.read_text().strip()=='on':control.write_text('auto\n')
            if control.read_text().strip()!='auto':raise ValueError()
            self.marker.unlink()
        except (OSError,ValueError,TypeError,AttributeError):
            raise RuntimeError('CELLULAR_TRANSPORT_UNAVAILABLE') from None

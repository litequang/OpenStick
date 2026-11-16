"""USB Internet sharing without touching the gadget or its NM profile.

The existing management DHCP server has no router/DNS options. Only that
validated usb0 server is exchanged; USB addresses, UDC and SSH stay intact.
All mutating methods are called under the portal's network lock.
"""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time
import uuid

from .hotspot import AP_UUID, CELL_UUID, Network, network_lock
from .modem_device import modem_lock
from .quick_intent import data_allowed
from .setup_ap import SETUP_UUID

SERVICE = 'openstick-usb-dhcp'
TABLE = 'openstick_usb_tether'
MANAGEMENT = ['unudhcpd', '-i', 'usb0', '-s', '172.16.42.1', '-c', '172.16.42.2']


class UsbTethering:
    def __init__(self, directory='/var/lib/openstick', *, network=None, proc='/proc',
                 service='/etc/init.d/openstick-usb-dhcp', sysctl='/proc/sys/net/ipv4/ip_forward', supported=None,
                 clock=time.monotonic, lock_factory=network_lock, modem_lock_factory=modem_lock, readiness=None,
                 controller='/etc/init.d/openstick-usb-tether'):
        self.directory = Path(directory)
        self.path = self.directory / 'usb-tethering.json'
        self.intent_path = self.directory / 'usb-tethering-intent.json'
        self.network = network or Network()
        self.proc, self.service, self.sysctl = Path(proc), Path(service), Path(sysctl)
        self.supported = supported or (lambda: os.name == 'posix' and self.service.is_file() and self.sysctl.is_file() and Path(controller).is_file())
        self.clock, self.lock_factory, self.modem_lock_factory = clock, lock_factory, modem_lock_factory
        self.readiness = readiness

    def boot(self):return (self.proc / 'sys/kernel/random/boot_id').read_text().strip()

    def read(self, path=None):
        try:
            value = json.loads((path or self.path).read_text())
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):return {}

    def write(self, value, path=None):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd, stage = tempfile.mkstemp(prefix='.usb-tethering-', dir=self.directory)
        try:
            with os.fdopen(fd, 'w') as stream:
                json.dump(value, stream);stream.flush();os.fsync(stream.fileno())
            os.replace(stage, path or self.path)
            if os.name == 'posix':
                descriptor = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
                try:os.fsync(descriptor)
                finally:os.close(descriptor)
        finally:
            if os.path.exists(stage):os.unlink(stage)

    def running(self):
        try:
            pid = (Path('/run/openstick/usb-dhcp.pid')).read_text().strip()
            return pid.isdigit() and b'--dhcp-leasefile=/run/openstick/usb.leases' in (self.proc / pid / 'cmdline').read_bytes()
        except OSError:return False

    def status(self):
        available = self.supported()
        value = self.read()
        intent = self.read(self.intent_path)
        reboot_pending = False
        try:
            same_boot = intent.get('request_boot') == self.boot()
            reboot_pending = (same_boot and intent.get('phase') in ('QUEUED', 'WAITING_MODEM', 'AWAIT_BOOT') or
                              not same_boot and intent.get('phase') == 'APPLYING')
            requested = available and value.get('enabled') is True and value.get('boot') == self.boot()
            enabled = requested and self.running() and self.sysctl.read_text().strip() == '1'
            if enabled:
                result = self.network.run(['nft', 'list', 'table', 'inet', TABLE],capture_output=True,text=True,timeout=8)
                enabled = result.returncode == 0 and 'masquerade' in result.stdout
        except (OSError, subprocess.SubprocessError):requested = False;enabled = False
        return {'available': available, 'enabled': bool(enabled),
                'reason': None if available else 'USB_TETHERING_NOT_INSTALLED',
                'degraded': bool(requested and not enabled),
                'desired_enabled': intent.get('desired') is True,
                'apply_state': intent.get('phase'), 'reboot_pending': bool(reboot_pending),
                'operation': intent.get('operation'),
                'host_dhcp_renew_required': False, 'boot_replay': True}

    def request(self, enabled, operation):
        """The dialog authorizes one normal reboot; no live gadget/profile reset."""
        if type(enabled) is not bool or str(uuid.UUID(operation)) != operation:raise ValueError('INPUT_INVALID')
        if not self.supported():raise RuntimeError('USB_TETHERING_NOT_INSTALLED')
        if self.status()['reboot_pending']:raise RuntimeError('USB_REBOOT_PENDING')
        self.write({'version': 2, 'desired': enabled, 'operation': operation,
                    'request_boot': self.boot(), 'phase': 'QUEUED', 'after': self.clock()+5}, self.intent_path)

    def tick(self):
        """Apply saved sharing on boot, but never turn on SIM or request a second reboot."""
        with self.lock_factory():
            intent = self.read(self.intent_path)
            if intent.get('version') != 2 or type(intent.get('desired')) is not bool:return
            boot = self.boot()
            if intent.get('request_boot') == boot:
                if intent.get('phase') in ('QUEUED', 'WAITING_MODEM'):
                    if self.clock() < intent.get('after', 0):return
                    with self.modem_lock_factory():
                        if self.read(self.directory/'setup-pending.json') or self.read(self.directory/'hotspot-pending.json'):return
                        try:
                            if self.readiness:ready = self.readiness()
                            else:
                                from .quick_settings import RadioControl
                                ready = RadioControl().status()
                        except RuntimeError as error:
                            if str(error) != 'MODEM_UNAVAILABLE':raise
                            ready = {}
                        if ready.get('ussd_state') in (2, 3):
                            if intent['phase'] != 'WAITING_MODEM':
                                intent['phase'] = 'WAITING_MODEM';self.write(intent, self.intent_path)
                            return
                        intent.update(phase='AWAIT_BOOT', deadline=self.clock()+45)
                        self.write(intent, self.intent_path)  # Durable before issuing reboot.
                        try:self.network.command(['/sbin/reboot'], timeout=10)
                        except Exception:
                            intent['phase'] = 'REBOOT_FAILED';self.write(intent, self.intent_path)
                elif intent.get('phase') == 'AWAIT_BOOT' and self.clock() > intent.get('deadline', 0):
                    intent['phase'] = 'REBOOT_FAILED';self.write(intent, self.intent_path)
                return
            if intent.get('applied_boot') == boot and intent.get('phase') in ('APPLIED', 'APPLY_FAILED'):return
            if intent.get('applying_boot') != boot:
                intent.update(phase='APPLYING', applying_boot=boot, apply_deadline=self.clock()+120)
                self.write(intent, self.intent_path)
            try:
                if intent['desired']:self.enable(require_internet=False)
                else:self.disable()
                intent.update(phase='APPLIED', applied_boot=boot)
            except Exception:
                # The dispatcher still supplies DHCP/USB administration; no reboot loop.
                if self.clock() < intent['apply_deadline']:return
                intent.update(phase='APPLY_FAILED', applied_boot=boot)
            self.write(intent, self.intent_path)

    def _management_processes(self):
        found = []
        for proc in self.proc.glob('[0-9]*'):
            try:
                if (proc / 'comm').read_text().strip() != 'unudhcpd':continue
                args = [v.decode() for v in (proc / 'cmdline').read_bytes().split(b'\0') if v]
                if 'usb0' not in args:continue
                if [Path(args[0]).name, *args[1:]] != MANAGEMENT:
                    raise RuntimeError('USB_DHCP_CONFLICT')
                found.append((int(proc.name), (proc / 'stat').read_text().split()[21]))
            except OSError:continue
        if len(found) > 1:raise RuntimeError('USB_DHCP_CONFLICT')
        return found

    def _stop_management(self):
        for pid, start in self._management_processes():
            proc = self.proc / str(pid)
            # Recheck identity immediately before signalling; never kill a reused PID.
            if (proc / 'stat').read_text().split()[21] != start:raise RuntimeError('USB_DHCP_CONFLICT')
            os.kill(pid, signal.SIGTERM)
            for _ in range(30):
                try:
                    if not (proc / 'cmdline').read_bytes():break
                except OSError:break
                time.sleep(.1)
            else:raise RuntimeError('USB_DHCP_CONFLICT')

    def _restore_management(self):
        if not self._management_processes():
            subprocess.Popen(MANAGEMENT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
            for _ in range(20):
                if self._management_processes():return
                time.sleep(.1)
            raise RuntimeError('USB_DHCP_RESTORE_FAILED')

    def upstreams(self):
        interfaces = {'wlan0'}
        controls = self.network.devices()
        for control in controls:
            value = self.network.nm('-g', 'GENERAL.IP-IFACE', 'device', 'show', control)
            if re.fullmatch(r'[A-Za-z0-9_.-]{1,32}', value) and value not in ('usb0', 'lo', '--'):
                interfaces.add(value)
        return sorted(interfaces)

    def _uplink(self):
        try:route = self.network.command(['ip', '-4', 'route', 'get', '1.1.1.1'])
        except RuntimeError:raise RuntimeError('USB_NO_INTERNET') from None
        match = re.search(r'\bdev ([A-Za-z0-9_.-]{1,32})\b', route)
        if not match:raise RuntimeError('USB_NO_INTERNET')
        interface = match[1]
        control = None
        if interface == 'wlan0' and self.network.active('wlan0') not in (None, AP_UUID, SETUP_UUID):control = 'wlan0'
        for device in self.network.devices():
            if (self.network.active(device) == CELL_UUID and data_allowed(self.directory)
                    and self.network.cellular_interface(device) == interface):control = device
        if not control or not self.network.internet(interface, control):raise RuntimeError('USB_NO_INTERNET')
        return interface

    def _rules(self, enabled):
        exists = self.network.run(['nft', 'list', 'table', 'inet', TABLE], capture_output=True, timeout=8).returncode == 0
        prefix = 'delete table inet '+TABLE+'\n' if exists else ''
        if enabled:
            names = ', '.join('"'+name+'"' for name in self.upstreams())
            body = ('chain forward { type filter hook forward priority -7; policy accept; '
                    'iifname "usb0" ip saddr != 172.16.42.0/24 drop; '
                    'iifname "usb0" oifname != { '+names+' } drop; '
                    'oifname "usb0" ct state != { established, related } drop; }\n '
                    'chain srcnat { type nat hook postrouting priority srcnat; policy accept; '
                    'ip saddr 172.16.42.0/24 oifname { '+names+' } masquerade; }\n')
        else:
            body = ('chain forward { type filter hook forward priority -7; policy accept; '
                    'iifname "usb0" drop; oifname "usb0" drop; }\n')
        rules = prefix+'table inet '+TABLE+' {\n '+body+'}\n'
        result = self.network.run(['nft', '-f', '-'], input=rules, text=True, capture_output=True, timeout=8)
        if result.returncode:raise RuntimeError('USB_TETHERING_FIREWALL_FAILED')

    def update_uplinks(self):
        if self.status()['enabled']:self._rules(True)

    def enable(self, *, require_internet=True):
        if not self.status()['available']:raise RuntimeError('USB_TETHERING_NOT_INSTALLED')
        if self.status()['enabled']:return self.status()
        identity = self.network.active('usb0')
        if not identity or self.network.nm('-g', 'ipv4.method', 'connection', 'show', 'uuid', identity) != 'manual':
            raise RuntimeError('USB_PROFILE_UNSUPPORTED')
        if require_internet:self._uplink()
        previous = self.sysctl.read_text().strip()
        if previous not in ('0', '1'):raise RuntimeError('USB_PROFILE_UNSUPPORTED')
        self._rules(False)
        try:
            management = self._management_processes()
            if not management and not self.running():raise RuntimeError('USB_DHCP_CONFLICT')
            if management:self._stop_management()
            self.network.command(['rc-service', SERVICE, 'start'], timeout=20)
            for _ in range(20):
                if self.running():break
                time.sleep(.1)
            else:raise RuntimeError('USB_DHCP_CONFLICT')
            self.sysctl.write_text('1\n')
            self._rules(True)
            self.write({'version': 1, 'enabled': True, 'boot': self.boot(), 'previous_forward': previous})
        except Exception:
            self._rules(False)
            self.network.run(['rc-service', SERVICE, 'stop'], capture_output=True, timeout=20)
            self._restore_management()
            if previous == '0' and self.network.active('wlan0') not in (AP_UUID, SETUP_UUID):self.sysctl.write_text('0\n')
            raise
        return self.status()
    def disable(self):
        value = self.read()
        self._rules(False)  # Close forwarding first, regardless of DHCP recovery.
        self.network.command(['rc-service', SERVICE, 'stop'], timeout=20)
        self._restore_management()
        if value.get('previous_forward') == '0' and self.network.active('wlan0') not in (AP_UUID, SETUP_UUID):
            self.sysctl.write_text('0\n')
        self.write({'version': 1, 'enabled': False, 'boot': self.boot()})
        return self.status()


def main():
    backend = UsbTethering()
    while True:
        try:backend.tick()
        except Exception:pass  # No credentials, identifiers or raw errors in logs.
        time.sleep(2)


if __name__ == '__main__':main()

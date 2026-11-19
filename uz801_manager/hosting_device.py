"""Linux USB-only portal. Does not expose firmware or Android operations."""
import json
import socket
import subprocess
import sys
import threading
import time
from copy import deepcopy

from waitress import serve

from .hosting import REMOTE, WIFI_ERRORS, create_hosting_app
from .modem_device import ModemManager
from .static_site import StaticSite
from .hotspot import Hotspot
from .sms_archive import ArchivedModem
from .network_policy import NetworkPolicy
from .setup_ap import SetupAP
from .leds import LedSettings
from .quick_settings import QuickSettings
from .device_power import DevicePower


class LocalWifi:
    def __init__(self, *, run=subprocess.run, clock=time.monotonic):
        self.run, self.clock = run, clock
        self.status_lock = threading.Lock()
        self.cache_lock = threading.Lock()
        self.status_value = None
        self.status_at = 0
        self.status_generation = 0

    def invalidate_status(self):
        with self.cache_lock:
            self.status_generation += 1
            self.status_value = None

    def call(self, action, **values):
        if action == 'status':
            # Concurrent header/legacy status reads share one bounded subprocess. This
            # cache is display-only; all mutation paths retain their live checks.
            with self.status_lock:
                with self.cache_lock:
                    if self.status_value is not None and self.clock()-self.status_at < 2:return deepcopy(self.status_value)
                    generation = self.status_generation
                value = self._call(action, **values)
                with self.cache_lock:
                    if generation == self.status_generation:self.status_value, self.status_at = value, self.clock()
                return deepcopy(value)
        try:return self._call(action, **values)
        finally:
            self.invalidate_status()

    def dashboard(self):
        # Connections arrive through the independent, shared header producer.
        # Keep legacy call('overview') behavior for older clients.
        from .portal_metrics import system_snapshot
        return {'system':system_snapshot(), 'wifi':{}, 'services':{}}

    def services(self):
        from .portal_metrics import service_snapshot
        return {'services':service_snapshot()}

    def _call(self, action, **values):
        result = self.run([sys.executable, '-c', REMOTE],
                          input=json.dumps({'action': action, **values}).encode(),
                          capture_output=True, timeout=110 if action == 'connect' else 50, shell=False)
        if len(result.stdout) > 65536:
            raise RuntimeError('NETWORK_OPERATION_FAILED')
        try:parsed = json.loads(result.stdout)
        except (ValueError, UnicodeError):raise RuntimeError('NETWORK_OPERATION_FAILED') from None
        if isinstance(parsed, dict) and parsed.get('error') in WIFI_ERRORS:
            raise RuntimeError(parsed['error'])
        if result.returncode:raise RuntimeError('NETWORK_OPERATION_FAILED')
        if not isinstance(parsed, dict) or 'error' in parsed:
            raise RuntimeError('NETWORK_OPERATION_FAILED')
        return parsed


def usb_socket(port=80):
    # Bind to the incoming interface as well as its address. Linux's weak
    # host model otherwise permits traffic to a USB IP arriving over Wi-Fi.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'usb0\0')
        sock.bind(('172.16.42.1', port))
        return sock
    except Exception:
        sock.close()
        raise


def main():
    from .lan_access import LAN_AUTHORITY, LanSettings
    from .lan_device import wifi_ipv4
    def lan_changed():
        result = subprocess.run(['rc-service', 'openstick-lan', 'restart'], capture_output=True, timeout=25)
        if result.returncode:raise RuntimeError('LAN_RESTART_FAILED')
    with open('/etc/openstick/hosting.json', encoding='utf-8') as source:
        hostname = json.load(source)['hostname']
    app = create_hosting_app(backend=LocalWifi(), hostname=hostname, usb_portal=True,
                             authority=('172.16.42.1', '172.16.42.1:8765', LAN_AUTHORITY),
                             modem_backend=ArchivedModem(ModemManager()), lan_settings=LanSettings(address=wifi_ipv4),
                             lan_changed=lan_changed, site_backend=StaticSite(), hotspot_backend=Hotspot(), network_backend=NetworkPolicy(), setup_backend=SetupAP(), led_backend=LedSettings(), quick_backend=QuickSettings(),power_backend=DevicePower())
    with usb_socket() as sock, usb_socket(8765) as named_sock:
        serve(app, sockets=[sock, named_sock], threads=4, channel_timeout=120,
              max_request_body_size=129 * 1048576, inbuf_overflow=65536, ident='OpenStick')


if __name__ == '__main__':
    main()

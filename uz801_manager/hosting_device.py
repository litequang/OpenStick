"""Linux USB-only portal. Does not expose firmware or Android operations."""
import json
import socket
import subprocess
import sys

from waitress import serve

from .hosting import REMOTE, WIFI_ERRORS, create_hosting_app
from .modem_device import ModemManager
from .static_site import StaticSite
from .hotspot import Hotspot
from .sms_archive import ArchivedModem
from .network_policy import NetworkPolicy
from .setup_ap import SetupAP


class LocalWifi:
    def __init__(self, *, run=subprocess.run):
        self.run = run

    def call(self, action, **values):
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


def usb_socket():
    # Bind to the incoming interface as well as its address. Linux's weak
    # host model otherwise permits traffic to a USB IP arriving over Wi-Fi.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'usb0\0')
        sock.bind(('172.16.42.1', 80))
        return sock
    except Exception:
        sock.close()
        raise


def main():
    from .lan_access import LanSettings
    from .lan_device import wifi_ipv4
    def lan_changed():
        result = subprocess.run(['rc-service', 'openstick-lan', 'restart'], capture_output=True, timeout=25)
        if result.returncode:raise RuntimeError('LAN_RESTART_FAILED')
    with open('/etc/openstick/hosting.json', encoding='utf-8') as source:
        hostname = json.load(source)['hostname']
    app = create_hosting_app(backend=LocalWifi(), hostname=hostname, usb_portal=True,
                             modem_backend=ArchivedModem(ModemManager()), lan_settings=LanSettings(address=wifi_ipv4),
                             lan_changed=lan_changed, site_backend=StaticSite(), hotspot_backend=Hotspot(), network_backend=NetworkPolicy(), setup_backend=SetupAP())
    with usb_socket() as sock:
        serve(app, sockets=[sock], threads=2, channel_timeout=30,
              max_request_body_size=1500000, ident='OpenStick')


if __name__ == '__main__':
    main()

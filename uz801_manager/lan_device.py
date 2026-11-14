"""Separate, opt-in Wi-Fi-bound listener. Never part of Tunnel ingress."""
import json
import socket
import struct
import time

from waitress import serve

from .hosting import create_hosting_app
from .hosting_device import LocalWifi
from .lan_access import LAN_AUTHORITY, LanSettings
from .modem_device import ModemManager
from .static_site import StaticSite
from .hotspot import Hotspot
from .sms_archive import ArchivedModem
from .network_policy import NetworkPolicy
from .setup_ap import SetupAP
from .leds import LedSettings


def wifi_ipv4():
    import fcntl
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            data = fcntl.ioctl(sock.fileno(), 0x8915, struct.pack('256s', b'wlan0'))
            return socket.inet_ntoa(data[20:24])
        except OSError:
            return None


def lan_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, b'wlan0\0')
        sock.bind(('0.0.0.0', 8765))
        return sock
    except Exception:
        sock.close()
        raise


def lan_authorities(address):
    # Keep both exact authorities private to the Wi-Fi-bound listener.
    # Origin must still match the specific Host used for each request.
    return (address + ':8765', LAN_AUTHORITY) if address else ()


def main():
    settings = LanSettings(address=wifi_ipv4)
    while not settings.private():time.sleep(3)
    with open('/etc/openstick/hosting.json') as source:hostname = json.load(source)['hostname']
    def authority():
        return lan_authorities(wifi_ipv4())
    app = create_hosting_app(backend=LocalWifi(), modem_backend=ArchivedModem(ModemManager()), usb_portal=True,
                             hostname=hostname, lan_auth=settings,
                             authority=authority, site_backend=StaticSite(), hotspot_backend=Hotspot(), network_backend=NetworkPolicy(), setup_backend=SetupAP(), led_backend=LedSettings())
    with lan_socket() as sock:
        serve(app, sockets=[sock], threads=2, channel_timeout=30, max_request_body_size=1500000, ident='OpenStick')


if __name__ == '__main__':main()

"""Explicit Quick Settings transactions; status never changes device state."""
from contextlib import nullcontext
import configparser
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

from .hotspot import AP_UUID, CELL_UUID, Hotspot, Network, network_lock
from .modem_device import OperationJournal, modem_lock, system_bus
from .network_policy import NetworkPolicy
from .quick_intent import data_allowed, load_intent, radio_allowed, save_intent
from .setup_ap import SETUP_UUID, SetupAP, SetupNetwork

ACTIONS = ('airplane_on', 'airplane_off', 'data_on', 'data_off', 'local_ap_on', 'local_ap_off', 'usb_tether_on', 'usb_tether_off',
           'wifi_auto', 'wifi_saved', 'wifi_scan', 'wifi_connect', 'wifi_off')
ERRORS = {'INPUT_INVALID', 'CONFIRM_REQUIRED', 'CONSENT_REQUIRED', 'ALREADY_ATTEMPTED',
          'NETWORK_BUSY', 'MODEM_BUSY', 'MODEM_UNAVAILABLE', 'SIM_NOT_READY', 'AIRPLANE_ACTIVE',
          'PENDING_NETWORK_TRIAL', 'CELLULAR_ALREADY_ACTIVE', 'CELLULAR_NOT_CONFIGURED',
          'DATA_DISCONNECT_FAILED', 'LOCAL_AP_UNAVAILABLE', 'RADIO_RESULT_UNKNOWN',
          'QUICK_OPERATION_FAILED', 'DATA_OFF_AP_FAILED'}
ERRORS |= {'USB_NO_INTERNET', 'USB_DHCP_CONFLICT', 'USB_DHCP_RESTORE_FAILED',
           'USB_TETHERING_NOT_INSTALLED', 'USB_PROFILE_UNSUPPORTED', 'USB_TETHERING_FIREWALL_FAILED',
           'USB_REBOOT_PENDING', 'DATA_CONNECT_FAILED'}
ERRORS |= {'WIFI_SAVED_NOT_FOUND', 'WIFI_PROFILE_NOT_FOUND', 'WIFI_NOT_CONNECTED',
           'WIFI_CONNECT_FAILED', 'WIFI_SCAN_FAILED', 'WIFI_RESTORE_FAILED',
           'WIFI_AUTH_REQUIRED', 'WIFI_TIMEOUT', 'WIFI_NOT_FOUND'}


def validate_quick(value):
    if not isinstance(value, dict) or value.get('action') not in ACTIONS:
        raise ValueError('INPUT_INVALID')
    expected = {'action', 'operation', 'confirm'} | ({'cellular_consent'} if value['action'] in ('data_on', 'usb_tether_on') else set())
    if value['action'] in ('wifi_saved', 'wifi_connect'):expected |= {'ssid'}
    if value['action'] == 'wifi_connect':expected |= {'password'}
    if set(value) != expected or not isinstance(value['operation'], str):
        raise ValueError('INPUT_INVALID')
    if str(uuid.UUID(value['operation'])) != value['operation']:
        raise ValueError('INPUT_INVALID')
    if value['confirm'] is not True:
        raise ValueError('CONFIRM_REQUIRED')
    if value['action'] in ('data_on', 'usb_tether_on') and value['cellular_consent'] is not True:
        raise ValueError('CONSENT_REQUIRED')
    if value['action'] in ('wifi_saved', 'wifi_connect'):
        ssid = value['ssid']
        if not isinstance(ssid, str) or not 1 <= len(ssid.encode()) <= 32 or any(ord(c)<32 or ord(c)==127 for c in ssid):
            raise ValueError('INPUT_INVALID')
    if value['action'] == 'wifi_connect':
        from .setup_ap import validate_setup
        validate_setup({'action':'connect','ssid':value['ssid'],'password':value['password'],'confirm':True})
    return value['action']


class RadioControl:
    """Typed, narrow DBus surface: no identities, GetAll, SMS or USSD content."""
    def __init__(self, bus_factory=system_bus, ussd_state=None):
        self.bus_factory = bus_factory
        if ussd_state is None:
            from .ussd_qmi import QmiUssd
            ussd_state = lambda: QmiUssd().status().get('state')
        self.ussd_state = ussd_state

    def _call(self, enabled=None):
        bus = self.bus_factory()
        service = 'org.freedesktop.ModemManager1'
        base = '/org/freedesktop/ModemManager1'
        props = 'org.freedesktop.DBus.Properties'
        interface = service + '.Modem'
        try:
            tree = ET.fromstring(str(bus.call_blocking(service, base + '/Modem',
                'org.freedesktop.DBus.Introspectable', 'Introspect', '', [], timeout=8)))
            paths = [base + '/Modem/' + n.get('name') for n in tree.findall('node')
                     if n.get('name', '').isdigit()]
            if len(paths) != 1:
                raise RuntimeError('MODEM_UNAVAILABLE')
            path = paths[0]
            def get(name):
                return bus.call_blocking(service, path, props, 'Get', 'ss', [interface, name], timeout=8)
            state, power = int(get('State')), int(get('PowerState'))
            sim_ready = str(get('Sim')) not in ('', '/') and int(get('UnlockRequired')) in (1, 3, 5)
            try:
                session = int(bus.call_blocking(service, path, props, 'Get', 'ss',
                    [interface + '.Modem3gpp.Ussd', 'State'], timeout=8))
            except Exception:
                session = None
            qmi_session = self.ussd_state()
            if qmi_session in (2, 3):session = qmi_session
            if enabled is not None:
                if session in (2, 3):
                    raise RuntimeError('MODEM_BUSY')
                if enabled and not sim_ready:
                    return {'waiting_sim': True}
                if enabled and state >= 5:
                    return {'radio_request_needed': False}
                if not enabled and state in (-1, 3) and power in (1, 2):
                    return {'radio_request_needed': False}
                bus.call_blocking(service, path, interface, 'Enable', 'b', [enabled], timeout=60)
                return {'radio_request_needed': True}
            return {'state': state, 'power_state': power, 'sim_ready': sim_ready,
                    'registered': state >= 8, 'ussd_state': session}
        except RuntimeError:
            raise
        except Exception:
            raise RuntimeError('RADIO_RESULT_UNKNOWN') from None
        finally:
            bus.close()

    def status(self):
        return self._call()

    def enable(self, enabled):
        return self._call(enabled)


class QuickSettings:
    def __init__(self, directory='/var/lib/openstick', *, network=None, radio=None,
                 lock_factory=network_lock, modem_lock_factory=modem_lock,
                 hotspot=None, setup=None, journal=None, identity_matches=None, forwarding=None, tethering=None, wifi=None):
        self.directory = Path(directory)
        self.network = network or Network()
        self.radio = radio or RadioControl()
        self.lock_factory, self.modem_lock_factory = lock_factory, modem_lock_factory
        self.hotspot = hotspot or Hotspot(directory, network=self.network, lock_factory=nullcontext,
                                          modem_lock_factory=nullcontext)
        self.setup = setup or SetupAP(directory, network=SetupNetwork(run=self.network.run),
                                      lock_factory=nullcontext, modem_lock_factory=nullcontext)
        self.journal = journal or OperationJournal(self.directory / 'quick-operations')
        self.identity_matches = identity_matches or self._matching_ap_identity
        self.ap_forwarding = forwarding or self._ap_forwarding
        from .usb_tethering import UsbTethering
        self.tethering = tethering or UsbTethering(directory, network=self.network)
        from .quick_wifi import QuickWifi
        self.wifi = wifi or QuickWifi(self)

    def _ap_forwarding(self, allowed):
        """Only our AP guard; never alter the base firewall or USB gadget."""
        exists = self.network.run(['nft', 'list', 'table', 'inet', 'openstick_quick_ap'],
            capture_output=True, timeout=8).returncode == 0
        if allowed:
            if exists:self.network.command(['nft', 'delete', 'table', 'inet', 'openstick_quick_ap'])
        elif not exists:
            rules = ('table inet openstick_quick_ap {\n chain forward {\n type filter hook forward '
                     'priority -6; policy accept;\n iifname "wlan0" drop;\n oifname "wlan0" drop;\n }\n}\n')
            result = self.network.run(['nft', '-f', '-'], input=rules, text=True, capture_output=True, timeout=8)
            if result.returncode:raise RuntimeError('LOCAL_AP_UNAVAILABLE')

    def _start_shared_ap(self, control):
        """One AP with stable DHCP/gateway, independent of cellular connectivity."""
        previous = self.network.active('wlan0')
        connected = self.network.active(control) == CELL_UUID and bool(self.network.cellular_interface(control))
        self.ap_forwarding(connected and radio_allowed(self.directory) and data_allowed(self.directory))
        if previous == AP_UUID:return
        config = self._read('setup-ap.json')
        if not config.get('ssid') or not self.setup.lan_ready():raise RuntimeError('LOCAL_AP_UNAVAILABLE')
        if previous and previous != SETUP_UUID:
            config['previous_wifi'] = previous
            self.setup.write('setup-ap.json', config)
        snapshot = self.hotspot._setup_snapshot()
        try:
            self.hotspot._adopt_setup_ap()  # Preserves the existing cellular profile.
            if previous == SETUP_UUID:self.setup.network.local_services(False)
            self.network.up(AP_UUID)
            if self.network.active('wlan0') != AP_UUID:raise RuntimeError('LOCAL_AP_UNAVAILABLE')
        except Exception:
            self.hotspot._restore_setup_snapshot({'setup_handoff': snapshot})
            if previous == SETUP_UUID:
                self.network.up(SETUP_UUID)
                self.setup.network.local_services(True)
            elif previous:
                self.ap_forwarding(True)
                self.network.up(previous)
            raise RuntimeError('LOCAL_AP_UNAVAILABLE') from None

    def _matching_ap_identity(self):
        """Staged credentials must match the SIM AP before promising continuity."""
        try:
            profiles = []
            for name in ('openstick-hotspot', 'openstick-setup'):
                path = self.hotspot.profiles / (name + '.nmconnection')
                if path.is_symlink():return False
                profile = configparser.ConfigParser(interpolation=None)
                profile.read_string(path.read_text())
                profiles.append((profile.get('wifi', 'ssid'), profile.get('wifi-security', 'psk')))
            return bool(profiles[0][0] and profiles[0][1] and profiles[0] == profiles[1])
        except (OSError, configparser.Error):
            return False

    def _read(self, name):
        return self.hotspot.read(name)

    def _controls(self):
        devices = self.network.devices()
        if len(devices) != 1:
            raise RuntimeError('MODEM_UNAVAILABLE')
        return devices[0]

    def status(self):
        intent = load_intent(self.directory)
        radio = self.radio.status()
        wifi = self.network.active('wlan0')
        controls = self.network.devices()
        cell = self.network.active(controls[0]) if len(controls) == 1 else None
        pending = bool(self._read('setup-pending.json') or self._read('hotspot-pending.json') or self.tethering.status().get('reboot_pending'))
        return {'intent': intent, 'radio': radio,
                'wifi_role': 'local_ap' if wifi == SETUP_UUID else 'sim_ap' if wifi == AP_UUID else 'station' if wifi else 'offline',
                'mobile_data_connected': bool(cell == CELL_UUID and self.network.cellular_interface(controls[0])),
                'foreign_cellular_active': bool(cell and cell != CELL_UUID),
                'pending_network_trial': pending, 'internet_verified': False,
                'hardware_validation': 'NOT_TESTED',
                'usb_tethering': self.tethering.status(),
                'advanced_ap': {'wpa3': 'BLOCKED_PMF', 'hidden': 'NOT_HARDWARE_VERIFIED',
                                'client_limit': 'NOT_HARDWARE_VERIFIED', 'isolation': 'NOT_HARDWARE_VERIFIED'}}

    def _preflight(self):
        if self._read('setup-pending.json') or self._read('hotspot-pending.json'):
            raise RuntimeError('PENDING_NETWORK_TRIAL')
        radio = self.radio.status()
        if radio.get('ussd_state') in (2, 3):
            raise RuntimeError('MODEM_BUSY')
        control = self._controls()
        if self.network.active(control) not in (None, CELL_UUID):
            raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
        # A foreign auto-connect profile must not reconnect behind the owner's veto.
        rows = self.network.nm('-t', '-f', 'UUID,TYPE', 'connection', 'show').splitlines()
        for row in rows:
            identity, _, kind = row.partition(':')
            if kind == 'gsm' and identity != CELL_UUID:
                if self.network.nm('-g', 'connection.autoconnect', 'connection', 'show', 'uuid', identity) == 'yes':
                    raise RuntimeError('CELLULAR_ALREADY_ACTIVE')
        return radio, control

    def _stop_automation(self):
        NetworkPolicy(self.directory).write('network-policy.json',
            {'mode': 'wifi_only', 'enabled': False, 'auto_wifi': False, 'cellular_consent': False})
        config = self._read('hotspot.json')
        if config.get('ssid'):
            self.network.autoconnect(AP_UUID, False)
            config['enabled'] = False
            self.hotspot.write('hotspot.json', config)
        if config.get('ssid') or self.network.active(self._controls()) == CELL_UUID:
            self.network.autoconnect(CELL_UUID, False)

    def _off_data(self, *, recover_ap=True, keep_ap=False):
        control = self._controls()
        was_ap = self.network.active('wlan0') == AP_UUID
        gate_failed = False
        if was_ap:
            try:self.ap_forwarding(False)
            except Exception:gate_failed = True
        identity_matches = self.identity_matches() if was_ap and recover_ap else True
        automation_failed = False
        try:self._stop_automation()
        except Exception:automation_failed = True
        if self.network.active(control) == CELL_UUID:
            self.network.down(CELL_UUID)
        if self.network.active(control):
            raise RuntimeError('DATA_DISCONNECT_FAILED')
        if automation_failed or gate_failed:raise RuntimeError('QUICK_OPERATION_FAILED')
        if was_ap and not keep_ap:
            # Never call Hotspot.stop(): it can reconnect the old station Wi-Fi.
            self.network.down(AP_UUID)
            if recover_ap:
                try:
                    if not identity_matches:raise RuntimeError('LOCAL_AP_UNAVAILABLE')
                    config = self._read('setup-ap.json')
                    if not config.get('ssid') or not self.setup.lan_ready():
                        raise RuntimeError('LOCAL_AP_UNAVAILABLE')
                    self.setup.start()
                except Exception:
                    raise RuntimeError('DATA_OFF_AP_FAILED') from None

    def reconcile_airplane(self):
        """Boot recovery of an already saved OFF intent; never replay data-on."""
        if radio_allowed(self.directory):return
        with self.lock_factory(), self.modem_lock_factory():
            if radio_allowed(self.directory):return
            self._preflight()
            try:self._off_data()
            finally:
                try:self.radio.enable(False)
                finally:self.network.nm('radio', 'wwan', 'off')

    def call(self, action, **values):
        validate_quick({'action': action, **values})
        with self.lock_factory(), self.modem_lock_factory():
            radio, control = self._preflight()
            if self.tethering.status().get('reboot_pending'):
                raise RuntimeError('USB_REBOOT_PENDING')
            receipt = self.journal.begin(values['operation'], action)
            try:
                old = load_intent(self.directory)
                airplane = bool(old and old['airplane'])
                if action in ('airplane_on', 'airplane_off', 'data_off'):
                    airplane = action == 'airplane_on' or airplane and action != 'airplane_off'
                    save_intent(self.directory, airplane=airplane, data_allowed=False)
                    try:
                        self._off_data(keep_ap=action == 'data_off')
                    finally:
                        # Airplane-on must still suppress WWAN if AP recovery failed.
                        if action == 'airplane_on':
                            try:self.radio.enable(False)
                            finally:self.network.nm('radio', 'wwan', 'off')
                    if action == 'airplane_off':
                        self.network.nm('radio', 'wwan', 'on')
                        self.radio.enable(True)  # Missing SIM remains waiting, never a bearer.
                elif action == 'local_ap_on':
                    connected = self.network.active(control) == CELL_UUID and bool(self.network.cellular_interface(control))
                    if old is None:save_intent(self.directory, airplane=False, data_allowed=connected)
                    self._stop_automation()
                    self._start_shared_ap(control)
                elif action == 'data_on':
                    if not radio_allowed(self.directory):
                        raise RuntimeError('AIRPLANE_ACTIVE')
                    if not radio.get('sim_ready') or not radio.get('registered'):
                        raise RuntimeError('SIM_NOT_READY')
                    if not self._read('hotspot.json').get('ssid'):
                        raise RuntimeError('CELLULAR_NOT_CONFIGURED')
                    # Data and AP are independent; the legacy trial/Keep route is unchanged.
                    self._stop_automation()
                    save_intent(self.directory, airplane=False, data_allowed=True)
                    try:
                        if self.network.active('wlan0') == SETUP_UUID:self._start_shared_ap(control)
                        self.network.autoconnect(CELL_UUID, False)
                        try:self.network.up(CELL_UUID)
                        except RuntimeError:raise RuntimeError('DATA_CONNECT_FAILED') from None
                        if not self.network.cellular_interface(control):
                            raise RuntimeError('QUICK_OPERATION_FAILED')
                        if self.network.active('wlan0') == AP_UUID:self.ap_forwarding(True)
                        self.tethering.update_uplinks()
                    except Exception:
                        save_intent(self.directory, airplane=False, data_allowed=False)
                        if self.network.active('wlan0') == AP_UUID:self.ap_forwarding(False)
                        if self.network.active(control) == CELL_UUID:
                            self.network.down(CELL_UUID)
                        raise
                elif action == 'local_ap_off':
                    active = self.network.active('wlan0')
                    if active not in (SETUP_UUID, AP_UUID):
                        raise RuntimeError('LOCAL_AP_UNAVAILABLE')
                    self._stop_automation()
                    config = self._read('setup-ap.json')
                    config['enabled'] = False
                    self.setup.write('setup-ap.json', config)
                    self.network.nm('device', 'set', 'wlan0', 'autoconnect', 'no')
                    if active == SETUP_UUID:
                        self.setup.network.local_services(False)
                        self.network.down(SETUP_UUID)
                        self.ap_forwarding(True)
                    else:
                        self.network.autoconnect(AP_UUID, False)
                        self.network.down(AP_UUID)
                        self.ap_forwarding(True)
                elif action == 'usb_tether_on':
                    self.tethering.request(True, values['operation'])
                elif action == 'usb_tether_off':
                    self.tethering.request(False, values['operation'])
                elif action.startswith('wifi_'):self.wifi.call(action, values)
                result = self.status()
                self.journal.finish(receipt, 'COMPLETED')
                return result
            except Exception as error:
                category = str(error) if str(error) in ERRORS else 'QUICK_OPERATION_FAILED'
                self.journal.finish(receipt, 'UNKNOWN', category)
                raise RuntimeError(category) from None

    def receipt(self, identity):
        if str(uuid.UUID(identity)) != identity:
            raise ValueError('INPUT_INVALID')
        try:
            value = json.loads((self.directory / 'quick-operations' / (identity + '.json')).read_text())
        except (OSError, ValueError):
            return {'state': 'NOT_FOUND'}
        result = {key: value[key] for key in ('kind', 'state', 'failure') if key in value}
        if result.get('kind') in ('usb_tether_on', 'usb_tether_off') and result.get('state') == 'COMPLETED':
            result['usb_tethering'] = self.tethering.status()
        return result

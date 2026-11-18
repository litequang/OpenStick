"""Private AP association inventory and opt-in Internet filtering by MAC.

Does not claim association ACL support. No OUI/cloud lookup or client history.
"""
from contextlib import nullcontext
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import uuid

from .hotspot import Hotspot, Network, network_lock, AP_UUID
from .modem_device import OperationJournal

TABLE = 'openstick_ap_clients'
MARKER = 'openstick-ap-clients-v1:'
ERRORS = {'AP_CLIENTS_UNAVAILABLE', 'AP_CLIENTS_INVALID', 'AP_CLIENTS_FIREWALL_FAILED',
          'AP_CLIENTS_SAVE_FAILED', 'AP_CLIENTS_ROLLBACK_FAILED', 'AP_CLIENTS_LIST_FULL',
          'NETWORK_BUSY', 'ALREADY_ATTEMPTED'}
ERRORS.add('AP_CLIENTS_OFFLOAD_UNSUPPORTED')


def mac(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}', value):
        raise ValueError('INPUT_INVALID')
    value = value.lower()
    if value == '00:00:00:00:00:00' or int(value[:2], 16) & 1:raise ValueError('INPUT_INVALID')
    return value


def validate(value):
    if (not isinstance(value, dict) or set(value) != {'action', 'mac', 'operation', 'confirm'}
            or value['action'] not in ('block', 'unblock') or value['confirm'] is not True
            or not isinstance(value['operation'], str)):
        raise ValueError('INPUT_INVALID')
    if str(uuid.UUID(value['operation'])) != value['operation']:raise ValueError('INPUT_INVALID')
    mac(value['mac'])
    return value['action']


def stations(text):
    """Only an actual driver station row establishes presence; never a DHCP lease."""
    if len(text) > 131072:raise RuntimeError('AP_CLIENTS_UNAVAILABLE')
    result = []; current = None
    for line in text.splitlines():
        if line.startswith('Station '):
            found = re.fullmatch(r'Station ([0-9a-fA-F:]{17}) \(on wlan0\)', line.strip())
            if not found or len(result) >= 128:raise RuntimeError('AP_CLIENTS_UNAVAILABLE')
            try:address = mac(found[1])
            except ValueError:raise RuntimeError('AP_CLIENTS_UNAVAILABLE') from None
            if any(r['mac'] == address for r in result):raise RuntimeError('AP_CLIENTS_UNAVAILABLE')
            current = {'mac': address, 'ip': None, 'name': None, 'signal_dbm': None,
                       'rx_bytes': None, 'tx_bytes': None, 'rx_mbps': None, 'tx_mbps': None,
                       'connected_seconds': None}
            result.append(current)
        elif current is not None:
            for label, key in [('rx bytes', 'rx_bytes'), ('tx bytes', 'tx_bytes'),
                               ('connected time', 'connected_seconds')]:
                found = re.fullmatch(r'\s*' + label + r':\s*([0-9]{1,20})(?:\s+seconds)?\s*', line)
                if found and int(found[1]) < 2**64:current[key] = int(found[1])
            found = re.match(r'\s*signal:\s*(-?[0-9]{1,3})(?:\s|\[|$)', line)
            if found and -127 <= int(found[1]) <= 0:current['signal_dbm'] = int(found[1])
            for direction in ('rx', 'tx'):
                found = re.match(r'\s*' + direction + r' bitrate:\s*([0-9]+(?:\.[0-9]+)?) MBit/s(?:\s|$)', line)
                if found and 0 <= float(found[1]) <= 10000:current[direction + '_mbps'] = float(found[1])
        elif line.strip():raise RuntimeError('AP_CLIENTS_UNAVAILABLE')
    return result


def local_ip(value):
    try:
        address = ipaddress.IPv4Address(value)
        if address in ipaddress.IPv4Network('192.168.8.0/24') and int(str(address).split('.')[-1]) in range(2, 255):return str(address)
    except (ValueError, TypeError):pass
    return None


def correlate(rows, leases, neighbors, now):
    known = {row['mac']: row for row in rows}
    for text in leases:
        for line in text.splitlines()[:512]:
            parts = line.split()
            if len(parts) != 5:continue
            try:address = mac(parts[1]); expiry = int(parts[0])
            except (ValueError, TypeError):continue
            ip = local_ip(parts[2])
            if address not in known or not ip or expiry < 0 or expiry != 0 and expiry <= now:continue
            known[address]['ip'] = ip
            name = parts[3]
            if name != '*' and len(name) <= 128 and not any(ord(c) < 32 or ord(c) == 127 for c in name):
                known[address]['name'] = name
    if isinstance(neighbors, list):
        for item in neighbors[:512]:
            if not isinstance(item, dict) or item.get('dev', 'wlan0') != 'wlan0':continue
            try:address = mac(item.get('lladdr'))
            except ValueError:continue
            ip = local_ip(item.get('dst'))
            state = item.get('state', [])
            if address in known and ip and isinstance(state, list) and set(state) & {'REACHABLE','STALE','DELAY','PROBE','PERMANENT'}:
                known[address]['ip'] = ip
    return rows


class ApClients:
    def __init__(self, directory='/var/lib/openstick', *, network=None, lock_factory=network_lock,
                 journal=None, leases=None, clock=time.time, available=shutil.which):
        self.directory = Path(directory); self.path = self.directory / 'ap-clients.json'
        self.network = network or Network(); self.lock_factory = lock_factory
        self.journal = journal or OperationJournal(self.directory / 'ap-client-operations')
        self.leases = leases if leases is not None else [Path('/run/openstick/setup.leases'), Path('/var/lib/NetworkManager/dnsmasq-wlan0.leases')]
        self.clock, self.available = clock, available

    def config(self):
        if self.path.is_symlink():raise RuntimeError('AP_CLIENTS_INVALID')
        if not self.path.exists():return None
        try:
            if self.path.is_symlink() or self.path.stat().st_size > 8192:raise ValueError()
            value = json.loads(self.path.read_text())
            if (not isinstance(value, dict) or set(value) != {'version','blocked'} or type(value['version']) is not int
                    or value['version'] != 1 or not isinstance(value['blocked'], list) or len(value['blocked']) > 128):raise ValueError()
            blocked = sorted(mac(v) for v in value['blocked'])
            if len(set(blocked)) != len(blocked):raise ValueError()
            return blocked
        except (OSError, ValueError, TypeError):raise RuntimeError('AP_CLIENTS_INVALID') from None

    def active(self):
        from .setup_ap import SETUP_UUID
        return self.network.active('wlan0') in (AP_UUID, SETUP_UUID)

    def _run(self, args, *, input=None):
        try:
            result = self.network.run(args, input=input, capture_output=True, text=True, timeout=8, shell=False)
            if result.returncode or len(result.stdout) > 131072:raise ValueError()
            return result.stdout
        except (OSError, ValueError, subprocess.SubprocessError):raise RuntimeError('AP_CLIENTS_UNAVAILABLE') from None

    def _table(self):
        try:
            result = self.network.run(['nft','list','table','inet',TABLE],capture_output=True,text=True,timeout=8,shell=False)
            if result.returncode:
                if 'No such file or directory' in result.stderr:return None
                raise ValueError()
            if len(result.stdout) > 131072 or MARKER not in result.stdout:raise ValueError()
            return result.stdout
        except (OSError, ValueError, subprocess.SubprocessError):raise RuntimeError('AP_CLIENTS_FIREWALL_FAILED') from None

    @staticmethod
    def fingerprint(blocked, ipv4=(), ipv6=()):
        return MARKER + hashlib.sha256(json.dumps([blocked,list(ipv4),list(ipv6)],separators=(',',':')).encode()).hexdigest()

    def targets(self, blocked):
        try:rows=json.loads(self._run(['ip','-j','neigh','show','dev','wlan0']))
        except (RuntimeError,ValueError):raise RuntimeError('AP_CLIENTS_FIREWALL_FAILED') from None
        if not isinstance(rows,list):raise RuntimeError('AP_CLIENTS_FIREWALL_FAILED')
        targets={4:set(),6:set()}
        for row in rows[:512]:
            if not isinstance(row,dict) or row.get('dev','wlan0')!='wlan0':continue
            try:
                if mac(row.get('lladdr')) not in blocked:continue
                if not set(row.get('state',[])) & {'REACHABLE','STALE','DELAY','PROBE','PERMANENT'}:continue
                address=ipaddress.ip_address(row.get('dst'))
                if address.is_multicast or address.is_unspecified or address.is_loopback:continue
                if address.version==4 and not local_ip(str(address)):continue
                targets[address.version].add(str(address))
            except (ValueError,TypeError):continue
        return sorted(targets[4]),sorted(targets[6])

    @staticmethod
    def rules(blocked, exists=False, ipv4=(), ipv6=()):
        # MAC is authoritative for client-originated routed traffic. Reply IP
        # guards follow the neighbor cache; never claim these are association ACLs.
        values = ', '.join(mac(v) for v in blocked)
        v4=', '.join(str(ipaddress.IPv4Address(v)) for v in ipv4)
        v6=', '.join(str(ipaddress.IPv6Address(v)) for v in ipv6)
        return (('delete table inet ' + TABLE + '\n' if exists else '') +
            'table inet ' + TABLE + ' {\n comment "' + ApClients.fingerprint(blocked,ipv4,ipv6) + '"\n'
            ' set blocked { type ether_addr;'+(' elements = { '+values+' };' if values else '')+' }\n'
            ' set blocked4 { type ipv4_addr;'+(' elements = { '+v4+' };' if v4 else '')+' }\n'
            ' set blocked6 { type ipv6_addr;'+(' elements = { '+v6+' };' if v6 else '')+' }\n'
            ' chain forward { type filter hook forward priority -15; policy accept;\n'
            '  iifname "wlan0" ether saddr @blocked counter drop\n'
            '  oifname "wlan0" ip daddr @blocked4 counter drop\n'
            '  oifname "wlan0" ip6 daddr @blocked6 counter drop\n }\n}\n')

    def apply(self, blocked):
        previous = self._table()
        if not blocked:
            if previous is not None:
                try:self._run(['nft','delete','table','inet',TABLE])
                except RuntimeError:raise RuntimeError('AP_CLIENTS_FIREWALL_FAILED') from None
            return
        if re.search(r'\bflowtable\b|\bflow\s+(?:add|offload)\b',self._run(['nft','list','ruleset'])):
            raise RuntimeError('AP_CLIENTS_OFFLOAD_UNSUPPORTED')
        ipv4,ipv6=self.targets(blocked)
        expected=self.fingerprint(blocked,ipv4,ipv6)
        if previous and expected in previous:return
        rules = self.rules(blocked, previous is not None,ipv4,ipv6)
        try:
            self._run(['nft','--check','-f','-'],input=rules)
            self._run(['nft','-f','-'],input=rules)
            if expected not in (self._table() or ''):raise ValueError()
        except (RuntimeError, ValueError):raise RuntimeError('AP_CLIENTS_FIREWALL_FAILED') from None

    def prepare_ap(self):
        value = self.config()
        if value is not None:self.apply(value)

    def suspend(self):
        if self.path.exists():self.apply([])

    def tick(self):
        if not self.path.exists():return
        with self.lock_factory():
            self.apply((self.config() or []) if self.active() else [])

    def status(self):
        with self.lock_factory():return self._status()

    def _status(self):
        blocked = self.config() or []; active = self.active()
        rows = []; error = None; inventory = active and bool(self.available('iw'))
        if inventory:
            try:
                rows = stations(self._run(['iw','dev','wlan0','station','dump']))
                leases = []
                for path in self.leases:
                    try:
                        if path.is_file() and not path.is_symlink() and path.stat().st_size <= 65536:leases.append(path.read_text())
                    except (OSError, UnicodeError):pass
                try:neighbors = json.loads(self._run(['ip','-j','neigh','show','dev','wlan0']))
                except (RuntimeError, ValueError):neighbors = []
                correlate(rows, leases, neighbors, self.clock())
            except RuntimeError:inventory = False;error = 'AP_CLIENTS_UNAVAILABLE'
        if active and not inventory:error = 'AP_CLIENTS_UNAVAILABLE'
        applied = not blocked
        if blocked and active:
            try:applied = self.fingerprint(blocked,*self.targets(blocked)) in (self._table() or '')
            except RuntimeError:applied = False;error = 'AP_CLIENTS_FIREWALL_FAILED'
        elif active:
            try:
                if self._table() is not None:applied=False;error='AP_CLIENTS_FIREWALL_FAILED'
            except RuntimeError:applied=False;error='AP_CLIENTS_FIREWALL_FAILED'
        for row in rows:row['internet_blocked'] = row['mac'] in blocked
        return {'ap_active':active,'inventory_available':inventory,'clients':rows,
                'count':len(rows) if inventory else None,'blocked':blocked,
                'filter_applied':applied if active else False,'error':error,
                'association_block_supported':False,'hardware_packet_test':'NOT_TESTED'}

    def call(self, action, **values):
        validate({'action':action,**values})
        with self.lock_factory():
            for name in ('setup-pending.json','hotspot-pending.json'):
                if (self.directory/name).exists():raise RuntimeError('NETWORK_BUSY')
            original = self.config()
            receipt = self.journal.begin(values['operation'],action)
            blocked = set(original or []);address = mac(values['mac'])
            if action == 'block':blocked.add(address)
            else:blocked.discard(address)
            blocked = sorted(blocked)
            wrote = False
            try:
                if len(blocked)>128:raise RuntimeError('AP_CLIENTS_LIST_FULL')
                self.directory.mkdir(mode=0o700,parents=True,exist_ok=True)
                wrote=True  # A failed fsync can follow a completed replace.
                try:Hotspot.atomic(self.path,json.dumps({'version':1,'blocked':blocked}))
                except Exception:raise RuntimeError('AP_CLIENTS_SAVE_FAILED') from None
                self.apply(blocked if self.active() else [])
                self.journal.finish(receipt,'COMPLETED')
            except Exception as e:
                failure = str(e) if str(e) in ERRORS else 'AP_CLIENTS_FIREWALL_FAILED'
                if wrote:
                    try:
                        if original is None:
                            self.path.unlink(missing_ok=True)
                            if os.name != 'nt':
                                fd=os.open(self.directory,os.O_RDONLY)
                                try:os.fsync(fd)
                                finally:os.close(fd)
                        else:Hotspot.atomic(self.path,json.dumps({'version':1,'blocked':original}))
                        self.apply((original or []) if self.active() else [])
                    except Exception:failure='AP_CLIENTS_ROLLBACK_FAILED'
                self.journal.finish(receipt,'UNKNOWN',failure)
                raise RuntimeError(failure) from None
            # Inventory failure after a successful filter write cannot undo it or
            # encourage duplicate mutation. The GET refresh reads inventory later.
            return {'saved':True,'blocked':blocked,'filter_applied':self.active(),
                    'association_block_supported':False}


def for_backend(backend):
    return ApClients(backend.directory,network=backend.network,lock_factory=nullcontext)


def main():
    backend = ApClients()
    while True:
        try:backend.tick()
        except Exception:pass  # No client MAC, hostname, IP or subprocess output in logs.
        time.sleep(5)


if __name__ == '__main__':main()

"""Read-only Linux telemetry. No SIM identities, message text or firmware reads."""
import json
import os
import shutil
import time
import sys
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path


def modem_snapshot():
    if sys.platform != 'linux':return None
    from .modem_device import ModemManager
    try:
        status = ModemManager().call('status')
        return {key: value for key, value in status.items()
                if key not in ('ussd_prompt', 'ussd_notification')}
    except Exception:
        return None


def system_snapshot(root=Path('/'), *, disk_usage=shutil.disk_usage, now=time.time):
    root = Path(root)
    def read(name):
        try:
            return (root / name.lstrip('/')).read_text().strip()
        except (OSError, UnicodeError):
            return ''

    def numbers(name):
        try:
            return [float(n) for n in read(name).split()]
        except ValueError:
            return []

    memory = {}
    for line in read('/proc/meminfo').splitlines():
        parts = line.replace(':', '').split()
        if len(parts) >= 2 and parts[1].isdigit():
            memory[parts[0]] = int(parts[1]) * 1024
    total, available = memory.get('MemTotal'), memory.get('MemAvailable')
    ram = {'total': total, 'used': max(0, total - available) if total is not None and available is not None else None}
    try:
        disk = disk_usage(str(root))
        storage = {'total': disk.total, 'used': disk.used, 'free': disk.free}
    except OSError:
        storage = {'total': None, 'used': None, 'free': None}
    uptime = numbers('/proc/uptime')
    uptime = uptime[0] if uptime else None
    load = numbers('/proc/loadavg')[:3]  # The last fields contain process IDs, not floats.
    if not load:
        try:load = [float(n) for n in read('/proc/loadavg').split()[:3]]
        except ValueError:load = []
    temperatures = []
    for sensor in (root / 'sys/class/thermal').glob('thermal_zone*/temp'):
        try:
            value = float(sensor.read_text()) / 1000
            if -20 <= value <= 150:temperatures.append(value)
        except (OSError, ValueError):
            pass
    os_name = 'Linux'
    for line in read('/etc/os-release').splitlines():
        if line.startswith('PRETTY_NAME='):
            os_name = line.split('=', 1)[1].strip('"')[:120]
    swap = {'total': memory.get('SwapTotal'), 'used': None, 'zram_total': 0,
            'zram_used': 0, 'other_total': 0, 'other_used': 0}
    if memory.get('SwapTotal') is not None and memory.get('SwapFree') is not None:
        swap['used'] = max(0, memory['SwapTotal'] - memory['SwapFree'])
    swap_lines = read('/proc/swaps').splitlines()
    if not swap_lines:
        for key in ('zram_total', 'zram_used', 'other_total', 'other_used'):swap[key] = None
    for line in swap_lines[1:]:
        parts = line.split()
        if len(parts) >= 4 and parts[2].isdigit() and parts[3].isdigit():
            prefix = 'zram' if parts[0].startswith('/dev/zram') else 'other'
            swap[prefix + '_total'] += int(parts[2]) * 1024
            swap[prefix + '_used'] += int(parts[3]) * 1024
    life = read('/sys/block/mmcblk0/device/life_time').split()
    try:life = [int(n, 0) for n in life]
    except ValueError:life = []
    ranges = []
    for value in life:
        if 1 <= value <= 10:ranges.append({'min': (value - 1) * 10, 'max': value * 10})
        elif value == 11:ranges.append({'min': 100, 'max': None})
    eol = read('/sys/block/mmcblk0/device/pre_eol_info')
    try:eol = {1: 'normal', 2: 'warning', 3: 'urgent'}.get(int(eol, 0), 'unknown')
    except ValueError:eol = 'unknown'
    stat = read('/sys/block/mmcblk0/stat').split()
    written = int(stat[6]) * 512 if len(stat) >= 7 and stat[6].isdigit() else None
    write_rate = written / uptime * 86400 if written is not None and uptime and uptime > 0 else None
    sms = {'submitted_today': 0, 'submitted_month': 0, 'unknown_today': 0,
           'unit_vnd': None, 'estimated_today_vnd': None, 'scope': 'manager_journal_only'}
    local_zone = timezone(timedelta(hours=7))
    date = datetime.fromtimestamp(now(), local_zone)
    for file in (root / 'var/lib/openstick/modem-operations').glob('*.json'):
        try:
            entry = json.loads(file.read_text())
            if entry.get('kind') != 'send':continue
            created = datetime.fromtimestamp(float(entry['created_at']), local_zone)
            if entry.get('state') == 'COMPLETED':
                if created.date() == date.date():sms['submitted_today'] += 1
                if (created.year, created.month) == (date.year, date.month):sms['submitted_month'] += 1
            elif created.date() == date.date():sms['unknown_today'] += 1
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            continue
    try:
        tariff = json.loads(read('/var/lib/openstick/sms-tariff.json'))['unit_vnd']
        if type(tariff) is int and 0 <= tariff <= 100000:
            sms['unit_vnd'] = tariff
            sms['estimated_today_vnd'] = tariff * sms['submitted_today']
    except (ValueError, KeyError, TypeError):
        pass
    return {'ram': ram, 'storage': storage, 'uptime_s': uptime, 'load': load,
            'temperature_c': max(temperatures) if temperatures else None,
            'temperature_source': 'highest_reported_sensor', 'os': os_name,
            'kernel': read('/proc/sys/kernel/osrelease')[:100], 'swap': swap,
            'emmc': {'life_used_ranges': ranges, 'pre_eol': eol,
                     'written_since_boot': written, 'estimated_daily_write': write_rate},
            'sms': sms, 'sampled_at': now()}


def save_tariff(unit_vnd, directory=Path('/var/lib/openstick')):
    if type(unit_vnd) is not int or not 0 <= unit_vnd <= 100000:
        raise ValueError('INPUT_INVALID')
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = directory / 'sms-tariff.tmp'
    with temporary.open('w') as output:
        os.chmod(temporary, 0o600)
        json.dump({'unit_vnd': unit_vnd}, output)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, directory / 'sms-tariff.json')
    return {'saved': True, 'unit_vnd': unit_vnd}


def service_snapshot(run=subprocess.run):
    result = {}
    for name in ('openstick-web', 'openstick-wifi', 'cloudflared', 'modemmanager', 'rmtfs', 'chronyd'):
        try:
            result[name] = run(['rc-service', name, 'status'], capture_output=True, timeout=4).returncode == 0
        except (OSError, subprocess.SubprocessError):
            result[name] = None
    return result

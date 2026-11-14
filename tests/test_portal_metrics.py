import json
import subprocess
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from uz801_manager.portal_metrics import save_tariff, service_snapshot, system_snapshot


@pytest.fixture
def linux_tree(tmp_path):
    def write(path, content):
        target = tmp_path / path.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    write('/proc/meminfo', 'MemTotal: 400000 kB\nMemAvailable: 250000 kB\nSwapTotal: 500000 kB\nSwapFree: 450000 kB\n')
    write('/proc/uptime', '86400.00 123456.00')
    write('/proc/loadavg', '0.08 0.29 0.47 1/80 1234')
    write('/proc/swaps', 'Filename Type Size Used Priority\n/dev/zram0 partition 400000 40000 100\n/swapfile file 100000 10000 -2\n')
    write('/proc/sys/kernel/osrelease', 'fixture-kernel')
    write('/etc/os-release', 'PRETTY_NAME="Fixture Linux"\n')
    write('/sys/class/thermal/thermal_zone0/temp', '41000')
    write('/sys/class/thermal/thermal_zone1/temp', 'not supported')
    write('/sys/block/mmcblk0/device/life_time', '0x01 0x02')
    write('/sys/block/mmcblk0/device/pre_eol_info', '0x01')
    write('/sys/block/mmcblk0/stat', '0 0 0 0 0 0 2048 0 0 0 0')
    return tmp_path, write


def snapshot(root, now=1794618000):
    return system_snapshot(root, disk_usage=lambda _: SimpleNamespace(total=1000, used=600, free=400), now=lambda: now)


def test_real_fields_have_correct_units_and_no_fabricated_lifetime(linux_tree):
    root, _ = linux_tree
    result = snapshot(root)
    assert result['ram'] == {'total': 409600000, 'used': 153600000}
    assert result['load'] == [0.08, 0.29, 0.47]
    assert result['temperature_c'] == 41
    assert result['os'] == 'Fixture Linux' and result['kernel'] == 'fixture-kernel'
    assert result['swap']['used'] == 50000 * 1024
    assert result['swap']['zram_used'] == 40000 * 1024
    assert result['swap']['other_total'] == 100000 * 1024
    assert result['emmc']['life_used_ranges'] == [{'min': 0, 'max': 10}, {'min': 10, 'max': 20}]
    assert result['emmc']['written_since_boot'] == 1048576
    assert result['emmc']['estimated_daily_write'] == 1048576


def test_unsupported_or_missing_telemetry_is_unknown_not_healthy_zero(tmp_path):
    result = system_snapshot(tmp_path, disk_usage=lambda _: (_ for _ in ()).throw(OSError()))
    assert result['ram']['used'] is None and result['storage']['used'] is None
    assert result['temperature_c'] is None and result['emmc']['life_used_ranges'] == []
    assert result['emmc']['pre_eol'] == 'unknown'
    assert result['emmc']['estimated_daily_write'] is None
    assert result['swap']['used'] is None
    assert result['swap']['zram_total'] is None and result['swap']['other_used'] is None
    assert result['sms']['estimated_today_vnd'] is None


def test_sms_counts_are_submission_only_with_vietnam_day_boundary(linux_tree):
    root, write = linux_tree
    # UTC 17:30 is the following day in Vietnam.
    now = datetime(2026, 11, 14, 18, tzinfo=timezone.utc).timestamp()
    entries = [('a', 'COMPLETED', datetime(2026, 11, 14, 17, 30, tzinfo=timezone.utc).timestamp()),
               ('b', 'COMPLETED', datetime(2026, 11, 14, 15, tzinfo=timezone.utc).timestamp()),
               ('c', 'UNKNOWN', now)]
    for name, state, stamp in entries:
        write('/var/lib/openstick/modem-operations/' + name + '.json', json.dumps({'kind': 'send', 'state': state, 'created_at': stamp}))
    write('/var/lib/openstick/modem-operations/ussd.json', json.dumps({'kind': 'ussd_start', 'state': 'COMPLETED', 'created_at': now}))
    write('/var/lib/openstick/modem-operations/broken.json', 'partial')
    write('/var/lib/openstick/sms-tariff.json', '{"unit_vnd":350}')
    result = snapshot(root, now)['sms']
    assert (result['submitted_today'], result['submitted_month'], result['unknown_today']) == (1, 2, 1)
    assert result['estimated_today_vnd'] == 350 and result['scope'] == 'manager_journal_only'


@pytest.mark.parametrize('life,eol,expected', [('0x00 0x00', '0x00', []),
    ('0x0b', '0x03', [{'min': 100, 'max': None}]), ('bad', 'bad', [])])
def test_emmc_unknown_and_exceeded_lifetime_are_not_normalized_to_healthy(linux_tree, life, eol, expected):
    root, write = linux_tree
    write('/sys/block/mmcblk0/device/life_time', life)
    write('/sys/block/mmcblk0/device/pre_eol_info', eol)
    result = snapshot(root)['emmc']
    assert result['life_used_ranges'] == expected
    assert result['pre_eol'] == ('urgent' if eol == '0x03' else 'unknown')


def test_tariff_is_local_atomic_metadata_and_rejects_wrong_types(tmp_path):
    assert save_tariff(0, tmp_path)['saved']
    assert json.loads((tmp_path / 'sms-tariff.json').read_text()) == {'unit_vnd': 0}
    for value in (True, '350', -1, 100001):
        with pytest.raises(ValueError):save_tariff(value, tmp_path)


def test_service_inspection_only_uses_fixed_read_only_commands():
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        assert kwargs['timeout'] == 4 and args[0] == 'rc-service' and args[-1] == 'status'
        return subprocess.CompletedProcess(args, 0)
    assert all(service_snapshot(run).values()) and len(calls) == 6

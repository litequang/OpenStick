import io
import subprocess
import sys
import threading

import pytest

from uz801_manager.adb import ADB, READS, TRAILER
from uz801_manager.demo import DemoADB
from uz801_manager.errors import SafetyError


def make_stream(tmp_path, payload, *, code=0, delay=0, timeout=1):
    script = tmp_path / "mock_adb.py"
    script.write_text("import sys,time\n" + f"sys.stdout.buffer.write({payload!r})\nsys.stdout.buffer.flush()\ntime.sleep({delay})\nsys.exit({code})\n")
    def popen(args, **kwargs):
        assert args[1:4] == ["-t", "1", "exec-out"]
        assert "of=" not in args[4]
        assert kwargs["shell"] is False
        return subprocess.Popen([sys.executable, str(script)], **kwargs)
    return ADB("mock-adb", popen=popen, idle_timeout=timeout)


def test_binary_transfer_preserves_all_bytes(tmp_path):
    payload = bytes(range(256)) * 4096
    adb = make_stream(tmp_path, payload + TRAILER)
    output = io.BytesIO()
    adb._stream("1", "cat /dev/block/mmcblk0", len(payload), output, threading.Event(), lambda _: None)
    assert output.getvalue() == payload


@pytest.mark.parametrize("payload,expected,code,error", [
    (b"abc" + TRAILER, 100, 0, "SIZE_MISMATCH"),
    (b"abc", 3, 0, "REMOTE_READ_FAILED"),
    (b"abc\nUZ801_RC=001\n", 3, 0, "REMOTE_READ_FAILED"),
    (b"abc" + TRAILER, 3, 1, "STREAM_FAILED"),
    (b"abc" + TRAILER + b"extra", 3, 0, "SIZE_MISMATCH"),
])
def test_binary_errors(tmp_path, payload, expected, code, error):
    adb = make_stream(tmp_path, payload, code=code)
    with pytest.raises(SafetyError, match=error):
        adb._stream("1", "cat /dev/block/mmcblk0", expected, io.BytesIO(), threading.Event(), lambda _: None)


def test_stalled_process_is_killed(tmp_path):
    adb = make_stream(tmp_path, b"", delay=5, timeout=.2)
    with pytest.raises(SafetyError, match="STREAM_TIMEOUT"):
        adb._stream("1", "cat /dev/block/mmcblk0", 100, io.BytesIO(), threading.Event(), lambda _: None)


def test_cancel_stalled_process(tmp_path):
    adb = make_stream(tmp_path, b"", delay=5)
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(SafetyError, match="CANCELLED"):
        adb._stream("1", "cat /dev/block/mmcblk0", 100, io.BytesIO(), cancel, lambda _: None)


class InspectorADB(ADB):
    def __init__(self, root=True):
        super().__init__("fake")
        self.demo = DemoADB(delay=0)
        self.root = root
        self.replacement = False

    def connection(self):
        return ("synthetic-serial", "2" if self.replacement else "1")

    def _read(self, transport, key):
        values = {"model": "UZ801", "product": "msm8916_32_512", "board": "msm8916", "platform": "msm8916",
                  "android": "4.4.4", "kernel": "Linux 3.10.28", "root": "uid=0(root)" if self.root else "uid=2000(shell)",
                  "ram": "MemTotal: 397824 kB", "cpu": "Hardware : Qualcomm MSM8916\nSerial: private",
                  "sectors": "4096", "logical_sector": "512", "emmc_name": "XINYH", "cid": "a" * 32,
                  "boot_id": "00000000-0000-4000-8000-000000000000",
                  "layout": "\n".join(f"mmcblk0p{p.number}\n{p.first_lba}\n{p.size // 512}" for p in self.demo.snapshot.partitions)}
        assert set(values) == set(READS)
        return values[key]

    def read_range(self, snapshot, offset, length):
        return self.demo.image[offset:offset + length]


def test_actual_inspector_parser_root_and_privacy():
    snapshot = InspectorADB().inspect()
    assert snapshot.backup_error is None
    assert len(snapshot.partitions) == 27
    assert snapshot.public()["root"] is True
    assert "private" not in str(snapshot.public())
    assert "aaaaaaaa" not in repr(snapshot)
    assert snapshot.public()["board_verified"] is False


def test_actual_inspector_no_root():
    snapshot = InspectorADB(root=False).inspect()
    assert snapshot.backup_error == "NO_ROOT"
    assert snapshot.public()["backup_allowed"] is False


def test_replaced_transport_rejected():
    adb = InspectorADB()
    snapshot = adb.inspect()
    adb.replacement = True
    with pytest.raises(SafetyError, match="DEVICE_CHANGED"):
        adb.assert_same(snapshot)

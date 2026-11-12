import io
import socket
import struct
import threading
import json
from pathlib import Path

import pytest

from uz801_manager.adb import ADB
from uz801_manager.adb_sync import SyncReader
from uz801_manager.backup import BackupManager
from uz801_manager.demo import synthetic_disk
from uz801_manager.errors import SafetyError
from uz801_manager.gpt import read_primary_gpt, read_gpt
from test_adb_stream import InspectorADB


def packet(kind, data=b""):
    return kind + struct.pack("<I", len(data)) + data


class Socket:
    def __init__(self, data):
        self.data, self.sent, self.closed = bytearray(data), [], False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def settimeout(self, timeout):
        pass

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        size = min(size, 7)  # split smart-socket headers and binary payloads
        result = bytes(self.data[:size])
        del self.data[:size]
        return result


def reader(data):
    sock = Socket(b"OKAYOKAY" + data)
    def connect(address, timeout):
        assert address == ("127.0.0.1", 5037)
        return sock
    return SyncReader("42", connect=connect), sock


def receive(sync, expected, cancel=None):
    out = io.BytesIO()
    sync.receive("/dev/block/mmcblk0", out, cancel or threading.Event(), lambda _: None,
                 expected=expected, limit=expected)
    return out.getvalue()


def test_sync_binary_all_values_and_fragmented_headers():
    payload = bytes(range(256)) * 257
    sync, sock = reader(packet(b"DATA", payload[:65536]) + packet(b"DATA", payload[65536:]) + packet(b"DONE"))
    assert receive(sync, len(payload)) == payload
    assert sock.sent == [b"0014host:transport-id:42", b"0005sync:", packet(b"RECV", b"/dev/block/mmcblk0")]
    assert sock.closed


@pytest.mark.parametrize("data,expected,error", [
    (packet(b"DATA", b"abc"), 3, "STREAM_FAILED"),  # exact data without DONE is incomplete
    (packet(b"DATA", b"ab") + packet(b"DONE"), 3, "SIZE_MISMATCH"),
    (packet(b"DATA", b"abcd") + packet(b"DONE"), 3, "SIZE_MISMATCH"),
    (packet(b"DATA", b"abc") + packet(b"DONE", b"x"), 3, "SIZE_MISMATCH"),
    (packet(b"FAIL", b"private serial and path"), 3, "REMOTE_READ_FAILED"),
    (b"DATA" + struct.pack("<I", 65537), 3, "SYNC_PROTOCOL"),
    (packet(b"DATA"), 3, "SYNC_PROTOCOL"),
    (packet(b"SEND"), 3, "SYNC_PROTOCOL"),
])
def test_bad_streams_fail_closed(data, expected, error):
    sync, sock = reader(data)
    with pytest.raises(SafetyError, match="^" + error + "$"):
        receive(sync, expected)
    assert sock.closed


def test_prefix_close_is_separate_from_complete_transfer():
    payload = bytes(range(256)) * 256
    sync, sock = reader(packet(b"DATA", payload))
    assert sync.primary_prefix() == payload
    assert sock.closed
    sync, _ = reader(packet(b"DATA", payload))
    with pytest.raises(SafetyError, match="STREAM_FAILED"):
        receive(sync, len(payload))


def test_cancel_closes_socket():
    sync, sock = reader(b"")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(SafetyError, match="CANCELLED"):
        receive(sync, 3, cancel)
    assert sock.closed


def test_idle_timeout_closes_socket():
    sync, sock = reader(b"")
    sync.timeout = .01
    def stalled(size):
        raise socket.timeout()
    sock.recv = stalled
    with pytest.raises(SafetyError, match="STREAM_TIMEOUT"):
        receive(sync, 3)
    assert sock.closed


@pytest.mark.parametrize("path", ["/data/private", "/dev/block/mmcblk0;reboot", "/dev/block/mmcblk0p0", "/sys/class/block/../private"])
def test_remote_path_allowlist(path):
    sync, sock = reader(b"")
    with pytest.raises(SafetyError, match="INPUT_INVALID"):
        sync.receive(path, io.BytesIO(), threading.Event(), lambda _: None, expected=3, limit=3)
    assert not sock.sent


def test_metadata_limit_and_private_errors():
    sync, _ = reader(packet(b"DATA", b"a" * 65536) + packet(b"DATA", b"x"))
    with pytest.raises(SafetyError, match="SIZE_MISMATCH"):
        sync.read_text("/system/build.prop")


def dent(name):
    return b"DENT" + struct.pack("<4I", 0, 0, 0, len(name)) + name


def test_list_only_valid_partition_names():
    sync, _ = reader(dent(b".") + dent(b"mmcblk0") + dent(b"mmcblk0p27") + dent(b"mmcblk0p0") + b"DONE" + bytes(16))
    assert sync.partitions() == ["mmcblk0p27"]


def test_list_rejects_duplicate_names():
    sync, _ = reader(dent(b"mmcblk0p1") * 2 + b"DONE" + bytes(16))
    with pytest.raises(SafetyError, match="LAYOUT_MISMATCH"):
        sync.partitions()


class LegacyADB(InspectorADB):
    def supports_exec_out(self, transport):
        return False

    def read_range(self, *args):
        pytest.fail("Legacy device must not request random access or use shell")


def test_legacy_primary_inspection_and_critical_gate(tmp_path):
    adb = LegacyADB()
    class FakeSync:
        def __init__(self, transport):
            assert transport == "1"
        def primary_prefix(self):
            return adb.demo.image[:65536]
    adb.sync_factory = FakeSync
    snapshot = adb.inspect()
    assert snapshot.backup_error is None
    assert len(snapshot.partitions) == 27
    assert snapshot.info["gpt_secondary"] == "DEFERRED_UNTIL_FULL_BACKUP"
    assert snapshot.public()["flash_enabled"] is False
    with pytest.raises(SafetyError, match="FULL_BACKUP_REQUIRED"):
        BackupManager(adb).create(snapshot, str(tmp_path), "critical", threading.Event(), lambda _: None)


def test_primary_only_never_relaxes_full_image_secondary_validation():
    image = bytearray(synthetic_disk())
    image[-512] ^= 1
    assert len(read_primary_gpt(image[:65536], len(image) // 512)) == 27
    with pytest.raises(SafetyError, match="GPT_INVALID"):
        read_gpt(lambda off, size: image[off:off + size], len(image) // 512)


@pytest.mark.parametrize("size,valid", [(0xffffffff, True), (1, False), (4094, False), (4095, True)])
def test_protective_mbr_vendor_sentinel_only(size, valid):
    image = bytearray(synthetic_disk())
    struct.pack_into("<I", image, 446 + 12, size)
    if valid:
        assert len(read_gpt(lambda off, n: image[off:off + n], len(image) // 512)) == 27
    else:
        with pytest.raises(SafetyError, match="GPT_INVALID"):
            read_primary_gpt(image[:65536], len(image) // 512)


def test_kernel_without_uname_and_root_without_shell():
    class Metadata:
        def __init__(self, transport):
            pass
        def read_text(self, path):
            return {"/proc/version": "Linux version 3.10.28 (private-user@private-host) build",
                    "/proc/self/status": "Name: adbd\nUid:\t0\t0\t0\t0\n"}[path]
    adb = ADB("fake", sync_factory=Metadata, run=lambda *a, **k: pytest.fail("no shell"))
    assert adb._read("1", "kernel") == "3.10.28"
    assert adb._read("1", "root") == "uid=0"


@pytest.mark.parametrize("fault", [None, "missing_done", "bad_secondary"])
def test_legacy_full_backup_through_real_sync_parser(tmp_path, fault):
    adb = LegacyADB()
    image = bytearray(adb.demo.image)
    struct.pack_into("<I", image, 446 + 12, 0xffffffff)
    if fault == "bad_secondary":
        image[-512] ^= 1
    adb.demo.image = bytes(image)
    def factory(transport):
        data = b"".join(packet(b"DATA", image[i:i + 65536]) for i in range(0, len(image), 65536))
        sync, _ = reader(data + (b"" if fault == "missing_done" else packet(b"DONE")))
        return sync
    adb.sync_factory = factory
    snapshot = adb.inspect()
    assert snapshot.backup_error is None
    assert snapshot.info["protective_mbr"] == "SATURATED_SIZE"
    if fault:
        with pytest.raises(SafetyError, match="STREAM_FAILED" if fault == "missing_done" else "GPT_INVALID"):
            BackupManager(adb).create(snapshot, str(tmp_path), "full", threading.Event(), lambda _: None)
        manifest = json.loads(next(tmp_path.glob("*/manifest.json")).read_text())
        assert manifest["status"] == "failed"
        assert not list(tmp_path.glob("*/verification.json"))
    else:
        result = BackupManager(adb).create(snapshot, str(tmp_path), "full", threading.Event(), lambda _: None)
        assert result["verification"]["gpt"] == "PASS"
        assert result["verification"]["flash_ready"] is False
        assert (Path(result["folder"]) / "emmc.img").read_bytes() == image


def test_handshake_failure_is_not_disclosed():
    sync, sock = reader(b"")
    sock.data = bytearray(b"FAIL0014private device error")
    with pytest.raises(SafetyError, match="^SYNC_UNAVAILABLE$"):
        receive(sync, 3)
    assert sock.closed


def test_disk_write_error_is_not_misreported_as_usb_error():
    sync, sock = reader(packet(b"DATA", b"abc") + packet(b"DONE"))
    class DiskFull:
        def write(self, data):
            raise OSError("disk full")
    with pytest.raises(OSError, match="disk full"):
        sync.receive("/dev/block/mmcblk0", DiskFull(), threading.Event(), lambda _: None,
                     expected=3, limit=3)
    assert sock.closed

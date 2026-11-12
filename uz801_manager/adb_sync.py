"""Read-only ADB SYNC v1 client (Android 4.4 compatible; never opens a PTY).

Only RECV and LIST are implemented. Protocol reference: AOSP android-4.4.4_r2
adb/file_sync_service.{c,h}. Full streams require exact size AND DONE.
"""
import io
import re
import socket
import struct
import threading
import time
from contextlib import contextmanager

from .errors import Cancelled, SafetyError

TEXT_PATHS = {
    "/system/build.prop", "/proc/self/status", "/proc/version", "/proc/meminfo",
    "/proc/cpuinfo", "/proc/sys/kernel/random/boot_id",
    "/sys/class/block/mmcblk0/size", "/sys/class/block/mmcblk0/queue/logical_block_size",
    "/sys/class/block/mmcblk0/device/name", "/sys/class/block/mmcblk0/device/cid",
}
MAX_PACKET = 65536


class SyncReader:
    def __init__(self, transport, *, connect=socket.create_connection, timeout=30):
        if not isinstance(transport, str) or not re.fullmatch(r"[0-9]+", transport):
            raise SafetyError("INPUT_INVALID")
        self.transport, self.connect, self.timeout = transport, connect, timeout

    @contextmanager
    def session(self, cancel):
        try:
            sock = self.connect(("127.0.0.1", 5037), timeout=self.timeout)
        except OSError:
            raise SafetyError("STREAM_FAILED") from None
        with sock:
            try:
                sock.settimeout(.2)
                for service in ("host:transport-id:" + self.transport, "sync:"):
                    data = service.encode("ascii")
                    sock.sendall(f"{len(data):04x}".encode("ascii") + data)
                    if self.exact(sock, 4, cancel) != b"OKAY":
                        raise SafetyError("SYNC_UNAVAILABLE")
            except OSError:
                raise SafetyError("STREAM_FAILED") from None
            # Do not translate filesystem errors from the consumer into USB errors.
            yield sock

    def exact(self, sock, size, cancel):
        data = bytearray()
        last = time.monotonic()
        while len(data) < size:
            if cancel.is_set():
                raise Cancelled()
            if time.monotonic() - last >= self.timeout:
                raise SafetyError("STREAM_TIMEOUT")
            try:
                chunk = sock.recv(size - len(data))
            except socket.timeout:
                continue
            except OSError:
                raise SafetyError("STREAM_FAILED") from None
            if not chunk:
                raise SafetyError("STREAM_FAILED")
            data.extend(chunk)
            last = time.monotonic()
        return bytes(data)

    @staticmethod
    def request(sock, operation, path):
        data = path.encode("ascii")
        try:
            sock.sendall(operation + struct.pack("<I", len(data)) + data)
        except OSError:
            raise SafetyError("STREAM_FAILED") from None

    def receive(self, path, output, cancel, progress, *, expected=None, limit=65536, prefix=False):
        block = bool(re.fullmatch(r"/dev/block/mmcblk0(?:p[1-9][0-9]{0,3})?", path))
        text = path in TEXT_PATHS or re.fullmatch(r"/sys/class/block/mmcblk0p[1-9][0-9]{0,3}/(?:start|size)", path)
        if not (block or text) or type(limit) is not int or limit <= 0:
            raise SafetyError("INPUT_INVALID")
        if expected is not None and (type(expected) is not int or expected <= 0 or expected > limit):
            raise SafetyError("INPUT_INVALID")
        if block and expected is None or prefix and (not block or expected != limit):
            raise SafetyError("INPUT_INVALID")
        received = 0
        with self.session(cancel) as sock:
            self.request(sock, b"RECV", path)
            while True:
                kind, size = struct.unpack("<4sI", self.exact(sock, 8, cancel))
                if kind == b"FAIL":
                    # Never disclose paths, serials or arbitrary device error text.
                    raise SafetyError("REMOTE_READ_FAILED")
                if kind == b"DONE":
                    if size or prefix or expected is not None and received != expected:
                        raise SafetyError("SIZE_MISMATCH")
                    return received
                if kind != b"DATA" or not 0 < size <= MAX_PACKET:
                    raise SafetyError("SYNC_PROTOCOL")
                if received + size > limit and not prefix:
                    raise SafetyError("SIZE_MISMATCH")
                take = min(size, limit - received)
                data = self.exact(sock, take, cancel)
                count = output.write(data)
                if count is not None and count != len(data):
                    raise SafetyError("IO_ERROR")
                received += take
                progress(received)
                if prefix and received == limit:
                    # Intentional early close is NOT a successful full transfer.
                    return received

    def read_text(self, path):
        out = io.BytesIO()
        self.receive(path, out, threading.Event(), lambda n: None)
        try:
            return out.getvalue().decode("utf-8").strip()
        except UnicodeDecodeError:
            raise SafetyError("INVALID_DEVICE_DATA") from None

    def primary_prefix(self):
        out = io.BytesIO()
        self.receive("/dev/block/mmcblk0", out, threading.Event(), lambda n: None,
                     expected=MAX_PACKET, limit=MAX_PACKET, prefix=True)
        return out.getvalue()

    def partitions(self):
        cancel, names = threading.Event(), []
        with self.session(cancel) as sock:
            self.request(sock, b"LIST", "/sys/class/block")
            for _ in range(4097):
                kind = self.exact(sock, 4, cancel)
                if kind == b"FAIL":
                    raise SafetyError("REMOTE_READ_FAILED")
                if kind not in (b"DENT", b"DONE"):
                    raise SafetyError("SYNC_PROTOCOL")
                fields = struct.unpack("<4I", self.exact(sock, 16, cancel))
                if kind == b"DONE":
                    if any(fields):
                        raise SafetyError("SYNC_PROTOCOL")
                    if len(names) != len(set(names)):
                        raise SafetyError("LAYOUT_MISMATCH")
                    return names
                length = fields[3]
                if not 0 < length <= 255:
                    raise SafetyError("SYNC_PROTOCOL")
                name = self.exact(sock, length, cancel).decode("ascii", errors="replace")
                if re.fullmatch(r"mmcblk0p[1-9][0-9]{0,3}", name):
                    names.append(name)
            raise SafetyError("SYNC_PROTOCOL")

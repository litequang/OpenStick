"""Narrow ADB read API. There is intentionally no general command endpoint."""
import hashlib
import hmac
import io
import os
import queue
import re
import secrets
import shutil
import struct
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .errors import Cancelled, SafetyError
from .gpt import Partition, read_gpt, read_primary_gpt
from .adb_sync import SyncReader

CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
TRAILER = b"\nUZ801_RC=000\n"
CRITICAL = ("modemst1", "modemst2", "fsg", "fsc", "persist", "sbl1", "aboot", "boot", "system", "userdata")
CALIBRATION = ("modemst1", "modemst2", "fsg", "fsc", "persist")
EXPECTED_NUMBERS = dict(zip(CRITICAL, (13, 14, 20, 16, 24, 2, 4, 22, 23, 27)))
PROPERTIES = dict(model="ro.product.model", product="ro.product.name", board="ro.product.board",
                  platform="ro.board.platform", android="ro.build.version.release")
PATHS = dict(kernel="/proc/version", root="/proc/self/status", ram="/proc/meminfo", cpu="/proc/cpuinfo",
             sectors="/sys/class/block/mmcblk0/size", logical_sector="/sys/class/block/mmcblk0/queue/logical_block_size",
             emmc_name="/sys/class/block/mmcblk0/device/name", cid="/sys/class/block/mmcblk0/device/cid",
             boot_id="/proc/sys/kernel/random/boot_id")
READS = (*PROPERTIES, *PATHS, "layout")


def find_adb():
    # Configuration is local process configuration, never a browser-supplied executable.
    configured = os.environ.get("UZ801_ADB")
    candidates = [configured] if configured else [r"C:\adb\adb.exe", shutil.which("adb")]
    for value in candidates:
        if value and Path(value).is_file():
            return str(Path(value).resolve())
    return None


@dataclass
class Snapshot:
    transport: str = field(repr=False)
    serial: str = field(repr=False)
    fingerprint: str = field(repr=False)
    info: dict
    partitions: list[Partition]
    warnings: list[str]
    backup_error: str | None = None

    def public(self):
        return {**self.info, "partitions": [p.public() for p in self.partitions],
                "warnings": self.warnings, "backup_error": self.backup_error,
                "backup_allowed": self.backup_error is None,
                "board_verified": False, "flash_enabled": False}


class ADB:
    def __init__(self, executable=None, *, run=subprocess.run, popen=subprocess.Popen, idle_timeout=30,
                 sync_factory=SyncReader):
        self.executable = executable or find_adb()
        self.run = run
        self.popen = popen
        self.idle_timeout = idle_timeout
        self._salt = secrets.token_bytes(32)
        self.sync_factory = sync_factory

    def _run(self, args):
        if not self.executable:
            raise SafetyError("ADB_NOT_FOUND")
        try:
            result = self.run([self.executable, "-H", "127.0.0.1", "-P", "5037", *args], capture_output=True,
                              timeout=20, creationflags=CREATE_FLAGS, shell=False)
        except subprocess.TimeoutExpired:
            raise SafetyError("ADB_TIMEOUT") from None
        except OSError:
            raise SafetyError("ADB_FAILED") from None
        if result.returncode:
            raise SafetyError("ADB_FAILED")
        if len(result.stdout) > 1024 * 1024:
            raise SafetyError("INVALID_DEVICE_DATA")
        return result.stdout.decode("utf-8", errors="replace").strip()

    def connection(self):
        lines = self._run(["devices", "-l"]).splitlines()
        devices = []
        for line in lines:
            fields = line.split()
            if len(fields) >= 2 and fields[1] == "device":
                tid = next((s[13:] for s in fields[2:] if s.startswith("transport_id:")), "")
                if not tid.isdecimal():
                    raise SafetyError("TRANSPORT_UNSUPPORTED")
                devices.append((fields[0], tid))
        if not devices:
            raise SafetyError("NO_DEVICE")
        if len(devices) != 1:
            raise SafetyError("MULTIPLE_DEVICES")
        return devices[0]

    def _read(self, transport, key):
        if not transport.isdecimal() or key not in READS:
            raise SafetyError("INPUT_INVALID")
        sync = self.sync_factory(transport)
        if key in PROPERTIES:
            props = dict(line.split("=", 1) for line in sync.read_text("/system/build.prop").splitlines()
                         if "=" in line and not line.lstrip().startswith("#"))
            return props.get(PROPERTIES[key], "")
        if key == "layout":
            lines = []
            for name in sync.partitions():
                lines.extend((name, sync.read_text(f"/sys/class/block/{name}/start"),
                              sync.read_text(f"/sys/class/block/{name}/size")))
            return "\n".join(lines)
        value = sync.read_text(PATHS[key])
        if key == "root":
            # /proc/self is adbd itself, the process servicing SYNC reads.
            uid = re.search(r"^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$", value, re.M)
            return "uid=0" if uid and all(n == "0" for n in uid.groups()) else "unprivileged"
        if key == "kernel":
            match = re.match(r"Linux version (\S+)", value)
            if not match:
                raise SafetyError("INVALID_DEVICE_DATA")
            return match[1]  # Do not publish build usernames/hostnames.
        return value

    def supports_exec_out(self, transport):
        """Synthetic 256-byte probe; no disk read and no shell/PTY fallback."""
        expected = bytes(range(256))
        command = "printf '" + "".join(f"\\{n:03o}" for n in range(256)) + "'"
        out = io.BytesIO()
        try:
            self._stream(transport, command, len(expected), out, threading.Event(), lambda n: None)
        except SafetyError:
            return False
        return out.getvalue() == expected

    def identity(self, transport):
        cid = self._read(transport, "cid").lower()
        boot = self._read(transport, "boot_id").lower()
        if not re.fullmatch(r"[0-9a-f]{32}", cid) or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot):
            raise SafetyError("IDENTITY_UNAVAILABLE")
        return hmac.new(self._salt, (cid + boot).encode(), hashlib.sha256).hexdigest()

    def assert_same(self, snapshot):
        serial, transport = self.connection()
        if (serial, transport) != (snapshot.serial, snapshot.transport):
            raise SafetyError("DEVICE_CHANGED")
        if not hmac.compare_digest(self.identity(transport), snapshot.fingerprint):
            raise SafetyError("DEVICE_CHANGED")

    def inspect(self):
        serial, transport = self.connection()
        values = {key: self._read(transport, key) for key in READS if key not in ("cid", "boot_id", "layout")}
        try:
            sectors = int(values["sectors"])
            logical = int(values["logical_sector"])
            ram = int(re.search(r"^MemTotal:\s+(\d+)\s+kB", values["ram"], re.M)[1])
            if not 68 <= sectors <= 2**40 or logical != 512:
                raise ValueError()
        except (ValueError, TypeError):
            raise SafetyError("INVALID_DEVICE_DATA") from None
        cpu = re.search(r"^Hardware\s*:\s*(.+)$", values["cpu"], re.M)
        info = {key: values[key][:200] for key in ("model", "product", "board", "platform", "android", "kernel", "emmc_name")}
        info.update(root=bool(re.search(r"(?:^|\s)uid=0(?:\D|$)", values["root"])),
                    ram_kb=ram, sectors=sectors, emmc_bytes=sectors * 512,
                    chipset=cpu[1].strip()[:200] if cpu else values["platform"][:200],
                    logical_sector=logical, connected=True)
        warnings = ["Mã board do Android báo không xác minh được chữ in trên PCB V3.2.",
                    "Backup ADB khi Android đang chạy có thể không nhất quán giữa các phân vùng."]
        expectations = {"model": "UZ801", "product": "msm8916_32_512", "android": "4.4.4", "emmc_name": "XINYH"}
        for key, expected in expectations.items():
            if info[key] != expected:
                warnings.append(f"{key}: không khớp cấu hình tham chiếu.")
        if sectors != 7569408 or ram != 397824 or "8916" not in info["chipset"]:
            warnings.append("Dung lượng eMMC, RAM hoặc chipset khác cấu hình tham chiếu.")
        snapshot = Snapshot(transport, serial, "", info, [], warnings)
        if not info["root"]:
            snapshot.backup_error = "NO_ROOT"
            return snapshot
        try:
            snapshot.fingerprint = self.identity(transport)
            exec_ok = self.supports_exec_out(transport)
            info.update(binary_transport="adb-sync-v1", exec_out="PASS" if exec_ok else "UNAVAILABLE",
                        gpt_primary="NOT_TESTED", gpt_secondary="NOT_TESTED")
            prefix = self.sync_factory(transport).primary_prefix()
            info["protective_mbr"] = "SATURATED_SIZE" if any(
                prefix[446 + i * 16 + 4] == 0xEE and
                struct.unpack_from("<I", prefix, 446 + i * 16 + 12)[0] == 0xFFFFFFFF
                for i in range(4)) and sectors - 1 < 0xFFFFFFFF else "STANDARD_SIZE"
            if info["protective_mbr"] == "SATURATED_SIZE":
                warnings.append("Protective MBR dùng 0xFFFFFFFF thay vì kích thước đĩa; "
                                "giữ nguyên dữ liệu, đối chiếu dung lượng bằng sysfs và GPT.")
            if exec_ok:
                parts = read_gpt(lambda off, length: self.read_range(snapshot, off, length), sectors)
                info["gpt_secondary"] = "PASS"
            else:
                parts = read_primary_gpt(prefix, sectors)
                info["gpt_secondary"] = "DEFERRED_UNTIL_FULL_BACKUP"
                warnings.append("exec-out không khả dụng. ADB SYNC chỉ đọc đã kiểm tra GPT chính; "
                                "GPT dự phòng sẽ kiểm tra từ ảnh full sau khi bạn cho phép backup riêng. "
                                "Chế độ chỉ phân vùng quan trọng bị khóa.")
            info["gpt_primary"] = "PASS"
            layout = self._read(transport, "layout").splitlines()
            if len(layout) % 3:
                raise SafetyError("LAYOUT_MISMATCH")
            observed = {}
            for i in range(0, len(layout), 3):
                name, start, count = layout[i:i + 3]
                if not re.fullmatch(r"mmcblk0p[1-9][0-9]*", name):
                    raise SafetyError("LAYOUT_MISMATCH")
                observed[name] = (int(start), int(count))
            expected = {f"mmcblk0p{p.number}": (p.first_lba, p.size // 512) for p in parts}
            if observed != expected:
                raise SafetyError("LAYOUT_MISMATCH")
            snapshot.partitions = parts
            if len(parts) != 27:
                warnings.append("GPT không có đúng 27 phân vùng như cấu hình tham chiếu.")
            names = {p.name: p.number for p in parts}
            if any(name not in names for name in CRITICAL):
                raise SafetyError("CRITICAL_MISSING")
            if any(names.get(name) != number for name, number in EXPECTED_NUMBERS.items()):
                warnings.append("Vị trí phân vùng khác tham chiếu; dùng vị trí GPT vừa đọc, không dùng số hardcode.")
            self.assert_same(snapshot)
        except SafetyError as exc:
            snapshot.backup_error = exc.code
        except ValueError:
            snapshot.backup_error = "INVALID_DEVICE_DATA"
        return snapshot

    def read_range(self, snapshot, offset, length):
        if type(offset) is not int or type(length) is not int or offset % 512 or length % 512:
            raise SafetyError("INPUT_INVALID")
        if offset < 0 or not 0 < length <= 4 * 1024 * 1024 or offset + length > snapshot.info["emmc_bytes"]:
            raise SafetyError("INPUT_INVALID")
        out = io.BytesIO()
        command = f"dd if=/dev/block/mmcblk0 bs=512 skip={offset // 512} count={length // 512}"
        self._stream(snapshot.transport, command, length, out, threading.Event(), lambda n: None)
        return out.getvalue()

    def copy(self, snapshot, partition, output, cancel, progress):
        self.assert_same(snapshot)
        if partition is None:
            block, size = "/dev/block/mmcblk0", snapshot.info["emmc_bytes"]
        else:
            if partition not in snapshot.partitions or not 1 <= partition.number <= 4096:
                raise SafetyError("INPUT_INVALID")
            block, size = partition.block, partition.size
        self.sync_factory(snapshot.transport).receive(block, output, cancel, progress,
                                                       expected=size, limit=size)
        self.assert_same(snapshot)

    def _stream(self, transport, command, expected, output, cancel, progress):
        if not transport.isdecimal():
            raise SafetyError("INPUT_INVALID")
        # exec-out is non-PTY. Remote status trailer detects errors even on shell-v1.
        # The command is built solely from fixed strings and checked integers.
        script = command + " 2>/dev/null; rc=$?; printf '\\nUZ801_RC=%03d\\n' \"$rc\""
        try:
            proc = self.popen([self.executable, "-H", "127.0.0.1", "-P", "5037", "-t", transport, "exec-out", script],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                              stdin=subprocess.DEVNULL, shell=False, creationflags=CREATE_FLAGS)
        except OSError:
            raise SafetyError("STREAM_FAILED") from None
        items = queue.Queue(maxsize=8)
        stopped = threading.Event()

        def enqueue(item):
            while not stopped.is_set():
                try:
                    items.put(item, timeout=0.2)
                    return
                except queue.Full:
                    pass

        def pump():
            try:
                while not stopped.is_set():
                    chunk = proc.stdout.read1(1024 * 1024)
                    if not chunk:
                        break
                    enqueue(chunk)
            except (OSError, ValueError):
                enqueue(False)
            finally:
                enqueue(None)

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        received, tail, last = 0, bytearray(), time.monotonic()
        try:
            while True:
                if cancel.is_set():
                    raise Cancelled()
                try:
                    item = items.get(timeout=0.2)
                except queue.Empty:
                    if time.monotonic() - last > self.idle_timeout:
                        raise SafetyError("STREAM_TIMEOUT")
                    continue
                last = time.monotonic()
                if item is False:
                    raise SafetyError("STREAM_FAILED")
                if item is None:
                    break
                length = min(len(item), expected - received)
                if length:
                    output.write(item[:length])
                    received += length
                    progress(received)
                tail.extend(item[length:])
                if len(tail) > len(TRAILER):
                    raise SafetyError("SIZE_MISMATCH")
            try:
                code = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                raise SafetyError("STREAM_TIMEOUT") from None
            if code:
                raise SafetyError("STREAM_FAILED")
            if received != expected:
                raise SafetyError("SIZE_MISMATCH")
            if tail != TRAILER:
                raise SafetyError("REMOTE_READ_FAILED")
        finally:
            stopped.set()
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
            reader.join(timeout=5)
            proc.stdout.close()

"""Small synthetic disk for demos and tests. Never opens USB or runs subprocesses."""
import copy
import io
import struct
import time
import uuid
import zlib

from .adb import EXPECTED_NUMBERS, Snapshot
from .errors import Cancelled, SafetyError
from .gpt import read_gpt


def synthetic_disk():
    sectors = 4096
    image = bytearray(sectors * 512)
    image[510:512] = b"\x55\xaa"
    image[450] = 0xEE
    struct.pack_into("<II", image, 454, 1, sectors - 1)
    entries = bytearray(128 * 128)
    names = {v: k for k, v in EXPECTED_NUMBERS.items()}
    for number in range(1, 28):
        name = names.get(number, f"reserved{number}")
        start = 40 + (number - 1) * 100
        end = start + 63
        entry = (number - 1) * 128
        entries[entry:entry + 16] = uuid.UUID("0fc63daf-8483-4772-8e79-3d69d8477de4").bytes_le
        entries[entry + 16:entry + 32] = uuid.UUID(int=number).bytes_le
        struct.pack_into("<QQQ", entries, entry + 32, start, end, 0)
        encoded = name.encode("utf-16-le")
        entries[entry + 56:entry + 56 + len(encoded)] = encoded
        image[start * 512:(end + 1) * 512] = bytes([number]) * ((end - start + 1) * 512)
    for current, other, table in ((1, sectors - 1, 2), (sectors - 1, 1, sectors - 33)):
        header = bytearray(512)
        struct.pack_into("<8sIIIIQQQQ16sQIII", header, 0, b"EFI PART", 0x10000, 92, 0, 0,
                         current, other, 34, sectors - 34, uuid.UUID(int=100).bytes_le,
                         table, 128, 128, zlib.crc32(entries))
        struct.pack_into("<I", header, 16, zlib.crc32(header[:92]))
        image[current * 512:(current + 1) * 512] = header
        image[table * 512:table * 512 + len(entries)] = entries
    return bytes(image)


class DemoADB:
    executable = "SIMULATION — không dùng ADB thật"

    def __init__(self, delay=0.01):
        self.image = synthetic_disk()
        self.delay = delay
        self.changed = False
        self.snapshot = Snapshot("1", "DEMO", "demo-fingerprint", {
            "model": "UZ801 (MÔ PHỎNG)", "product": "msm8916_32_512", "board": "CHƯA XÁC MINH",
            "platform": "msm8916", "chipset": "Qualcomm MSM8916 (mô phỏng)", "android": "4.4.4",
            "kernel": "Linux 3.10.28 (mô phỏng)", "root": True, "ram_kb": 397824,
            "sectors": len(self.image) // 512, "logical_sector": 512,
            "emmc_bytes": len(self.image), "emmc_name": "SYNTHETIC", "connected": True, "demo": True,
        }, read_gpt(lambda offset, size: self.image[offset:offset + size], len(self.image) // 512),
            ["Đây là dữ liệu mô phỏng 2 MiB, không phải dữ liệu USB thật."])

    def inspect(self):
        return copy.deepcopy(self.snapshot)

    def assert_same(self, snapshot):
        if self.changed or snapshot.fingerprint != self.snapshot.fingerprint:
            raise SafetyError("DEVICE_CHANGED")

    def copy(self, snapshot, partition, output, cancel, progress):
        self.assert_same(snapshot)
        data = self.image if partition is None else self.image[partition.first_lba * 512:(partition.last_lba + 1) * 512]
        with io.BytesIO(data) as f:
            count = 0
            while chunk := f.read(65536):
                if cancel.is_set():
                    raise Cancelled()
                output.write(chunk)
                count += len(chunk)
                progress(count)
                if self.delay:
                    time.sleep(self.delay)
        self.assert_same(snapshot)

"""Strict 512-byte-sector GPT reader, independently implemented from UEFI layout.

No repair, conversion, writing, or automatic acceptance of a surviving GPT copy.
"""
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .errors import SafetyError

SECTOR = 512


@dataclass(frozen=True)
class Partition:
    number: int
    name: str
    first_lba: int
    last_lba: int

    @property
    def size(self):
        return (self.last_lba - self.first_lba + 1) * SECTOR

    @property
    def block(self):
        return f"/dev/block/mmcblk0p{self.number}"

    def public(self):
        return {**asdict(self), "size": self.size, "block": self.block}


def read_gpt(read: Callable[[int, int], bytes], total_sectors: int) -> list[Partition]:
    """read(offset_bytes, size_bytes) must return exactly the requested range."""
    def fail():
        raise SafetyError("GPT_INVALID")

    def get(offset, size):
        if offset < 0 or size < 0 or offset + size > total_sectors * SECTOR:
            fail()
        data = read(offset, size)
        if len(data) != size:
            fail()
        return bytes(data)

    def header(lba):
        data = get(lba * SECTOR, SECTOR)
        if data[:8] != b"EFI PART":
            fail()
        revision, size, crc, reserved = struct.unpack_from("<4I", data, 8)
        if revision != 0x10000 or not 92 <= size <= SECTOR or reserved:
            fail()
        check = bytearray(data[:size])
        check[16:20] = b"\0" * 4
        if zlib.crc32(check) != crc:
            fail()
        current, other, first, last = struct.unpack_from("<4Q", data, 24)
        table, count, entry_size, table_crc = struct.unpack_from("<QIII", data, 72)
        if current != lba or other != (total_sectors - 1 if lba == 1 else 1):
            fail()
        if not (34 <= first <= last < total_sectors - 1):
            fail()
        if not 1 <= count <= 4096 or entry_size < 128 or entry_size > 4096 or entry_size % 128:
            fail()
        length = count * entry_size
        if length > 4 * 1024 * 1024:
            fail()
        table_sectors = (length + SECTOR - 1) // SECTOR
        if lba == 1:
            if table < 2 or table + table_sectors > first:
                fail()
        elif table <= last or table + table_sectors > lba:
            fail()
        entries = get(table * SECTOR, table_sectors * SECTOR)[:length]
        if zlib.crc32(entries) != table_crc:
            fail()
        return first, last, data[56:72], count, entry_size, entries

    if type(total_sectors) is not int or total_sectors < 68:
        fail()
    mbr = get(0, SECTOR)
    protective = [mbr[446 + 16 * i:462 + 16 * i] for i in range(4)]
    if mbr[510:512] != b"\x55\xaa" or sum(e[4] == 0xEE for e in protective) != 1:
        fail()
    if any(e[4] not in (0, 0xEE) for e in protective):
        fail()
    entry = next(e for e in protective if e[4] == 0xEE)
    if struct.unpack_from("<II", entry, 8) != (1, min(total_sectors - 1, 0xFFFFFFFF)):
        fail()
    primary, secondary = header(1), header(total_sectors - 1)
    if primary != secondary or primary[2] == b"\0" * 16:
        fail()
    first, last, _, count, entry_size, entries = primary
    parts, names, guids = [], set(), set()
    for index in range(count):
        e = entries[index * entry_size:(index + 1) * entry_size]
        if e[:16] == b"\0" * 16:
            continue
        start, end = struct.unpack_from("<QQ", e, 32)
        try:
            name = e[56:128].decode("utf-16-le").split("\0", 1)[0]
        except UnicodeDecodeError:
            fail()
        # Names are metadata only, never shell arguments or filenames.
        if not name or len(name) > 36 or any(ord(c) < 32 for c in name):
            fail()
        if not first <= start <= end <= last or name in names:
            fail()
        guid = e[16:32]
        if guid == b"\0" * 16 or guid in guids:
            fail()
        names.add(name)
        guids.add(guid)
        parts.append(Partition(index + 1, name, start, end))
    ordered = sorted(parts, key=lambda p: p.first_lba)
    if not parts or any(a.last_lba >= b.first_lba for a, b in zip(ordered, ordered[1:])):
        fail()
    return parts


def file_gpt(path: Path) -> list[Partition]:
    with path.open("rb") as f:
        def read(offset, length):
            f.seek(offset)
            return f.read(length)
        size = path.stat().st_size
        if size % SECTOR:
            raise SafetyError("GPT_INVALID")
        return read_gpt(read, size // SECTOR)

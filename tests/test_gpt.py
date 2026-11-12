import struct
import zlib

import pytest

from uz801_manager.demo import synthetic_disk
from uz801_manager.errors import SafetyError
from uz801_manager.gpt import read_gpt


def parse(image):
    return read_gpt(lambda offset, size: image[offset:offset + size], len(image) // 512)


def test_27_partitions():
    parts = parse(synthetic_disk())
    assert len(parts) == 27
    assert next(p.number for p in parts if p.name == "persist") == 24


@pytest.mark.parametrize("offset", [510, 512, 528, 1024, -512, -500, -1024])
def test_corrupt_gpt_and_secondary_rejected(offset):
    image = bytearray(synthetic_disk())
    image[offset] ^= 1
    with pytest.raises(SafetyError, match="GPT_INVALID"):
        parse(image)


def test_huge_table_rejected_before_allocation():
    image = bytearray(synthetic_disk())
    struct.pack_into("<I", image, 512 + 80, 0xFFFFFFFF)
    image[528:532] = bytes(4)
    struct.pack_into("<I", image, 528, zlib.crc32(image[512:604]))
    with pytest.raises(SafetyError, match="GPT_INVALID"):
        parse(image)

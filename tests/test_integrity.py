import hashlib
import json
import struct
import threading
import zlib
from pathlib import Path

import pytest

from uz801_manager.backup import BackupManager, verify_backup
from uz801_manager.demo import DemoADB, synthetic_disk
from uz801_manager.errors import SafetyError
from uz801_manager.gpt import read_gpt
from uz801_manager.storage import Jobs, atomic_json, local_directory


def resign_tables(image, mutate):
    table = bytearray(image[1024:1024 + 16384])
    mutate(table)
    sectors = len(image) // 512
    for header_lba, table_lba in [(1, 2), (sectors - 1, sectors - 33)]:
        start = header_lba * 512
        image[table_lba * 512:table_lba * 512 + len(table)] = table
        struct.pack_into("<I", image, start + 88, zlib.crc32(table))
        image[start + 16:start + 20] = bytes(4)
        struct.pack_into("<I", image, start + 16, zlib.crc32(image[start:start + 92]))


@pytest.mark.parametrize("kind", ["overlap", "duplicate_name", "duplicate_guid", "outside"])
def test_valid_crc_but_invalid_geometry(kind):
    image = bytearray(synthetic_disk())
    def mutate(table):
        if kind == "overlap":
            struct.pack_into("<QQ", table, 128 + 32, 40, 80)
        elif kind == "duplicate_name":
            table[128 + 56:256] = table[56:128]
        elif kind == "duplicate_guid":
            table[128 + 16:128 + 32] = table[16:32]
        else:
            struct.pack_into("<QQ", table, 32, 10, 20)
    resign_tables(image, mutate)
    with pytest.raises(SafetyError, match="GPT_INVALID"):
        read_gpt(lambda o, n: image[o:o+n], len(image) // 512)


def make_backup(tmp_path):
    adb = DemoADB(delay=0)
    result = BackupManager(adb).create(adb.inspect(), str(tmp_path), "full", threading.Event(), lambda _: None)
    return Path(result["folder"])


def test_gpt_verification_independent_of_saved_hash(tmp_path):
    folder = make_backup(tmp_path)
    path = folder / "emmc.img"
    image = bytearray(path.read_bytes())
    image[512] ^= 1
    path.write_bytes(image)
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["files"][0]["sha256"] = hashlib.sha256(image).hexdigest()
    atomic_json(folder / "manifest.json", manifest)
    with pytest.raises(SafetyError, match="GPT_INVALID"):
        verify_backup(str(folder))


def test_missing_sidecar(tmp_path):
    folder = make_backup(tmp_path)
    (folder / "p013.img").rename(folder / "missing.img")
    with pytest.raises(SafetyError, match="BACKUP_INCOMPLETE"):
        verify_backup(str(folder))


def test_raw_and_sidecar_must_match_even_if_both_hashes_saved(tmp_path):
    folder = make_backup(tmp_path)
    path = folder / "p013.img"
    data = b"x" * path.stat().st_size
    path.write_bytes(data)
    manifest = json.loads((folder / "manifest.json").read_text())
    next(e for e in manifest["files"] if e["file"] == path.name)["sha256"] = hashlib.sha256(data).hexdigest()
    atomic_json(folder / "manifest.json", manifest)
    with pytest.raises(SafetyError, match="HASH_MISMATCH"):
        verify_backup(str(folder))


def test_restart_marks_interrupted_and_closes_database(tmp_path):
    jobs = Jobs(tmp_path)
    with jobs.connect() as db:
        db.execute("INSERT INTO jobs VALUES ('crash', 'backup', 'running', 1, 1, '{}')")
    jobs.recover_interrupted()
    assert jobs.history()[0]["status"] == "interrupted"
    jobs.db.rename(tmp_path / "closed.db")  # Windows rejects this if a connection leaks.


@pytest.mark.parametrize("path", ["../bad", r"\\server\share", r"C:\folder\..\secret", r"\\.\PhysicalDrive0", r"C:\data\test:stream"])
def test_reject_paths(path):
    with pytest.raises(SafetyError, match="PATH_INVALID"):
        local_directory(path)

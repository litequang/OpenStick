import json
import threading
from types import SimpleNamespace

import pytest

from uz801_manager.backup import BackupManager, verify_backup
from uz801_manager.demo import DemoADB
from uz801_manager.errors import SafetyError
from uz801_manager.storage import Jobs, atomic_json


@pytest.fixture
def adb():
    return DemoADB(delay=0)


def create(adb, tmp_path, mode="full", cancel=None):
    return BackupManager(adb).create(adb.inspect(), str(tmp_path), mode, cancel or threading.Event(), lambda _: None)


def test_full_backup_and_verification(adb, tmp_path):
    result = create(adb, tmp_path)
    verified = verify_backup(result["folder"])
    assert verified["status"] == "PASS"
    assert verified["gpt"] == "PASS"
    assert verified["partition_count"] == 27
    assert verified["flash_ready"] is False
    assert verified["source"] == "demo"


def test_critical_only_cannot_claim_gpt_pass(adb, tmp_path):
    result = create(adb, tmp_path, "critical")
    assert result["verification"]["gpt"] == "NOT_TESTED"


def test_no_root_blocks_before_output(adb, tmp_path):
    snapshot = adb.inspect()
    snapshot.backup_error = "NO_ROOT"
    with pytest.raises(SafetyError, match="NO_ROOT"):
        BackupManager(adb).create(snapshot, str(tmp_path), "full", threading.Event(), lambda _: None)
    assert list(tmp_path.iterdir()) == []


def test_disk_full_preflight(adb, tmp_path):
    with pytest.raises(SafetyError, match="DISK_SPACE"):
        BackupManager(adb, disk_usage=lambda _: SimpleNamespace(free=0)).create(
            adb.inspect(), str(tmp_path), "full", threading.Event(), lambda _: None)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("fault", ["disconnect", "short", "disk_full"])
def test_incomplete_stream_never_complete(adb, tmp_path, fault):
    def copy(snapshot, partition, output, cancel, progress):
        output.write(b"partial")
        if fault == "disconnect":
            raise SafetyError("STREAM_FAILED")
        if fault == "disk_full":
            raise OSError("private filesystem path")
    adb.copy = copy
    with pytest.raises((SafetyError, OSError)):
        create(adb, tmp_path)
    folder = next(tmp_path.iterdir())
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert not (folder / "emmc.img").exists()
    assert (folder / "emmc.img.part").exists()
    with pytest.raises(SafetyError, match="BACKUP_INCOMPLETE"):
        verify_backup(str(folder))


def test_swap_device(adb, tmp_path):
    adb.changed = True
    with pytest.raises(SafetyError, match="DEVICE_CHANGED"):
        create(adb, tmp_path)


def test_cancel(adb, tmp_path):
    event = threading.Event()
    def callback(_):
        event.set()
    with pytest.raises(SafetyError, match="CANCELLED"):
        BackupManager(adb).create(adb.inspect(), str(tmp_path), "full", event, callback)
    assert json.loads(next(tmp_path.glob("*/manifest.json")).read_text())["status"] == "cancelled"


def test_hash_mismatch(adb, tmp_path):
    from pathlib import Path
    folder = Path(create(adb, tmp_path)["folder"])
    target = folder / "p013.img"
    with target.open("r+b") as f:
        f.write(b"tampered")
    with pytest.raises(SafetyError, match="HASH_MISMATCH"):
        verify_backup(str(folder))


def test_short_file(adb, tmp_path):
    from pathlib import Path
    folder = Path(create(adb, tmp_path)["folder"])
    (folder / "p013.img").write_bytes(b"short")
    with pytest.raises(SafetyError, match="SIZE_MISMATCH"):
        verify_backup(str(folder))


def test_manifest_traversal(adb, tmp_path):
    from pathlib import Path
    folder = Path(create(adb, tmp_path)["folder"])
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["files"][0]["file"] = "../secret"
    atomic_json(folder / "manifest.json", manifest)
    with pytest.raises(SafetyError):
        verify_backup(str(folder))


def test_two_jobs_and_two_managers_block(tmp_path):
    one, two = Jobs(tmp_path), Jobs(tmp_path)
    entered, release = threading.Event(), threading.Event()
    def work(cancel, update):
        entered.set()
        assert release.wait(5)
    one.start("backup", work)
    assert entered.wait(5)
    try:
        for manager in (one, two):
            with pytest.raises(SafetyError, match="BUSY"):
                manager.start("backup", work)
    finally:
        release.set()
        one.thread.join(5)
    assert one.history()[0]["status"] == "complete"


def test_uniform_calibration_requires_review(adb, tmp_path):
    part = next(p for p in adb.snapshot.partitions if p.name == "modemst1")
    image = bytearray(adb.image)
    image[part.first_lba * 512:(part.last_lba + 1) * 512] = bytes(part.size)
    adb.image = bytes(image)
    result = create(adb, tmp_path)
    assert result["verification"]["status"] == "REVIEW_REQUIRED"

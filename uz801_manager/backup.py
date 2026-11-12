import hashlib
import json
import os
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .adb import CALIBRATION, CRITICAL
from .errors import Cancelled, SafetyError
from .gpt import Partition, file_gpt
from .storage import atomic_json, local_directory

CHUNK = 1024 * 1024
RESERVE = 128 * CHUNK


def check_cancel(cancel):
    if cancel.is_set():
        raise Cancelled()


def digest_file(path, cancel=None, progress=None):
    cancel = cancel or threading.Event()
    digest, total = hashlib.sha256(), 0
    uniform_zero, uniform_ff = True, True
    with path.open("rb") as f:
        while data := f.read(CHUNK):
            check_cancel(cancel)
            digest.update(data)
            total += len(data)
            uniform_zero = uniform_zero and data.count(0) == len(data)
            uniform_ff = uniform_ff and data.count(255) == len(data)
            if progress:
                progress(total)
    return digest.hexdigest(), total, (uniform_zero or uniform_ff)


class HashWriter:
    def __init__(self, handle):
        self.handle = handle
        self.digest = hashlib.sha256()
        self.count = 0

    def write(self, data):
        count = self.handle.write(data)
        if count != len(data):
            raise SafetyError("IO_ERROR")
        self.digest.update(data)
        self.count += count


class BackupManager:
    def __init__(self, adb, *, disk_usage=shutil.disk_usage):
        self.adb = adb
        self.disk_usage = disk_usage

    def create(self, snapshot, folder, mode, cancel, progress):
        if mode not in ("full", "critical"):
            raise SafetyError("INPUT_INVALID")
        if snapshot.backup_error:
            raise SafetyError(snapshot.backup_error)
        if mode == "critical" and snapshot.info.get("gpt_secondary") == "DEFERRED_UNTIL_FULL_BACKUP":
            raise SafetyError("FULL_BACKUP_REQUIRED")
        root = local_directory(folder)
        self.adb.assert_same(snapshot)
        # Re-read geometry and GPT immediately before allocating any backup files.
        current = self.adb.inspect()
        if current.backup_error:
            raise SafetyError(current.backup_error)
        if mode == "critical" and current.info.get("gpt_secondary") == "DEFERRED_UNTIL_FULL_BACKUP":
            raise SafetyError("FULL_BACKUP_REQUIRED")
        if (current.transport, current.fingerprint, current.partitions, current.info["emmc_bytes"]) != (
                snapshot.transport, snapshot.fingerprint, snapshot.partitions, snapshot.info["emmc_bytes"]):
            raise SafetyError("DEVICE_CHANGED")
        parts = [p for p in snapshot.partitions if p.name in CRITICAL]
        if set(p.name for p in parts) != set(CRITICAL):
            raise SafetyError("CRITICAL_MISSING")
        total = sum(p.size for p in parts) + (snapshot.info["emmc_bytes"] if mode == "full" else 0)
        if self.disk_usage(root).free < total + RESERVE:
            raise SafetyError("DISK_SPACE")
        check_cancel(cancel)
        folder = root / ("backup-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid.uuid4().hex[:8])
        folder.mkdir(exist_ok=False)
        manifest = {"schema": 1, "source": "demo" if snapshot.info.get("demo") else "adb-live",
                    "mode": mode, "status": "incomplete", "created_utc": datetime.now(timezone.utc).isoformat(),
                    "consistency": "NOT_GUARANTEED_LIVE", "flash_ready": False,
                    "binary_transport": snapshot.info.get("binary_transport", "demo"),
                    "inspection_gpt_secondary": snapshot.info.get("gpt_secondary", "PASS"),
                    "emmc_bytes": snapshot.info["emmc_bytes"],
                    "partitions": [p.public() for p in snapshot.partitions], "files": []}
        manifest_path = folder / "manifest.json"
        atomic_json(manifest_path, manifest)
        started, completed = time.monotonic(), 0

        def log(code):
            with (folder / "backup.log").open("a", encoding="utf-8") as f:
                f.write(datetime.now(timezone.utc).isoformat() + " " + code + "\n")

        def report(current_bytes, phase):
            check_cancel(cancel)
            progress({"bytes": completed + current_bytes, "total": total,
                      "speed": (completed + current_bytes) / max(time.monotonic() - started, .001),
                      "phase": phase, "folder": str(folder)})

        def save_file(filename, part, producer):
            nonlocal completed
            expected = snapshot.info["emmc_bytes"] if part is None else part.size
            if self.disk_usage(folder).free < expected + RESERVE:
                raise SafetyError("DISK_SPACE")
            partial = folder / (filename + ".part")
            with partial.open("xb") as f:
                writer = HashWriter(f)
                producer(writer, lambda n: report(n, "Đang sao lưu " + filename))
                check_cancel(cancel)
                f.flush()
                os.fsync(f.fileno())
            if writer.count != expected:
                raise SafetyError("SIZE_MISMATCH")
            report(expected, "Đọc lại và kiểm tra " + filename)
            sha, size, uniform = digest_file(partial, cancel, lambda n: report(expected, "Kiểm tra SHA-256 " + filename))
            if sha != writer.digest.hexdigest() or size != expected:
                raise SafetyError("HASH_MISMATCH")
            partial.rename(folder / filename)
            manifest["files"].append({"file": filename, "partition": part.name if part else None,
                                      "size": size, "sha256": sha, "uniform": uniform})
            completed += expected
            atomic_json(manifest_path, manifest)
            log("FILE_VERIFIED " + filename)

        try:
            log("START_READ_ONLY")
            if mode == "full":
                save_file("emmc.img", None, lambda out, cb: self.adb.copy(snapshot, None, out, cancel, cb))
                if file_gpt(folder / "emmc.img") != snapshot.partitions:
                    raise SafetyError("LAYOUT_MISMATCH")
                for part in parts:
                    def extract(out, cb, part=part):
                        # Sidecars come from the same raw snapshot, not a later live read.
                        with (folder / "emmc.img").open("rb") as f:
                            f.seek(part.first_lba * 512)
                            remaining = part.size
                            while remaining:
                                check_cancel(cancel)
                                data = f.read(min(CHUNK, remaining))
                                if not data:
                                    raise SafetyError("SIZE_MISMATCH")
                                out.write(data)
                                remaining -= len(data)
                                cb(part.size - remaining)
                    save_file(f"p{part.number:03d}.img", part, extract)
            else:
                for part in parts:
                    save_file(f"p{part.number:03d}.img", part,
                              lambda out, cb, p=part: self.adb.copy(snapshot, p, out, cancel, cb))
            self.adb.assert_same(snapshot)
            check_cancel(cancel)
            manifest["status"] = "complete"
            atomic_json(manifest_path, manifest)
            result = verify_backup(str(folder), cancel, progress)
            atomic_json(folder / "verification.json", result)
            (folder / "report.txt").write_text(
                "UZ801 — BÁO CÁO SAO LƯU\n" + json.dumps(result, ensure_ascii=False, indent=2) +
                "\nSHA-256 kiểm tra tệp cục bộ; không chứng minh Android live nhất quán hay khôi phục thành công.\n",
                encoding="utf-8")
            log("COMPLETE_" + result["status"])
            return {"folder": str(folder), "verification": result, "bytes": completed, "total": total,
                    "message": "Đã sao lưu; xem trạng thái xác minh và giới hạn live ADB."}
        except BaseException as exc:
            manifest["status"] = "cancelled" if isinstance(exc, Cancelled) else "failed"
            manifest["error"] = exc.code if isinstance(exc, SafetyError) else "IO_ERROR"
            try:
                atomic_json(manifest_path, manifest)
                log(manifest["error"])
            except OSError:
                pass  # The previously durable incomplete manifest remains authoritative.
            raise


def load_manifest(folder):
    path = folder / "manifest.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * CHUNK:
        raise SafetyError("MANIFEST_INVALID")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or manifest["schema"] != 1 or manifest["mode"] not in ("full", "critical"):
            raise ValueError()
        if manifest["status"] != "complete":
            raise SafetyError("BACKUP_INCOMPLETE")
        if manifest["source"] not in ("adb-live", "demo"):
            raise ValueError()
        total = manifest["emmc_bytes"]
        if type(total) is not int or total < 68 * 512 or total % 512:
            raise ValueError()
        parts = [Partition(**{key: p[key] for key in ("number", "name", "first_lba", "last_lba")}) for p in manifest["partitions"]]
        if not 1 <= len(parts) <= 4096:
            raise ValueError()
        for p in parts:
            if not isinstance(p.name, str) or not p.name or len(p.name) > 36:
                raise ValueError()
            if any(type(v) is not int for v in (p.number, p.first_lba, p.last_lba)):
                raise ValueError()
            if not 1 <= p.number <= 4096 or not 34 <= p.first_lba <= p.last_lba < total // 512 - 1:
                raise ValueError()
        ordered = sorted(parts, key=lambda p: p.first_lba)
        if len({p.name for p in parts}) != len(parts) or len({p.number for p in parts}) != len(parts):
            raise ValueError()
        if any(a.last_lba >= b.first_lba for a, b in zip(ordered, ordered[1:])):
            raise ValueError()
        files = manifest["files"]
        if not isinstance(files, list) or not 1 <= len(files) <= 4097:
            raise ValueError()
        expected = {f"p{p.number:03d}.img": (p.name, p.size) for p in parts if p.name in CRITICAL}
        if manifest["mode"] == "full":
            expected["emmc.img"] = (None, total)
        if len(files) != len(expected) or {e["file"] for e in files} != set(expected):
            raise SafetyError("BACKUP_INCOMPLETE")
        for e in files:
            if (e["partition"], e["size"]) != expected[e["file"]] or not re.fullmatch(r"[0-9a-f]{64}", e["sha256"]):
                raise ValueError()
            candidate = folder / e["file"]
            if candidate.is_symlink() or candidate.resolve().parent != folder:
                raise ValueError()
        if set(CRITICAL) - {p.name for p in parts}:
            raise SafetyError("CRITICAL_MISSING")
        return manifest, parts
    except (KeyError, TypeError, ValueError, OverflowError):
        raise SafetyError("MANIFEST_INVALID") from None


def verify_backup(value, cancel=None, progress=lambda _: None):
    cancel = cancel or threading.Event()
    folder = local_directory(value)
    manifest, parts = load_manifest(folder)
    suspicious = []
    for e in manifest["files"]:
        check_cancel(cancel)
        path = folder / e["file"]
        if not path.is_file():
            raise SafetyError("BACKUP_INCOMPLETE")
        if path.stat().st_size != e["size"]:
            raise SafetyError("SIZE_MISMATCH")
        sha, size, uniform = digest_file(path, cancel, lambda n: progress({"phase": "Xác minh " + e["file"], "bytes": n, "total": e["size"]}))
        if sha != e["sha256"] or size != e["size"]:
            raise SafetyError("HASH_MISMATCH")
        if uniform and e["partition"] in CALIBRATION:
            suspicious.append(e["partition"])
    gpt_status = "NOT_TESTED"
    if manifest["mode"] == "full":
        if file_gpt(folder / "emmc.img") != parts:
            raise SafetyError("LAYOUT_MISMATCH")
        # Verify sidecars really match ranges from the full image, not only their hashes.
        with (folder / "emmc.img").open("rb") as raw:
            for e in manifest["files"]:
                if e["partition"] is None:
                    continue
                part = next(p for p in parts if p.name == e["partition"])
                raw.seek(part.first_lba * 512)
                remaining, digest = part.size, hashlib.sha256()
                while remaining:
                    check_cancel(cancel)
                    data = raw.read(min(CHUNK, remaining))
                    if not data:
                        raise SafetyError("SIZE_MISMATCH")
                    digest.update(data)
                    remaining -= len(data)
                    progress({"phase": "Đối chiếu phân vùng với ảnh raw", "bytes": part.size - remaining, "total": part.size})
                if digest.hexdigest() != e["sha256"]:
                    raise SafetyError("HASH_MISMATCH")
        gpt_status = "PASS"
    return {"status": "REVIEW_REQUIRED" if suspicious or len(parts) != 27 else "PASS",
            "sha256": "PASS", "readback": "PASS", "gpt": gpt_status,
            "partition_count": len(parts), "expected_27": len(parts) == 27,
            "critical_content": "REVIEW_REQUIRED" if suspicious else "STRUCTURAL_CHECK_ONLY",
            "suspicious_partitions": suspicious, "source": manifest["source"],
            "consistency": "NOT_GUARANTEED_LIVE", "restore_test": "NOT_TESTED", "flash_ready": False}

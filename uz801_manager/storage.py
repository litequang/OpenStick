import json
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .errors import Cancelled, SafetyError, message


def data_directory():
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share")) / "UZ801Manager"


def local_directory(value):
    if not isinstance(value, str) or not value or "\0" in value:
        raise SafetyError("PATH_INVALID")
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise SafetyError("PATH_INVALID")
    if os.name == "nt":
        if value.startswith(("\\\\", "//")) or ":" in str(path)[2:]:
            raise SafetyError("PATH_INVALID")
        if any(p.endswith((".", " ")) for p in path.parts[1:]):
            raise SafetyError("PATH_INVALID")
        import ctypes
        if ctypes.windll.kernel32.GetDriveTypeW(str(path.anchor)) == 4:
            raise SafetyError("PATH_INVALID")
    for parent in (path, *path.parents):
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise SafetyError("PATH_INVALID")
    if not path.is_dir():
        raise SafetyError("PATH_INVALID")
    return path.resolve()


class FileLock:
    """OS-backed lock automatically released if the process dies."""
    def __init__(self, path):
        self.path = Path(path)
        self.handle = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0, 2)
                if not handle.tell():
                    handle.write(b"0")
                    handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            handle.close()
            raise SafetyError("BUSY") from None
        self.handle = handle

    def release(self):
        if self.handle:
            if os.name == "nt":
                import msvcrt
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            self.handle.close()
            self.handle = None


def atomic_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


class Jobs:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = self.directory / "history.db"
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, kind TEXT, status TEXT, created REAL, updated REAL, detail TEXT)")
        self._guard = threading.Lock()
        self._cancel = threading.Event()
        self._active = None
        self.thread = None

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def recover_interrupted(self):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status='interrupted', detail=? WHERE status='running'",
                       (json.dumps({"code": "BACKUP_INCOMPLETE", "message": message("BACKUP_INCOMPLETE")}),))

    def history(self):
        with self.connect() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 100").fetchall()
        return [{**dict(row), "detail": json.loads(row["detail"])} for row in rows]

    def _save(self, job_id, status, detail):
        with self.connect() as db:
            db.execute("UPDATE jobs SET status=?, updated=?, detail=? WHERE id=?",
                       (status, time.time(), json.dumps(detail, ensure_ascii=False), job_id))

    def start(self, kind, operation):
        if not self._guard.acquire(blocking=False):
            raise SafetyError("BUSY")
        lock = FileLock(self.directory / "operation.lock")
        try:
            lock.acquire()
            job_id = uuid.uuid4().hex
            self._cancel = threading.Event()
            with self.connect() as db:
                db.execute("INSERT INTO jobs VALUES (?, ?, 'running', ?, ?, '{}')", (job_id, kind, time.time(), time.time()))
            self._active = job_id
        except BaseException:
            lock.release()
            self._guard.release()
            raise

        def worker():
            last = 0.0
            last_detail = {}
            def update(detail):
                nonlocal last, last_detail
                last_detail = detail
                if self._cancel.is_set():
                    raise Cancelled()
                now = time.monotonic()
                if now - last >= 0.25 or detail.get("force"):
                    self._save(job_id, "running", detail)
                    last = now
            try:
                result = operation(self._cancel, update)
                self._save(job_id, "complete", result or {})
            except SafetyError as exc:
                self._save(job_id, "cancelled" if isinstance(exc, Cancelled) else "failed",
                           {"code": exc.code, "message": message(exc.code),
                            **({"folder": last_detail["folder"]} if "folder" in last_detail else {})})
            except OSError:
                self._save(job_id, "failed", {"code": "IO_ERROR", "message": message("IO_ERROR")})
            except Exception:
                # Never log arbitrary exception strings: adb tools may include CID/IMEI.
                self._save(job_id, "failed", {"code": "INTERNAL_ERROR", "message": message("INTERNAL_ERROR")})
            finally:
                self._active = None
                lock.release()
                self._guard.release()
        self.thread = threading.Thread(target=worker, daemon=False, name=f"uz801-{kind}")
        self.thread.start()
        return job_id

    def cancel(self, job_id):
        if self._active == job_id:
            self._cancel.set()
            return True
        return False

    def shutdown(self):
        self._cancel.set()
        if self.thread:
            # Keep the application lock until its worker has actually stopped.
            self.thread.join()

"""Bound a fixed set of service logs without replacing active writer inodes.

Copy/truncate intentionally has the usual small concurrent-write loss window.
Archives are private, capped tails; never scan or rotate owner site/SMS files.
"""
import os
from pathlib import Path
import stat
import tempfile
import time

MIB = 1048576
LIMITS = {'cloudflared.log': 8*MIB, 'openstick-wifi.log': 2*MIB,
          'openstick-lan.log': MIB, 'openstick-supervisor.log': MIB,
          'nginx/openstick-supervisor.log': MIB}


def regular(path):
    try:
        value = path.lstat()
        return stat.S_ISREG(value.st_mode) and value.st_nlink == 1
    except FileNotFoundError:
        return True


def rotate(path, limit):
    path = Path(path)
    if path.parent.is_symlink() or path.is_symlink():return False
    archives = [path.with_name(path.name+'.'+str(n)) for n in (1,2)]
    if not all(regular(p) for p in archives):return False
    try:fd = os.open(path, os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    except (FileNotFoundError, OSError):return False
    temporary = None
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size <= limit:return False
        # At most two times the nominal log threshold is retained per archive.
        os.lseek(fd, max(0, before.st_size-2*limit), os.SEEK_SET)
        out, temporary = tempfile.mkstemp(prefix='.openstick-log-', dir=path.parent)
        with os.fdopen(out, 'wb') as target:
            remaining = min(before.st_size, 2*limit)
            while remaining:
                chunk = os.read(fd, min(65536, remaining))
                if not chunk:break
                target.write(chunk);remaining -= len(chunk)
            target.flush();os.fsync(target.fileno())
        current = path.lstat()
        if (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino):return False
        # Never rename the active log: OpenRC/Tunnel keep their existing fd.
        if archives[0].exists():os.replace(archives[0], archives[1])
        os.replace(temporary, archives[0]);temporary = None
        os.ftruncate(fd, 0);os.fsync(fd)
        return True
    finally:
        os.close(fd)
        if temporary is not None:Path(temporary).unlink(missing_ok=True)


class LogRetention:
    def __init__(self, root=Path('/var/log'), *, clock=time.monotonic):
        self.root, self.clock = Path(root), clock
        self.next_at = 0

    def tick(self):
        now = self.clock()
        if now < self.next_at:return
        self.next_at = now+60
        if self.root.is_symlink():return
        for name, limit in LIMITS.items():
            try:rotate(self.root/name, limit)
            except OSError:pass  # No private path/log/error output or retry loop.

"""Bounded, streaming file operations inside one public static-site root.

Callers serialize these operations with the shared portal site lock. Uploaded
archives and rollback copies live outside every public document root.
"""
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import tempfile
import unicodedata
import zipfile

from .static_site import ASSETS, TEXT, SiteError

MIB = 1024 * 1024
UPLOAD_LIMIT = 32 * MIB
ZIP_LIMIT = 128 * MIB
SITE_LIMIT = 256 * MIB
TEXT_LIMIT = 2 * MIB
ENTRY_LIMIT = 2000
FREE_RESERVE = 32 * MIB
CHUNK = 64 * 1024
PUBLIC_TYPES = ASSETS | {'.pdf', '.wasm', '.webmanifest', '.mp3', '.mp4', '.webm', '.ogg', '.wav'}


class SiteFiles:
    def __init__(self, root, private):
        self.root, self.private = Path(root).absolute(), Path(private).absolute()

    def path(self, name, *, directory=False, root=False):
        if name == '' and root:
            self._check_root()
            return self.root
        if (not isinstance(name, str) or len(name) > 240 or unicodedata.normalize('NFC', name) != name
                or not 1 <= len(name.split('/')) <= 16):
            raise SiteError('PATH_INVALID')
        for part in name.split('/'):
            if (not part or part.startswith('.') or part[-1:] in (' ', '.') or len(part) > 100
                    or any(ord(c) < 32 or ord(c) == 127 or c in '\\<>:"|?*' for c in part)
                    or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)):
                raise SiteError('PATH_INVALID')
        self._check_root()
        path = self.root
        for part in name.split('/'):
            path = path / part
            if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
                raise SiteError('PATH_INVALID')
            if path != self.root / name and path.exists() and not path.is_dir():
                raise SiteError('PATH_INVALID')
        if not path.resolve().is_relative_to(self.root.resolve()):raise SiteError('PATH_INVALID')
        if not directory and path.suffix.lower() not in PUBLIC_TYPES:raise SiteError('FILE_TYPE_BLOCKED')
        return path

    def _check_root(self):
        for item in (self.root, *self.root.parents):
            if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
                raise SiteError('PATH_INVALID')
        if not self.root.is_dir():raise SiteError('SITE_UNAVAILABLE')

    def listing(self):
        self._check_root()
        entries, total, digest = [], 0, hashlib.sha256()
        for current, dirs, files in os.walk(self.root, followlinks=False):
            dirs.sort();files.sort()
            for name in dirs + files:
                path = Path(current) / name
                if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():raise SiteError('PATH_INVALID')
                if name.startswith('.'):
                    if name in dirs:dirs.remove(name)
                    continue
                st = path.stat()
                if not stat.S_ISREG(st.st_mode) and not stat.S_ISDIR(st.st_mode):raise SiteError('PATH_INVALID')
                rel = path.relative_to(self.root).as_posix()
                if len(rel.split('/')) > 16:raise SiteError('SITE_TOO_MANY_FILES')
                kind = 'directory' if path.is_dir() else 'file'
                size = st.st_size if kind == 'file' else 0
                total += size
                digest.update(json.dumps([rel, kind, size, st.st_mtime_ns, st.st_ino], ensure_ascii=True).encode())
                try:self.path(rel, directory=kind == 'directory')
                except SiteError:
                    continue  # Unmanaged extensions still count towards byte quota.
                entries.append({'path': rel, 'kind': kind, 'bytes': size,
                                'editable': kind == 'file' and path.suffix.lower() in TEXT and size <= TEXT_LIMIT})
                if len(entries) > ENTRY_LIMIT:raise SiteError('SITE_TOO_MANY_FILES')
        return {'entries': entries, 'bytes': total, 'revision': digest.hexdigest(),
                'recovery_required': bool(self.pending()),
                'limits': {'file': UPLOAD_LIMIT, 'zip': ZIP_LIMIT, 'site': SITE_LIMIT,
                           'text': TEXT_LIMIT, 'entries': ENTRY_LIMIT}}

    def check_revision(self, expected):
        listing = self.listing()
        if listing['recovery_required']:raise SiteError('ZIP_RECOVERY_REQUIRED')
        if not isinstance(expected, str) or expected != listing['revision']:raise SiteError('FILE_CHANGED')
        return listing

    @staticmethod
    def hash_file(path):
        if not path.exists():return None
        if not path.is_file():raise SiteError('PATH_INVALID')
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(CHUNK), b''):digest.update(chunk)
        return digest.hexdigest()

    def read_text(self, name):
        path = self.path(name)
        if not path.is_file():raise SiteError('FILE_NOT_FOUND')
        if path.suffix.lower() not in TEXT or path.stat().st_size > TEXT_LIMIT:raise SiteError('TEXT_NOT_EDITABLE')
        with path.open('rb') as source:data = source.read(TEXT_LIMIT + 1)
        if len(data) > TEXT_LIMIT:raise SiteError('TEXT_NOT_EDITABLE')
        try:text = data.decode('utf-8')
        except UnicodeError:raise SiteError('TEXT_NOT_EDITABLE') from None
        return {'path': name, 'text': text, 'etag': hashlib.sha256(data).hexdigest()}

    def room(self, amount):
        if shutil.disk_usage(self.root).free < amount + FREE_RESERVE:raise SiteError('DISK_SPACE_LOW')

    @staticmethod
    def sync_directory(path):
        if os.name == 'nt':return
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)

    @contextmanager
    def workspace(self):
        if self.private.is_symlink():raise SiteError('SITE_UNAVAILABLE')
        self.private.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.private, 0o700)
        work = Path(tempfile.mkdtemp(prefix='operation-', dir=self.private))
        self.sync_directory(self.private)
        try:yield work
        finally:
            # A durable journal marks a publication that has not committed or
            # rolled back. Keep its originals even if the process is interrupted.
            if not (work / 'journal.json').exists():shutil.rmtree(work)

    def pending(self):
        if not self.private.exists():return []
        pending = []
        for path in sorted(self.private.glob('operation-*/journal.json')):
            try:
                if path.is_symlink() or path.parent.is_symlink() or path.stat().st_size > 2 * MIB:raise ValueError()
                value = json.loads(path.read_text(encoding='utf-8'))
                if value.get('root') == str(self.root):pending.append(path.parent)
            except (OSError, ValueError, TypeError, AttributeError):
                # Corrupt recovery material must never be silently discarded.
                pending.append(path.parent)
        return pending

    def restore(self, work):
        journal = work / 'journal.json'
        try:
            value = json.loads(journal.read_text(encoding='utf-8'))
            if (set(value) != {'version', 'root', 'files', 'directories'} or value['version'] != 1
                    or value['root'] != str(self.root) or not isinstance(value['files'], list)
                    or not isinstance(value['directories'], list)
                    or len(value['files']) > ENTRY_LIMIT or len(value['directories']) > ENTRY_LIMIT):
                raise ValueError()
            for entry in value['files']:
                if (set(entry) != {'path', 'index', 'before', 'after'} or type(entry['index']) is not int
                        or not 0 <= entry['index'] < ENTRY_LIMIT
                        or not re.fullmatch('[0-9a-f]{64}', entry['after'])
                        or (entry['before'] is not None and not re.fullmatch('[0-9a-f]{64}', entry['before']))):
                    raise ValueError()
                path = self.path(entry['path'])
                current = self.hash_file(path)
                if current not in (entry['before'], entry['after']):raise SiteError('ZIP_RECOVERY_CHANGED')
                backup = work / ('before-' + str(entry['index']))
                if entry['before'] is not None and (backup.is_symlink() or self.hash_file(backup) != entry['before']):
                    raise ValueError()
            for directory in value['directories']:self.path(directory, directory=True)
        except SiteError:raise
        except Exception:raise SiteError('ZIP_RECOVERY_INVALID') from None
        self.room(max(((work / ('before-' + str(e['index']))).stat().st_size for e in value['files']
                       if e['before'] is not None), default=0))
        for entry in value['files']:
            path = self.path(entry['path'])
            if self.hash_file(path) == entry['before']:continue
            if entry['before'] is None:path.unlink(missing_ok=True)
            else:self.replace(entry['path'], work / ('before-' + str(entry['index'])))
        for name in sorted(value['directories'], key=lambda s: len(s.split('/')), reverse=True):
            directory = self.path(name, directory=True)
            if directory.exists():directory.rmdir()
        journal.unlink()
        self.sync_directory(work)

    def recover(self):
        pending = self.pending()
        if len(pending) != 1:raise SiteError('ZIP_RECOVERY_INVALID')
        self.restore(pending[0])
        shutil.rmtree(pending[0])
        return self.listing()

    @staticmethod
    def stream(source, target, limit):
        total = 0
        with target.open('xb') as out:
            os.chmod(target, 0o600)
            while True:
                chunk = source.read(min(CHUNK, limit - total + 1))
                if not chunk:break
                total += len(chunk)
                if total > limit:raise SiteError('FILE_TOO_LARGE')
                out.write(chunk)
            out.flush();os.fsync(out.fileno())
        return total

    def replace(self, name, source):
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        self.path(name)
        fd, temporary = tempfile.mkstemp(prefix='.openstick-', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as out, Path(source).open('rb') as incoming:
                shutil.copyfileobj(incoming, out, CHUNK)
                out.flush();os.fsync(out.fileno())
            os.chmod(temporary, 0o644)
            os.replace(temporary, path)
            self.sync_directory(path.parent)
        finally:Path(temporary).unlink(missing_ok=True)

    def upload(self, name, stream, expected):
        listing = self.check_revision(expected)
        target = self.path(name)
        if target.exists() and not target.is_file():raise SiteError('PATH_INVALID')
        with self.workspace() as work:
            self.room(UPLOAD_LIMIT * 2)
            size = self.stream(stream, work / 'upload', UPLOAD_LIMIT)
            old_size = target.stat().st_size if target.exists() else 0
            if listing['bytes'] - old_size + size > SITE_LIMIT:raise SiteError('SITE_TOO_LARGE')
            self.room(size)
            # Account for new parent directories before any public write.
            parents = [p for p in target.parents if p != self.root and self.root in p.parents and not p.exists()]
            if len(listing['entries']) + len(parents) + (not target.exists()) > ENTRY_LIMIT:
                raise SiteError('SITE_TOO_MANY_FILES')
            self.replace(name, work / 'upload')
        return self.listing()

    def put(self, name, text, expected, revision):
        self.check_revision(revision)
        path = self.path(name)
        if path.suffix.lower() not in TEXT or not isinstance(text, str):raise SiteError('INPUT_INVALID')
        data = text.encode('utf-8')
        if len(data) > TEXT_LIMIT:raise SiteError('FILE_TOO_LARGE')
        if expected != self.hash_file(path):raise SiteError('FILE_CHANGED')
        return self.upload(name, io.BytesIO(data), revision)

    def mutate(self, action, name, revision, target=None):
        before = self.check_revision(revision)
        path = self.path(name, directory=True)
        if action == 'mkdir':
            if path.exists():raise SiteError('PATH_EXISTS')
            missing = sum(not p.exists() for p in (path, *path.parents) if p == self.root or self.root in p.parents)
            if len(before['entries']) + missing > ENTRY_LIMIT:raise SiteError('SITE_TOO_MANY_FILES')
            path.mkdir(parents=True, mode=0o755)
        else:
            if not path.exists():raise SiteError('FILE_NOT_FOUND')
            if not path.is_dir():self.path(name)
            if action == 'delete':
                if path.is_dir():shutil.rmtree(path)
                else:path.unlink()
            elif action in ('move', 'copy'):
                destination = self.path(target, directory=path.is_dir())
                if not path.is_dir():self.path(name)
                if destination.exists():raise SiteError('PATH_EXISTS')
                if destination.is_relative_to(path):raise SiteError('PATH_INVALID')
                # Verify the entire translated subtree before mkdir/copy/move.
                subtree = [e for e in before['entries'] if e['path'] == name or e['path'].startswith(name + '/')]
                if path.is_dir():
                    actual = [p for p in path.rglob('*')]
                    if len(actual) + 1 != len(subtree):raise SiteError('UNMANAGED_FILES')
                for entry in subtree:
                    self.path(target + entry['path'][len(name):], directory=entry['kind'] == 'directory')
                parent_count = sum(not p.exists() for p in destination.parents if self.root in p.parents)
                if len(before['entries']) + parent_count + (len(subtree) if action == 'copy' else 0) > ENTRY_LIMIT:
                    raise SiteError('SITE_TOO_MANY_FILES')
                if action == 'copy':
                    size = sum(e['bytes'] for e in subtree)
                    if before['bytes'] + size > SITE_LIMIT:raise SiteError('SITE_TOO_LARGE')
                    self.room(size)
                destination.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                if action == 'move':os.rename(path, destination)
                else:
                    try:
                        if path.is_dir():shutil.copytree(path, destination)
                        else:shutil.copyfile(path, destination)
                    except Exception:
                        if destination.is_dir():shutil.rmtree(destination)
                        else:destination.unlink(missing_ok=True)
                        raise
            else:raise SiteError('INPUT_INVALID')
        return self.listing()

    def archive(self, name, output):
        self.listing()  # Refuse symlinks/special files before walking a subtree.
        path = self.path(name, directory=True, root=True)
        if not path.is_dir():raise SiteError('PATH_INVALID')
        self.room(SITE_LIMIT)
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
            for file in sorted(path.rglob('*')):
                rel = file.relative_to(path).as_posix()
                if file.is_dir():
                    self.path(file.relative_to(self.root).as_posix(), directory=True)
                    archive.writestr(rel + '/', b'')
                elif file.is_file():
                    self.path(file.relative_to(self.root).as_posix())
                    archive.write(file, rel)

    def inspect_zip(self, archive, destination, work):
        listing = self.listing()
        self.path(destination, directory=True, root=True)
        if destination and not self.path(destination, directory=True).is_dir():raise SiteError('PATH_INVALID')
        archive.seek(0, 2)
        archive_size = archive.tell()
        if archive_size > ZIP_LIMIT:raise SiteError('ZIP_TOO_LARGE')
        # Bound central-directory metadata before ZipFile builds its in-memory
        # member list. A tiny-content ZIP can otherwise exhaust the USB's RAM.
        archive.seek(max(0, archive_size - 65557))
        tail = archive.read(65557)
        offset = tail.rfind(b'PK\x05\x06')
        if offset < 0 or len(tail) - offset < 22:raise SiteError('ZIP_INVALID')
        _, disk, start_disk, disk_count, count, central_size, central_offset, comment = struct.unpack(
            '<4s4H2LH', tail[offset:offset + 22])
        if (disk or start_disk or disk_count != count or not 1 <= count <= ENTRY_LIMIT
                or central_size > 4 * MIB or central_offset == 0xffffffff
                or central_offset + central_size > archive_size - len(tail) + offset
                or len(tail) - offset != 22 + comment):
            raise SiteError('ZIP_INVALID')
        archive.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: archive.read(CHUNK), b''):digest.update(chunk)
        archive.seek(0)
        entries, names, total, old_bytes = [], set(), 0, 0
        with zipfile.ZipFile(archive) as package:
            infos = package.infolist()
            if not infos or len(infos) > ENTRY_LIMIT:raise SiteError('ZIP_INVALID')
            required = set(e['path'] for e in listing['entries'])
            existing = {e['path'].casefold(): e['path'] for e in listing['entries']}
            canonical = dict(existing)
            for index, info in enumerate(infos):
                name = info.filename.rstrip('/') if info.is_dir() else info.filename
                if info.orig_filename != info.filename or info.flag_bits & 1:raise SiteError('ZIP_INVALID')
                mode = info.external_attr >> 16
                if stat.S_IFMT(mode) not in (0, stat.S_IFDIR if info.is_dir() else stat.S_IFREG):raise SiteError('ZIP_INVALID')
                if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):raise SiteError('ZIP_INVALID')
                rel = (destination + '/' if destination else '') + name
                path = self.path(rel, directory=info.is_dir())
                if rel.casefold() in names:raise SiteError('ZIP_DUPLICATE')
                if rel.casefold() in existing and existing[rel.casefold()] != rel:raise SiteError('ZIP_DUPLICATE')
                names.add(rel.casefold())
                for item in (Path(rel), *Path(rel).parents):
                    component = item.as_posix()
                    if component == '.':continue
                    if component.casefold() in canonical and canonical[component.casefold()] != component:
                        raise SiteError('ZIP_DUPLICATE')
                    canonical[component.casefold()] = component
                    required.add(component)
                required.add(rel)
                if len(required) > ENTRY_LIMIT:raise SiteError('SITE_TOO_MANY_FILES')
                if path.exists() and path.is_dir() != info.is_dir():raise SiteError('PATH_EXISTS')
                if info.is_dir():
                    entries.append({'path': rel, 'kind': 'directory', 'bytes': 0, 'overwrite': path.exists(), 'index': index})
                    continue
                if info.file_size > UPLOAD_LIMIT:raise SiteError('FILE_TOO_LARGE')
                total += info.file_size
                if total > SITE_LIMIT:raise SiteError('SITE_TOO_LARGE')
                old_bytes += path.stat().st_size if path.exists() else 0
                staged = work / str(index)
                self.room(info.file_size)
                with package.open(info) as source:
                    count = self.stream(source, staged, UPLOAD_LIMIT)
                if count != info.file_size:raise SiteError('ZIP_INVALID')
                entries.append({'path': rel, 'kind': 'file', 'bytes': count,
                                'overwrite': path.exists(), 'index': index})
        if listing['bytes'] - old_bytes + total > SITE_LIMIT:raise SiteError('SITE_TOO_LARGE')
        # Detect file/descendant collisions even when ZIP order puts the child first.
        files = {e['path'].casefold() for e in entries if e['kind'] == 'file'}
        if any(p.as_posix().casefold() in files for e in entries for p in Path(e['path']).parents):
            raise SiteError('ZIP_INVALID')
        return {'files': entries, 'bytes': total, 'revision': listing['revision'], 'digest': digest.hexdigest()}

    def unzip(self, archive, destination, *, publish=False, expected=None, digest=None):
        if self.pending():raise SiteError('ZIP_RECOVERY_REQUIRED')
        with self.workspace() as work:
            preview = self.inspect_zip(archive, destination, work)
            if not publish:
                return {**preview, 'files': [{k: v for k, v in e.items() if k != 'index'} for e in preview['files']]}
            if expected != preview['revision'] or digest != preview['digest']:raise SiteError('FILE_CHANGED')
            files = [e for e in preview['files'] if e['kind'] == 'file']
            self.room(preview['bytes'] * 2)
            # Back up all overwritten bytes before the first public mutation.
            backups = {}
            self.room(sum(self.path(e['path']).stat().st_size for e in files if self.path(e['path']).exists()) + preview['bytes'])
            for entry in files:
                path = self.path(entry['path'])
                if path.exists():
                    backup = work / ('before-' + str(entry['index']))
                    shutil.copyfile(path, backup)
                    with backup.open('r+b') as original:original.flush();os.fsync(original.fileno())
                    backups[entry['path']] = backup
            directories = set()
            for entry in preview['files']:
                path = self.path(entry['path'], directory=entry['kind'] == 'directory')
                required = path if entry['kind'] == 'directory' else path.parent
                directories.update(p.relative_to(self.root).as_posix() for p in (required, *required.parents)
                                   if p != self.root and self.root in p.parents and not p.exists())
            journal = {'version': 1, 'root': str(self.root), 'directories': sorted(directories),
                       'files': [{'path': e['path'], 'index': e['index'],
                                  'before': self.hash_file(backups[e['path']]) if e['path'] in backups else None,
                                  'after': self.hash_file(work / str(e['index']))} for e in files]}
            with (work / 'journal.json').open('x', encoding='utf-8') as output:
                os.chmod(work / 'journal.json', 0o600)
                json.dump(journal, output);output.flush();os.fsync(output.fileno())
            self.sync_directory(work)
            try:
                for entry in preview['files']:
                    path = self.path(entry['path'], directory=entry['kind'] == 'directory')
                    required = path if entry['kind'] == 'directory' else path.parent
                    missing = [p for p in (required, *required.parents) if p != self.root and self.root in p.parents and not p.exists()]
                    for directory in reversed(missing):directory.mkdir(mode=0o755)
                    if entry['kind'] == 'file':
                        self.replace(entry['path'], work / str(entry['index']))
            except Exception:
                try:
                    self.restore(work)
                except Exception:
                    raise SiteError('ZIP_ROLLBACK_FAILED') from None
                raise SiteError('ZIP_PUBLISH_FAILED') from None
            (work / 'journal.json').unlink()
            self.sync_directory(work)
            return {**self.listing(), 'published': len(files)}

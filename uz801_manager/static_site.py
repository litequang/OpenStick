"""Small static-file editor, confined to the public website directory."""
import base64
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import tempfile
import threading

from flask import jsonify, render_template, request

TEXT = {'.html', '.htm', '.css', '.js', '.mjs', '.json', '.txt', '.md', '.xml', '.svg', '.map'}
ASSETS = TEXT | {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.avif', '.woff', '.woff2', '.ttf', '.otf'}
FILE_LIMIT = 1048576
SITE_LIMIT = 64 * 1048576


class SiteError(Exception):
    pass


class StaticSite:
    def __init__(self, directory='/var/www/openstick', lock_path='/var/lib/openstick/site.lock'):
        self.directory = Path(directory).absolute()
        self.lock_path = Path(lock_path) if lock_path else None
        self.lock = threading.Lock()

    @contextmanager
    def transaction(self):
        with self.lock:
            if self.lock_path is None:
                yield
                return
            import fcntl
            self.lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                yield
            finally:
                os.close(fd)

    def path(self, name):
        if (not isinstance(name, str) or len(name) > 240 or not 1 <= len(name.split('/')) <= 6
                or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', part)
                       for part in name.split('/')) or Path(name).suffix.lower() not in ASSETS):
            raise SiteError('PATH_INVALID')
        path = self.directory
        for part in (None, *name.split('/')):
            if part is not None:path = path / part
            if path.is_symlink():raise SiteError('PATH_INVALID')
        if not path.resolve().is_relative_to(self.directory.resolve()):raise SiteError('PATH_INVALID')
        return path

    def listing(self):
        if self.directory.is_symlink() or not self.directory.is_dir():raise SiteError('SITE_UNAVAILABLE')
        files, total = [], 0
        # Do not follow symlinks, or enumerate anything outside the public root.
        for root, dirs, names in os.walk(self.directory, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(root) / d).is_symlink() and not d.startswith('.')]
            if len(Path(root).relative_to(self.directory).parts) >= 5:dirs[:] = []
            for name in names:
                path = Path(root) / name
                if path.is_symlink() or not path.is_file():continue
                total += path.stat().st_size
                if len(files) >= 500:raise SiteError('SITE_TOO_MANY_FILES')
                try:self.path(path.relative_to(self.directory).as_posix())
                except SiteError:continue
                files.append({'path': path.relative_to(self.directory).as_posix(), 'bytes': path.stat().st_size,
                              'editable': path.suffix.lower() in TEXT})
        return {'files': sorted(files, key=lambda item: item['path']), 'bytes': total, 'limit_bytes': SITE_LIMIT}

    @staticmethod
    def read(path):
        try:
            if not path.is_file():return None
            with path.open('rb') as source:data = source.read(FILE_LIMIT + 1)
            if len(data) > FILE_LIMIT:raise SiteError('FILE_TOO_LARGE')
            return data
        except OSError:raise SiteError('SITE_UNAVAILABLE') from None

    @staticmethod
    def etag(data):
        return hashlib.sha256(data).hexdigest() if data is not None else None

    def call(self, value):
        if not isinstance(value, dict):raise SiteError('INPUT_INVALID')
        action = value.get('action')
        fields = {'list': {'action'}, 'get': {'action', 'path'},
                  'put': {'action', 'path', 'text', 'expected', 'confirm'},
                  'upload': {'action', 'path', 'base64', 'expected', 'confirm'},
                  'delete': {'action', 'path', 'expected', 'confirm'}}
        if action not in fields or set(value) != fields[action]:raise SiteError('INPUT_INVALID')
        with self.transaction():
            if action == 'list':return self.listing()
            path = self.path(value['path'])
            old = self.read(path)
            if action == 'get':
                if old is None:raise SiteError('FILE_NOT_FOUND')
                text = None
                if path.suffix.lower() in TEXT:
                    try:text = old.decode('utf-8')
                    except UnicodeError:pass
                return {'path': value['path'], 'text': text, 'etag': self.etag(old), 'bytes': len(old)}
            if value['confirm'] is not True:raise SiteError('CONFIRM_REQUIRED')
            expected = value['expected']
            if expected is not None and (not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
                raise SiteError('INPUT_INVALID')
            if expected != self.etag(old):raise SiteError('FILE_CHANGED')
            if action == 'delete':
                if old is None:raise SiteError('FILE_NOT_FOUND')
                path.unlink()
                return {'deleted': True}
            if action == 'put':
                if path.suffix.lower() not in TEXT or not isinstance(value['text'], str):raise SiteError('INPUT_INVALID')
                data = value['text'].encode('utf-8')
            else:
                if not isinstance(value['base64'], str) or len(value['base64']) > 1398104:raise SiteError('FILE_TOO_LARGE')
                try:data = base64.b64decode(value['base64'], validate=True)
                except ValueError:raise SiteError('INPUT_INVALID') from None
            if len(data) > FILE_LIMIT:raise SiteError('FILE_TOO_LARGE')
            listing = self.listing()
            if listing['bytes'] - len(old or b'') + len(data) > SITE_LIMIT:raise SiteError('SITE_TOO_LARGE')
            if old is None and len(listing['files']) >= 500:raise SiteError('SITE_TOO_MANY_FILES')
            path.parent.mkdir(parents=True, exist_ok=True)
            # Resolve/check again after creating directories, before replacing.
            self.path(value['path'])
            fd, temporary = tempfile.mkstemp(prefix='.openstick-', dir=path.parent)
            try:
                with os.fdopen(fd, 'wb') as output:
                    output.write(data)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(temporary, 0o644)
                os.replace(temporary, path)
            finally:
                Path(temporary).unlink(missing_ok=True)
            return {'saved': True, 'etag': self.etag(data), 'bytes': len(data)}


def register_site_routes(app, backend, token, hostname):
    @app.get('/website')
    def website():
        return render_template('website.html', token=token, page='wifi', hostname=hostname)

    @app.post('/api/site')
    def site():
        value = request.get_json(silent=True)
        try:
            return jsonify(backend.call(value))
        except SiteError as error:
            code = str(error)
            return jsonify(error=code), 409 if code == 'FILE_CHANGED' else 400
        except Exception:
            return jsonify(error='SITE_OPERATION_FAILED'), 500
        finally:
            if isinstance(value, dict):value.clear()

"""Private multi-site registry and authenticated static-web file manager."""
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
import zipfile

from flask import jsonify, request, send_file
from werkzeug.exceptions import HTTPException

from .site_domains import DomainPublisher
from .site_files import SiteFiles, UPLOAD_LIMIT, ZIP_LIMIT, SITE_LIMIT, ENTRY_LIMIT
from .static_site import SiteError, StaticSite

MAX_SITES = 8


def domains(value):
    if not isinstance(value, list) or len(value) > 10:raise SiteError('DOMAIN_INVALID')
    result = []
    for name in value:
        if not isinstance(name, str):raise SiteError('DOMAIN_INVALID')
        name = name.strip().lower().rstrip('.')
        if (len(name) > 253 or not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}', name)
                or name.endswith(('.local', '.localhost', '.internal', '.invalid'))):
            raise SiteError('DOMAIN_INVALID')
        if name in result:raise SiteError('DOMAIN_DUPLICATE')
        result.append(name)
    return result


class WebsitePanel:
    def __init__(self, default, hostname, *, directory=None, roots=None, publisher=None):
        self.default, self.hostname = default, hostname
        base = default.lock_path.parent if default.lock_path else default.directory.parent
        self.directory = Path(directory) if directory else base / 'web-panel'
        self.roots = Path(roots) if roots else default.directory.parent / 'openstick-sites'
        self.publisher = publisher or DomainPublisher()

    def read(self):
        path = self.directory / 'sites.json'
        if self.directory.is_symlink() or path.is_symlink():raise SiteError('REGISTRY_INVALID')
        if not path.exists():
            return [{'id': 'main', 'name': 'Website hiện tại', 'domains': [self.hostname]}]
        try:
            if path.stat().st_size > 32768:raise ValueError()
            value = json.loads(path.read_text(encoding='utf-8'))
            if set(value) != {'version', 'sites'} or value['version'] != 1:raise ValueError()
            sites = value['sites']
            if not isinstance(sites, list) or not 1 <= len(sites) <= MAX_SITES:raise ValueError()
            ids, names = set(), set()
            for site in sites:
                if set(site) != {'id', 'name', 'domains'}:raise ValueError()
                identity = site['id']
                if identity != 'main' and str(uuid.UUID(identity)) != identity:raise ValueError()
                self.validate_name(site['name'])
                if identity in ids:raise ValueError()
                ids.add(identity)
                requested = site['domains']
                # The configured legacy hostname can be example.invalid in demos.
                if identity == 'main' and self.hostname.endswith('.invalid'):
                    normalized = [self.hostname] + domains([d for d in requested if d != self.hostname])
                else:normalized = domains(requested)
                if normalized != site['domains'] or any(d in names for d in normalized):raise ValueError()
                names.update(normalized)
            if sites[0]['id'] != 'main' or self.hostname not in sites[0]['domains']:raise ValueError()
            return sites
        except (OSError, ValueError, TypeError, KeyError, SiteError):raise SiteError('REGISTRY_INVALID') from None

    @staticmethod
    def validate_name(name):
        if (not isinstance(name, str) or not name.strip() or len(name) > 60
                or any(ord(c) < 32 or ord(c) == 127 for c in name)):
            raise SiteError('SITE_NAME_INVALID')

    def write(self, sites):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        fd, name = tempfile.mkstemp(prefix='.sites-', dir=self.directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump({'version': 1, 'sites': sites}, out, ensure_ascii=False)
                out.flush();os.fsync(out.fileno())
            os.replace(name, self.directory / 'sites.json')
        finally:Path(name).unlink(missing_ok=True)

    @staticmethod
    def revision(sites):
        import hashlib
        return hashlib.sha256(json.dumps(sites, sort_keys=True, ensure_ascii=True).encode()).hexdigest()

    def root(self, site):
        if site['id'] == 'main':return self.default.directory
        if self.roots.is_symlink():raise SiteError('PATH_INVALID')
        return self.roots / site['id']

    def files(self, site):
        return SiteFiles(self.root(site), self.directory / 'work')

    def public(self, sites):
        inventory = []
        for site in sites:
            listing = self.files(site).listing()
            inventory.append({**site, 'bytes': listing['bytes'], 'entries': len(listing['entries']),
                              'protected': site['id'] == 'main'})
        mapped = [{**site, 'root': self.root(site)} for site in sites]
        return {'sites': inventory, 'revision': self.revision(sites), 'max_sites': MAX_SITES,
                'routing': self.publisher.state(mapped, self.hostname),
                'limits': {'file': UPLOAD_LIMIT, 'zip': ZIP_LIMIT, 'site': SITE_LIMIT, 'entries': ENTRY_LIMIT}}

    def select(self, sites, identity):
        if not isinstance(identity, str):raise SiteError('SITE_NOT_FOUND')
        site = next((s for s in sites if s['id'] == identity), None)
        if site is None:raise SiteError('SITE_NOT_FOUND')
        return site

    def call(self, value):
        if not isinstance(value, dict):raise SiteError('INPUT_INVALID')
        action = value.get('action')
        fields = {'sites': {'action'}, 'create': {'action', 'name', 'domains', 'expected', 'confirm'},
                  'configure': {'action', 'site', 'name', 'domains', 'expected', 'confirm'},
                  'publish_domains': {'action', 'expected', 'confirm'},
                  'list': {'action', 'site'}, 'get': {'action', 'site', 'path'},
                  'recover_zip': {'action', 'site', 'confirm'},
                  'put': {'action', 'site', 'path', 'text', 'expected', 'revision', 'confirm'},
                  'mkdir': {'action', 'site', 'path', 'revision', 'confirm'},
                  'delete': {'action', 'site', 'path', 'revision', 'confirm'},
                  'move': {'action', 'site', 'path', 'target', 'revision', 'confirm'},
                  'copy': {'action', 'site', 'path', 'target', 'revision', 'confirm'}}
        if action not in fields or set(value) != fields[action]:raise SiteError('INPUT_INVALID')
        if action not in ('sites', 'list', 'get') and value.get('confirm') is not True:
            raise SiteError('CONFIRM_REQUIRED')
        with self.default.transaction():
            sites = self.read()
            if action == 'sites':return self.public(sites)
            if action in ('create', 'configure', 'publish_domains'):
                if value['expected'] != self.revision(sites):raise SiteError('FILE_CHANGED')
                if action == 'publish_domains':
                    mapped = [{**s, 'root': self.root(s)} for s in sites]
                    result = self.publisher.apply(mapped, self.hostname, self.directory / 'domain-backups')
                    return {**self.public(sites), 'applied': result}
                self.validate_name(value['name'])
                requested = value['domains']
                if action == 'configure' and value['site'] == 'main' and self.hostname.endswith('.invalid'):
                    new_domains = [self.hostname] + domains([d for d in requested if d != self.hostname])
                else:new_domains = domains(requested)
                site = self.select(sites, value['site']) if action == 'configure' else None
                if site and site['id'] == 'main' and self.hostname not in new_domains:raise SiteError('PRIMARY_DOMAIN_PROTECTED')
                used = {d for s in sites if s is not site for d in s['domains']}
                if any(d in used for d in new_domains):raise SiteError('DOMAIN_DUPLICATE')
                if action == 'create':
                    if len(sites) >= MAX_SITES:raise SiteError('SITE_LIMIT')
                    site = {'id': str(uuid.uuid4()), 'name': value['name'].strip(), 'domains': new_domains}
                    self.roots.mkdir(parents=True, exist_ok=True, mode=0o755)
                    root = self.root(site);root.mkdir(mode=0o755)
                    sites.append(site)
                    try:self.write(sites)
                    except Exception:root.rmdir();raise
                else:
                    site.update(name=value['name'].strip(), domains=new_domains);self.write(sites)
                return {**self.public(sites), 'selected': site['id']}
            site = self.select(sites, value['site'])
            files = self.files(site)
            if action == 'list':return files.listing()
            if action == 'get':return files.read_text(value['path'])
            if action == 'recover_zip':return files.recover()
            if action == 'put':return files.put(value['path'], value['text'], value['expected'], value['revision'])
            return files.mutate(action, value['path'], value['revision'], value.get('target'))


def register_panel_routes(app, panel):
    def failure(error):
        code = str(error)
        details = {'entry': error.entry} if hasattr(error, 'entry') else {}
        return jsonify(error=code, **details), 409 if code in ('FILE_CHANGED', 'PATH_EXISTS') else 400

    @app.post('/api/websites')
    def websites():
        value = request.get_json(silent=True)
        try:return jsonify(panel.call(value))
        except SiteError as error:return failure(error)
        except HTTPException:raise
        except Exception:return jsonify(error='SITE_OPERATION_FAILED'), 500
        finally:
            if isinstance(value, dict):value.clear()

    @app.post('/api/websites/transfer')
    def transfer():
        try:
            form = request.form
            if (len(request.files) != 1 or len(request.files.getlist('file')) != 1
                    or any(len(v) != 1 for v in form.to_dict(flat=False).values())):
                raise SiteError('INPUT_INVALID')
            action = form.get('action')
            expected_fields = {'action', 'site', 'path', 'revision', 'confirm'} if action == 'upload' else (
                {'action', 'site', 'path'} if action == 'inspect_zip' else
                {'action', 'site', 'path', 'revision', 'digest', 'confirm'})
            if action not in ('upload', 'inspect_zip', 'unzip') or set(form) != expected_fields:
                raise SiteError('INPUT_INVALID')
            if action != 'inspect_zip' and form.get('confirm') != 'true':raise SiteError('CONFIRM_REQUIRED')
            with panel.default.transaction():
                files = panel.files(panel.select(panel.read(), form['site']))
                stream = request.files['file'].stream
                if action == 'upload':return jsonify(files.upload(form['path'], stream, form['revision']))
                result = files.unzip(stream, form['path'], publish=action == 'unzip',
                                     expected=form.get('revision'), digest=form.get('digest'))
                return jsonify(result)
        except SiteError as error:return failure(error)
        except HTTPException:raise
        except (zipfile.BadZipFile, RuntimeError, EOFError, ValueError):return jsonify(error='ZIP_INVALID'), 400
        except Exception:return jsonify(error='SITE_OPERATION_FAILED'), 500

    @app.post('/api/websites/download')
    def download():
        value = request.get_json(silent=True)
        stream = None
        try:
            if (not isinstance(value, dict) or set(value) != {'site', 'path', 'revision'}):raise SiteError('INPUT_INVALID')
            with panel.default.transaction():
                files = panel.files(panel.select(panel.read(), value['site']))
                files.check_revision(value['revision'])
                path = files.path(value['path'], directory=True, root=True)
                if path.is_dir():
                    files.private.mkdir(parents=True, exist_ok=True, mode=0o700)
                    stream = tempfile.TemporaryFile(dir=files.private)
                    files.archive(value['path'], stream);stream.seek(0)
                    name = (path.name if value['path'] else 'website') + '.zip'
                else:
                    files.path(value['path'])
                    stream = path.open('rb');name = path.name
            response = send_file(stream, as_attachment=True, download_name=name, mimetype='application/octet-stream')
            response.call_on_close(stream.close)
            return response
        except SiteError as error:
            if stream:stream.close()
            return failure(error)
        except Exception:
            if stream:stream.close()
            return jsonify(error='SITE_OPERATION_FAILED'), 500

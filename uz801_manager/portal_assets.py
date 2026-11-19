"""Versioned public package assets only; private responses remain no-store."""
import hashlib
from pathlib import Path
import re
from urllib.parse import quote

from flask import g, request


def filegator_versions(root):
    versions = {}
    for folder in ('js', 'css'):
        directory = Path(root)/folder
        if directory.is_symlink():continue
        for p in directory.glob('*'):
            if p.is_file() and not p.is_symlink() and p.suffix in ('.js','.css'):
                with p.open('rb') as source:version=hashlib.file_digest(source,'sha256').hexdigest()[:24]
                versions[folder+'/'+p.name]=version
    return versions


def version_filegator_html(data, versions):
    # Only known package JS/CSS references, never API URLs, cookies or owner files.
    def replace(match):
        name=match['name'].removeprefix('./')
        version=versions.get(name)
        return match[0] if not version else match['prefix']+match['name']+'?v='+version+match['quote']
    return re.sub(r'(?P<prefix>\b(?:src|href)=(?P<quote>["\x27]))(?P<name>(?:\./)?(?:js|css)/[A-Za-z0-9_.-]+)(?P=quote)',replace,data)


def install_assets(app):
    root = Path(app.static_folder)
    # Package is immutable during a running portal. Deploy restarts both portal
    # processes; hashes change only with bytes, not a timestamp or a private value.
    versions = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:24]
                for p in root.iterdir() if p.is_file() and not p.is_symlink()
                and p.suffix in ('.js', '.css')}

    def asset_url(name):
        version = versions.get(name)
        path = '/static/' + quote(name, safe='')
        return path + '?v=' + version if version else path

    app.jinja_env.globals['portal_asset'] = asset_url
    app.extensions['portal_asset_versions'] = versions


def public_asset_response(app, response):
    if (request.method not in ('GET', 'HEAD') or response.status_code not in (200, 304)
            or 'Set-Cookie' in response.headers):
        return False
    if request.endpoint == 'static':
        name = (request.view_args or {}).get('filename')
        version = app.extensions['portal_asset_versions'].get(name)
        return bool(version and request.args.to_dict(flat=False) == {'v': [version]}
                    and response.headers.get('Content-Disposition','inline').startswith('inline'))
    # The bridge sets this only after selecting/validating the root and checking
    # the installed package's fingerprinted asset path, never for an API/download.
    return (getattr(g, 'filegator_public_asset', False) and 'Content-Disposition' not in response.headers
            and response.mimetype in ('application/javascript','text/javascript','text/css',
                'font/woff','font/woff2','font/ttf','font/otf','application/font-woff',
                'application/vnd.ms-fontobject','image/svg+xml','image/png','image/jpeg',
                'image/gif','image/webp','image/x-icon','image/vnd.microsoft.icon'))


def fingerprinted_filegator_asset(asset):
    return bool(re.fullmatch(r'(?:css|js|fonts|img)/[A-Za-z0-9_/-]+\.[0-9a-f]{8,64}\.(?:js|css|woff2?|ttf|eot|svg|png|jpe?g|gif|webp|ico)', asset))

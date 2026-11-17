"""Install the pinned upstream bundle on postmarketOS. Run locally as root.

Usage: python3 install.py /path/to/filegator_v7.16.9.zip
The five integration files beside this script must accompany it. This installer
does not install portal source, publish site files, change domains, or reboot.
"""
import hashlib
import grp
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

VERSION = '7.16.9'
SHA256 = '304d979f646ec9db4e6a38452b796a269fa97016460aa3f8e458abc7bfe559e1'
CONFIGS = ['configuration.php', 'php-fpm.conf', 'nginx.conf',
           'openstick-filegator-php', 'openstick-filegator-http']
PACKAGES = ['php83-fpm', 'php83-session', 'php83-zip', 'php83-mbstring', 'php83-fileinfo',
            'php83-iconv', 'php83-ctype', 'php83-tokenizer', 'php83-dom', 'php83-openssl', 'acl']


def command(args):
    result = subprocess.run(args, capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError('INSTALL_COMMAND_FAILED:' + args[0])
    return result.stdout


def install(archive):
    if os.geteuid() != 0:
        raise RuntimeError('ROOT_REQUIRED')
    base, private = Path('/opt/openstick-filegator'), Path('/var/lib/openstick-filegator')
    if base.exists() or private.exists():
        raise RuntimeError('ALREADY_INSTALLED_OR_PARTIAL_INSTALL')
    if shutil.disk_usage('/var/lib').free < 256 * 1048576:
        raise RuntimeError('DISK_SPACE_LOW')
    for pending in Path('/var/lib/openstick/web-panel/work').glob('operation-*/journal.json'):
        raise RuntimeError('ZIP_RECOVERY_REQUIRED')
    archive = Path(archive)
    if archive.stat().st_size != 4136684 or hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise RuntimeError('ARCHIVE_HASH_MISMATCH')
    source = Path(__file__).resolve().parent
    for name in CONFIGS:
        if not (source / name).is_file():
            raise RuntimeError('INTEGRATION_FILE_MISSING')
    command(['apk', 'add', '--no-cache', *PACKAGES])
    try: group = grp.getgrnam('openstick-files')
    except KeyError:
        command(['addgroup', '-S', 'openstick-files'])
        group = grp.getgrnam('openstick-files')
    try: identity = pwd.getpwnam('openstick-files')
    except KeyError:
        command(['adduser', '-S', '-D', '-H', '-G', 'openstick-files', '-s', '/sbin/nologin', 'openstick-files'])
        identity = pwd.getpwnam('openstick-files')
    private.mkdir(mode=0o750)
    os.chown(private, 0, group.gr_gid)
    Path('/run/openstick-filegator').mkdir(mode=0o755, exist_ok=True)
    # Retain ACLs for manual uninstall. Never change existing owner/mode/content.
    roots = [Path('/var/www/openstick')]
    parent = Path('/var/www/openstick-sites')
    if not parent.exists():parent.mkdir(mode=0o755)
    roots += [p for p in parent.iterdir() if p.is_dir() and not p.is_symlink()]
    if any(p.is_symlink() for root in roots for p in [root, *root.rglob('*')]):
        raise RuntimeError('PUBLIC_SYMLINK_BLOCKED')
    acl = command(['getfacl', '-R', '-p', *map(str, roots), str(parent)])
    (private / 'before.acl').write_bytes(acl)
    for name in ['uploads', 'work', 'nginx', 'fastcgi', 'sandbox', 'logs']:
        path = private / name; path.mkdir(mode=0o700)
        os.chown(path, identity.pw_uid, group.gr_gid)
    (private / 'csrf-key').write_text(secrets.token_hex(32))
    (private / 'users.json').write_text(json.dumps({'1': {'username': 'guest', 'name': 'OpenStick',
        'role': 'guest', 'homedir': '/', 'permissions': 'read|write|upload|download|batchdownload|zip', 'password': ''}}))
    for name in ['csrf-key', 'users.json']:
        os.chown(private / name, 0, group.gr_gid);os.chmod(private / name, 0o640)
    with tempfile.TemporaryDirectory(prefix='filegator-install-', dir='/opt') as staging:
        with zipfile.ZipFile(archive) as package:
            for item in package.infolist():
                path = Path(item.filename)
                mode = item.external_attr >> 16
                if path.is_absolute() or '..' in path.parts or stat.S_ISLNK(mode):
                    raise RuntimeError('ARCHIVE_PATH_INVALID')
            package.extractall(staging)
        shutil.move(str(Path(staging) / 'filegator'), base)
    integration = base / 'integration';integration.mkdir()
    for name in CONFIGS:shutil.copyfile(source / name, integration / name)
    shutil.copyfile(source / 'configuration.php', base / 'configuration.php')
    # Upstream index requires its log directory writable; only that subdirectory
    # is writable, not application/config/default-user files.
    log = base / 'private/logs'
    os.chown(log, identity.pw_uid, group.gr_gid)
    for root in roots:
        command(['setfacl', '-R', '-m', 'u:openstick-files:rwX', str(root)])
        for directory, dirs, files in os.walk(root, followlinks=False):
            command(['setfacl', '-m', 'd:u:openstick-files:rwx', directory])
    command(['setfacl', '-m', 'u:openstick-files:rx,d:u:openstick-files:rwx', str(parent)])
    for name in ['openstick-filegator-php', 'openstick-filegator-http']:
        target = Path('/etc/init.d') / name
        if target.exists():raise RuntimeError('SERVICE_ALREADY_EXISTS')
        shutil.copyfile(integration / name, target);target.chmod(0o755)
    command(['/usr/sbin/php-fpm83', '--test', '--fpm-config', str(integration / 'php-fpm.conf')])
    command(['/usr/sbin/nginx', '-t', '-c', str(integration / 'nginx.conf'), '-p', str(private)])
    for name in ['openstick-filegator-php', 'openstick-filegator-http']:
        command(['rc-service', name, 'start'])
    # Portal feature is opt-in only after a complete installation. A subsequent
    # health check enables boot persistence; an unsuccessful trial stays disabled.
    (base / 'installed.json').write_text(json.dumps({'version': VERSION, 'archive_sha256': SHA256}))
    return {'installed': VERSION, 'loopback_only': True, 'boot_enabled': False}


if __name__ == '__main__':
    try:print(json.dumps(install(sys.argv[1])))
    except Exception as error:
        print(json.dumps({'error': str(error) if isinstance(error, RuntimeError) else type(error).__name__}))
        sys.exit(1)

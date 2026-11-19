"""Bridge the upstream FileGator UI through the existing administration boundary.

The upstream HTTP listener is loopback-only, unprivileged and has no public
route through Nginx/Tunnel. Its guest account is trusted only behind this bridge.
FileGator retains its own per-site session and CSRF check; LAN authentication,
Host/Origin checks and logout/password rotation remain owned by OpenStick.
"""
from http.client import HTTPConnection
import json
from pathlib import Path
import re
import shutil
import subprocess

from flask import Response, jsonify, request, stream_with_context
from werkzeug.exceptions import HTTPException

from .static_site import SiteError

MARKER = Path('/opt/openstick-filegator/installed.json')
CHUNK_REQUEST_LIMIT = 2 * 1048576
FREE_RESERVE = 128 * 1048576
READ_ACTIONS = {'/', '/getconfig', '/getuser', '/getdir', '/changedir', '/download', '/batchdownload'}
ACTIONS = READ_ACTIONS | {'/upload', '/copyitems', '/moveitems', '/renameitem', '/zipitems',
                          '/unzipitem', '/deleteitems', '/createnew', '/savecontent'}
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; "
    "worker-src 'self' blob:; object-src 'none'; frame-ancestors 'self'; "
    "base-uri 'self'; form-action 'self'")


def installed():
    return MARKER.is_file() and not MARKER.is_symlink()


def provision_root(root):
    """Grant only the dedicated file manager identity access to a new public root."""
    if not installed():
        return
    result = subprocess.run(['setfacl', '-m', 'u:openstick-files:rwx,d:u:openstick-files:rwx', str(root)],
                            capture_output=True, timeout=10)
    if result.returncode:
        raise SiteError('FILEGATOR_PERMISSIONS_FAILED')


def register_filegator(app, panel, *, enabled=None, connection=HTTPConnection):
    available = installed if enabled is None else lambda: enabled

    @app.context_processor
    def filegator_context():
        return {'filegator_enabled': available()}

    @app.before_request
    def filegator_limits():
        if request.path.startswith('/files/'):
            request.max_content_length = CHUNK_REQUEST_LIMIT

    @app.route('/files/<site_id>/', defaults={'asset': ''}, methods=['GET', 'POST'])
    @app.route('/files/<site_id>/<path:asset>', methods=['GET', 'POST'])
    def filegator(site_id, asset):
        if not available():
            return jsonify(error='FILEGATOR_NOT_INSTALLED'), 503
        upstream = None
        try:
            action = request.args.get('r', '/')
            if (action not in ACTIONS or len(request.args.getlist('r')) > 1
                    or (asset and (request.method != 'GET' or not re.fullmatch(
                        r'(?:css|js|fonts|img)/[A-Za-z0-9_./-]+', asset)
                        or '..' in asset.split('/')))):
                raise SiteError('INPUT_INVALID')
            with panel.default.transaction():
                site = panel.select(panel.read(), site_id)
                files = panel.files(site)
                files._check_root()
                if files.pending():
                    raise SiteError('ZIP_RECOVERY_REQUIRED')
                if request.method == 'POST' and action not in READ_ACTIONS:
                    if shutil.disk_usage(files.root).free < FREE_RESERVE:
                        raise SiteError('DISK_SPACE_LOW')
                # Bound chunk data, not the complete selected file. No input
                # cookie/header can select the upstream server or website root.
                body = request.get_data(cache=False) if request.method == 'POST' else None
                headers = {'X-OpenStick-Root': str(files.root), 'X-OpenStick-Site': site_id,
                           'Content-Type': request.headers.get('Content-Type', 'application/json'),
                           'Cookie': '; '.join(f'{k}={v}' for k,v in request.cookies.items()
                                             if k == 'filegator'),
                           'X-CSRF-Token': request.headers.get('X-CSRF-Token', '')}
                upstream = connection('127.0.0.1', 8788, timeout=120)
                path = '/' + asset
                if request.query_string:
                    path += '?' + request.query_string.decode('ascii')
                unzip = request.method == 'POST' and action == '/unzipitem' and not asset
                if unzip:
                    try:value = json.loads(body)
                    except (ValueError, TypeError):raise SiteError('INPUT_INVALID') from None
                    if (not isinstance(value, dict) or set(value) != {'item', 'destination'}
                            or not all(isinstance(v, str) for v in value.values())):
                        raise SiteError('INPUT_INVALID')
                    # Reuse the upstream session/CSRF validation before touching
                    # the filesystem, then keep the proven ZIP journal/quotas.
                    path, body = '/?r=/getdir', b'{"dir":"/"}'
                upstream.request(request.method, path, body=body, headers=headers)
                reply = upstream.getresponse()
                outgoing = [(k,v) for k,v in reply.getheaders() if k.lower() in (
                    'content-type', 'content-disposition', 'x-csrf-token', 'set-cookie')]
                # Mutations finish under the same lock as the old editor and ZIP
                # recovery. Downloads are streamed with bounded memory below.
                if request.method == 'POST':
                    data = reply.read(2 * 1048576 + 1)
                    if len(data) > 2 * 1048576:
                        raise SiteError('FILEGATOR_RESPONSE_TOO_LARGE')
                    status = reply.status
                    upstream.close(); upstream = None
                    if unzip:
                        if status != 200 or not data or 'data' not in json.loads(data):
                            return jsonify(error='FILEGATOR_CSRF_REQUIRED'), 403
                        source = files.path(value['item'].lstrip('/'), directory=True)
                        if not source.is_file() or source.suffix.lower() != '.zip':
                            raise SiteError('ZIP_INVALID')
                        destination = value['destination'].strip('/')
                        with source.open('rb') as archive:
                            preview = files.unzip(archive, destination)
                            archive.seek(0)
                            files.unzip(archive, destination, publish=True,
                                        expected=preview['revision'], digest=preview['digest'])
                        return jsonify(data='Done')
                    return Response(data, status=status, headers=outgoing)

            def chunks():
                try:
                    while True:
                        data = reply.read(65536)
                        if not data:
                            break
                        yield data
                finally:
                    upstream.close()
            return Response(stream_with_context(chunks()), status=reply.status, headers=outgoing)
        except SiteError as error:
            if upstream:upstream.close()
            messages = {'DISK_SPACE_LOW':'USB thiếu dung lượng trống; cần giữ tối thiểu 128 MiB dự phòng.',
                        'SITE_TOO_LARGE':'Bộ mã sau giải nén vượt giới hạn website 256 MiB.',
                        'FILE_TOO_LARGE':'Một file sau giải nén vượt 32 MiB.',
                        'ZIP_RECOVERY_REQUIRED':'Có lần giải nén dở. Trở lại Website để khôi phục trước.',
                        'FILE_TYPE_BLOCKED':'ZIP có loại file không phù hợp website tĩnh.',
                        'PATH_INVALID':'Đường dẫn không hợp lệ.',
                        'SITE_TOO_MANY_FILES':'Bộ mã vượt 2.000 file và thư mục.',
                        'ZIP_INVALID':'ZIP lỗi, chứa đường dẫn hoặc liên kết không hợp lệ.'}
            return jsonify(error=str(error), data=messages.get(str(error),str(error))), 409 if str(error) == 'ZIP_RECOVERY_REQUIRED' else 400
        except HTTPException:
            if upstream:upstream.close()
            raise
        except Exception:
            if upstream:upstream.close()
            return jsonify(error='FILEGATOR_UNAVAILABLE'), 503
        except SiteError as error:
            if upstream: upstream.close()
            return jsonify(error=str(error)), 409 if str(error) == 'ZIP_RECOVERY_REQUIRED' else 400
        except (OSError, ValueError):
            if upstream: upstream.close()
            return jsonify(error='FILEGATOR_UNAVAILABLE'), 502

"""Opt-in LAN administration; credentials are configured only through USB."""
import json
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path

from flask import jsonify, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash


class LanSettings:
    def __init__(self, directory='/var/lib/openstick', address=lambda: None):
        self.directory = Path(directory)
        self.address = address

    def private(self):
        try:
            value = json.loads((self.directory / 'lan-admin.json').read_text())
            if (value.get('enabled') is True and isinstance(value.get('password_hash'), str)
                    and isinstance(value.get('secret_key'), str) and len(value['secret_key']) >= 32
                    and isinstance(value.get('version'), str)):
                return value
        except (OSError, ValueError, TypeError, AttributeError):
            pass
        return None

    def status(self):
        value, address = self.private(), self.address()
        return {'enabled': value is not None, 'url': 'http://' + address + ':8765' if address else None}

    def configure(self, password):
        if (not isinstance(password, str) or not 12 <= len(password) <= 128
                or any(ord(c) < 32 for c in password)):
            raise ValueError('PASSWORD_INVALID')
        value = {'enabled': True, 'password_hash': generate_password_hash(password, method='pbkdf2:sha256:600000'),
                 'secret_key': secrets.token_urlsafe(48), 'version': secrets.token_hex(16)}
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self.directory / 'lan-admin.tmp'
        with temporary.open('w') as output:
            os.chmod(temporary, 0o600)
            json.dump(value, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, self.directory / 'lan-admin.json')
        return self.status()

    def disable(self):
        path = self.directory / 'lan-admin.json'
        path.unlink(missing_ok=True)
        return self.status()


class LoginLimiter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.global_attempts = deque()
        self.attempts = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, address):
        with self.lock:
            now = self.clock()
            for key in list(self.attempts):
                queue = self.attempts[key]
                while queue and now - queue[0] >= 300:queue.popleft()
                if not queue:del self.attempts[key]
            while self.global_attempts and now - self.global_attempts[0] >= 60:self.global_attempts.popleft()
            if len(self.attempts) >= 128 and address not in self.attempts:return False
            queue = self.attempts[address]
            if len(queue) >= 5 or len(self.global_attempts) >= 20:return False
            queue.append(now)
            self.global_attempts.append(now)
            return True


def install_lan_auth(app, settings, limiter=None):
    configuration = settings.private()
    if not configuration:raise RuntimeError('LAN_NOT_CONFIGURED')
    app.secret_key = configuration['secret_key']
    app.config.update(SESSION_COOKIE_NAME='openstick_lan_session', SESSION_COOKIE_HTTPONLY=True,
                      SESSION_COOKIE_SAMESITE='Strict', SESSION_COOKIE_SECURE=False,
                      PERMANENT_SESSION_LIFETIME=timedelta(hours=8))
    limiter = limiter or LoginLimiter()

    def csrf():
        value = request.form.get('csrf', '')
        return isinstance(session.get('csrf'), str) and value.isascii() and secrets.compare_digest(
            value, session['csrf'])

    @app.before_request
    def authenticated():
        current = settings.private()
        if not current or current['secret_key'] != app.secret_key:
            session.clear()
            return jsonify(error='LAN_DISABLED_OR_CHANGED'), 403
        if request.path == '/login' or request.path.startswith('/static/'):
            return None
        if session.get('credential_version') != current['version']:
            session.clear()
            return (jsonify(error='LOGIN_REQUIRED'), 401) if request.path.startswith('/api/') else redirect('/login')

    @app.context_processor
    def login_context():
        return {'lan_session': True, 'logout_csrf': session.get('csrf', '')}

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        error = None
        if request.method == 'POST':
            if not csrf():return jsonify(error='FORBIDDEN'), 403
            if not limiter.allow(request.remote_addr or ''):
                return render_template('lan_login.html', csrf=session['csrf'], error='Thử quá nhiều lần. Vui lòng đợi rồi thử lại.'), 429
            password = request.form.get('password', '')
            current = settings.private()
            if len(password) <= 128 and current and check_password_hash(current['password_hash'], password):
                session.clear()
                session.permanent = True
                session.update(credential_version=current['version'], csrf=secrets.token_urlsafe(32))
                return redirect('/overview')
            error = 'Mật khẩu chưa đúng.'
        session.setdefault('csrf', secrets.token_urlsafe(32))
        return render_template('lan_login.html', csrf=session['csrf'], error=error)

    @app.post('/logout')
    def logout():
        if not csrf():return jsonify(error='FORBIDDEN'), 403
        session.clear()
        return redirect('/login')


def register_lan_settings(app, settings, token, changed=lambda: None):
    @app.post('/api/lan')
    def lan_configuration():
        value = request.get_json(silent=True)
        if not isinstance(value, dict):return jsonify(error='INPUT_INVALID'), 400
        action = value.get('action')
        expected = {'action', 'password', 'confirm'} if action == 'configure' else {'action', 'confirm'} if action == 'disable' else {'action'}
        if action not in ('status', 'configure', 'disable') or set(value) != expected:
            return jsonify(error='INPUT_INVALID'), 400
        if action != 'status' and value.get('confirm') is not True:return jsonify(error='CONFIRM_REQUIRED'), 400
        try:
            result = settings.configure(value['password']) if action == 'configure' else settings.disable() if action == 'disable' else settings.status()
            if action != 'status':changed()
            return jsonify(result)
        except ValueError:
            return jsonify(error='PASSWORD_INVALID'), 400
        except Exception:
            return jsonify(error='LAN_CONFIGURATION_FAILED'), 500
        finally:
            value.clear()

"""USB Wi-Fi setup for Linux. Separate from Android/firmware operations."""
import argparse
import html
import json
import os
import re
import secrets
import shlex
import subprocess
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, request
from waitress import serve


REMOTE = r'''
import hashlib,json,os,re,subprocess,sys,uuid
value=json.load(sys.stdin)
def run(args,timeout=15):
    p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError('NETWORK_OPERATION_FAILED')
    return p.stdout
def fields(line):
    out=[];part='';escaped=False
    for c in line:
        if escaped:part+=c;escaped=False
        elif c=='\\':escaped=True
        elif c==':':out.append(part);part=''
        else:part+=c
    return out+[part]
try:
    action=value['action']
    if action=='scan':
        output=run(['nmcli','-t','-e','yes','-f','SSID,SIGNAL,SECURITY','device','wifi','list','ifname','wlan0','--rescan','yes'])
        networks={}
        for line in output.splitlines():
            row=fields(line)
            if len(row)==3 and row[0] and row[1].isdigit():
                networks[row[0]]={'ssid':row[0][:32],'signal':int(row[1]),'security':row[2][:80]}
        result={'networks':sorted(networks.values(),key=lambda n:-n['signal'])[:100]}
    elif action=='status':
        state=run(['nmcli','-g','GENERAL.STATE,GENERAL.CONNECTION','device','show','wlan0']).strip().splitlines()
        result={'state':state[0][:80] if state else 'unknown','connection':state[1][:80] if len(state)>1 else ''}
    elif action=='connect':
        ssid,password=value['ssid'],value['password']
        assert isinstance(ssid,str) and 1<=len(ssid.encode())<=32
        assert isinstance(password,str) and 8<=len(password)<=63
        assert not any(ord(c)<32 for c in ssid+password)
        psk=hashlib.pbkdf2_hmac('sha1',password.encode(),ssid.encode(),4096,32).hex()
        escaped=ssid.replace('\\','\\\\').replace(';','\\;')
        profile='openstick-'+hashlib.sha256(ssid.encode()).hexdigest()[:16]
        target='/etc/NetworkManager/system-connections/'+profile+'.nmconnection'
        existing=''
        if os.path.isfile(target):
            with open(target) as f:existing=f.read(8192)
        match=re.search(r'^uuid=([0-9a-f-]{36})$',existing,re.M)
        identity=str(uuid.UUID(match[1])) if match else str(uuid.uuid4())
        data='[connection]\nid='+profile+'\nuuid='+identity+'\ntype=wifi\ninterface-name=wlan0\nautoconnect=true\nautoconnect-priority=10\n\n[wifi]\nmode=infrastructure\nssid='+escaped+'\n\n[wifi-security]\nkey-mgmt=wpa-psk\npsk='+psk+'\n\n[ipv4]\nmethod=auto\nroute-metric=100\n\n[ipv6]\nmethod=auto\nroute-metric=100\n'
        temp=target+'.tmp'
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
        run(['nmcli','connection','load',target])
        run(['nmcli','-w','35','connection','up','id',profile],40)
        result={'connected':True}
    else:raise RuntimeError('INPUT_INVALID')
    print(json.dumps(result))
except Exception:
    print(json.dumps({'error':'NETWORK_OPERATION_FAILED'}));sys.exit(1)
'''


class LinuxWifi:
    def __init__(self, private_dir, *, run=subprocess.run):
        self.directory = Path(private_dir).resolve()
        self.run = run

    def call(self, action, **values):
        args = ['ssh', '-F', 'NUL', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes',
                '-o', 'ConnectTimeout=5', '-o', 'UserKnownHostsFile=' + str(self.directory / 'pmos_known_hosts'),
                '-i', str(self.directory / 'manager_ed25519'), 'user@172.16.42.1',
                'sudo -n python3 -c ' + shlex.quote(REMOTE)]
        result = self.run(args, input=json.dumps({'action': action, **values}).encode(),
                          capture_output=True, timeout=50, shell=False,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode or len(result.stdout) > 65536:
            raise RuntimeError('USB_SSH_UNAVAILABLE')
        parsed = json.loads(result.stdout)
        if not isinstance(parsed, dict) or 'error' in parsed:
            raise RuntimeError('NETWORK_OPERATION_FAILED')
        return parsed


HTML = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenStick — Kết nối Wi-Fi</title><style>
*{box-sizing:border-box}body{margin:0;font:16px system-ui;background:#f2f6fa;color:#173047}main{max-width:740px;margin:5vh auto;padding:24px}section{background:white;padding:24px;border-radius:18px;box-shadow:0 8px 40px #17304710;margin:20px 0}h1{font-size:30px;margin-bottom:8px}p{line-height:1.6}.sub{color:#52677b}label{display:block;margin:18px 0 8px}input,select,button{font:inherit;padding:12px;border-radius:9px;border:1px solid #c9d5df}input,select{width:100%}button{cursor:pointer;background:#006d77;color:white;border:0;margin-top:16px}button.secondary{background:#e6eff4;color:#173047}button:disabled{opacity:.5;cursor:wait}#status{padding:14px;background:#eaf3f6;border-radius:9px;white-space:pre-wrap}.row{display:flex;gap:12px;flex-wrap:wrap}small{color:#52677b}a{color:#006d77}</style>
<main><h1>Kết nối Wi-Fi cho OpenStick</h1><p class="sub">Quản trị cục bộ qua USB • Linux • Wi-Fi Client</p>
<section><div id="status" role="status">Đang kiểm tra kết nối USB…</div><div class="row"><button id="scan" class="secondary">Tìm mạng Wi-Fi</button><button id="check" class="secondary">Kiểm tra trạng thái</button></div>
<label for="networks">Mạng tìm thấy</label><select id="networks"><option value="">Chọn mạng hoặc nhập tên bên dưới</option></select>
<form id="wifi"><label for="ssid">Tên Wi-Fi (SSID)</label><input id="ssid" name="ssid" maxlength="32" autocomplete="off" required>
<label for="password">Mật khẩu Wi-Fi</label><input id="password" name="password" type="password" minlength="8" maxlength="63" autocomplete="new-password" required><button id="connect" type="submit">Kết nối Wi-Fi</button></form>
<p><small>Mật khẩu không hiển thị trong báo cáo. Thiết bị lưu khóa Wi-Fi để tự kết nối sau khi bật nguồn. Nếu đổi mạng không thành công, vẫn có thể cấu hình lại qua USB.</small></p></section>
<section><strong>Website công khai</strong><p><a href="https://__OPENSTICK_HOSTNAME__" target="_blank" rel="noopener">__OPENSTICK_HOSTNAME__</a></p><small>Trang quản trị Wi-Fi chỉ truy cập qua USB. Sau khi lưu Wi-Fi, có thể cắm nguồn USB để thiết bị tự kết nối và chạy website.</small></section></main>
<script>
const token=__OPENSTICK_BOOTSTRAP_TOKEN__||new URLSearchParams(location.hash.slice(1)).get('token')||sessionStorage.getItem('openstick-hosting-token')||'';if(token)sessionStorage.setItem('openstick-hosting-token',token);history.replaceState(null,'',location.pathname);
const status=document.getElementById('status'),networks=document.getElementById('networks');let busy=false;
async function call(action,extra={}){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);status.textContent='Đang thực hiện…';try{const r=await fetch('/api/wifi',{method:'POST',headers:{'Content-Type':'application/json','X-OpenStick-Token':token},body:JSON.stringify({action,...extra})});if(!r.ok)throw Error();await poll()}catch(e){status.textContent='Không thực hiện được. Hãy kiểm tra USB và tải lại trang quản trị.'}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false)}}
async function poll(){for(;;){const r=await fetch('/api/state',{headers:{'X-OpenStick-Token':token}});if(!r.ok)throw Error();const s=await r.json();if(s.busy){await new Promise(r=>setTimeout(r,700));continue}if(s.error){status.textContent='Thao tác Wi-Fi chưa thành công. Kiểm tra tên mạng, mật khẩu rồi thử lại qua USB.';return}if(s.result.networks){networks.replaceChildren(new Option('Chọn mạng hoặc nhập tên bên dưới',''));for(const n of s.result.networks)networks.add(new Option(`${n.ssid} — ${n.signal}% — ${n.security||'mở'}`,n.ssid));status.textContent=`Đã tìm thấy ${s.result.networks.length} mạng. Hỗ trợ kết nối WPA/WPA2 Personal.`}else if(s.result.connected){document.getElementById('password').value='';status.textContent='Đã kết nối Wi-Fi. Bạn có thể kiểm tra website công khai.'}else{status.textContent=`USB đã kết nối. Wi-Fi: ${s.result.state||'chưa xác định'}\nProfile: ${s.result.connection||'chưa có'}`}return}}
networks.onchange=()=>{if(networks.value)document.getElementById('ssid').value=networks.value};document.getElementById('scan').onclick=()=>call('scan');document.getElementById('check').onclick=()=>call('status');document.getElementById('wifi').onsubmit=e=>{e.preventDefault();call('connect',{ssid:document.getElementById('ssid').value,password:document.getElementById('password').value})};call('status');
</script></html>'''


def create_hosting_app(private_dir=None, *, backend=None, token=None, port=8770, hostname='example.invalid', usb_portal=False, modem_backend=None):
    if (not isinstance(hostname, str) or len(hostname) > 253
            or not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,63}', hostname)):
        raise ValueError('Invalid website hostname')
    app = Flask(__name__)
    backend = backend or LinuxWifi(private_dir)
    token = token or secrets.token_urlsafe(32)
    lock = threading.Lock()
    state = {'busy': False, 'result': {}, 'error': False}
    app.config.update(MAX_CONTENT_LENGTH=4096)
    app.extensions['hosting'] = {'token': token, 'state': state}

    @app.before_request
    def guard():
        authority = '172.16.42.1' if usb_portal else f'127.0.0.1:{port}'
        origin = 'http://' + authority
        if request.host != authority or request.headers.get('Origin', origin) != origin:
            return jsonify(error='FORBIDDEN'), 403
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return jsonify(error='FORBIDDEN'), 403
        if request.path.startswith('/api/') and not secrets.compare_digest(request.headers.get('X-OpenStick-Token', ''), token):
            return jsonify(error='FORBIDDEN'), 403

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.get('/')
    def index():
        page = HTML.replace('__OPENSTICK_HOSTNAME__', html.escape(hostname))
        if usb_portal and modem_backend is not None:
            page = page.replace('<main>', '<main><nav><a href="/modem">SMS / USSD và trạng thái 4G</a></nav>', 1)
        # Device mode is served only by a socket bound to the physical USB
        # interface. Same-origin API requests still require this random token.
        return page.replace('__OPENSTICK_BOOTSTRAP_TOKEN__', json.dumps(token if usb_portal else ''))

    @app.get('/api/state')
    def current():
        with lock:
            return jsonify(state)

    @app.post('/api/wifi')
    def wifi():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or body.get('action') not in ('status', 'scan', 'connect'):
            return jsonify(error='INPUT_INVALID'), 400
        action = body['action']
        expected = {'action', 'ssid', 'password'} if action == 'connect' else {'action'}
        if set(body) != expected:
            return jsonify(error='INPUT_INVALID'), 400
        if action == 'connect':
            ssid, password = body['ssid'], body['password']
            if (not isinstance(ssid, str) or not isinstance(password, str)
                    or not 1 <= len(ssid.encode()) <= 32 or not 8 <= len(password) <= 63
                    or any(ord(c) < 32 for c in ssid + password)):
                return jsonify(error='INPUT_INVALID'), 400
        with lock:
            if state['busy']:
                return jsonify(error='BUSY'), 409
            state.update(busy=True, result={}, error=False)

        def work():
            try:
                result = backend.call(action, **{k: v for k, v in body.items() if k != 'action'})
                with lock:
                    state.update(result=result)
            except Exception:
                with lock:
                    state.update(error=True, result={})
            finally:
                body.clear()  # do not retain a password in job/history state
                with lock:
                    state['busy'] = False
        thread = threading.Thread(target=work, daemon=True)
        app.extensions['hosting']['thread'] = thread
        thread.start()
        return jsonify(accepted=True), 202

    if usb_portal and modem_backend is not None:
        from .modem import register_modem_routes
        register_modem_routes(app, modem_backend, token)
    return app


def main():
    parser = argparse.ArgumentParser(description='OpenStick Linux Wi-Fi setup over USB')
    parser.add_argument('--private-dir', type=Path, required=True)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    for name in ('pmos_known_hosts', 'manager_ed25519'):
        if not (args.private_dir / name).is_file():
            parser.error('Missing local SSH identity or host pin')
    configuration = args.private_dir / 'hosting-config.json'
    hostname = json.loads(configuration.read_text(encoding='utf-8')).get('hostname', 'example.invalid') if configuration.is_file() else 'example.invalid'
    app = create_hosting_app(args.private_dir, hostname=hostname)
    url = 'http://127.0.0.1:8770/#token=' + app.extensions['hosting']['token']
    (args.private_dir / 'hosting-ui.json').write_text(json.dumps({'pid': os.getpid(), 'url': url}), encoding='utf-8')
    if not args.no_browser:
        webbrowser.open(url)
    print('OpenStick Wi-Fi setup is listening on 127.0.0.1:8770', flush=True)
    serve(app, host='127.0.0.1', port=8770)


if __name__ == '__main__':
    main()

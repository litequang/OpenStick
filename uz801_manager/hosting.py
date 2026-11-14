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

from flask import Flask, jsonify, render_template, request
from waitress import serve

WIFI_ERRORS = {'WIFI_AUTH_REQUIRED', 'WIFI_TIMEOUT', 'WIFI_NOT_FOUND', 'HOTSPOT_ACTIVE', 'SETUP_ACTIVE', 'POLICY_ACTIVE', 'NETWORK_BUSY'}


REMOTE = r'''
import hashlib,json,os,re,shutil,subprocess,sys,uuid
from contextlib import ExitStack
if os.path.isdir('/opt/openstick'):sys.path.insert(0,'/opt/openstick')
value=json.load(sys.stdin)
guard=ExitStack()
def run(args,timeout=15):
    try:p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired:raise RuntimeError('WIFI_TIMEOUT') from None
    if p.returncode:
        if 'connection' in args and 'up' in args:
            error=p.stderr or ''
            if 'Secrets were required' in error or 'No secrets' in error:raise RuntimeError('WIFI_AUTH_REQUIRED')
            if 'Timeout expired' in error:raise RuntimeError('WIFI_TIMEOUT')
            if 'SSID' in error and 'not found' in error:raise RuntimeError('WIFI_NOT_FOUND')
        raise RuntimeError('NETWORK_OPERATION_FAILED')
    return p.stdout
def fields(line):
    out=[];part='';escaped=False
    for c in line:
        if escaped:part+=c;escaped=False
        elif c=='\\':escaped=True
        elif c==':':out.append(part);part=''
        else:part+=c
    return out+[part]

def station_profile(ssid,password,identity):
    psk=hashlib.pbkdf2_hmac('sha1',password.encode(),ssid.encode(),4096,32).hex()
    escaped=ssid.replace('\\','\\\\').replace(';','\\;')
    profile='openstick-'+hashlib.sha256(ssid.encode()).hexdigest()[:16]
    return ('[connection]\nid='+profile+'\nuuid='+identity+
        '\ntype=wifi\ninterface-name=wlan0\nautoconnect=true\nautoconnect-priority=10\n\n'
        '[wifi]\nmode=infrastructure\ncloned-mac-address=permanent\npowersave=2\nssid='+escaped+
        '\n\n[wifi-security]\nkey-mgmt=wpa-psk\npsk='+psk+
        '\n\n[ipv4]\nmethod=auto\nroute-metric=100\n\n[ipv6]\nmethod=auto\nroute-metric=100\n')
def wifi_status():
    output=run(['nmcli','-t','-e','yes','-f','GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY','device','show','wlan0'])
    rows={}
    for line in output.splitlines():
        row=fields(line)
        if len(row)==2:rows[row[0]]=row[1]
    state=rows.get('GENERAL.STATE','unknown')
    result={'state':state,'connection':rows.get('GENERAL.CONNECTION',''),
            'connected':state.startswith('100'),'ssid':None,'signal_percent':None,
            'signal_dbm':None,'tx_mbps':None,'rx_mbps':None,
            'ipv4':[v for k,v in rows.items() if k.startswith('IP4.ADDRESS')],
            'gateway':rows.get('IP4.GATEWAY','')}
    result['setup_active']=result['connected'] and result['connection']=='openstick-setup'
    result['hotspot_active']=result['connected'] and result['connection'] in ('openstick-hotspot','openstick-setup')
    if result['hotspot_active']:
        result['connected']=False
        try:
            ap=run(['nmcli','-g','802-11-wireless.ssid,802-11-wireless.channel',
                    'connection','show','id',result['connection']]).splitlines()
            if ap:result['ssid']=ap[0][:32]
            result['channel']=int(ap[1]) if len(ap)>1 and ap[1].isdigit() else None
        except (RuntimeError,OSError,subprocess.SubprocessError):pass
    if result['connected']:
        try:cached=run(['nmcli','-t','-e','yes','-f','IN-USE,SSID,SIGNAL','device','wifi','list','ifname','wlan0','--rescan','no'])
        except (RuntimeError,OSError,subprocess.SubprocessError):cached=''
        for line in cached.splitlines():
            row=fields(line)
            if len(row)==3 and row[0]=='*':
                result['ssid']=row[1][:32]
                if row[2].isdigit() and 0<=int(row[2])<=100:result['signal_percent']=int(row[2])
                break
        if shutil.which('iw'):
            try:p=subprocess.run(['iw','dev','wlan0','link'],capture_output=True,text=True,timeout=10)
            except (OSError,subprocess.SubprocessError):p=None
            if p is not None and p.returncode==0:
                for key in ('tx','rx'):
                    match=re.search(r'^\s*'+key+r' bitrate:\s*([0-9.]+) MBit/s',p.stdout,re.M)
                    if match:result[key+'_mbps']=float(match[1])
                match=re.search(r'^\s*signal:\s*(-?[0-9]+) dBm',p.stdout,re.M)
                if match:result['signal_dbm']=int(match[1])
                match=re.search(r'^\s*SSID: (.*)$',p.stdout,re.M)
                if match:result['ssid']=match[1][:32]
    result['modem_status']=None
    try:
        from uz801_manager.portal_metrics import modem_snapshot
        result['modem_status']=modem_snapshot()
    except ImportError:pass
    return result
def download_speed():
    if not wifi_status()['connected']:raise RuntimeError('WIFI_NOT_CONNECTED')
    # Fixed HTTPS endpoint, a bounded download, and explicit Wi-Fi binding.
    # No user-supplied URL, upload, automatic run or default-route fallback.
    size=2097152
    output=run(['curl','--silent','--show-error','--fail','--proto','=https',
        '--interface','wlan0','--connect-timeout','8','--max-time','20',
        '--max-filesize',str(size),'--output','/dev/null','--write-out',
        '%{http_code} %{size_download} %{speed_download} %{time_total}',
        'https://speed.cloudflare.com/__down?bytes='+str(size)],25).split()
    if len(output)!=4 or output[0]!='200' or int(float(output[1]))!=size:
        raise RuntimeError('SPEED_TEST_FAILED')
    return {'download_mbps':round(float(output[2])*8/1000000,2),
            'duration_s':round(float(output[3]),2),'bytes':size,'interface':'wlan0'}
try:
    action=value['action']
    if action in ('scan','connect','speed') and os.path.isdir('/opt/openstick'):
        from uz801_manager.hotspot import Hotspot,Network,AP_UUID,network_lock
        from uz801_manager.setup_ap import SETUP_UUID
        guard.enter_context(network_lock())
        hotspot=Hotspot()
        if Network().active('wlan0')==SETUP_UUID or hotspot.read('setup-pending.json'):raise RuntimeError('SETUP_ACTIVE')
        if (hotspot.read('hotspot.json').get('enabled') or hotspot.read('hotspot-pending.json')
                or Network().active('wlan0')==AP_UUID):raise RuntimeError('HOTSPOT_ACTIVE')
        if action=='connect':
            from uz801_manager.network_policy import NetworkPolicy
            if NetworkPolicy().config()['enabled']:raise RuntimeError('POLICY_ACTIVE')
    if action=='scan':
        output=run(['nmcli','-t','-e','yes','-f','SSID,SIGNAL,SECURITY','device','wifi','list','ifname','wlan0','--rescan','yes'])
        networks={}
        for line in output.splitlines():
            row=fields(line)
            if len(row)==3 and row[0] and row[1].isdigit():
                networks[row[0]]={'ssid':row[0][:32],'signal':int(row[1]),'security':row[2][:80]}
        result={'networks':sorted(networks.values(),key=lambda n:-n['signal'])[:100]}
    elif action=='status':
        result=wifi_status()
    elif action=='speed':
        result=download_speed()
    elif action=='overview':
        from uz801_manager.portal_metrics import system_snapshot,service_snapshot
        result={'system':system_snapshot(),'wifi':wifi_status(),'services':service_snapshot()}
    elif action=='tariff':
        from uz801_manager.portal_metrics import save_tariff
        result=save_tariff(value['unit_vnd'])
    elif action=='connect':
        ssid,password=value['ssid'],value['password']
        assert isinstance(ssid,str) and 1<=len(ssid.encode())<=32
        assert isinstance(password,str) and 8<=len(password)<=63
        assert not any(ord(c)<32 for c in ssid+password)
        profile='openstick-'+hashlib.sha256(ssid.encode()).hexdigest()[:16]
        target='/etc/NetworkManager/system-connections/'+profile+'.nmconnection'
        existing=''
        if os.path.isfile(target):
            with open(target) as f:existing=f.read(8192)
        match=re.search(r'^uuid=([0-9a-f-]{36})$',existing,re.M)
        identity=str(uuid.UUID(match[1])) if match else str(uuid.uuid4())
        data=station_profile(ssid,password,identity)
        temp=target+'.tmp'
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(fd,'w') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
        run(['nmcli','connection','load',target])
        run(['nmcli','-w','55','connection','up','uuid',identity],60)
        result={'connected':True}
    else:raise RuntimeError('INPUT_INVALID')
    print(json.dumps(result))
except Exception as error:
    allowed={'WIFI_AUTH_REQUIRED','WIFI_TIMEOUT','WIFI_NOT_FOUND','HOTSPOT_ACTIVE','SETUP_ACTIVE','POLICY_ACTIVE','NETWORK_BUSY'}
    print(json.dumps({'error':str(error) if str(error) in allowed else 'NETWORK_OPERATION_FAILED'}));sys.exit(1)
finally:guard.close()
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
                          capture_output=True, timeout=110 if action == 'connect' else 50, shell=False,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if len(result.stdout) > 65536:
            raise RuntimeError('USB_SSH_UNAVAILABLE')
        try:parsed = json.loads(result.stdout)
        except (ValueError, UnicodeError):raise RuntimeError('USB_SSH_UNAVAILABLE') from None
        if isinstance(parsed, dict) and parsed.get('error') in WIFI_ERRORS:
            raise RuntimeError(parsed['error'])
        if result.returncode:raise RuntimeError('USB_SSH_UNAVAILABLE')
        if not isinstance(parsed, dict) or 'error' in parsed:
            raise RuntimeError('NETWORK_OPERATION_FAILED')
        return parsed


HTML = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenStick — Kết nối Wi-Fi</title><style>
*{box-sizing:border-box}body{margin:0;font:16px system-ui;background:#f2f6fa;color:#173047}main{max-width:740px;margin:5vh auto;padding:24px}section{background:white;padding:24px;border-radius:18px;box-shadow:0 8px 40px #17304710;margin:20px 0}h1{font-size:30px;margin-bottom:8px}p{line-height:1.6}.sub{color:#52677b}label{display:block;margin:18px 0 8px}input,select,button{font:inherit;padding:12px;border-radius:9px;border:1px solid #c9d5df}input,select{width:100%}button{cursor:pointer;background:#006d77;color:white;border:0;margin-top:16px}button.secondary{background:#e6eff4;color:#173047}button:disabled{opacity:.5;cursor:wait}#status{padding:14px;background:#eaf3f6;border-radius:9px;white-space:pre-wrap}.row{display:flex;gap:12px;flex-wrap:wrap}small{color:#52677b}a{color:#006d77}</style>
<main><div class="ux-page-lead"><h1>Wi-Fi nhận Internet</h1><p class="sub">Kiểm tra và kết nối USB vào Wi-Fi nhà hoặc văn phòng để vận hành website. Các cài đặt mạng nâng cao nằm trong <a href="/manage">Quản lý</a>.</p></div>
<section><h2>Wi-Fi đang sử dụng</h2><div id="status" role="status">Đang kiểm tra kết nối USB…</div><button id="check" class="secondary">Cập nhật trạng thái</button><p><small>Tự cập nhật mỗi 15 giây khi mở trang. Tốc độ liên kết TX/RX do driver báo, không phải tốc độ tải Internet.</small></p></section>
<details class="ux-advanced"><summary>Đo tốc độ Wi-Fi (tùy chọn)</summary><section><h2>Tốc độ tải Internet qua Wi-Fi</h2><div id="speed-result" role="status">Chưa đo. Phép đo tải 2 MiB từ Cloudflare qua Wi-Fi, không thử tải lên.</div><button id="speed" disabled>Đo tốc độ tải Internet</button><p><small>Kết quả là mẫu tải ngắn tới một máy chủ; không phải cam kết băng thông. Chỉ đo khi bạn bấm nút.</small></p></section></details>
<section><details id="wifi-settings" open><summary id="wifi-summary" style="cursor:pointer;font-weight:600">Chọn Wi-Fi để kết nối</summary><button id="scan" class="secondary">Tìm mạng Wi-Fi</button>
<label for="networks">Mạng tìm thấy</label><select id="networks"><option value="">Chọn mạng hoặc nhập tên bên dưới</option></select>
<form id="wifi"><label for="ssid">Tên Wi-Fi (SSID)</label><input id="ssid" name="ssid" maxlength="32" autocomplete="off" required>
<label for="password">Mật khẩu Wi-Fi</label><input id="password" name="password" type="password" minlength="8" maxlength="63" autocomplete="new-password" required><button id="connect" type="submit">Kết nối Wi-Fi</button></form>
<p><small>Mật khẩu không hiển thị trong báo cáo. Thiết bị lưu khóa Wi-Fi để tự kết nối sau khi bật nguồn. Nếu đổi mạng không thành công, vẫn có thể cấu hình lại qua USB.</small></p></details><p id="operation-status" role="status"></p></section>
<section><strong>Website công khai</strong><p><a href="https://__OPENSTICK_HOSTNAME__" target="_blank" rel="noopener">__OPENSTICK_HOSTNAME__</a></p><small>Quản trị qua USB hoặc Wi-Fi có đăng nhập nếu đã bật. Sau khi lưu Wi-Fi, có thể cắm nguồn USB để thiết bị tự kết nối và chạy website.</small></section></main>
<script>
const token=__OPENSTICK_BOOTSTRAP_TOKEN__||new URLSearchParams(location.hash.slice(1)).get('token')||sessionStorage.getItem('openstick-hosting-token')||'';if(token)sessionStorage.setItem('openstick-hosting-token',token);history.replaceState(null,'',location.pathname);
const status=document.getElementById('status'),networks=document.getElementById('networks'),notice=document.getElementById('operation-status');let busy=false,wifiConnected=false,initialized=false;
let lastWifiError='';
const wifiErrors={WIFI_AUTH_REQUIRED:'Wi-Fi yêu cầu lại mật khẩu. Nhập mật khẩu của mạng Wi-Fi, không phải mật khẩu quản trị LAN.',WIFI_TIMEOUT:'Kết nối Wi-Fi hết thời gian chờ. Kiểm tra lại mật khẩu và bộ phát.',WIFI_NOT_FOUND:'Không tìm thấy mạng Wi-Fi. Tìm lại danh sách mạng.',HOTSPOT_ACTIVE:'Dừng hotspot trước khi kết nối Wi-Fi nhận Internet.',POLICY_ACTIVE:'Tắt tự quản lý Internet trước khi lưu Wi-Fi mới.',NETWORK_BUSY:'USB đang thực hiện thao tác mạng khác. Thử lại sau.'};
function renderStatus(s){if(typeof renderHeader==='function')renderHeader(s.modem_status);wifiConnected=s.connected===true;const details=document.getElementById('wifi-settings');details.hidden=s.hotspot_active===true;if(s.hotspot_active){details.open=false;status.textContent='Wi-Fi đang phát từ USB. Quản lý tại mục Phát Wi-Fi từ SIM 4G bên dưới. Internet cho web dùng phiên dữ liệu SIM; không phải Wi-Fi nhà.';document.getElementById('speed').disabled=true;return}if(!initialized||!wifiConnected)details.open=!wifiConnected;initialized=true;document.getElementById('wifi-summary').textContent=wifiConnected?'Đổi Wi-Fi':'Chọn Wi-Fi để kết nối';const quality=s.signal_percent==null?'chưa có số liệu':`${s.signal_percent}%`;const dbm=s.signal_dbm==null?'':` (${s.signal_dbm} dBm)`;const rate=value=>value==null?'chưa có số liệu':`${value} Mbps`;status.textContent=`Wi-Fi: ${wifiConnected?'đã kết nối':'chưa kết nối'}\nTên mạng: ${s.ssid||'chưa xác định'}\nMức sóng: ${quality}${dbm}\nLiên kết TX: ${rate(s.tx_mbps)} • RX: ${rate(s.rx_mbps)}\nIPv4: ${(s.ipv4||[]).join(', ')||'chưa có'}\nGateway: ${s.gateway||'chưa có'}\nIP quản trị USB: 172.16.42.1 (riêng với IP Wi-Fi)`;document.getElementById('speed').disabled=busy||!wifiConnected}
const renderStationStatus=renderStatus;renderStatus=function(s){if(!s.setup_active){renderStationStatus(s);return}wifiConnected=false;document.getElementById('wifi-settings').hidden=true;document.getElementById('speed').disabled=true;status.textContent='Wi-Fi setup: '+(s.ssid||'')+' ? http://192.168.8.1:8765/setup';const a=document.createElement('a');a.href='/setup';a.textContent=' Mở trang cài Wi-Fi →';status.append(a)};wifiErrors.SETUP_ACTIVE='Đang phát Wi-Fi cài đặt. Mở mục Wi-Fi cài đặt để đổi mạng.';
async function call(action,extra={}){if(busy)return;if(action!=='status')lastWifiError='';busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);notice.textContent=action==='speed'?'Đang tải mẫu 2 MiB qua Wi-Fi…':'Đang kiểm tra…';try{const r=await fetch('/api/wifi',{method:'POST',headers:{'Content-Type':'application/json','X-OpenStick-Token':token},body:JSON.stringify({action,...extra})});if(!r.ok)throw Error();const ok=await poll();if(action==='connect'&&ok)setTimeout(()=>call('status'),0)}catch(e){notice.textContent='Thao tác chưa thành công. Kiểm tra kết nối USB/Wi-Fi rồi thử lại.'}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false);document.getElementById('speed').disabled=!wifiConnected}}
async function poll(){const end=Date.now()+120000;while(Date.now()<end){const r=await fetch('/api/state',{headers:{'X-OpenStick-Token':token}});if(!r.ok)throw Error();const s=await r.json();if(s.busy){await new Promise(r=>setTimeout(r,700));continue}if(s.error){if(wifiErrors[s.error_code]){lastWifiError=wifiErrors[s.error_code];notice.textContent=lastWifiError;return false}notice.textContent='Thao tác Wi-Fi chưa thành công. Kết quả tốc độ có thể không có nếu máy chủ đo không phản hồi.';return}if(s.result.networks){networks.replaceChildren(new Option('Chọn mạng hoặc nhập tên bên dưới',''));for(const n of s.result.networks)networks.add(new Option(`${n.ssid} — ${n.signal}% — ${n.security||'mở'}`,n.ssid));document.getElementById('wifi-settings').open=true;notice.textContent=`Đã tìm thấy ${s.result.networks.length} mạng.`}else if(s.result.download_mbps!=null){document.getElementById('speed-result').textContent=`Tốc độ tải: ${s.result.download_mbps} Mbps • Mẫu 2 MiB • ${s.result.duration_s} giây\nĐo lúc ${new Date().toLocaleTimeString()}`;notice.textContent='Đã đo qua Wi-Fi.'}else if(s.result.state){renderStatus(s.result);if(s.result.connected)lastWifiError='';notice.textContent=lastWifiError||'Đã cập nhật trạng thái.'}else if(s.result.connected){document.getElementById('password').value='';document.getElementById('wifi-settings').open=false;notice.textContent='Đã kết nối Wi-Fi.'}return true}throw Error('TIMEOUT')}
networks.onchange=()=>{if(networks.value)document.getElementById('ssid').value=networks.value};document.getElementById('scan').onclick=()=>call('scan');document.getElementById('check').onclick=()=>call('status');document.getElementById('speed').onclick=()=>call('speed');document.getElementById('wifi').onsubmit=e=>{e.preventDefault();call('connect',{ssid:document.getElementById('ssid').value,password:document.getElementById('password').value})};setInterval(()=>{if(!busy&&!document.hidden)call('status')},15000);call('status');
</script></html>'''


def create_hosting_app(private_dir=None, *, backend=None, token=None, port=8770, hostname='example.invalid', usb_portal=False, modem_backend=None, authority=None, lan_auth=None, lan_settings=None, lan_changed=lambda: None, site_backend=None, hotspot_backend=None, network_backend=None, setup_backend=None):
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
        expected_authority = authority() if callable(authority) else authority
        if expected_authority is None and lan_auth is None:
            expected_authority = '172.16.42.1' if usb_portal else f'127.0.0.1:{port}'
        if not expected_authority:return jsonify(error='FORBIDDEN'), 403
        origin = 'http://' + expected_authority
        if request.host != expected_authority or request.headers.get('Origin', origin) != origin:
            return jsonify(error='FORBIDDEN'), 403
        if request.headers.get('Sec-Fetch-Site') == 'cross-site':
            return jsonify(error='FORBIDDEN'), 403
        if request.path.startswith('/api/') and not secrets.compare_digest(request.headers.get('X-OpenStick-Token', ''), token):
            return jsonify(error='FORBIDDEN'), 403

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        # Native login/logout form POSTs use no-cors mode. With no-referrer,
        # browsers serialize Origin as "null", failing our strict origin check.
        # same-origin preserves the origin locally and sends no referrer outside.
        response.headers['Referrer-Policy'] = 'same-origin' if lan_auth is not None else 'no-referrer'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        form_action = "'self'" if lan_auth is not None else "'none'"
        response.headers['Content-Security-Policy'] = "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; form-action " + form_action + "; frame-ancestors 'none'; base-uri 'none'"
        return response

    @app.get('/')
    def index():
        page = HTML.replace('__OPENSTICK_HOSTNAME__', html.escape(hostname))
        if usb_portal and modem_backend is not None:
            page = page.replace('<main>', '<main>' + render_template('portal_chrome.html', page='wifi', token=token), 1)
        if usb_portal and modem_backend is not None:
            page = page.replace('</main>', '<section class="ux-compact-link"><h2>Thiết lập nâng cao</h2><p class="muted">Nguồn Internet, SIM, Wi-Fi cài đặt, điểm phát và website được phân nhóm riêng.</p><a class="ux-link-cta" href="/manage">Mở trung tâm Quản lý →</a></section></main>', 1)
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
        if not isinstance(body, dict) or body.get('action') not in ('status', 'scan', 'connect', 'speed', 'overview', 'tariff'):
            return jsonify(error='INPUT_INVALID'), 400
        action = body['action']
        expected = {'action', 'ssid', 'password'} if action == 'connect' else {'action', 'unit_vnd'} if action == 'tariff' else {'action'}
        if set(body) != expected:
            return jsonify(error='INPUT_INVALID'), 400
        if action == 'tariff' and (type(body['unit_vnd']) is not int or not 0 <= body['unit_vnd'] <= 100000):
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
            state.pop('error_code', None)

        def work():
            try:
                result = backend.call(action, **{k: v for k, v in body.items() if k != 'action'})
                with lock:
                    state.update(result=result)
            except Exception as exc:
                with lock:
                    state.update(error=True, result={})
                    if str(exc) in WIFI_ERRORS:state['error_code'] = str(exc)
            finally:
                body.clear()  # do not retain a password in job/history state
                with lock:
                    state['busy'] = False
        thread = threading.Thread(target=work, daemon=True)
        app.extensions['hosting']['thread'] = thread
        thread.start()
        return jsonify(accepted=True), 202

    if usb_portal and modem_backend is not None:
        @app.get('/api/header')
        def header_status():
            # Read-only snapshot; do not overwrite an in-flight Wi-Fi job or
            # its result when a different page updates the shared header.
            try:return jsonify(backend.call('status'))
            except Exception:return jsonify(error='STATUS_UNAVAILABLE'), 503

        @app.get('/overview')
        def overview():
            return render_template('overview.html', token=token, page='overview', hostname=hostname)
        @app.get('/manage')
        def manage():
            features = {'network': network_backend is not None, 'setup': setup_backend is not None,
                        'hotspot': hotspot_backend is not None, 'website': site_backend is not None,
                        'lan': lan_settings is not None and lan_auth is None}
            return render_template('manage.html', token=token, page='manage', features=features,
                                   can_manage_lan=lan_settings is not None and lan_auth is None)
        from .modem import register_modem_routes
        register_modem_routes(app, modem_backend, token)
    if usb_portal and lan_settings is not None and lan_auth is None:
        from .lan_access import register_lan_settings
        register_lan_settings(app, lan_settings, token, lan_changed)
    if usb_portal and site_backend is not None:
        # Only this authenticated/token-protected endpoint accepts file bodies.
        @app.before_request
        def site_body_limit():
            if request.path == '/api/site':request.max_content_length = 1500000
        from .static_site import register_site_routes
        register_site_routes(app, site_backend, token, hostname)
    if lan_auth is not None:
        from .lan_access import install_lan_auth
        install_lan_auth(app, lan_auth)
    if usb_portal and hotspot_backend is not None:
        from .hotspot_web import register_hotspot_routes
        register_hotspot_routes(app, hotspot_backend, token)
    if usb_portal and network_backend is not None:
        from .network_web import register_network_routes
        register_network_routes(app, network_backend, token)
    if usb_portal and setup_backend is not None:
        from .setup_web import register_setup_routes
        register_setup_routes(app, setup_backend, token)
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

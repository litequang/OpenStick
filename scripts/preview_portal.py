"""Disposable portal preview: fictional messages, no USB/SSH/DBus operations."""
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from waitress import serve
from uz801_manager.hosting import create_hosting_app
from uz801_manager.sms_archive import ArchivedModem, SmsArchive
from uz801_manager.static_site import StaticSite


class Modem:
    def call(self, action, **values):
        if action == 'status':
            return {'state':'registered','sim_present':True,'registered':True,'sms_available':True,
                    'can_send':False,'ussd_available':False,'ussd_state':1,'signal_percent':72,
                    'signal_recent':True,'operator_name':'Mạng mô phỏng','registration_state':1,
                    'access_technologies':16384,'supported_modes':[[8,0]],'current_mode':[8,0]}
        if action == 'messages':return {'messages':[], 'limited':False}
        raise RuntimeError('UNSUPPORTED')


class Policy:
    def call(self, action, **values):
        if action == 'status':return {'config':{'mode':'wifi_preferred','enabled':False,'auto_wifi':True},
                                      'runtime':{'source':'wifi','health':{'wifi':True,'sim':False}}}
        if action == 'profiles':return {'profiles':[{'uuid':'07ca019c-485b-4f06-b99d-171c167e18bb',
                                                     'ssid':'Wi-Fi mẫu','active':True}]}
        raise RuntimeError('NETWORK_OPERATION_FAILED')


class Hotspot:
    def call(self, action, **values):
        if action != 'status':raise RuntimeError('HOTSPOT_OPERATION_FAILED')
        return {'configured':False,'ap_supported':True,'ssid':None,'enabled':False,
                'pending':False,'hotspot_active':False,'cellular_connected':False,
                'seconds_remaining':0,'verification':'UNVERIFIED'}


class Wifi:
    def call(self, action, **values):
        if action=='status':return {'state':'100 (connected)','connected':True,'ssid':'Wi-Fi mẫu',
                                    'ipv4':['192.0.2.2/24'],'modem_status':Modem().call('status')}
        raise RuntimeError('NETWORK_OPERATION_FAILED')


class Setup:
    def status(self, credentials=False):
        value = {'enabled': True, 'configured': True, 'setup_active': True, 'lan_ready': True,
                 'ssid': 'OpenStick-Setup-DEMO', 'url': 'http://192.0.2.1:8765/setup',
                 'busy': False, 'result': 'SCAN_READY', 'error': None, 'scan_at': 1794646800,
                 'networks': [{'ssid': 'Wi-Fi mẫu', 'signal': 72, 'security': 'WPA2'}]}
        if credentials:value['password'] = 'demo-password-only'
        return value

    def call(self, action, **values):raise RuntimeError('DEMO_READ_ONLY')


def main():
    with tempfile.TemporaryDirectory(prefix='openstick-preview-') as name:
        directory=Path(name);site=directory/'site';site.mkdir()
        (site/'index.html').write_text('<!doctype html><html lang="vi"><title>Website mẫu</title><h1>OpenStick</h1></html>',encoding='utf-8')
        archive=SmsArchive(directory/'sms')
        archive.import_messages([{'number':'DEMO','text':'Đây là tin nhắn mẫu. Không đọc SIM hoặc gửi SMS thật.',
                                   'timestamp':'2026-11-14T10:00:00Z','state':3,'path':'/demo/1'},
                                  {'number':'+84000000000','text':'Lịch sử SMS được lưu riêng trên USB.',
                                   'timestamp':'2026-11-14T10:01:00Z','state':3,'path':'/demo/2'}])
        app=create_hosting_app(backend=Wifi(),modem_backend=ArchivedModem(Modem(),archive),
              hotspot_backend=Hotspot(),network_backend=Policy(),site_backend=StaticSite(site,lock_path=None),
              usb_portal=True,authority='127.0.0.1:8771',hostname='example.invalid',setup_backend=Setup())
        @app.after_request
        def demo_banner(response):
            if response.mimetype=='text/html':
                banner='<div style="text-align:center;background:#473513;color:#ffe3a0;padding:8px">MÔ PHỎNG — Không kết nối USB, SIM hoặc mạng thật</div>'
                response.set_data(re.sub(r'<body\b[^>]*>',lambda m:m[0]+banner,
                                         response.get_data(as_text=True),count=1))
            return response
        print('Preview only: http://127.0.0.1:8771/modem/sms',flush=True)
        serve(app,host='127.0.0.1',port=8771,threads=4)


if __name__=='__main__':main()

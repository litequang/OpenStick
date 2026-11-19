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
from uz801_manager.lan_access import LanSettings
from uz801_manager.leds import default_network_rules


class Leds:
    def status(self):
        return {'supported':True,'saved':False,
                'network':{'enabled':False,'state':'wifi_station','rules':default_network_rules()},
                'leds':[{'id':color,'label':label,'modes':['default','off','on','blink'],
                         'settings':{'mode':'default','on_ms':500,'off_ms':500},
                         'lit':False,'controlled':False}
                        for color,label in [('red','Đỏ'),('green','Xanh lá'),('blue','Xanh dương')]]}

    def configure(self, values):raise RuntimeError('DEMO_READ_ONLY')


class Quick:
    """Memory-only demo: no real radio/network object is constructed."""
    def __init__(self):
        self.intent=None;self.role='station';self.receipts={};self.wifi=self

    def options(self):
        return {'connected':self.role=='station','ssid':'Wi-Fi mẫu' if self.role=='station' else None,
                'ap_active':self.role in ('local_ap','sim_ap'),
                'saved':[{'ssid':'Wi-Fi mẫu','active':self.role=='station'},{'ssid':'Wi-Fi phụ','active':False}],
                'networks':[{'ssid':'Wi-Fi mới','signal':82,'security':'WPA2'},
                            {'ssid':'Wi-Fi mẫu','signal':68,'security':'WPA2'},
                            {'ssid':'Mạng doanh nghiệp','signal':50,'security':'WPA2 802.1X'}],
                'scan_at':1794800000}

    def status(self):
        return {'intent':self.intent,'radio':{'state':-1,'power_state':1,'sim_ready':False,'registered':False},
                'wifi_role':self.role,'mobile_data_connected':False,'foreign_cellular_active':False,
                'pending_network_trial':False,'internet_verified':False,'hardware_validation':'NOT_TESTED',
                'usb_tethering':{'available':False,'reason':'DEMO_NO_USB'}}

    def call(self,action,**values):
        from uz801_manager.quick_settings import validate_quick
        validate_quick({'action':action,**values})
        identity=values['operation']
        if identity in self.receipts:raise RuntimeError('ALREADY_ATTEMPTED')
        if action=='data_on':raise RuntimeError('SIM_NOT_READY')
        airplane=bool(self.intent and self.intent['airplane'])
        if action=='airplane_on':airplane=True
        if action=='airplane_off':airplane=False
        self.intent={'version':1,'airplane':airplane,'data_allowed':False}
        if action=='local_ap_on':self.role='local_ap'
        if action in ('local_ap_off','wifi_off'):self.role='offline'
        if action in ('wifi_auto','wifi_saved','wifi_connect'):self.role='station'
        self.receipts[identity]={'kind':action,'state':'COMPLETED'}
        return self.status()

    def receipt(self,identity):return self.receipts.get(identity,{'state':'NOT_FOUND'})


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


class Power:
    """Preview only: no physical power backend and no executor."""
    def activity(self):
        from contextlib import nullcontext
        return nullcontext()
    def status(self):return {'available':False,'pending':False,'phase':'IDLE','action':None,'operation':None,'error':None}
    def call(self,*args,**kwargs):raise RuntimeError('POWER_UNAVAILABLE')


class Setup:
    def status(self, credentials=False):
        value = {'enabled': True, 'configured': True, 'setup_active': False, 'lan_ready': True,
                 'ssid': 'OpenStick-Setup-DEMO', 'url': 'http://192.0.2.1:8765/setup',
                 'busy': False, 'result': None, 'error': None, 'scan_at': 1794646800,
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
              usb_portal=True,authority='127.0.0.1:8771',hostname='example.invalid',setup_backend=Setup(),
              lan_settings=LanSettings(directory/'lan',address=lambda:'192.0.2.2'),led_backend=Leds(),quick_backend=Quick(),power_backend=Power())
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

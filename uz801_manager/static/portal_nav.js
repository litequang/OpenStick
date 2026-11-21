// Adapted from thophuongpro @83adf488: bottomNavScroll.ts / useBottomNavAutoHide.ts.
const BOTTOM_NAV_SCROLL={top:12,downSpeed:.65,downDistance:72,upDistance:18,noise:3,sampleGap:180};
function boundedScrollPosition(position,maximum){return Math.max(0,Math.min(Number.isFinite(position)?position:0,Math.max(0,maximum)))}
class BottomNavScrollTracker{
 constructor(y,time,hidden=false){this.y=y;this.time=time;this.hidden=hidden;this.down=0;this.up=0}
 rebase(y,time){this.y=y;this.time=time;this.down=0;this.up=0}
 sample(y,time){const delta=y-this.y,elapsed=time-this.time;this.y=y;this.time=time;if(y<=BOTTOM_NAV_SCROLL.top){this.hidden=false;this.down=0;this.up=0;return this.hidden}if(elapsed<=0)return this.hidden;if(elapsed>BOTTOM_NAV_SCROLL.sampleGap){this.down=0;this.up=0}if(delta>0){this.up=delta>=BOTTOM_NAV_SCROLL.noise?0:Math.max(0,this.up-delta);if(elapsed<=BOTTOM_NAV_SCROLL.sampleGap&&delta>=BOTTOM_NAV_SCROLL.noise&&delta/elapsed>=BOTTOM_NAV_SCROLL.downSpeed)this.down+=delta;else this.down=0;if(this.down>=BOTTOM_NAV_SCROLL.downDistance)this.hidden=true}else if(delta<0){this.down=0;this.up-=delta;if(this.up>=BOTTOM_NAV_SCROLL.upDistance)this.hidden=false}return this.hidden}
}
function portalTechnology(value){if(value==null||value===0)return 'chưa xác định';const names=[];for(const [flag,label] of [[32768,'5G'],[16384,'4G LTE'],[8192,'3G HSPA+'],[4096,'3G EVDO-B'],[2048,'3G EVDO-A'],[1024,'3G EVDO'],[512,'CDMA 1x'],[256,'3G HSPA'],[128,'3G HSUPA'],[64,'3G HSDPA'],[32,'3G UMTS'],[16,'2G EDGE'],[8,'2G GPRS'],[4,'2G GSM']])if(value&flag)names.push(label);return names.join(' / ')||'chưa xác định'}
// Session-only display snapshots survive full-page navigation. Do not cache
// the raw modem API response: it may contain subscriber/device identifiers.
const PORTAL_HEADER_CACHE='openstick-header-display-v1';
function portalScopedCacheKey(key){
 // LAN re-login issues a new CSRF value; isolate snapshots between sessions
 // without storing the session/CSRF secret itself in browser storage.
 const csrf=document.querySelector?.('.access-banner input[name="csrf"]')?.value;
 if(!csrf)return key+'-usb';
 let hash=2166136261;for(let i=0;i<csrf.length;i++)hash=Math.imul(hash^csrf.charCodeAt(i),16777619);
 return key+'-lan-'+(hash>>>0).toString(36);
}
function portalReadCache(key){
 try{const entry=JSON.parse(sessionStorage.getItem(portalScopedCacheKey(key)));if(entry?.version===1&&Number.isFinite(entry.at)&&entry.at<=Date.now()&&Date.now()-entry.at<8*3600000&&entry.value&&typeof entry.value==='object')return entry}catch(_){}
 return null;
}
function portalWriteCache(key,value){
 try{sessionStorage.setItem(portalScopedCacheKey(key),JSON.stringify({version:1,at:Date.now(),value}))}catch(_){}
}
// Settings snapshots contain explicit display/config fields only. Never store
// API bodies wholesale, credentials, file contents, CSRF or operation receipts.
const portalSettingsSchemas={
 quick:{intent:{airplane:true,data_allowed:true},radio:{state:true,power_state:true,sim_ready:true,registered:true,ussd_state:true},startup:{saved:true,wifi_role:true,data_on:true},wifi_role:true,mobile_data_connected:true,foreign_cellular_active:true,pending_network_trial:true,usb_tethering:{available:true,enabled:true,desired_enabled:true,degraded:true,reboot_pending:true}},
 modem:{state:true,sim_present:true,sim_missing:true,sim_locked:true,registered:true,secondary_lock:true,can_enable:true,operator_name:true,registration_state:true,access_technologies:true,signal_percent:true,signal_recent:true,can_set_mode:true,supported_modes:[[true]],current_mode:[true],saved_mode:[true],can_set_bands:true,band_choices:[{id:true,label:true,bands:[true]}],current_bands:[true],saved_bands:true,can_set_roaming:true,roaming:{available:true,allowed:true,home_locked:true},ussd_state:true},
 wifi:{connected:true,hotspot_active:true,setup_active:true,ssid:true,ipv4:[true],signal_percent:true,tx_mbps:true,rx_mbps:true},
 setup:{enabled:true,configured:true,setup_active:true,busy:true,ssid:true,channel:true,url:true,station_url:true,scan_at:true,networks:[{ssid:true,signal:true,security:true}],ap_options:{hidden:true,max_clients:true,isolation:true,configured:true,invalid:true}},
 policy:{config:{mode:true,enabled:true,auto_wifi:true},runtime:{source:true,health:{wifi:true,sim:true},error:true},age_seconds:true},
 cellular:{settings:{available:true,name:true,apn:true,auth:true,ip_family:true,roaming:true,password_saved:true},profiles:[{id:true,name:true,apn:true,auth:true,ip_family:true,roaming:true,password_saved:true,active:true}],blocked:true},
 clients:{ap_active:true,inventory_available:true,count:true,filter_applied:true,blocked:[true],clients:[{mac:true,ip:true,name:true,signal_dbm:true,rx_bytes:true,tx_bytes:true,rx_mbps:true,tx_mbps:true,internet_blocked:true}]},
 lan:{enabled:true,stable_url:true,url:true},
 power:{available:true,phase:true,pending:true,delay_seconds:true},
 hotspot:{hotspot_active:true,setup_active:true,cellular_connected:true,enabled:true},
 saved_profiles:{profiles:[{uuid:true,ssid:true,active:true}]},
 sites:{routing:{local:true,available:true},selected:true,sites:[{id:true,name:true,domain:true,domains:[true],is_main:true,enabled:true,revision:true}],revision:true}
};
const portalUsageAmount={total_bytes:true,download_bytes:true,upload_bytes:true};
portalSettingsSchemas.usage={available:true,stale:true,today:portalUsageAmount,month:portalUsageAmount,session:portalUsageAmount,total:portalUsageAmount};
const portalLedReading={mode:true,on_ms:true,off_ms:true};
const portalLedRecipe={red:portalLedReading,green:portalLedReading,blue:portalLedReading};
portalSettingsSchemas.leds={supported:true,saved:true,leds:[{id:true,label:true,modes:[true],settings:portalLedReading,lit:true,controlled:true}],network:{enabled:true,state:true,rules:Object.fromEntries(['setup_hotspot','sim_hotspot','wifi_station','cellular_data','offline','unknown'].map(k=>[k,portalLedRecipe]))}};
function portalSettingsPick(value,schema){
 if(value==null)return value;
 if(schema===true)return typeof value==='boolean'||typeof value==='number'&&Number.isFinite(value)?value:typeof value==='string'?value.slice(0,512):undefined;
 if(Array.isArray(schema))return Array.isArray(value)?value.slice(0,256).map(v=>portalSettingsPick(v,schema[0])):undefined;
 if(typeof value!=='object'||Array.isArray(value))return undefined;
 const result={};for(const [key,shape] of Object.entries(schema)){if(Object.hasOwn(value,key)){const field=portalSettingsPick(value[key],shape);if(field!==undefined)result[key]=field}}return result;
}
function portalRememberSettings(kind,value){
 if(value?._display_cached||!portalSettingsSchemas[kind])return;
 const entry={version:1,at:Date.now(),value:portalSettingsPick(value,portalSettingsSchemas[kind])};
 const key=portalScopedCacheKey('openstick-settings-display-v1-'+kind);
 try{sessionStorage.setItem(key,JSON.stringify(entry))}catch(_){}
 // Client inventory stays session-only; other projections contain no secrets.
 if(kind!=='clients')try{localStorage.setItem(key,JSON.stringify(entry))}catch(_){}
}
function portalRestoreSettings(kind){
 if(!portalSettingsSchemas[kind])return null;
 const key=portalScopedCacheKey('openstick-settings-display-v1-'+kind);
 for(const read of [()=>sessionStorage.getItem(key),()=>kind!=='clients'?localStorage.getItem(key):null])try{
  const entry=JSON.parse(read());
  if(entry?.version===1&&Number.isFinite(entry.at)&&entry.at<=Date.now()&&Date.now()-entry.at<8*3600000&&entry.value&&typeof entry.value==='object')return {...portalSettingsPick(entry.value,portalSettingsSchemas[kind]),_display_cached:true};
 }catch(_){}return null;
}
function portalSettingsNote(element){if(element)element.textContent='Trạng thái gần nhất · đang cập nhật nền. Bạn vẫn có thể chỉnh cài đặt.'}
// Serving channels only; discard all cell/location keys before display/cache.
function portalLteCarriers(modem){
 if(!modem?.registered||!modem.sim_present||modem.sim_locked||!(modem.access_technologies&16384)||!Array.isArray(modem.serving_lte))return [];
 return modem.serving_lte.slice(0,8).filter(v=>v&&Number.isInteger(v.band)&&v.band>=1&&v.band<=88&&Number.isInteger(v.earfcn)&&v.earfcn>=0&&v.earfcn<=300000&&Number.isFinite(v.nominal_mhz)&&v.nominal_mhz>=300&&v.nominal_mhz<=8000&&Number.isFinite(v.downlink_mhz)&&v.downlink_mhz>=300&&v.downlink_mhz<=8000).map(v=>({band:v.band,nominal_mhz:v.nominal_mhz,earfcn:v.earfcn,downlink_mhz:v.downlink_mhz}));
}
function portalDisplayModem(modem){
 if(!modem||typeof modem.registered!=='boolean'||typeof modem.sim_present!=='boolean')return null;
 const result={};for(const key of ['state','registered','sim_present','sim_locked','operator_name','access_technologies','signal_percent','signal_recent','secondary_lock','can_enable'])if(Object.hasOwn(modem,key))result[key]=modem[key];
 result.serving_lte=portalLteCarriers(modem);
 // This is display-only information. A short-lived modem sample gap must not
 // erase the last usable signal on the next full-page navigation.
 if(portalLastSignal&&modem.sim_present&&!modem.sim_locked)result.last_signal={...portalLastSignal};
 return result;
}
function portalDisplayWifi(wifi){
 if(!wifi||typeof wifi.connected!=='boolean'&&typeof wifi.hotspot_active!=='boolean')return null;
 const result={};for(const key of ['connected','hotspot_active','setup_active','ssid','channel','ipv4','gateway','signal_percent','signal_dbm'])if(Object.hasOwn(wifi,key))result[key]=wifi[key];
 return result;
}
function portalRememberHeader(value){
 const last=portalReadCache(PORTAL_HEADER_CACHE)?.value||{};
 const wifi=portalDisplayWifi(value),modem=portalDisplayModem(value?.modem_status);
 if(wifi||modem)portalWriteCache(PORTAL_HEADER_CACHE,{wifi:wifi||last.wifi,modem:modem||last.modem});
}
function portalRestoreHeader(){
 const saved=portalReadCache(PORTAL_HEADER_CACHE)?.value;if(!saved)return;
 if(saved.wifi)renderWifiHeader(saved.wifi);
 if(saved.modem)renderHeader(saved.modem);
 for(const key of ['modem','sim','network','wifi'])portalFreshness(key,true);
}
let portalLastSignal=null;
function portalFreshness(key,stale){
 const chip=document.getElementById('chip-'+key),detail=document.getElementById(key+'-status'),summary=document.getElementById('chip-'+key+'-summary');
 if(chip){if(stale)chip.dataset.stale='true';else delete chip.dataset.stale}
 if(detail){if(stale&&!detail.dataset.stale){detail.textContent+='\nDữ liệu lần gần nhất; chưa cập nhật được.';detail.dataset.stale='true'}else if(!stale)delete detail.dataset.stale}
 if(summary){if(stale&&!summary.dataset.stale){summary.title=(summary.title||'')+' · Dữ liệu lần gần nhất; chưa cập nhật được.';summary.dataset.stale='true'}else if(!stale){summary.title='';delete summary.dataset.stale}}
}
function renderHeader(c){
 const set=(id,text)=>{const e=document.getElementById(id);if(e)e.textContent=text};
 const state=(id,value)=>{const e=document.getElementById('chip-'+id);if(e)e.dataset.state=value};
 const summary=(id,text)=>{const e=document.getElementById('chip-'+id+'-summary');if(e){e.setAttribute('aria-label',text);e.title=text}};
 const network=document.getElementById('chip-network');
 if(!c||typeof c.registered!=='boolean'||typeof c.sim_present!=='boolean'){for(const k of ['modem','sim','network'])portalFreshness(k,true);return}
 for(const k of ['modem','sim','network'])portalFreshness(k,false);
 set('chip-modem-label',c.registered?'Online':c.state||'Modem');state('modem',c.registered?'ready':'warning');
 const knownCarrier=c.registered&&typeof c.operator_name==='string'&&c.operator_name.trim()?c.operator_name.trim():null;
 const measuredTechnology=c.access_technologies&32768?'5G':c.access_technologies&16384?'4G':c.access_technologies&16352?'3G':c.access_technologies&28?'2G':null;
 const validSignal=c.sim_present&&!c.sim_locked&&c.registered&&c.signal_recent===true&&Number.isFinite(c.signal_percent)&&c.signal_percent>=0&&c.signal_percent<=100;
 // A missing operator, a transient unregistered response or stale signal is
 // not proof of a network switch. SIM removal/locking and a *known* new
 // operator are authoritative invalidations.
 if(!c.sim_present||c.sim_locked||(portalLastSignal?.carrier&&knownCarrier&&portalLastSignal.carrier!==knownCarrier))portalLastSignal=null;
 if(!portalLastSignal&&c.last_signal&&c.sim_present&&!c.sim_locked&&
    Number.isFinite(c.last_signal.percent)&&c.last_signal.percent>=0&&c.last_signal.percent<=100&&
    (!knownCarrier||!c.last_signal.carrier||knownCarrier===c.last_signal.carrier)){
  portalLastSignal={percent:c.last_signal.percent,carrier:c.last_signal.carrier||null,technology:c.last_signal.technology||null};
 }
 if(validSignal)portalLastSignal={percent:c.signal_percent,carrier:knownCarrier||portalLastSignal?.carrier||null,technology:measuredTechnology||portalLastSignal?.technology||null};
 const previousCarrier=portalLastSignal?.carrier||null;
 const carrier=!c.sim_present?'No SIM':c.sim_locked?'SIM khóa':!c.registered?'Chưa đăng ký':knownCarrier||previousCarrier||'Chưa rõ';
 set('chip-sim-label',carrier);state('sim',c.sim_present&&!c.sim_locked?'ready':'warning');summary('sim','Nhà mạng: '+carrier+'. Bấm xem thông tin SIM.');
 const technology=!c.sim_present?'No SIM':c.sim_locked?'Khóa':!c.registered?'Tìm mạng':measuredTechnology||portalLastSignal?.technology||'Mạng';
 const shownSignal=validSignal?c.signal_percent:portalLastSignal?.percent;
 const bars=shownSignal==null?null:Math.ceil(shownSignal/25);
 if(network)network.dataset.bars=bars==null?'unknown':String(bars);
 const serving=portalLteCarriers(c),bandSummary=[...new Set(serving.map(v=>'B'+v.band))].join('/');
 const bandDetail=serving.length?serving.map(v=>'B'+v.band+' · '+v.nominal_mhz+' MHz (DL '+v.downlink_mhz+' MHz · EARFCN '+v.earfcn+')').join('; '):'chưa đọc được';
 set('chip-network-label',technology+(bandSummary?' · '+bandSummary:''));state('network',c.registered&&bars!=null?'ready':'warning');
 summary('network','Mạng '+technology+', '+(bars==null?'chưa có mức sóng mới':bars+'/4 vạch, '+shownSignal+'%'+(validSignal?'':' (lần đo gần nhất)'))+'. Bấm xem chi tiết.');
 set('modem-status','Modem: '+(c.state||'chưa xác định')+'\n'+(c.registered?'Đã đăng ký mạng.':'Chưa đăng ký mạng.'));
 set('modem-readiness',c.registered?'Modem đang hoạt động, không cần kích hoạt thêm.':c.can_enable?'Modem đang tắt. Mở Cài đặt nhanh để cho phép di động.':'Đang chờ SIM hoặc đăng ký mạng.');
 set('sim-status',!c.sim_present?'Chưa có SIM sẵn sàng.':c.sim_locked?'SIM đang yêu cầu mở khóa chính. Không tự đoán PIN.':'Nhà mạng: '+carrier+'\nSIM đã được nhận.'+(c.secondary_lock?'\n'+c.secondary_lock.toUpperCase()+': khóa phụ, không chặn modem hoạt động.':'')+'\nBăng LTE đang dùng: '+bandDetail);
 set('network-status','Nhà mạng: '+carrier+'\nMạng đang dùng: '+(!c.registered?'chưa có kết nối':measuredTechnology?portalTechnology(c.access_technologies):portalLastSignal?.technology||portalTechnology(c.access_technologies))+'\nĐăng ký: '+(c.registered?'đã đăng ký':'chưa đăng ký')+'\nBăng LTE đang dùng: '+bandDetail+'\nNguồn Internet: kiểm tra tại Wi-Fi & Web / Phát Wi-Fi từ SIM.');
 set('signal-status',validSignal?bars+'/4 vạch · '+c.signal_percent+'% — chất lượng do modem báo.\nSố liệu gần đây.':shownSignal!=null?bars+'/4 vạch · '+shownSignal+'% — lần đo gần nhất; chưa có cập nhật mới.':!c.sim_present?'Không có SIM để đo sóng.':c.sim_locked?'SIM đang khóa, chưa có mức sóng khả dụng.':!c.registered?'Chưa đăng ký mạng; chưa có mức sóng kết nối.':'Chưa có số liệu mức sóng hợp lệ.');
 if(c.sim_present&&!c.sim_locked&&!validSignal)portalFreshness('network',true);
 if(c.sim_present&&!c.sim_locked&&!knownCarrier&&previousCarrier)portalFreshness('sim',true);
}
function renderWifiHeader(w){
 const chip=document.getElementById('chip-wifi'),label=document.getElementById('chip-wifi-label'),detail=document.getElementById('wifi-status'),link=document.getElementById('wifi-settings-link');
 if(!chip||!label||!detail)return;
 if(!w||typeof w.connected!=='boolean'&&typeof w.hotspot_active!=='boolean'){portalFreshness('wifi',true);return}
 portalFreshness('wifi',false);
 const ap=w.hotspot_active===true,connected=w.connected===true;
 label.textContent=w.setup_active?'Cài Wi-Fi':ap?'Hotspot':connected?'Wi-Fi':'Wi-Fi tắt';chip.dataset.state=ap||connected?'ready':'warning';
 const lines=[ap?'Chế độ: phát Wi-Fi từ USB':connected?'Chế độ: kết nối Wi-Fi':'Wi-Fi chưa kết nối / không phát hotspot'];
 if(ap||connected){lines.push('Tên mạng: '+(w.ssid||'chưa xác định'));if(ap)lines.push('Kênh: '+(w.channel||'chưa xác định'));else lines.push('Mức sóng: '+(w.signal_percent==null?'chưa có số liệu':w.signal_percent+'%')+(w.signal_dbm==null?'':' ('+w.signal_dbm+' dBm)'));lines.push('IPv4: '+((w.ipv4||[]).join(', ')||'chưa có'));if(!ap)lines.push('Gateway: '+(w.gateway||'chưa có'));lines.push('Kết nối Wi-Fi không xác nhận Internet đang hoạt động.')}
 if(w.setup_active)lines.push('Hotspot cài đặt: không cần SIM, không chia sẻ Internet.');
 detail.textContent=lines.join('\n');if(link){link.href=ap?'/setup#usb-ap-settings':'/setup';link.textContent=ap?'Cấu hình Wi-Fi phát →':'Cài đặt Wi-Fi →'}
}
// Only allowlisted display GETs use this helper. Never retry a mutation.
const portalTelemetryReads=new Map();
async function portalReadTelemetry(path){
 if(!['/api/header','/api/overview','/api/quick','/api/services','/api/modem/status','/api/internet/status','/api/wifi/profiles'].includes(path))throw Error('STATUS_UNAVAILABLE');
 if(portalTelemetryReads.has(path))return portalTelemetryReads.get(path);
 const token=document.querySelector('.portal-header')?.dataset.statusToken;if(!token)throw Error('STATUS_UNAVAILABLE');
 const pending=(async()=>{
  const end=Date.now()+15000;let delay=1000;
  do{
   const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),5000);
   try{
    const response=await fetch(path,{headers:{'X-OpenStick-Token':token},cache:'no-store',signal:controller.signal});
    if(response.status===401){location.href='/login';throw Error('STATUS_UNAVAILABLE')}
    const value=await response.json();
    // The server already started a bounded refresh. Render its retained sample
    // immediately with the existing stale indicator instead of polling it 15x.
    if(response.ok)return value;
    else if(response.status!==503||value.error!=='STATUS_PENDING')throw Error('STATUS_UNAVAILABLE');
   }catch(error){if(error.message==='STATUS_UNAVAILABLE')throw error;}finally{clearTimeout(timer)}
   if(document.hidden||Date.now()+delay>=end)break;
   await new Promise(resolve=>setTimeout(resolve,delay));delay=Math.min(4000,delay*2);
  }while(Date.now()<end&&!document.hidden);
  throw Error('STATUS_UNAVAILABLE');
 })();
 portalTelemetryReads.set(path,pending);
 try{return await pending}finally{portalTelemetryReads.delete(path)}
}
let portalHeaderSample=null,portalHeaderAt=0,portalHeaderRequest=null,portalHeaderFollowup=null;
async function portalLoadHeader(followup=false){
 if(portalHeaderSample&&Date.now()-portalHeaderAt<Math.max(0,5000-(portalHeaderSample._telemetry?.age_seconds||0)*1000))return portalHeaderSample;
 if(portalHeaderRequest)return portalHeaderRequest;
 portalHeaderRequest=(async()=>{
  const value=await portalReadTelemetry('/api/header');portalHeaderSample=value;portalHeaderAt=Date.now();
  renderWifiHeader(value);renderHeader(value.modem_status||null);
  if(value._telemetry?.stale){for(const key of ['modem','sim','network','wifi'])portalFreshness(key,true)}else portalRememberHeader(value);
  // One delayed read per ordinary refresh, never an unbounded stale retry loop.
  if(value._telemetry?.stale&&value._telemetry?.refreshing&&!followup&&portalHeaderFollowup===null){
   portalHeaderFollowup=setTimeout(()=>{portalHeaderFollowup=null;if(!document.hidden)portalLoadHeader(true).catch(()=>{})},2000);
  }
  if(typeof renderOverviewConnections==='function')renderOverviewConnections(value);
  return value;
 })();
 try{return await portalHeaderRequest}finally{portalHeaderRequest=null}
}
function setupHeaderStatus(){
 const header=document.querySelector('.portal-header'),token=header?.dataset.statusToken;if(!token)return;
 let pending=false;
 const refresh=async()=>{if(pending||document.hidden)return;pending=true;
  try{await portalLoadHeader()}catch(_){renderWifiHeader(null);renderHeader(null)}finally{pending=false}
 };
 refresh();setInterval(refresh,60000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
}
// The header is already parsed at this script position. Restore before the
// rest of the document loads to avoid a waiting-state flash on navigation.
if(typeof document!=='undefined')portalRestoreHeader();
function setupStatusPopovers(root=document){
 const chips=Array.from(root.querySelectorAll('.status-chip'));
 const closeExcept=keep=>chips.forEach(chip=>{if(chip!==keep)chip.open=false});
 root.addEventListener('click',event=>closeExcept(chips.find(chip=>chip.contains(event.target))));
 root.addEventListener('keydown',event=>{if(event.key==='Escape')closeExcept(null)});
 chips.forEach(chip=>chip.addEventListener('toggle',()=>{if(chip.open)closeExcept(chip)}));
}
if(typeof window!=='undefined')window.addEventListener('DOMContentLoaded',()=>{
 const logout=document.querySelector('.access-banner form[action="/logout"]');
 logout?.addEventListener('submit',()=>{try{sessionStorage.removeItem(portalScopedCacheKey(PORTAL_HEADER_CACHE));sessionStorage.removeItem(portalScopedCacheKey('openstick-overview-display-v2'));for(const store of [sessionStorage,localStorage])for(const key of Object.keys(store))if(key.startsWith('openstick-settings-display-v1-'))store.removeItem(key)}catch(_){}});
 setupStatusPopovers();
 setupHeaderStatus();
 const nav=document.getElementById('portal-nav');if(!nav)return;
 const root=document.scrollingElement||document.documentElement;
 const position=()=>boundedScrollPosition(root.scrollTop,root.scrollHeight-root.clientHeight);
 const tracker=new BottomNavScrollTracker(position(),performance.now());
 let width=window.innerWidth,height=window.innerHeight;
 const publish=hidden=>{if(hidden){nav.dataset.scrollHidden='true';nav.setAttribute('aria-hidden','true')}else{delete nav.dataset.scrollHidden;nav.removeAttribute('aria-hidden')}nav.inert=hidden;nav.querySelectorAll('a').forEach(a=>a.tabIndex=hidden?-1:0)};
 const resize=()=>{width=window.innerWidth;height=window.innerHeight;tracker.rebase(position(),performance.now())};
 window.addEventListener('scroll',event=>{
  if(![document,window,root].includes(event.target))return;
  if(width!==window.innerWidth||height!==window.innerHeight||document.body.style.overflow==='hidden'||document.querySelector('[aria-modal="true"]')||(nav.contains(document.activeElement)&&document.activeElement?.matches(':focus-visible'))){resize();return}
  publish(tracker.sample(position(),performance.now()));
 },{passive:true,capture:true});
 window.addEventListener('resize',resize,{passive:true});window.visualViewport?.addEventListener('resize',resize,{passive:true});
},{once:true});

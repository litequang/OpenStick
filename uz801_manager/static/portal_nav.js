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
function portalDisplayModem(modem){
 if(!modem||typeof modem.registered!=='boolean'||typeof modem.sim_present!=='boolean')return null;
 const result={};for(const key of ['state','registered','sim_present','sim_locked','operator_name','access_technologies','signal_percent','signal_recent','secondary_lock','can_enable'])if(Object.hasOwn(modem,key))result[key]=modem[key];
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
 const knownCarrier=typeof c.operator_name==='string'&&c.operator_name.trim()?c.operator_name.trim():null;
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
 const carrier=!c.sim_present?'No SIM':c.sim_locked?'SIM khóa':knownCarrier||previousCarrier||'Chưa rõ';
 set('chip-sim-label',carrier);state('sim',c.sim_present&&!c.sim_locked?'ready':'warning');summary('sim','Nhà mạng: '+carrier+'. Bấm xem thông tin SIM.');
 const technology=!c.sim_present?'No SIM':c.sim_locked?'Khóa':measuredTechnology||portalLastSignal?.technology||(!c.registered?'Tìm':'Mạng');
 const shownSignal=validSignal?c.signal_percent:portalLastSignal?.percent;
 const bars=shownSignal==null?null:Math.ceil(shownSignal/25);
 if(network)network.dataset.bars=bars==null?'unknown':String(bars);
 set('chip-network-label',technology);state('network',bars!=null?'ready':'warning');
 summary('network','Mạng '+technology+', '+(bars==null?'chưa có mức sóng mới':bars+'/4 vạch, '+shownSignal+'%'+(validSignal?'':' (lần đo gần nhất)'))+'. Bấm xem chi tiết.');
 set('modem-status','Modem: '+(c.state||'chưa xác định')+'\n'+(c.registered?'Đã đăng ký mạng.':'Chưa đăng ký mạng.'));
 set('modem-readiness',c.registered?'Modem đang hoạt động, không cần kích hoạt thêm.':c.can_enable?'Modem đang tắt. Mở Cài đặt nhanh để cho phép di động.':'Đang chờ SIM hoặc đăng ký mạng.');
 set('sim-status',!c.sim_present?'Chưa có SIM sẵn sàng.':c.sim_locked?'SIM đang yêu cầu mở khóa chính. Không tự đoán PIN.':'Nhà mạng: '+carrier+'\nSIM đã được nhận.'+(c.secondary_lock?'\n'+c.secondary_lock.toUpperCase()+': khóa phụ, không chặn modem hoạt động.':''));
 set('network-status','Nhà mạng: '+carrier+'\nMạng đang dùng: '+(measuredTechnology?portalTechnology(c.access_technologies):portalLastSignal?.technology||portalTechnology(c.access_technologies))+'\nĐăng ký: '+(c.registered?'đã đăng ký':'chưa đăng ký')+'\nNguồn Internet: kiểm tra tại Wi-Fi & Web / Phát Wi-Fi từ SIM.');
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
function setupHeaderStatus(){
 const header=document.querySelector('.portal-header'),token=header?.dataset.statusToken;if(!token)return;
 let pending=false;
 const refresh=async()=>{if(pending||document.hidden)return;pending=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
  try{const response=await fetch('/api/header',{headers:{'X-OpenStick-Token':token},signal:controller.signal});if(!response.ok)throw Error();const value=await response.json();renderWifiHeader(value);renderHeader(value.modem_status||null);portalRememberHeader(value)}catch(_){renderWifiHeader(null);renderHeader(null)}finally{clearTimeout(timer);pending=false}
 };
 refresh();setInterval(refresh,15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
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
 logout?.addEventListener('submit',()=>{try{sessionStorage.removeItem(portalScopedCacheKey(PORTAL_HEADER_CACHE));sessionStorage.removeItem(portalScopedCacheKey('openstick-overview-display-v2'))}catch(_){}});
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

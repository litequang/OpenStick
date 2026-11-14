// Adapted from thophuongpro @83adf488: bottomNavScroll.ts / useBottomNavAutoHide.ts.
const BOTTOM_NAV_SCROLL={top:12,downSpeed:.65,downDistance:72,upDistance:18,noise:3,sampleGap:180};
function boundedScrollPosition(position,maximum){return Math.max(0,Math.min(Number.isFinite(position)?position:0,Math.max(0,maximum)))}
class BottomNavScrollTracker{
 constructor(y,time,hidden=false){this.y=y;this.time=time;this.hidden=hidden;this.down=0;this.up=0}
 rebase(y,time){this.y=y;this.time=time;this.down=0;this.up=0}
 sample(y,time){const delta=y-this.y,elapsed=time-this.time;this.y=y;this.time=time;if(y<=BOTTOM_NAV_SCROLL.top){this.hidden=false;this.down=0;this.up=0;return this.hidden}if(elapsed<=0)return this.hidden;if(elapsed>BOTTOM_NAV_SCROLL.sampleGap){this.down=0;this.up=0}if(delta>0){this.up=delta>=BOTTOM_NAV_SCROLL.noise?0:Math.max(0,this.up-delta);if(elapsed<=BOTTOM_NAV_SCROLL.sampleGap&&delta>=BOTTOM_NAV_SCROLL.noise&&delta/elapsed>=BOTTOM_NAV_SCROLL.downSpeed)this.down+=delta;else this.down=0;if(this.down>=BOTTOM_NAV_SCROLL.downDistance)this.hidden=true}else if(delta<0){this.down=0;this.up-=delta;if(this.up>=BOTTOM_NAV_SCROLL.upDistance)this.hidden=false}return this.hidden}
}
function portalTechnology(value){if(value==null||value===0)return 'chưa xác định';const names=[];for(const [flag,label] of [[32768,'5G'],[16384,'4G LTE'],[8192,'3G HSPA+'],[4096,'3G EVDO-B'],[2048,'3G EVDO-A'],[1024,'3G EVDO'],[512,'CDMA 1x'],[256,'3G HSPA'],[128,'3G HSUPA'],[64,'3G HSDPA'],[32,'3G UMTS'],[16,'2G EDGE'],[8,'2G GPRS'],[4,'2G GSM']])if(value&flag)names.push(label);return names.join(' / ')||'chưa xác định'}
function renderHeader(c){
 const set=(id,text)=>{const e=document.getElementById(id);if(e)e.textContent=text};
 const state=(id,value)=>{const e=document.getElementById('chip-'+id);if(e)e.dataset.state=value};
 if(!c){for(const k of ['modem','sim','network']){set('chip-'+k+'-label','Chờ');state(k,'warning')}return}
 set('chip-modem-label',c.registered?'Online':c.state||'Modem');state('modem',c.registered?'ready':'warning');
 set('chip-sim-label',!c.sim_present?'No SIM':c.sim_locked?'Khóa':c.signal_percent==null?'SIM':'SIM '+c.signal_percent+'%');state('sim',c.sim_present&&!c.sim_locked&&c.signal_recent?'ready':'warning');
 set('chip-network-label',c.access_technologies&16384?'4G':c.registered?'Mạng':'Tìm');state('network',c.registered?'ready':'warning');
 set('modem-status','Modem: '+(c.state||'chưa xác định')+'\n'+(c.registered?'Đã đăng ký mạng.':'Chưa đăng ký mạng.'));
 set('modem-readiness',c.registered?'Modem đang hoạt động, không cần kích hoạt thêm.':c.can_enable?'Modem đang tắt. Vào Mạng SIM để bật.':'Đang chờ SIM hoặc đăng ký mạng.');
 set('sim-status',!c.sim_present?'Chưa có SIM sẵn sàng.':c.sim_locked?'SIM đang yêu cầu mở khóa chính. Không tự đoán PIN.':'SIM đã được nhận.'+(c.secondary_lock?'\n'+c.secondary_lock.toUpperCase()+': khóa phụ, không chặn modem hoạt động.':''));
 set('network-status','Nhà mạng: '+(c.operator_name||'chưa xác định')+'\nMạng đang dùng: '+portalTechnology(c.access_technologies)+'\nĐăng ký: '+(c.registered?'đã đăng ký':'chưa đăng ký')+'\nNguồn Internet: kiểm tra tại Wi-Fi & Web / Phát Wi-Fi từ SIM.');
 set('signal-status',c.signal_percent==null?'Chưa có số liệu mức sóng.':c.signal_percent+'% — chất lượng do modem báo.\n'+(c.signal_recent?'Số liệu gần đây.':'Số liệu cũ, chưa có cập nhật mới.'));
}
function renderWifiHeader(w){
 const chip=document.getElementById('chip-wifi'),label=document.getElementById('chip-wifi-label'),detail=document.getElementById('wifi-status'),link=document.getElementById('wifi-settings-link');
 if(!chip||!label||!detail)return;
 if(!w){label.textContent='Wi-Fi ?';chip.dataset.state='warning';detail.textContent='Chưa đọc được trạng thái Wi-Fi. Thông tin có thể đã thay đổi.';return}
 const ap=w.hotspot_active===true,connected=w.connected===true;
 label.textContent=w.setup_active?'Cài Wi-Fi':ap?'Hotspot':connected?'Wi-Fi':'Wi-Fi tắt';chip.dataset.state=ap||connected?'ready':'warning';
 const lines=[ap?'Chế độ: phát Wi-Fi từ USB':connected?'Chế độ: kết nối Wi-Fi':'Wi-Fi chưa kết nối / không phát hotspot'];
 if(ap||connected){lines.push('Tên mạng: '+(w.ssid||'chưa xác định'));if(ap)lines.push('Kênh: '+(w.channel||'chưa xác định'));else lines.push('Mức sóng: '+(w.signal_percent==null?'chưa có số liệu':w.signal_percent+'%')+(w.signal_dbm==null?'':' ('+w.signal_dbm+' dBm)'));lines.push('IPv4: '+((w.ipv4||[]).join(', ')||'chưa có'));if(!ap)lines.push('Gateway: '+(w.gateway||'chưa có'));lines.push('Kết nối Wi-Fi không xác nhận Internet đang hoạt động.')}
 if(w.setup_active)lines.push('Hotspot cài đặt: không cần SIM, không chia sẻ Internet.');
 detail.textContent=lines.join('\n');if(link){link.href=w.setup_active?'/setup':ap?'/hotspot':'/';link.textContent=ap?'Quản lý hotspot →':'Cài đặt Wi-Fi →'}
}
function setupHeaderStatus(){
 const header=document.querySelector('.portal-header'),token=header?.dataset.statusToken;if(!token)return;
 let pending=false;
 const refresh=async()=>{if(pending||document.hidden)return;pending=true;const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
  try{const response=await fetch('/api/header',{headers:{'X-OpenStick-Token':token},signal:controller.signal});if(!response.ok)throw Error();const value=await response.json();renderWifiHeader(value);if(value.modem_status)renderHeader(value.modem_status)}catch(_){renderWifiHeader(null)}finally{clearTimeout(timer);pending=false}
 };
 refresh();setInterval(refresh,15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});
}
function setupStatusPopovers(root=document){
 const chips=Array.from(root.querySelectorAll('.status-chip'));
 const closeExcept=keep=>chips.forEach(chip=>{if(chip!==keep)chip.open=false});
 root.addEventListener('click',event=>closeExcept(chips.find(chip=>chip.contains(event.target))));
 root.addEventListener('keydown',event=>{if(event.key==='Escape')closeExcept(null)});
 chips.forEach(chip=>chip.addEventListener('toggle',()=>{if(chip.open)closeExcept(chip)}));
}
if(typeof window!=='undefined')window.addEventListener('DOMContentLoaded',()=>{
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

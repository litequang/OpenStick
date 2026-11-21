/* Read-only on load. Network mode cycles on explicit click; other changes use dialogs. */
(() => {
  const el = id => document.getElementById(id);
  const headers = {'Content-Type':'application/json', 'X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
  let current = null, busy = false, selected = null, refreshing=false, refreshAgain=false;
  let recoveryTimer=null, readFailed=false;
  const compact = !!document.querySelector('.quick-panel--compact');
  const errors = {
    AP_OPTIONS_INVALID:'Cấu hình điểm phát không khớp. Lưu lại tại Cài đặt Wi-Fi qua cổng USB trước khi bật phát.',
    AP_OPTIONS_UNAVAILABLE:'Chưa truy cập được backend điểm phát để đặt giới hạn thiết bị. Chưa bật phát với giới hạn chưa xác nhận; kiểm tra qua USB.',
    AP_OPTIONS_APPLY_FAILED:'Backend chưa xác nhận giới hạn/cách ly. Không giữ điểm phát mới; kiểm tra qua USB, không tự gửi lại.',
    AP_OPTIONS_ROLLBACK_FAILED:'Chưa hoàn tác đầy đủ tùy chọn điểm phát. Giữ kết nối USB để kiểm tra.',
    AP_LEGACY_ACTIVE:'Còn chế độ hotspot cũ tự bật. Dùng Cài đặt nhanh để dừng cơ chế cũ trước khi lưu tùy chọn nâng cao.',
    NETWORK_SAVE_FAILED:'Mạng có thể đã đổi nhưng chưa lưu được chế độ khởi động. Giữ USB cắm và kiểm tra lại; chưa xác nhận lưu thành công.',
    SIM_NOT_READY:'SIM chưa sẵn sàng hoặc chưa đăng ký được mạng. Kiểm tra trạng thái SIM và nhà mạng; không tự thay APN hoặc tháo SIM khi USB đang chạy.',
    AIRPLANE_ACTIVE:'Tắt chế độ máy bay trước. Việc đó không tự bật dữ liệu SIM.',
    MODEM_BUSY:'Modem đang có giao dịch. Đợi kết thúc SMS/USSD rồi thử lại.',
    NETWORK_BUSY:'USB đang thực hiện thao tác mạng khác.',
    PENDING_NETWORK_TRIAL:'Hoàn tất hoặc hủy lượt thử tại mục Phát Wi-Fi trước.',
    CELLULAR_ALREADY_ACTIVE:'Có cấu hình/kết nối SIM ngoài quyền điều khiển của tính năng này; cần kiểm tra qua USB.',
    CELLULAR_NOT_CONFIGURED:'Lưu APN/cấu hình SIM ở mục Phát Wi-Fi trước.',
    DATA_OFF_AP_FAILED:'Dữ liệu SIM đã được yêu cầu tắt nhưng chưa phát lại Wi-Fi nội bộ được. Giữ USB cắm để quản trị; không tự bật lại data.',
    ALREADY_ATTEMPTED:'Yêu cầu này đã có receipt. Không gửi lại thao tác.',
    RADIO_RESULT_UNKNOWN:'Chưa xác minh được kết quả radio. Kiểm tra lại trạng thái; không tự gửi lại.',
    LOCAL_AP_UNAVAILABLE:'Wi-Fi nội bộ chưa sẵn sàng. Kiểm tra cấu hình và mật khẩu quản trị qua USB.'
  };
  Object.assign(errors,{
    USB_NO_INTERNET:'Chưa có nguồn Internet hoạt động. Kết nối Wi-Fi nhà hoặc bật Dữ liệu SIM trước.',
    USB_DHCP_CONFLICT:'Dịch vụ cấp IP USB chưa sẵn sàng; giữ kết nối USB và kiểm tra lại.',
    USB_DHCP_RESTORE_FAILED:'Chưa khôi phục được dịch vụ cấp IP quản trị. Giữ nguyên cáp USB để kiểm tra.',
    USB_TETHERING_NOT_INSTALLED:'USB tethering chưa được cài trên thiết bị này.',
    USB_REBOOT_PENDING:'Đã lưu thay đổi USB, đang chờ khởi động lại. Không gửi thêm thao tác.',
    USB_REBOOT_FAILED:'Đã lưu chế độ nhưng chưa khởi động lại được. Có thể rút USB, đợi 10 giây rồi cắm lại bình thường để áp dụng.',
    USB_APPLY_FAILED:'USB đã khởi động lại nhưng chưa áp dụng được chia sẻ Internet. Mạng quản trị USB được giữ; cần kiểm tra lại.',
    DATA_CONNECT_FAILED:'Modem chưa kết nối được dữ liệu SIM. Không tự gửi lại hoặc đổi APN. Nếu vẫn kẹt khi SIM đã sẵn sàng, bạn có thể xác nhận bật rồi tắt chế độ máy bay, đợi đăng ký mạng và bật data lại.',
    USB_PROFILE_UNSUPPORTED:'Cấu hình USB khác cấu hình đã kiểm chứng; chưa thay đổi gadget.',
    USB_TETHERING_FIREWALL_FAILED:'Chưa áp dụng được chia sẻ Internet qua USB; chưa xác nhận bật thành công.'
  });
  Object.assign(errors,{
    WIFI_SAVED_NOT_FOUND:'Chưa kết nối được Wi-Fi đã lưu. Đã thử khôi phục mạng trước; chọn mạng trong danh sách để kết nối.',
    WIFI_PROFILE_NOT_FOUND:'Mạng này chưa còn trong danh sách đã lưu. Quét lại hoặc nhập mật khẩu.',
    WIFI_NOT_CONNECTED:'USB hiện chưa nhận Wi-Fi.',
    WIFI_CONNECT_FAILED:'Chưa nối được Wi-Fi. Đã thử khôi phục mạng trước; kiểm tra tên mạng và mật khẩu.',
    WIFI_AUTH_REQUIRED:'Wi-Fi yêu cầu lại mật khẩu. Nhập mật khẩu mới để kết nối.',
    WIFI_TIMEOUT:'Hết thời gian kết nối Wi-Fi. Kiểm tra bộ phát và mật khẩu.',
    WIFI_NOT_FOUND:'Chưa tìm thấy Wi-Fi. Quét lại hoặc nhập tên mạng ẩn.',
    WIFI_SCAN_FAILED:'Chưa quét được Wi-Fi; đã thử khôi phục mạng trước.',
    WIFI_RESTORE_FAILED:'Chưa khôi phục được Wi-Fi trước. Giữ kết nối USB để kiểm tra; không gửi lại thao tác.'
  });
  const notice = text => {el('quick-notice').textContent = text;};
  function operationId() {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const hex = Array.from(bytes, value => value.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
  }
  function tile(id, text, active, disabled) {
    const node = el(id); node.querySelector('small').textContent = text;
    node.dataset.active = String(active); node.disabled = disabled;
    node.setAttribute('aria-pressed', String(active));
  }
  function draw(s) {
    current = s;
    const saved=el('quick-startup-status');
    if(saved) saved.textContent=s.startup?.saved?
      'Đã lưu khi bật nguồn: '+({ap:'Phát Wi-Fi',station:'Nhận Wi-Fi',off:'Wi-Fi tắt'}[s.startup.wifi_role]||'Wi-Fi')+
      ' · '+(s.startup.data_on&&s.intent?.data_allowed&&!s.intent?.airplane?'Dữ liệu SIM bật':'Dữ liệu SIM tắt')+'.':
      'Thay đổi mạng thành công sẽ được lưu cho lần cấp nguồn sau.';
    drawMode();
    const airplane = s.intent?.airplane === true, blocked = busy || s.pending_network_trial || s.foreign_cellular_active;
    tile('quick-airplane', airplane?(compact?'Đã yêu cầu tắt':'Đã yêu cầu tắt di động'):(compact?'Cho phép di động':'Di động được cho phép'), airplane, blocked);
    const wantsData = s.intent?.data_allowed === true && !airplane;
    const recovery = s.cellular_recovery || {};
    const recoveryText = recovery.error==='STATE_INVALID'?'Lỗi trạng thái · cần kiểm tra USB':({WAITING_NETWORK:'Đang chờ đăng ký mạng',WAITING_RECONNECT:'Mất kết nối · chờ nối lại',ATTEMPTING:'Đang nối lại phiên SIM',UNKNOWN:'Mất mạng · tắt/bật để thử lại',LIMIT_REACHED:'Đã dừng tự nối · cần kiểm tra'})[recovery.phase] || 'Đã yêu cầu bật · chưa kết nối';
    tile('quick-data', s.mobile_data_connected?(compact?'Bật · Internet chưa đo':'Đã kết nối · Internet chưa xác minh'):wantsData?recoveryText:!s.radio.sim_ready?(compact?'Chưa có SIM':'Chưa có SIM sẵn sàng'):'Đang tắt', wantsData || s.mobile_data_connected, blocked || (!wantsData && !s.mobile_data_connected && (airplane || !s.radio.registered || !s.radio.sim_ready)));
    const ap = ['local_ap','sim_ap'].includes(s.wifi_role);
    tile('quick-ap', ap?(s.mobile_data_connected?'Đang phát · có phiên SIM':wantsData?'Đang phát · SIM mất kết nối':'Đang phát · không Internet'):'Đang tắt', ap, blocked);
    tile('quick-usb', !s.usb_tethering.available?'Chưa được cài':s.usb_tethering.reboot_pending?'Đã lưu · đang áp dụng':s.usb_tethering.degraded?'Chưa xác minh · chạm để tắt':s.usb_tethering.enabled?'Đang chia sẻ Internet':'Tắt · chạm để bật', !!s.usb_tethering.enabled, blocked || !s.usb_tethering.available);
    tile('quick-receive',(compact?{station:'Đã nối · chạm để đổi',local_ap:'Chạm để nhận Wi-Fi',sim_ap:'Chạm để nhận Wi-Fi',offline:'Chạm để kết nối'}:{station:'Đã kết nối · chọn để xem hoặc đổi',local_ap:'Chạm để chuyển sang nhận Wi-Fi',sim_ap:'Chạm để chuyển sang nhận Wi-Fi',offline:'Tự nối mạng đã lưu hoặc chọn mạng mới'})[s.wifi_role] || 'Chưa xác định',s.wifi_role==='station',blocked);
    const modemState=!s.radio.registered&&s.radio.state>=8?'Chưa đăng ký mạng · chưa có kết nối xác minh':({'-1':'Chưa sẵn sàng',0:'Chưa xác định',1:'Đang khởi tạo',2:'SIM đang khóa',3:'Đã tắt',4:'Đang tắt',5:'Đang bật',6:'Đã bật',7:'Đang tìm mạng',8:'Đã đăng ký mạng',9:'Đang ngắt dữ liệu',10:'Đang kết nối dữ liệu',11:'Đã kết nối dữ liệu'})[s.radio.state] || 'Chưa xác định';
    if (el('quick-details')) el('quick-details').textContent = `SIM: ${s.radio.sim_ready?'sẵn sàng':'chưa sẵn sàng'}\nModem: ${modemState}\n${s.pending_network_trial?'Đang có lượt thử mạng.':'Không có lượt thử mạng.'}\nCác chức năng mới: đang kiểm chứng phần cứng.`;
  }
  let modeStatus = null;
  const modeName = ([a,p]) => a===8?'Chỉ 4G':a===4?'Chỉ 3G':a!==12?'Chế độ khác':p===8?'3G/4G · ưu tiên 4G':p===4?'3G/4G · ưu tiên 3G':'3G/4G tự động';
  const modeChoices = c => [[8,0],[4,0],[12,0],[12,8],[12,4]].filter(pair => (c.supported_modes||[]).some(m=>m[0]===pair[0]&&m[1]===pair[1]));
  function drawMode() {
    const node=el('quick-mode');if(!node)return;
    const c=modeStatus, modes=c?modeChoices(c):[];
    node.disabled=busy||!c?.can_set_mode||[2,3].includes(c?.ussd_state)||modes.length<2||!!current?.pending_network_trial;
    if(c?.current_mode)node.querySelector('small').textContent=modeName(c.current_mode)+' · chạm để đổi';
    else if(!c)node.querySelector('small').textContent='Chưa đọc được chế độ';
  }
  async function readMode() {
    if(!el('quick-mode'))return;
    try{const value=await portalLoadHeader(),c=value.modem_status;if(c){modeStatus=c;if(!value._telemetry?.stale)globalThis.portalRememberSettings?.('modem',c);drawMode();return !value._telemetry?.stale;}}catch(_){}drawMode();return false;
  }
  if(el('quick-mode'))el('quick-mode').onclick=async()=>{
    if(busy||el('quick-mode').disabled)return;
    busy=true;draw(current);drawMode();
    let target;
    try {
      const c=modeStatus; // The backend validates live capabilities before changing modes.
      if(!c?.can_set_mode||[2,3].includes(c.ussd_state))throw Error('MODEM_BUSY');
      const modes=modeChoices(c);if(modes.length<2)throw Error('UNSUPPORTED');
      const index=modes.findIndex(m=>m[0]===c.current_mode[0]&&m[1]===c.current_mode[1]);
      target=modes[(index+1)%modes.length];
      notice('Đang chuyển sang '+modeName(target)+'; mạng SIM có thể tạm ngắt.');
      const r=await fetch('/api/modem',{method:'POST',headers,body:JSON.stringify({action:'mode',allowed:target[0],preferred:target[1],confirm:true})});
      if(!r.ok)throw Error('MODEM_BUSY');
      const deadline=Date.now()+90000;
      let done=false;
      while(Date.now()<deadline){
        const poll=await fetch('/api/modem/state',{headers,cache:'no-store'});if(!poll.ok)throw Error('RESULT_UNKNOWN');
        const state=await poll.json();if(!state.busy){if(state.error)throw Error(state.error);done=true;break;}
        await new Promise(resolve=>setTimeout(resolve,700));
      }
      if(!done)throw Error('RESULT_UNKNOWN');
      await readMode();
      if(modeStatus?.current_mode?.join(',')!==target.join(','))throw Error('RESULT_UNKNOWN');
      notice('Đã chuyển sang '+modeName(target)+'.');
    }catch(e){notice(errors[e.message]||'Chưa xác minh được chế độ mạng. Đọc lại trạng thái; không tự gửi lại.');}
    finally{busy=false;await refresh(true);drawMode();}
  };
  async function refresh(force=false) {
    if(refreshing){refreshAgain=refreshAgain||force;return}refreshing=true;
    try {
      const value=await portalReadTelemetry('/api/quick');
      if(!busy)draw(value);
      if(!value._telemetry?.stale)globalThis.portalRememberSettings?.('quick',value);
      readMode(); // Mode telemetry must not hold up the other Quick Settings.
      if(value._telemetry?.stale)throw Error();
      if (readFailed || el('quick-notice').textContent === 'Đang đọc trạng thái…') notice('Chạm một ô để xem và xác nhận thay đổi.');
      readFailed=false;
      if(recoveryTimer){clearTimeout(recoveryTimer);recoveryTimer=null;}
    } catch (_) {
      readFailed=true;
      if(current)draw(current);
      else for (const id of ['quick-airplane','quick-data','quick-ap','quick-usb','quick-receive']) el(id).disabled = true;
      notice(current?'Số liệu lần đọc trước · đang cập nhật nền. Bạn vẫn có thể chọn cài đặt; USB kiểm tra lại trước khi áp dụng.':'Đang lấy trạng thái đầu tiên. Trang sẽ tự đọc lại; bạn vẫn có thể mở các mục cài đặt khác.');
      if(!recoveryTimer&&!document.hidden)recoveryTimer=setTimeout(()=>{recoveryTimer=null;if(!busy)refresh();},2000);
    }finally{refreshing=false;if(refreshAgain){refreshAgain=false;refresh()}}
  }
  function ask(action, copy, values={}) {
    if (busy || !current) return;
    if(el('quick-wifi-dialog').open)el('quick-wifi-dialog').close();
    selected = {action,values}; el('quick-dialog-copy').textContent = copy; el('quick-dialog').returnValue='cancel';el('quick-dialog').showModal();
  }
  async function apply(action,values={}) {
    if (busy) return;
    busy = true; if(current) draw(current); notice('Đang thực hiện. Nếu mất kết nối, mở lại trang để đọc trạng thái; không gửi lại lệnh.');
    let operation;
    let chooseWifi=false, wifiMessage='';
    // Keep only an operation ID, never radio identities or credentials.
    try {
      operation = operationId();
      try {sessionStorage.setItem('openstick-quick-operation', operation);} catch (_) {}
      let r;
      try {r = await fetch('/api/quick', {method:'POST',headers,body:JSON.stringify({action,operation,confirm:true,...values,...(['data_on','usb_tether_on'].includes(action)?{cellular_consent:true}:{})})});}
      catch (_) {await poll(operation,action);return;}
      if (!r.ok) {const result = await r.json();throw Error(result.error || 'QUICK_OPERATION_FAILED');}
      await poll(operation,action);
      chooseWifi=action==='wifi_scan';
    } catch (error) {wifiMessage=errors[error.message] || 'Chưa xác minh được kết quả. Kiểm tra trạng thái qua USB trước khi thử tiếp.';notice(wifiMessage);chooseWifi=action.startsWith('wifi_')&&error.message!=='WIFI_RESTORE_FAILED';}
    finally {values={};busy = false; await refresh(true);if(chooseWifi)await showWifi(wifiMessage);}
  }
  async function poll(operation,action=null) {
    const deadline = Date.now()+210000;
    let rebooting = ['usb_tether_on','usb_tether_off'].includes(action);
    while (Date.now()<deadline) {
      let r;
      try {r = await fetch('/api/quick/operation/'+operation, {headers,cache:'no-store'});}
      catch (error) {if(!rebooting)throw error;await new Promise(resolve=>setTimeout(resolve,2000));continue;}
      if (rebooting && !r.ok) {
        if (r.status===403) {
          try {
            const bootstrap=await fetch('/quick',{cache:'no-store'});
            if (bootstrap.redirected && new URL(bootstrap.url).pathname==='/login') {location.href='/login';return;}
            const doc=new DOMParser().parseFromString(await bootstrap.text(),'text/html');
            const token=doc.querySelector('.portal-header')?.dataset.statusToken;
            if(token)headers['X-OpenStick-Token']=token;
          } catch (_) {}
        }
        await new Promise(resolve=>setTimeout(resolve,2000));continue;
      }
      if (!r.ok) throw Error('RADIO_RESULT_UNKNOWN');
      const receipt = await r.json();
      if (receipt.error || receipt.failure) throw Error(receipt.error || receipt.failure);
      if (receipt.state==='COMPLETED') {
        if (['usb_tether_on','usb_tether_off'].includes(receipt.kind)) {
          const usb=receipt.usb_tethering;rebooting=true;
          if (usb?.apply_state==='REBOOT_FAILED') throw Error('USB_REBOOT_FAILED');
          if (usb?.apply_state==='APPLY_FAILED') throw Error('USB_APPLY_FAILED');
          if (usb?.operation!==operation) throw Error('RADIO_RESULT_UNKNOWN');
          if (usb.apply_state!=='APPLIED') {
            notice('Đã lưu. USB đang khởi động lại và áp dụng chế độ; giữ nguyên USB, trang sẽ tự kết nối lại…');
            await new Promise(resolve=>setTimeout(resolve,2000));continue;
          }
          if (usb.enabled!==(receipt.kind==='usb_tether_on')) throw Error('USB_APPLY_FAILED');
          notice(usb.enabled?'Đã bật chia sẻ USB sau khởi động lại. PC tự nhận cấu hình mạng; Internet phụ thuộc Wi-Fi hoặc dữ liệu SIM đang hoạt động.':'Đã tắt chia sẻ USB sau khởi động lại. USB vẫn dùng được để quản trị.');
        } else notice(receipt.kind==='wifi_scan'?'Đã quét xong. Chọn mạng để kết nối.':['wifi_auto','wifi_saved','wifi_connect'].includes(receipt.kind)?'Đã kết nối Wi-Fi. Internet cần được kiểm tra riêng; bấm ô Nhận Wi-Fi để xem hoặc đổi mạng.':'Đã hoàn tất. Trạng thái vừa được đọc lại; Internet chưa được chứng nhận từ kết quả này.');
        try{sessionStorage.removeItem('openstick-quick-operation');}catch(_){}return;
      }
      if (!receipt.busy && receipt.state!=='STARTED' && !(receipt.state==='NOT_FOUND' && Date.now()<deadline-200000)) throw Error('RADIO_RESULT_UNKNOWN');
      await new Promise(resolve=>setTimeout(resolve,1000));
    }
    throw Error('RADIO_RESULT_UNKNOWN');
  }
  const wifiImpact=()=>['local_ap','sim_ap'].includes(current?.wifi_role)?'Wi-Fi đang phát sẽ tạm ngừng; nếu không kết nối được sẽ thử phát lại. Giữ USB để quản trị.':'Kết nối Wi-Fi quản trị hiện tại có thể ngắt; cổng USB vẫn dùng được.';
  async function showWifi(message='') {
    if(busy||!current)return;
    const dialog=el('quick-wifi-dialog');
    el('quick-wifi-feedback').textContent=message;
    if(!dialog.open)dialog.showModal();
    el('quick-wifi-current').textContent='Đang đọc Wi-Fi…';
    el('quick-wifi-saved').replaceChildren();el('quick-wifi-nearby').replaceChildren();
    el('quick-wifi-disconnect').hidden=true;
    try {
      const r=await fetch('/api/quick/wifi',{headers,cache:'no-store'});
      if(!r.ok)throw Error();const s=await r.json();
      el('quick-wifi-current').textContent=s.connected?`Đang kết nối: ${s.ssid||'Wi-Fi đã lưu'}`:s.ap_active?'USB đang phát Wi-Fi. Chọn mạng để chuyển sang nhận.':'USB chưa nhận Wi-Fi.';
      el('quick-wifi-disconnect').hidden=!s.connected;
      const saved=s.saved||[], names=new Set(saved.map(p=>p.ssid));
      function row(parent,title,detail,click,active=false,disabled=false) {
        const button=document.createElement('button');button.type='button';button.className='quick-wifi-network';button.dataset.active=String(active);button.disabled=disabled;
        const label=document.createElement('span'),small=document.createElement('small');label.textContent=title;small.textContent=detail;button.append(label,small);button.onclick=click;parent.append(button);
      }
      function connectSaved(ssid){ask('wifi_saved',`Kết nối Wi-Fi đã lưu “${ssid}”? ${wifiImpact()} Dữ liệu SIM giữ nguyên; không tự bật thêm data.`,{ssid});}
      for(const p of saved)row(el('quick-wifi-saved'),p.ssid,p.active?'Đang kết nối':'Đã lưu · không cần nhập lại mật khẩu',()=>connectSaved(p.ssid),p.active,p.active);
      if(!saved.length)el('quick-wifi-saved').textContent='Chưa có Wi-Fi đã lưu.';
      for(const n of s.networks||[]) {
        const supported=/(^|\s)WPA[12]($|\s)/.test(n.security)&&!/(802\.1X|EAP)/.test(n.security);
        row(el('quick-wifi-nearby'),n.ssid,`${n.signal}% · ${n.security||'Mạng mở'}${supported?'':' · chưa hỗ trợ'}`,()=>{
          if(names.has(n.ssid)){connectSaved(n.ssid);return;}
          el('quick-wifi-ssid').value=n.ssid;el('quick-wifi-password').value='';el('quick-wifi-form-title').textContent='Nhập mật khẩu để kết nối';el('quick-wifi-password').focus();
        },false,!supported);
      }
      if(!(s.networks||[]).length)el('quick-wifi-nearby').textContent='Chưa có kết quả quét. Bấm Quét lại hoặc nhập Wi-Fi ẩn bên dưới.';
      el('quick-wifi-scan-age').textContent=s.scan_at?`Lần quét: ${new Date(s.scan_at*1000).toLocaleTimeString()}. Bấm Quét lại để cập nhật.`:'Chọn mạng chỉ điền thông tin; chưa thay kết nối.';
    } catch (_) {el('quick-wifi-current').textContent='Chưa đọc được danh sách. Giữ USB và kiểm tra lại.';}
  }
  el('quick-dialog').addEventListener('close',()=>{const request=selected;selected=null;if(el('quick-dialog').returnValue==='apply'&&request)apply(request.action,request.values);});
  el('quick-receive').onclick=()=>current.wifi_role==='station'?showWifi():ask('wifi_auto',`Quét và kết nối Wi-Fi đã lưu? ${wifiImpact()} Nếu không nối được, mở danh sách để chọn mạng hoặc nhập mật khẩu. Không tự bật dữ liệu SIM.`);
  el('quick-wifi-close').onclick=()=>el('quick-wifi-dialog').close();
  el('quick-wifi-dialog').addEventListener('close',()=>{el('quick-wifi-password').value='';});
  el('quick-wifi-scan').onclick=()=>ask('wifi_scan',`Quét Wi-Fi xung quanh? ${['local_ap','sim_ap'].includes(current?.wifi_role)?wifiImpact():'Giữ nguyên Wi-Fi đang nhận.'} Chỉ quét rồi trở về mạng trước, chưa chọn mạng mới; kết nối SIM giữ nguyên.`);
  el('quick-wifi-disconnect').onclick=()=>ask('wifi_off','Ngắt nhận Wi-Fi? Không tự phát Wi-Fi hoặc nối sang mạng khác. Dữ liệu SIM giữ nguyên; trang quản trị USB vẫn dùng được.');
  el('quick-wifi-form').onsubmit=event=>{
    event.preventDefault();if(busy||!current)return;
    const ssid=el('quick-wifi-ssid').value,password=el('quick-wifi-password').value;
    if(new TextEncoder().encode(ssid).length>32){el('quick-wifi-feedback').textContent='Tên Wi-Fi vượt quá 32 byte.';return;}
    ask('wifi_connect',`Kết nối Wi-Fi “${ssid}” và lưu cho lần sau? ${wifiImpact()} Không tự bật dữ liệu SIM.`,{ssid,password});
  };
  el('quick-airplane').onclick=()=>ask(current.intent?.airplane?'airplane_off':'airplane_on',current.intent?.airplane?'Cho phép modem di động hoạt động lại? Dữ liệu SIM vẫn tắt; chưa có SIM thì chờ lắp SIM.':'Tắt kết nối di động? SMS/USSD và dữ liệu SIM sẽ ngừng. Wi-Fi và USB Ethernet vẫn được giữ; nếu đang chia sẻ SIM, Wi-Fi có thể ngắt rồi phát lại nội bộ, không Internet.');
  el('quick-data').onclick=()=>{const on=current.mobile_data_connected||current.intent?.data_allowed===true&&!current.intent?.airplane;ask(on?'data_off':'data_on',on?'Tắt dữ liệu SIM và dừng tự nối lại? Web/Tunnel và thiết bị dùng Internet SIM sẽ mất Internet. Wi-Fi đang phát vẫn giữ để quản trị; không tự bật lại data.':'Bật dữ liệu SIM và cho phép phát sinh cước? Nếu Wi-Fi đang phát, các thiết bị kết nối sẽ được dùng Internet SIM. Phiên đã kết nối bị rớt sẽ được thử nối lại tối đa 3 lần; kết quả không rõ ràng sẽ dừng để kiểm tra. Giữ cùng tên và mật khẩu Wi-Fi.');};
  el('quick-ap').onclick=()=>{const ap=['local_ap','sim_ap'].includes(current.wifi_role);ask(ap?'local_ap_off':'local_ap_on',ap?'Tắt phát Wi-Fi? Điện thoại sẽ ngắt. Không tự nối Wi-Fi nhà; dữ liệu SIM giữ nguyên.':current.mobile_data_connected?'Bật phát Wi-Fi để chia sẻ Internet SIM? Các thiết bị kết nối có thể phát sinh cước SIM. Wi-Fi nhà sẽ ngắt; dùng tên và mật khẩu phát đã lưu.':'Bật phát Wi-Fi để quản trị? Wi-Fi nhà sẽ ngắt. Chưa có Internet cho đến khi bạn bật Dữ liệu SIM.');};
  el('quick-refresh').onclick=()=>{if(!busy)refresh();};
  el('quick-usb').onclick=()=>{const off=current.usb_tethering.enabled||current.usb_tethering.degraded||current.usb_tethering.desired_enabled;ask(off?'usb_tether_off':'usb_tether_on',off?'Lưu chế độ tắt chia sẻ Internet và khởi động lại USB một lần? PC tự nhận lại mạng quản trị. Website, Tunnel và kết nối sẽ tạm ngắt trong lúc khởi động.':'Lưu chế độ chia sẻ Internet và khởi động lại USB một lần để PC tự nhận mạng? Không cài phần mềm trên PC. Website/Tunnel tạm ngắt khi khởi động. Wi-Fi đã lưu sẽ kết nối lại; không tự bật dữ liệu SIM. Dùng SIM có thể phát sinh cước khi bạn bật data.');};
  let resumedOperation;try{resumedOperation=sessionStorage.getItem('openstick-quick-operation');}catch(_){}
  if(!/^[0-9a-f-]{36}$/.test(resumedOperation||''))resumedOperation=null;
  busy=!!resumedOperation;
  modeStatus=globalThis.portalRestoreSettings?.('modem');
  const remembered=globalThis.portalRestoreSettings?.('quick');
  if(remembered){try{draw(remembered);readFailed=true;globalThis.portalSettingsNote?.(el('quick-notice'));}catch(_){current=null}}
  if(resumedOperation){notice('Có yêu cầu trước cần đối chiếu receipt. Chỉ đọc kết quả, không gửi lại.');(async()=>{try{await poll(resumedOperation);}catch(_){notice('Kết quả yêu cầu trước chưa rõ. Đọc lại trạng thái qua USB; không tự gửi lại.');}finally{busy=false;await refresh();}})();}
  else refresh();
  setInterval(()=>{if(!busy&&!document.hidden&&!el('quick-dialog').open&&!el('quick-wifi-dialog').open)refresh();},60000);
  document.addEventListener('visibilitychange',()=>{if(!busy&&!document.hidden)refresh();});
})();

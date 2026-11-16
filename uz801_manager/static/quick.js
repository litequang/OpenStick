/* Read-only on load. Every mutation needs a fresh UUID and explicit dialog. */
(() => {
  const el = id => document.getElementById(id);
  const headers = {'Content-Type':'application/json', 'X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
  let current = null, busy = false, selected = null;
  const compact = !!document.querySelector('.quick-panel--compact');
  const errors = {
    SIM_NOT_READY:'Chưa có SIM sẵn sàng và đăng ký mạng. Lắp SIM sau khi ngắt nguồn, rồi đọc lại.',
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
    const airplane = s.intent?.airplane === true, blocked = busy || s.pending_network_trial || s.foreign_cellular_active;
    tile('quick-airplane', airplane?(compact?'Đã yêu cầu tắt':'Đã yêu cầu tắt di động'):(compact?'Cho phép di động':'Di động được cho phép'), airplane, blocked);
    tile('quick-data', s.mobile_data_connected?(compact?'Bật · Internet chưa đo':'Đã kết nối · Internet chưa xác minh'):!s.radio.sim_ready?(compact?'Chưa có SIM':'Chưa có SIM sẵn sàng'):'Đang tắt', s.mobile_data_connected, blocked || (!s.mobile_data_connected && (airplane || !s.radio.registered || !s.radio.sim_ready)));
    const ap = ['local_ap','sim_ap'].includes(s.wifi_role);
    tile('quick-ap', ap?(s.mobile_data_connected?'Đang phát · Internet SIM':'Đang phát · không Internet'):'Đang tắt', ap, blocked);
    tile('quick-usb', !s.usb_tethering.available?'Chưa được cài':s.usb_tethering.reboot_pending?'Đã lưu · đang áp dụng':s.usb_tethering.degraded?'Chưa xác minh · chạm để tắt':s.usb_tethering.enabled?'Đang chia sẻ Internet':'Tắt · chạm để bật', !!s.usb_tethering.enabled, blocked || !s.usb_tethering.available);
    el('quick-wifi').textContent = (compact?{station:'Đã nối Wi-Fi',local_ap:'Tạm dừng',sim_ap:'Tạm dừng',offline:'Chọn mạng Wi-Fi'}:{station:'Đang nhận Internet từ Wi-Fi',local_ap:'Tạm dừng khi đang phát Wi-Fi',sim_ap:'Tạm dừng khi đang phát Wi-Fi',offline:'Chọn Wi-Fi để lấy Internet'})[s.wifi_role] || 'Chưa xác định';
    const modemState=({'-1':'Chưa sẵn sàng',0:'Chưa xác định',1:'Đang khởi tạo',2:'SIM đang khóa',3:'Đã tắt',4:'Đang tắt',5:'Đang bật',6:'Đã bật',7:'Đang tìm mạng',8:'Đã đăng ký mạng',9:'Đang ngắt dữ liệu',10:'Đang kết nối dữ liệu',11:'Đã kết nối dữ liệu'})[s.radio.state] || 'Chưa xác định';
    if (el('quick-details')) el('quick-details').textContent = `SIM: ${s.radio.sim_ready?'sẵn sàng':'chưa sẵn sàng'}\nModem: ${modemState}\n${s.pending_network_trial?'Đang có lượt thử mạng.':'Không có lượt thử mạng.'}\nCác chức năng mới: đang kiểm chứng phần cứng.`;
  }
  async function refresh() {
    try {
      const r = await fetch('/api/quick', {headers, cache:'no-store'});
      if (r.status===401) {location.href='/login';return;}
      if (!r.ok) throw Error();
      draw(await r.json());
      if (el('quick-notice').textContent === 'Đang đọc trạng thái…') notice('Chạm một ô để xem và xác nhận thay đổi.');
    } catch (_) {
      current = null;
      for (const id of ['quick-airplane','quick-data','quick-ap','quick-usb']) el(id).disabled = true;
      notice('Chưa đọc được trạng thái USB. Các công tắc đã khóa; kiểm tra kết nối rồi đọc lại.');
    }
  }
  function ask(action, copy) {
    if (busy || !current) return;
    selected = action; el('quick-dialog-copy').textContent = copy; el('quick-dialog').returnValue='cancel';el('quick-dialog').showModal();
  }
  async function apply(action) {
    if (busy) return;
    busy = true; if(current) draw(current); notice('Đang thực hiện. Nếu mất kết nối, mở lại trang để đọc trạng thái; không gửi lại lệnh.');
    let operation;
    // Keep only an operation ID, never radio identities or credentials.
    try {
      operation = operationId();
      try {sessionStorage.setItem('openstick-quick-operation', operation);} catch (_) {}
      let r;
      try {r = await fetch('/api/quick', {method:'POST',headers,body:JSON.stringify({action,operation,confirm:true,...(['data_on','usb_tether_on'].includes(action)?{cellular_consent:true}:{})})});}
      catch (_) {await poll(operation,action);return;}
      if (!r.ok) {const result = await r.json();throw Error(result.error || 'QUICK_OPERATION_FAILED');}
      await poll(operation,action);
    } catch (error) {notice(errors[error.message] || 'Chưa xác minh được kết quả. Kiểm tra trạng thái qua USB trước khi thử tiếp.');}
    finally {busy = false; await refresh();}
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
        } else notice('Đã hoàn tất. Trạng thái vừa được đọc lại; Internet chưa được chứng nhận từ kết quả này.');
        try{sessionStorage.removeItem('openstick-quick-operation');}catch(_){}return;
      }
      if (!receipt.busy && receipt.state!=='STARTED' && !(receipt.state==='NOT_FOUND' && Date.now()<deadline-200000)) throw Error('RADIO_RESULT_UNKNOWN');
      await new Promise(resolve=>setTimeout(resolve,1000));
    }
    throw Error('RADIO_RESULT_UNKNOWN');
  }
  el('quick-dialog').addEventListener('close',()=>{const action=selected;selected=null;if(el('quick-dialog').returnValue==='apply'&&action)apply(action);});
  el('quick-airplane').onclick=()=>ask(current.intent?.airplane?'airplane_off':'airplane_on',current.intent?.airplane?'Cho phép modem di động hoạt động lại? Dữ liệu SIM vẫn tắt; chưa có SIM thì chờ lắp SIM.':'Tắt kết nối di động? SMS/USSD và dữ liệu SIM sẽ ngừng. Wi-Fi và USB Ethernet vẫn được giữ; nếu đang chia sẻ SIM, Wi-Fi có thể ngắt rồi phát lại nội bộ, không Internet.');
  el('quick-data').onclick=()=>ask(current.mobile_data_connected?'data_off':'data_on',current.mobile_data_connected?'Tắt dữ liệu SIM? Web/Tunnel và thiết bị dùng Internet SIM sẽ mất Internet. Wi-Fi đang phát vẫn giữ để quản trị; không tự bật lại data.':'Bật dữ liệu SIM và cho phép phát sinh cước? Nếu Wi-Fi đang phát, các thiết bị kết nối sẽ được dùng Internet SIM. Giữ cùng tên và mật khẩu Wi-Fi.');
  el('quick-ap').onclick=()=>{const ap=['local_ap','sim_ap'].includes(current.wifi_role);ask(ap?'local_ap_off':'local_ap_on',ap?'Tắt phát Wi-Fi? Điện thoại sẽ ngắt. Không tự nối Wi-Fi nhà; dữ liệu SIM giữ nguyên.':current.mobile_data_connected?'Bật phát Wi-Fi để chia sẻ Internet SIM? Các thiết bị kết nối có thể phát sinh cước SIM. Wi-Fi nhà sẽ ngắt; dùng tên và mật khẩu phát đã lưu.':'Bật phát Wi-Fi để quản trị? Wi-Fi nhà sẽ ngắt. Chưa có Internet cho đến khi bạn bật Dữ liệu SIM.');};
  el('quick-refresh').onclick=()=>{if(!busy)refresh();};
  el('quick-usb').onclick=()=>{const off=current.usb_tethering.enabled||current.usb_tethering.degraded||current.usb_tethering.desired_enabled;ask(off?'usb_tether_off':'usb_tether_on',off?'Lưu chế độ tắt chia sẻ Internet và khởi động lại USB một lần? PC tự nhận lại mạng quản trị. Website, Tunnel và kết nối sẽ tạm ngắt trong lúc khởi động.':'Lưu chế độ chia sẻ Internet và khởi động lại USB một lần để PC tự nhận mạng? Không cài phần mềm trên PC. Website/Tunnel tạm ngắt khi khởi động. Wi-Fi đã lưu sẽ kết nối lại; không tự bật dữ liệu SIM. Dùng SIM có thể phát sinh cước khi bạn bật data.');};
  refresh().then(async()=>{let operation;try{operation=sessionStorage.getItem('openstick-quick-operation');}catch(_){}if(operation&&/^[0-9a-f-]{36}$/.test(operation)){notice('Có yêu cầu trước cần đối chiếu receipt. Chỉ đọc kết quả, không gửi lại.');busy=true;if(current)draw(current);try{await poll(operation);}catch(_){notice('Kết quả yêu cầu trước chưa rõ. Đọc lại trạng thái qua USB; không tự gửi lại.');}finally{busy=false;await refresh();}}});
  setInterval(()=>{if(!busy&&!document.hidden)refresh();},15000);
})();

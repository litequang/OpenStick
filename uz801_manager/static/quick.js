/* Read-only on load. Every mutation needs a fresh UUID and explicit dialog. */
(() => {
  const el = id => document.getElementById(id);
  const headers = {'Content-Type':'application/json', 'X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
  let current = null, busy = false, selected = null;
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
  const notice = text => {el('quick-notice').textContent = text;};
  function tile(id, text, active, disabled) {
    const node = el(id); node.querySelector('small').textContent = text;
    node.dataset.active = String(active); node.disabled = disabled;
    node.setAttribute('aria-pressed', String(active));
  }
  function draw(s) {
    current = s;
    const airplane = s.intent?.airplane === true, blocked = busy || s.pending_network_trial || s.foreign_cellular_active;
    tile('quick-airplane', airplane?'Đã yêu cầu tắt di động':'Di động được cho phép', airplane, blocked);
    tile('quick-data', s.mobile_data_connected?'Đã kết nối · Internet chưa xác minh':!s.radio.sim_ready?'Chưa có SIM sẵn sàng':'Đang tắt', s.mobile_data_connected, blocked || (!s.mobile_data_connected && (airplane || !s.radio.registered || !s.radio.sim_ready)));
    tile('quick-ap', s.wifi_role==='local_ap'?'Đang phát · không Internet':'Chạm để phát Wi-Fi quản trị', s.wifi_role==='local_ap', blocked);
    el('quick-wifi').textContent = ({station:'Đang nhận Wi-Fi',local_ap:'Đang phát nội bộ',sim_ap:'Đang phát từ SIM',offline:'Chưa kết nối'})[s.wifi_role] || 'Chưa xác định';
    const modemState=({'-1':'Chưa sẵn sàng',0:'Chưa xác định',1:'Đang khởi tạo',2:'SIM đang khóa',3:'Đã tắt',4:'Đang tắt',5:'Đang bật',6:'Đã bật',7:'Đang tìm mạng',8:'Đã đăng ký mạng',9:'Đang ngắt dữ liệu',10:'Đang kết nối dữ liệu',11:'Đã kết nối dữ liệu'})[s.radio.state] || 'Chưa xác định';
    el('quick-details').textContent = `SIM: ${s.radio.sim_ready?'sẵn sàng':'chưa sẵn sàng'}\nModem: ${modemState}\n${s.pending_network_trial?'Đang có lượt thử mạng.':'Không có lượt thử mạng.'}\nCác chức năng mới: chưa kiểm thử phần cứng.`;
  }
  async function refresh() {
    try {
      const r = await fetch('/api/quick', {headers, cache:'no-store'});
      if (r.status===401) {location.href='/login';return;}
      if (!r.ok) throw Error();
      draw(await r.json());
    } catch (_) {
      current = null;
      for (const id of ['quick-airplane','quick-data','quick-ap']) el(id).disabled = true;
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
    const operation = crypto.randomUUID();
    // Keep only an operation ID, never radio identities or credentials.
    try {sessionStorage.setItem('openstick-quick-operation', operation);} catch (_) {}
    try {
      let r;
      try {r = await fetch('/api/quick', {method:'POST',headers,body:JSON.stringify({action,operation,confirm:true,...(action==='data_on'?{cellular_consent:true}:{})})});}
      catch (_) {await poll(operation);return;}
      if (!r.ok) {const result = await r.json();throw Error(result.error || 'QUICK_OPERATION_FAILED');}
      await poll(operation);
    } catch (error) {notice(errors[error.message] || 'Chưa xác minh được kết quả. Kiểm tra trạng thái qua USB trước khi thử tiếp.');}
    finally {busy = false; await refresh();}
  }
  async function poll(operation) {
    const deadline = Date.now()+210000;
    while (Date.now()<deadline) {
      const r = await fetch('/api/quick/operation/'+operation, {headers,cache:'no-store'});
      if (!r.ok) throw Error('RADIO_RESULT_UNKNOWN');
      const receipt = await r.json();
      if (receipt.error || receipt.failure) throw Error(receipt.error || receipt.failure);
      if (receipt.state==='COMPLETED') {notice('Đã hoàn tất. Trạng thái vừa được đọc lại; Internet chưa được chứng nhận từ kết quả này.');try{sessionStorage.removeItem('openstick-quick-operation');}catch(_){}return;}
      if (!receipt.busy && receipt.state!=='STARTED') throw Error('RADIO_RESULT_UNKNOWN');
      await new Promise(resolve=>setTimeout(resolve,1000));
    }
    throw Error('RADIO_RESULT_UNKNOWN');
  }
  el('quick-dialog').addEventListener('close',()=>{const action=selected;selected=null;if(el('quick-dialog').returnValue==='apply'&&action)apply(action);});
  el('quick-airplane').onclick=()=>ask(current.intent?.airplane?'airplane_off':'airplane_on',current.intent?.airplane?'Cho phép modem di động hoạt động lại? Dữ liệu SIM vẫn tắt; chưa có SIM thì chờ lắp SIM.':'Tắt kết nối di động? SMS/USSD và dữ liệu SIM sẽ ngừng. Wi-Fi và USB Ethernet vẫn được giữ; nếu đang chia sẻ SIM, Wi-Fi có thể ngắt rồi phát lại nội bộ, không Internet.');
  el('quick-data').onclick=()=>ask(current.mobile_data_connected?'data_off':'data_on',current.mobile_data_connected?'Tắt dữ liệu SIM? Web/Tunnel dùng SIM và máy đang dùng hotspot sẽ mất Internet. Wi-Fi USB có thể ngắt rồi phát lại nội bộ. Nếu phát lại lỗi, quản trị qua USB; không tự bật lại data.':'Cho phép kết nối dữ liệu SIM và phát sinh cước? Giữ vai trò Wi-Fi hiện tại. Việc này không xác nhận Internet hoạt động hoặc tự chia sẻ cho hotspot nội bộ.');
  el('quick-ap').onclick=()=>ask(current.wifi_role==='local_ap'?'local_ap_off':'local_ap_on',current.wifi_role==='local_ap'?'Dừng Wi-Fi nội bộ và tự phát dự phòng? Điện thoại sẽ ngắt; USB có thể thử nối Wi-Fi cũ.':'Chuyển sang Wi-Fi nội bộ để quản trị? Wi-Fi nhận Internet và dữ liệu SIM do OpenStick quản lý sẽ ngắt. Điện thoại cần nối lại Wi-Fi USB; mạng nội bộ không có Internet.');
  el('quick-refresh').onclick=()=>{if(!busy)refresh();};
  refresh().then(async()=>{let operation;try{operation=sessionStorage.getItem('openstick-quick-operation');}catch(_){}if(operation&&/^[0-9a-f-]{36}$/.test(operation)){notice('Có yêu cầu trước cần đối chiếu receipt. Chỉ đọc kết quả, không gửi lại.');busy=true;if(current)draw(current);try{await poll(operation);}catch(_){notice('Kết quả yêu cầu trước chưa rõ. Đọc lại trạng thái qua USB; không tự gửi lại.');}finally{busy=false;await refresh();}}});
  setInterval(()=>{if(!busy&&!document.hidden)refresh();},15000);
})();

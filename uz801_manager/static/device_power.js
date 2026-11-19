/* Only explicit, confirmed POSTs. Polls never repeat power commands. */
(()=>{
 const el=id=>document.getElementById('power-'+id);if(!el('state'))return;
 const headers={'Content-Type':'application/json','X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
 const errors={POWER_UNAVAILABLE:'Bộ điều khiển chưa sẵn sàng hoặc hệ thống chưa hỗ trợ.',POWER_BUSY:'USB đang có thao tác khác; chờ hoàn tất rồi thử lại.',POWER_PENDING:'Đã có yêu cầu nguồn đang chờ.',POWER_STATE_INVALID:'Trạng thái điều khiển bị lỗi; cần kiểm tra qua USB.',POWER_SAVE_FAILED:'Chưa lưu được yêu cầu; không tự gửi lại.',POWER_RESULT_UNKNOWN:'Chưa rõ lệnh đã thực hiện hay chưa; không tự gửi lại.',ALREADY_ATTEMPTED:'Mã yêu cầu này đã được dùng; không gửi lại.',POWER_NOT_CANCELLABLE:'Đã qua giai đoạn có thể hủy.',NETWORK_TRIAL_PENDING:'Hoàn tất hoặc hủy bước thử cấu hình mạng trước.',USAGE_CHECKPOINT_FAILED:'Chưa lưu được thống kê SIM; chưa yêu cầu tắt/khởi động lại.'};
 let state=null,busy=false,reading=false,attempt=null,acceptedAt=0,revision=0;
 function identity(){const a=crypto.getRandomValues(new Uint8Array(16));a[6]=(a[6]&15)|64;a[8]=(a[8]&63)|128;const s=[...a].map(n=>n.toString(16).padStart(2,'0')).join('');return [s.slice(0,8),s.slice(8,12),s.slice(12,16),s.slice(16,20),s.slice(20)].join('-')}
 function draw(s){
  state=s;const labels={IDLE:'Sẵn sàng.',QUEUED:'Đã lưu yêu cầu; chờ '+s.delay_seconds+' giây trước khi chuẩn bị.',WAITING_BUSY:'Đang chờ thao tác đang chạy hoàn tất; yêu cầu có thời hạn.',DISPATCHING:'Đang chuyển yêu cầu cho hệ điều hành. Không rút nguồn.',DISPATCHED:'Hệ điều hành đã nhận yêu cầu. Đang chờ kết nối thay đổi; chưa xác nhận USB đã tắt/khởi động xong.',CANCELLED:'Yêu cầu đã được hủy; chưa gửi lệnh nguồn.',EXPIRED:'Hết thời gian chờ; không gửi lệnh nguồn.',FAILED:'Chưa gửi lệnh nguồn: '+(errors[s.error]||'không thể chuẩn bị.'),UNKNOWN:'Không rõ kết quả. Không tự gửi lại lệnh.',BOOT_CHANGED:'USB đã có phiên khởi động mới kể từ yêu cầu trước.'};
  el('state').textContent=!s.available&&!s.pending?'Bộ điều khiển chưa sẵn sàng. '+(labels[s.phase]||''):labels[s.phase]||'Chưa xác định trạng thái.';
  for(const id of ['reboot','off'])el(id).disabled=busy||!s.available||s.pending;
  el('cancel').hidden=!['QUEUED','WAITING_BUSY'].includes(s.phase);el('cancel').disabled=busy;
  if(attempt&&s.operation===attempt)el('notice').textContent=s.error?errors[s.error]||'Chưa xác nhận kết quả.':'Trạng thái yêu cầu đã được đọc lại; không gửi thêm lệnh.';
 }
 async function refresh(){
  if(reading||busy)return;reading=true;const version=revision,controller=new AbortController(),timer=setTimeout(()=>controller.abort(),6000);
  try{const r=await fetch('/api/device/power',{headers,cache:'no-store',signal:controller.signal});if(r.status===401){location.href='/login';return}const s=await r.json();if(version!==revision)return;if(!r.ok)throw Error(errors[s.error]||'Chưa đọc được trạng thái.');draw(s)}
  catch(e){for(const id of ['reboot','off','cancel'])el(id).disabled=true;state=null;el('state').textContent=acceptedAt?'Đã mất liên lạc với USB; chưa xác nhận tắt/khởi động hoàn tất. Trang chỉ kiểm tra lại, không gửi lặp.':'Chưa đọc được bộ điều khiển. Kiểm tra kết nối rồi bấm Kiểm tra lại.'}
  finally{clearTimeout(timer);reading=false}
 }
 async function act(action){
  if(busy||!state)return;
  if(action!=='cancel'&&(!state.available||state.pending))return;
  const text=action==='reboot'?'Khởi động lại USB? Website, Tunnel và mọi kết nối sẽ bị ngắt. Cấu hình đã lưu được giữ lại.':'Tắt hệ điều hành USB an toàn? Website, Tunnel và mọi kết nối sẽ dừng. Muốn bật lại phải rút/cắm nguồn USB.';
  if(action!=='cancel'&&!confirm(text))return;
  let operation;try{operation=action==='cancel'?state.operation:identity()}catch(_){el('notice').textContent='Trình duyệt không tạo được mã yêu cầu; chưa gửi lệnh.';return}
  revision++;busy=true;attempt=operation;draw(state);el('notice').textContent='Đang gửi yêu cầu một lần…';
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
  try{const r=await fetch('/api/device/power',{method:'POST',headers,signal:controller.signal,body:JSON.stringify({action,operation,confirm:true})});const s=await r.json();if(!r.ok)throw Error(errors[s.error]||'Yêu cầu chưa được xác nhận.');acceptedAt=Date.now();draw(s)}
  catch(e){el('notice').textContent=e.name==='AbortError'||e instanceof TypeError?'Mất kết nối/hết thời gian: chưa rõ yêu cầu đã được nhận chưa. Đang đọc trạng thái, không tự gửi lại.':e.message}
  finally{clearTimeout(timer);busy=false;if(state)draw(state);refresh()}
 }
 el('reboot').onclick=()=>act('reboot');el('off').onclick=()=>act('poweroff');el('cancel').onclick=()=>act('cancel');el('refresh').onclick=refresh;
 refresh();setInterval(()=>{if(!document.hidden&&(!acceptedAt||Date.now()-acceptedAt<120000))refresh()},3000);
})();

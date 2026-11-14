(()=>{
 const token=document.querySelector('.portal-header').dataset.statusToken,e=id=>document.getElementById(id);
 const headers={'X-OpenStick-Token':token,'Content-Type':'application/json'};
 let posting=false,current=null,transition=false,lastScan=null;
 const errors={LAN_NOT_CONFIGURED:'Cần đặt mật khẩu quản trị LAN qua cổng USB trước khi dùng điện thoại.',HOTSPOT_ACTIVE:'Dừng hotspot dùng SIM trước khi chuyển sang Wi-Fi cài đặt.',POLICY_ACTIVE:'Đang chọn chế độ chỉ dùng SIM. Đổi chế độ tại Nguồn Internet trước.',CELLULAR_ALREADY_ACTIVE:'Dừng phiên dữ liệu SIM trước khi phát Wi-Fi cài đặt.',NETWORK_BUSY:'USB đang đổi mạng. Đợi rồi kiểm tra lại.',WIFI_CONNECT_FAILED:'Chưa kết nối được Wi-Fi mới. USB đã phát lại Wi-Fi cài đặt; kiểm tra tên mạng và mật khẩu.',SETUP_INTERRUPTED:'Lần đổi mạng bị ngắt nguồn. Đã quay lại Wi-Fi cài đặt.'};
 function draw(s){current=s;e('setup-state').textContent=`Tự phát khi không nối được Wi-Fi: ${s.enabled?'bật':'tắt'}\nWi-Fi cài đặt: ${s.setup_active?'đang phát':'chưa phát'}\nTên Wi-Fi: ${s.ssid||'chưa tạo'}\nTrang cài đặt: ${s.url}\nThao tác: ${s.busy?'đang xử lý':s.result==='WIFI_CONNECTED'?'đã kết nối Wi-Fi mới':'sẵn sàng'}`;
  for(const id of ['setup-enable','setup-disable','setup-start','setup-stop','setup-submit','setup-scan'])e(id).disabled=posting||s.busy;
  e('setup-start').disabled||=!s.configured;e('setup-stop').disabled||=!s.setup_active;e('setup-submit').disabled||=!s.setup_active;
  if(s.scan_at!==lastScan){lastScan=s.scan_at;const selected=e('setup-networks').value;e('setup-networks').replaceChildren(new Option('Nhập tay hoặc chọn mạng',''));for(const n of s.networks||[]){const supported=/WPA[12]?/.test(n.security)&&!/(802\.1X|EAP|WPA3)/.test(n.security);const option=new Option(`${n.ssid} — ${n.signal}% — ${n.security||'mở'}${supported?'':' (chưa hỗ trợ)'}`,n.ssid);option.disabled=!supported;e('setup-networks').add(option)}e('setup-networks').value=selected;e('setup-scan-note').textContent=`${(s.networks||[]).length} mạng từ lần quét ${s.scan_at?new Date(s.scan_at*1000).toLocaleTimeString():'chưa xác định'}. Chọn mạng chỉ điền tên; có thể nhập tay tên mạng ẩn.`}
  if(s.error)e('setup-notice').textContent=errors[s.error]||'Thao tác chưa hoàn tất. Kiểm tra lại trạng thái.';
  else if(!s.busy&&s.result==='WIFI_CONNECTED'){transition=false;e('setup-notice').textContent='USB đã nối Wi-Fi mới. Kết nối điện thoại vào cùng mạng để quản trị qua địa chỉ IP mới.'}
  else if(!s.busy&&s.result==='SCAN_READY'){transition=false;e('setup-notice').textContent='Đã quét xong. Chọn mạng, nhập mật khẩu rồi bấm Lưu & kết nối.'}
 }
 async function refresh(){try{const r=await fetch('/api/setup',{headers});if(r.status===401){location.href='/login';return}if(r.ok)draw(await r.json())}catch(_){if(!transition)e('setup-notice').textContent='Chưa đọc được trạng thái. Kiểm tra kết nối rồi tải lại.'}}
 async function act(action,extra={}){if(posting)return;posting=true;if(current)draw(current);
  if(['connect','start','scan'].includes(action)){transition=true;e('setup-notice').textContent=action==='scan'?'Đang quét: Wi-Fi USB có thể ngắt tạm thời. Nối lại cùng Wi-Fi USB sau khoảng 30 giây; danh sách sẽ tự cập nhật.':action==='connect'?'USB sắp ngừng phát để thử Wi-Fi mới. Nếu chưa nối được, hãy quay lại Wi-Fi cài đặt sau khoảng 1–2 phút.':'USB sắp chuyển sang phát Wi-Fi cài đặt. Dùng thông tin đã lưu để kết nối điện thoại.'}
  else e('setup-notice').textContent='Đang lưu…';
  try{const r=await fetch('/api/setup',{method:'POST',headers,body:JSON.stringify({action,confirm:true,...extra})}),s=await r.json();if(!r.ok)throw Error(errors[s.error]||'Yêu cầu chưa thực hiện được.');draw(s);if(action==='connect')e('setup-password').value='';if(action==='enable')e('setup-notice').textContent='Đã bật. Hãy xem và lưu thẻ kết nối vào điện thoại.'}
  catch(err){e('setup-notice').textContent=err.message}finally{posting=false;if(current)draw(current)}
 }
 for(const action of ['enable','disable','start','stop'])e('setup-'+action).onclick=()=>act(action);
 e('setup-scan').onclick=()=>{if(current?.setup_active&&!confirm('USB sẽ ngừng phát tạm thời để quét Wi-Fi, rồi tự phát lại sau khoảng 30 giây. Nối lại cùng Wi-Fi USB để xem danh sách. Tiếp tục?'))return;act('scan')};
 e('setup-networks').onchange=()=>{if(e('setup-networks').value)e('setup-ssid').value=e('setup-networks').value};
 e('setup-connect').onsubmit=event=>{event.preventDefault();act('connect',{ssid:e('setup-ssid').value,password:e('setup-password').value})};
 e('setup-reveal').onclick=async()=>{try{const r=await fetch('/api/setup/credentials',{headers});if(!r.ok)throw Error();const s=await r.json();e('setup-credentials').hidden=false;e('setup-credentials').textContent=s.configured?`Tên Wi-Fi: ${s.ssid}\nMật khẩu Wi-Fi: ${s.password}\nTrang cài đặt: ${s.url}`:'Bật tự phát trước để tạo thông tin kết nối.'}catch(_){e('setup-notice').textContent='Chưa tải được thông tin kết nối.'}};
 e('setup-card').onclick=async()=>{try{const r=await fetch('/api/setup/card',{headers});if(!r.ok)throw Error();const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download='openstick-wifi-setup.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(_){e('setup-notice').textContent='Chưa tải được thẻ kết nối.'}};
 refresh();setInterval(()=>{if(!posting&&!document.hidden)refresh()},5000);
})();

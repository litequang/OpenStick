(()=>{
 const token=document.querySelector('.portal-header').dataset.statusToken,e=id=>document.getElementById(id);
 const headers={'X-OpenStick-Token':token,'Content-Type':'application/json'};
 let posting=false,current=null,transition=false,lastScan=null,identityLoaded=false,wifi=null,wifiInitialized=false,stationScan=null;
 const connectNotice=text=>{e('setup-connect-notice').textContent=text};
 function drawWifi(s){
  wifi=s;
  const role=s.setup_active?'Đang phát Wi-Fi cài đặt':s.hotspot_active?'Đang chia sẻ Internet SIM':s.connected?'Đang nhận Wi-Fi':'Chưa kết nối Wi-Fi';
  const rate=value=>value==null?'chưa có số liệu':value+' Mbps';
  e('setup-wifi-status').textContent=`${role}\n${s.ssid?'Tên mạng: '+s.ssid+'\n':''}Địa chỉ: ${(s.ipv4||[]).join(', ')||'chưa có'}${s.connected?'\nSóng: '+(s.signal_percent==null?'chưa có số liệu':s.signal_percent+'%')+' · TX '+rate(s.tx_mbps)+' · RX '+rate(s.rx_mbps):''}`;
  if(!wifiInitialized){e('setup-connect-details').open=!s.connected;wifiInitialized=true}
  if(current)draw(current);
 }
 async function refreshWifi(){try{const r=await fetch('/api/header',{headers,cache:'no-store'});if(!r.ok)throw Error();drawWifi(await r.json())}catch(_){wifi=null;e('setup-wifi-status').textContent='Chưa đọc được kết nối. Kiểm tra USB hoặc Wi-Fi rồi thử lại.';if(current)draw(current)}}
 async function stationAction(action,extra={}){
  if(posting)return;posting=true;draw(current);connectNotice(action==='scan'?'Đang tìm mạng Wi-Fi…':'Đang kết nối. Wi-Fi quản trị có thể ngắt; không gửi lại yêu cầu.');
  try{
   const response=await fetch('/api/wifi',{method:'POST',headers,body:JSON.stringify({action,...extra})});
   if(response.status===401){location.href='/login';return}
   if(!response.ok)throw Error('USB đang bận hoặc chưa chấp nhận yêu cầu. Kiểm tra lại trạng thái trước khi thử lại.');
   const deadline=Date.now()+130000;
   while(Date.now()<deadline){
    const r=await fetch('/api/state',{headers,cache:'no-store'});if(!r.ok)throw Error('Không đọc được kết quả. Mở lại openstick.local:8765/setup hoặc quản trị qua USB; không tự gửi lại lệnh.');
    const result=await r.json();if(result.busy){await new Promise(resolve=>setTimeout(resolve,800));continue}
    if(result.error)throw Error(({WIFI_AUTH_REQUIRED:'Wi-Fi yêu cầu lại mật khẩu. Kiểm tra mật khẩu mạng rồi thử lại.',WIFI_TIMEOUT:'Hết thời gian kết nối. Kiểm tra mật khẩu và bộ phát.',WIFI_NOT_FOUND:'Không tìm thấy mạng. Quét lại hoặc nhập tên Wi-Fi ẩn.',HOTSPOT_ACTIVE:'Dừng phát Wi-Fi từ SIM trước khi nhận Wi-Fi.',SETUP_ACTIVE:'Chế độ Wi-Fi đã đổi. Kiểm tra lại trước khi kết nối.',POLICY_ACTIVE:'Tắt tự quản lý nguồn Internet trước khi đổi Wi-Fi.',NETWORK_BUSY:'USB đang đổi mạng. Đợi hoàn tất rồi thử lại.'})[result.error_code]||'Kết nối chưa thành công. Kiểm tra qua USB trước khi thử lại.');
    if(action==='scan'){stationScan={networks:result.result.networks||[],scan_at:Date.now()/1000};draw(current);connectNotice('Đã quét xong. Chọn mạng rồi nhập mật khẩu; chưa thay kết nối.')}
    else {e('setup-password').value='';connectNotice('Đã kết nối Wi-Fi. Điện thoại cần ở cùng mạng để mở lại openstick.local:8765/setup.');await refreshWifi()}
    return;
   }
   throw Error('Chưa có kết quả. Kiểm tra qua cổng USB trước khi thử lại.');
  }catch(error){connectNotice(error instanceof TypeError?'Mất kết nối tới USB. Nối điện thoại vào Wi-Fi mới rồi mở openstick.local:8765/setup; không tự gửi lại yêu cầu.':error.message)}
  finally{posting=false;if(current)draw(current)}
 }
 const errors={MODEM_BUSY:'Modem \u0111ang g\u1eedi SMS ho\u1eb7c c\u00f3 phi\u00ean USSD. USB ch\u1edd k\u1ebft th\u00fac r\u1ed3i m\u1edbi kh\u1edfi \u0111\u1ed9ng l\u1ea1i.',REBOOT_FAILED:'Ch\u01b0a kh\u1edfi \u0111\u1ed9ng l\u1ea1i \u0111\u01b0\u1ee3c. \u0110\u00e3 quay l\u1ea1i Wi-Fi c\u00e0i \u0111\u1eb7t.',LAN_NOT_CONFIGURED:'Cần đặt mật khẩu quản trị LAN qua cổng USB trước khi dùng điện thoại.',HOTSPOT_ACTIVE:'Dừng hotspot dùng SIM trước khi chuyển sang Wi-Fi cài đặt.',POLICY_ACTIVE:'Đang chọn chế độ chỉ dùng SIM. Đổi chế độ tại Nguồn Internet trước.',CELLULAR_ALREADY_ACTIVE:'Dừng phiên dữ liệu SIM trước khi phát Wi-Fi cài đặt.',NETWORK_BUSY:'USB đang đổi mạng. Đợi rồi kiểm tra lại.',WIFI_CONNECT_FAILED:'Chưa kết nối được Wi-Fi mới. USB đã phát lại Wi-Fi cài đặt; kiểm tra tên mạng và mật khẩu.',SETUP_INTERRUPTED:'Lần đổi mạng bị ngắt nguồn. Đã quay lại Wi-Fi cài đặt.',SETUP_OPERATION_FAILED:'Chưa lưu được cấu hình Wi-Fi USB. Kiểm tra lại qua cổng USB.'};
 function draw(s){current=s;if(!s.setup_active&&stationScan)s={...s,...stationScan};e('setup-state').textContent=`Tự phát khi không nối được Wi-Fi: ${s.enabled?'bật':'tắt'}\nWi-Fi cài đặt: ${s.setup_active?'đang phát':'chưa phát'}\nTên Wi-Fi: ${s.ssid||'chưa tạo'}\nTrang cài đặt: ${s.url}\nThao tác: ${s.busy?'đang xử lý':s.result==='WIFI_CONNECTED'?'đã kết nối Wi-Fi mới':'sẵn sàng'}`;
  for(const [id,active,label] of [['setup-auto-state',s.enabled,s.enabled?'Đang bật':'Đang tắt'],['setup-ap-state',s.setup_active,s.setup_active?'Đang phát':'Chưa phát']]){const badge=e(id);badge.textContent=label;badge.dataset.active=String(Boolean(active))}
  for(const [id,visible] of [['setup-enable',!s.enabled],['setup-disable',s.enabled]])e(id).hidden=!visible;
  if(!identityLoaded){e('setup-ap-ssid').value=s.ssid||'';e('setup-ap-channel').value=String(s.channel||6);identityLoaded=true}
  e('setup-ap-save').disabled=posting||s.busy;
  for(const id of ['setup-enable','setup-disable','setup-submit','setup-scan'])e(id).disabled=posting||s.busy;
  e('setup-submit').disabled||=!wifi||(!s.setup_active&&wifi.hotspot_active);
  e('setup-scan').disabled||=!wifi||(!s.setup_active&&wifi.hotspot_active);
  e('setup-connect-impact').textContent=!wifi?'Chưa đọc được chế độ mạng; chờ kiểm tra trước khi kết nối.':s.setup_active?'USB sẽ khởi động lại một lần. Nếu không vào được mạng mới, USB thử Wi-Fi đã lưu rồi phát lại Wi-Fi cài đặt. Chờ 1–3 phút.':wifi.hotspot_active?'USB đang phát Internet từ SIM. Dừng chế độ phát tại mục Phát Wi-Fi trước khi nhận Wi-Fi.':'Kết nối trực tiếp, không khởi động lại USB. Wi-Fi quản trị có thể ngắt khi đổi mạng; cổng USB vẫn dùng được. Nếu thất bại, kiểm tra lại kết nối qua USB.';
  e('setup-submit').textContent=s.setup_active?'Lưu & khởi động lại để kết nối':'Kết nối Wi-Fi';
  if(s.scan_at!==lastScan){lastScan=s.scan_at;const selected=e('setup-networks').value;e('setup-networks').replaceChildren(new Option('Nhập tay hoặc chọn mạng',''));for(const n of s.networks||[]){const supported=/(^|\s)WPA[12]($|\s)/.test(n.security)&&!/(802\.1X|EAP)/.test(n.security);const option=new Option(`${n.ssid} — ${n.signal}% — ${n.security||'mở'}${supported?'':' (chưa hỗ trợ)'}`,n.ssid);option.disabled=!supported;e('setup-networks').add(option)}e('setup-networks').value=selected;e('setup-scan-note').textContent=`${(s.networks||[]).length} mạng từ lần quét ${s.scan_at?new Date(s.scan_at*1000).toLocaleTimeString():'chưa xác định'}. Chọn mạng chỉ điền tên; có thể nhập tay tên mạng ẩn.`}
  if(s.station_url&&e('setup-station-link')){const a=document.createElement('a');a.href=s.station_url;a.textContent=s.station_url;e('setup-station-link').replaceChildren(a)}else if(e('setup-station-link'))e('setup-station-link').replaceChildren();
  if(s.error)e('setup-notice').textContent=errors[s.error]||'Thao tác chưa hoàn tất. Kiểm tra lại trạng thái.';
  else if(!s.busy&&['WIFI_CONNECTED','SAVED_WIFI_CONNECTED'].includes(s.result)){transition=false;e('setup-notice').textContent='USB đã nối Wi-Fi. Kết nối điện thoại vào cùng mạng rồi mở lại http://openstick.local:8765.'}
  else if(s.result==='REBOOTING')e('setup-notice').textContent='USB \u0111\u00e3 l\u01b0u Wi-Fi v\u00e0 \u0111ang kh\u1edfi \u0111\u1ed9ng l\u1ea1i m\u1ed9t l\u1ea7n. Ch\u1edd kho\u1ea3ng 1\u20133 ph\u00fat; n\u1ebfu kh\u00f4ng n\u1ed1i \u0111\u01b0\u1ee3c m\u1ea1ng n\u00e0o, hotspot s\u1ebd ph\u00e1t l\u1ea1i.';
  else if(!s.busy&&s.result==='SCAN_READY'){transition=false;e('setup-notice').textContent='Đã quét xong. Chọn mạng, nhập mật khẩu rồi bấm Lưu & kết nối.'}
 }
 async function refresh(){try{const r=await fetch('/api/setup',{headers});if(r.status===401){location.href='/login';return}if(r.status===403&&transition){location.reload();return}if(r.ok)draw(await r.json())}catch(_){if(!transition)e('setup-notice').textContent='Chưa đọc được trạng thái. Kiểm tra kết nối rồi tải lại.'}}
 async function act(action,extra={}){if(posting)return;posting=true;if(current)draw(current);
  if(['connect','start','scan'].includes(action)){transition=true;e('setup-notice').textContent=action==='scan'?'Đang quét: Wi-Fi USB có thể ngắt tạm thời. Nối lại cùng Wi-Fi USB sau khoảng 30 giây; danh sách sẽ tự cập nhật.':action==='connect'?'USB sẽ lưu cấu hình và khởi động lại một lần. Chờ khoảng 1–3 phút; nếu không nối được Wi-Fi nào, hãy nối lại hotspot cài đặt.':'USB sắp chuyển sang phát Wi-Fi cài đặt. Dùng thông tin đã lưu để kết nối điện thoại.'}
  else e('setup-notice').textContent='Đang lưu…';
  try{const r=await fetch('/api/setup',{method:'POST',headers,body:JSON.stringify({action,confirm:true,...extra})}),s=await r.json();if(!r.ok)throw Error(errors[s.error]||'Yêu cầu chưa thực hiện được.');draw(s);if(action==='connect'){e('setup-password').value='';connectNotice('Đã gửi yêu cầu lưu và khởi động lại một lần. Chờ 1–3 phút rồi mở lại openstick.local:8765/setup; không bấm gửi lại.')}if(action==='enable')e('setup-notice').textContent='Đã bật. Hãy xem và lưu thẻ kết nối vào điện thoại.';if(action==='configure_ap'){e('setup-ap-password').value='';e('setup-ap-notice').textContent=s.setup_active?'Đã lưu. Wi-Fi USB đang phát tiếp tục dùng thông tin cũ cho đến lần phát sau.':'Đã lưu thông tin Wi-Fi USB dùng chung; chưa đổi kết nối hoặc bật SIM.'}}
  catch(err){e(action==='configure_ap'?'setup-ap-notice':'setup-notice').textContent=err.message;if(action==='connect')connectNotice('Chưa xác định được kết quả: '+err.message+' Kiểm tra trạng thái trước khi gửi lại.')}finally{posting=false;if(current)draw(current)}
 }
 for(const action of ['enable','disable'])e('setup-'+action).onclick=()=>{if(posting||!current)return;if(!confirm('Lưu chế độ '+(action==='enable'?'bật':'tắt')+' tự phát khi mất kết nối? Không ngắt Wi-Fi hiện tại.'))return;act('set_fallback',{enabled:action==='enable'})};
 e('setup-scan').onclick=()=>{if(!current||!wifi||posting)return;if(!current.setup_active){if(!wifi.hotspot_active)stationAction('scan');return}if(!confirm('USB sẽ ngừng phát tạm thời để quét Wi-Fi, rồi tự phát lại sau khoảng 30 giây. Nối lại cùng Wi-Fi USB để xem danh sách. Tiếp tục?'))return;act('scan')};
 e('setup-networks').onchange=()=>{if(e('setup-networks').value)e('setup-ssid').value=e('setup-networks').value};
 for(const [buttonId,inputId] of [['setup-password-toggle','setup-password'],['setup-ap-password-toggle','setup-ap-password']]){
  const button=e(buttonId),input=e(inputId);
  button.onclick=()=>{const shown=input.type==='password';input.type=shown?'text':'password';button.textContent=shown?'Ẩn':'Hiện';button.setAttribute('aria-pressed',String(shown))};
 }
 e('setup-connect').onsubmit=event=>{event.preventDefault();if(!current||!wifi||posting||e('setup-submit').disabled)return;const values={ssid:e('setup-ssid').value,password:e('setup-password').value};if(new TextEncoder().encode(values.ssid).length>32){connectNotice('Tên Wi-Fi vượt quá 32 byte. Tên có dấu có thể chiếm nhiều byte.');e('setup-ssid').focus();return}if(!confirm(current.setup_active?'Lưu Wi-Fi và khởi động lại USB một lần? Chờ 1–3 phút rồi kết nối điện thoại vào cùng mạng Wi-Fi mới.':'Đổi Wi-Fi của USB? Kết nối quản trị hiện tại có thể ngắt. Sau đó mở lại openstick.local:8765/setup từ cùng Wi-Fi mới.'))return;if(current.setup_active)act('connect',values);else stationAction('connect',values)};
 e('setup-ap-form').onsubmit=event=>{event.preventDefault();act('configure_ap',{ssid:e('setup-ap-ssid').value,password:e('setup-ap-password').value,channel:Number(e('setup-ap-channel').value)})};
 e('setup-reveal').onclick=async()=>{if(!e('setup-credentials').hidden){e('setup-credentials').hidden=true;e('setup-credentials').textContent='';e('setup-reveal').textContent='Xem thông tin kết nối';e('setup-reveal').setAttribute('aria-expanded','false');return}try{const r=await fetch('/api/setup/credentials',{headers});if(!r.ok)throw Error();const s=await r.json();e('setup-credentials').hidden=false;e('setup-reveal').textContent='Ẩn thông tin kết nối';e('setup-reveal').setAttribute('aria-expanded','true');e('setup-credentials').textContent=s.configured?`Tên Wi-Fi: ${s.ssid}\nMật khẩu Wi-Fi: ${s.password}\nTrang cài đặt: ${s.url}`:'Bật tự phát trước để tạo thông tin kết nối.'}catch(_){e('setup-notice').textContent='Chưa tải được thông tin kết nối.'}};
 e('setup-card').onclick=async()=>{try{const r=await fetch('/api/setup/card',{headers});if(!r.ok)throw Error();const url=URL.createObjectURL(await r.blob()),a=document.createElement('a');a.href=url;a.download='openstick-wifi-setup.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch(_){e('setup-notice').textContent='Chưa tải được thẻ kết nối.'}};
 refresh();refreshWifi();setInterval(()=>{if(!posting&&!document.hidden){refresh();refreshWifi()}},5000);
})();

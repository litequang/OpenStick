/* Inventory is read-only. Mutations require a confirmed, unique operation. */
(()=>{
 const el=id=>document.getElementById('ap-clients-'+id);
 if(!el('list'))return;
 const headers={'Content-Type':'application/json','X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
 let busy=false,reading=false,state=null;
 const errors={NETWORK_BUSY:'USB đang đổi mạng. Đợi hoàn tất rồi đọc lại.',AP_CLIENTS_UNAVAILABLE:'Chưa đọc được danh sách thiết bị từ driver.',AP_CLIENTS_INVALID:'Danh sách chặn đã lưu bị lỗi. Kiểm tra qua USB; chưa xác nhận áp dụng.',AP_CLIENTS_FIREWALL_FAILED:'Chưa áp dụng được chặn Internet. Kiểm tra trạng thái; không tự gửi lại.',AP_CLIENTS_SAVE_FAILED:'Chưa lưu được danh sách chặn.',AP_CLIENTS_ROLLBACK_FAILED:'Chưa hoàn tác đầy đủ. Giữ cổng USB để kiểm tra.',AP_CLIENTS_LIST_FULL:'Danh sách đã đủ 128 địa chỉ.',ALREADY_ATTEMPTED:'Thao tác đã có biên nhận. Đọc lại trạng thái; không tự gửi lại.',INPUT_INVALID:'Địa chỉ MAC phải gồm sáu cặp số hex, ngăn bằng dấu hai chấm.'};
 const node=(tag,text,cls)=>{const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n};
 const bytes=v=>v==null?'—':v>=1048576?(v/1048576).toFixed(1)+' MiB':v>=1024?(v/1024).toFixed(1)+' KiB':v+' B';
 errors.AP_CLIENTS_OFFLOAD_UNSUPPORTED='Đang có flow offload ngoài bộ lọc này. Chưa xác nhận chặn Internet; cần kiểm tra qua USB.';
 function operationId(){const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const h=Array.from(b,v=>v.toString(16).padStart(2,'0')).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`}
 function controls(){el('refresh').disabled=busy||reading;el('block').disabled=busy||!state;for(const b of document.querySelectorAll('#ap-clients-list button,#ap-clients-blocked button'))b.disabled=busy||!state}
 function button(address,blocked){const b=node('button',blocked?'Bỏ chặn':'Chặn Internet','secondary');b.type='button';b.onclick=()=>act(blocked?'unblock':'block',address);return b}
 function draw(s){
  state=s;el('list').replaceChildren();el('blocked').replaceChildren();
  el('status').textContent=!s.ap_active?'USB chưa phát Wi-Fi. Danh sách chặn vẫn được lưu; chưa áp dụng vào Wi-Fi nhận mạng.':!s.inventory_available?'Chưa đọc được thiết bị từ driver; không coi đây là danh sách rỗng.':`${s.count} thiết bị đang kết nối. ${s.blocked.length? (s.filter_applied?'Danh sách chặn đã có trong firewall.':'Danh sách chặn CHƯA được xác nhận áp dụng.'):'Chưa chặn thiết bị nào.'}`;
  if(s.error)el('notice').textContent=errors[s.error]||'Chưa xác nhận được trạng thái.';
  for(const c of s.clients||[]){
   const card=node('div','','ap-client-card'),info=node('div','','ap-client-info');
   info.append(node('strong',c.name||'Thiết bị chưa có tên'),node('code',c.mac),node('small',`IP: ${c.ip||'chưa xác định'} · Sóng: ${c.signal_dbm==null?'—':c.signal_dbm+' dBm'}`),node('small',`USB nhận ${bytes(c.rx_bytes)} · gửi ${bytes(c.tx_bytes)} · liên kết RX ${c.rx_mbps??'—'} / TX ${c.tx_mbps??'—'} Mbps`));
   card.append(info,button(c.mac,c.internet_blocked));el('list').append(card);
  }
  if(s.ap_active&&s.inventory_available&&!s.clients.length)el('list').append(node('p','Chưa có thiết bị Wi-Fi kết nối.','setup-field-help'));
  for(const address of s.blocked||[]){const card=node('div','','ap-client-card');card.append(node('code',address),button(address,true));el('blocked').append(card)}
  if(!s.blocked.length)el('blocked').append(node('p','Danh sách trống.','setup-field-help'));
  controls();
 }
 async function refresh(){
  if(busy||reading)return;reading=true;controls();
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
  try{const r=await fetch('/api/ap/clients',{headers,cache:'no-store',signal:controller.signal});if(r.status===401){location.href='/login';return}const s=await r.json();if(!r.ok)throw Error(errors[s.error]||'Chưa đọc được danh sách.');draw(s)}
  catch(e){state=null;el('list').replaceChildren();el('status').textContent='Danh sách hiện tại chưa xác định. Bấm Làm mới để kiểm tra.';el('notice').textContent=e instanceof TypeError||e.name==='AbortError'?'Mất kết nối hoặc hết thời gian đọc. Không có lệnh chặn nào được gửi.':e.message}
  finally{clearTimeout(timer);reading=false;controls()}
 }
 async function act(action,address){
  if(busy||!state)return;
  if(!/^([0-9a-f]{2}:){5}[0-9a-f]{2}$/i.test(address)||parseInt(address.slice(0,2),16)&1||/^00(:00){5}$/.test(address)){el('notice').textContent=errors.INPUT_INVALID;return}
  if(!confirm(`${action==='block'?'Chặn Internet':'Bỏ chặn Internet'} cho ${address}? Thiết bị vẫn có thể kết nối Wi-Fi và mở trang quản trị. Lựa chọn được lưu sau khi tắt nguồn.`))return;
  busy=true;controls();el('notice').textContent='Đang lưu và áp dụng…';
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),20000);
  try{const r=await fetch('/api/ap/clients',{method:'POST',headers,signal:controller.signal,body:JSON.stringify({action,mac:address,operation:operationId(),confirm:true})});const s=await r.json();if(!r.ok)throw Error(errors[s.error]||'Thao tác chưa được xác nhận.');el('notice').textContent=s.filter_applied?'Đã lưu và áp dụng bộ lọc Internet; không phải chặn kết nối Wi-Fi.':'Đã lưu cho lần phát Wi-Fi tiếp theo.';document.getElementById('ap-client-mac').value=''}
  catch(e){el('notice').textContent=e instanceof TypeError||e.name==='AbortError'?'Mất kết nối hoặc hết thời gian: kết quả chưa xác định. Đọc lại trạng thái; không tự gửi lại.':e.message}
  finally{clearTimeout(timer);busy=false;await refresh();controls()}
 }
 el('refresh').onclick=refresh;
 el('form').onsubmit=e=>{e.preventDefault();act('block',document.getElementById('ap-client-mac').value.trim())};
 refresh();setInterval(()=>{if(!document.hidden)refresh()},15000);
})();

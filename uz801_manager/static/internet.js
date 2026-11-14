const policyId=id=>document.getElementById(id);let policyBusy=false,policyLoaded=false;
const policyErrors={HOTSPOT_ACTIVE:'Đang ở vai trò hotspot. Dừng hotspot trước khi quản lý nguồn Internet.',CELLULAR_NOT_CONFIGURED:'Hãy lưu APN/cấu hình SIM ở trang Phát Wi-Fi từ SIM trước.',CELLULAR_ALREADY_ACTIVE:'Có kết nối di động khác đang hoạt động. Cần kiểm tra qua USB.',PROFILE_ACTIVE:'Đang dùng mạng này. Kết nối sang mạng khác trước khi xóa.',PROFILE_NOT_FOUND:'Mạng đã lưu không còn tồn tại. Tải lại danh sách.',POLICY_CONFLICT:'Chính sách Chỉ SIM đang bật; đổi chính sách trước khi kết nối Wi-Fi.',SWITCH_FAILED:'Chưa chuyển được sang đường có Internet. Đã yêu cầu hoàn tác; kiểm tra lại qua USB.',WIFI_SWITCH_FAILED:'Wi-Fi thử chưa có Internet. Đã yêu cầu hoàn tác.',ROLLBACK_FAILED:'Hoàn tác chưa thành công. Kiểm tra kết nối qua USB.',NETWORK_BUSY:'Thiết bị đang đổi mạng. Thử lại sau.'};
async function policyJob(action,values={}){
  if(policyBusy)throw Error('NETWORK_BUSY');policyBusy=true;
  policyId('policy-fields').disabled=true;policyId('policy-refresh').disabled=true;policyId('profiles-refresh').disabled=true;
  policyId('data-off').disabled=true;
  try{
    const response=await fetch('/api/internet',{method:'POST',headers:{'Content-Type':'application/json','X-OpenStick-Token':policyToken},body:JSON.stringify({action,...values})});
    if(!response.ok)throw Error('NETWORK_OPERATION_FAILED');
    const end=Date.now()+290000;
    while(Date.now()<end){const poll=await fetch('/api/internet/state',{headers:{'X-OpenStick-Token':policyToken}});if(!poll.ok)throw Error();const s=await poll.json();if(!s.busy){if(s.error)throw Error(s.error);return s.result}await new Promise(resolve=>setTimeout(resolve,800))}
    throw Error('RESULT_UNKNOWN');
  }finally{policyBusy=false;policyId('policy-fields').disabled=!policyLoaded;policyId('policy-refresh').disabled=false;policyId('profiles-refresh').disabled=false;policyId('data-off').disabled=false}
}
function policyExplain(error){policyId('policy-notice').textContent=policyErrors[error.message]||'Chưa nhận được kết quả. Kiểm tra trạng thái qua USB trước khi thử lại.'}
function renderPolicy(result){
  const c=result.config,r=result.runtime;policyLoaded=true;
  policyId('internet-mode').value=c.mode;policyId('policy-enabled').checked=c.enabled;policyId('policy-auto-wifi').checked=c.auto_wifi;policyId('policy-cellular').checked=false;policyId('policy-confirm').checked=false;policyId('policy-fields').disabled=false;
  policyId('policy-status').textContent=`Tự quản lý: ${c.enabled?'đang bật':'đang tắt'}\nNguồn chọn lần cuối: ${r.source==='wifi'?'Wi-Fi':r.source==='sim'?'SIM':'chưa có'}\nWi-Fi: ${r.health?.wifi?'đã kiểm tra Internet':'chưa xác minh Internet'} · SIM: ${r.health?.sim?'đã kiểm tra Internet':'chưa xác minh Internet'}${r.error?'\nLần chuyển gần nhất chưa thành công.':''}`;
  if(c.enabled&&(result.age_seconds==null||result.age_seconds>120))policyId('policy-status').textContent+='\nChưa có số liệu gần đây; cần kiểm tra dịch vụ tự quản lý trên USB.';
}
async function refreshPolicy(){try{renderPolicy(await policyJob('status'))}catch(e){policyExplain(e)}}
async function profiles(){
  try{const result=await policyJob('profiles'),box=policyId('saved-profiles');box.replaceChildren();if(!result.profiles.length){box.textContent='Chưa có Wi-Fi đã lưu.';return}
    for(const p of result.profiles){const row=document.createElement('div');row.className='profile';const label=document.createElement('span');label.textContent=p.ssid+(p.active?' · đang kết nối':'');const connect=document.createElement('button');connect.textContent='Kết nối';connect.disabled=p.active;connect.onclick=async()=>{if(!window.confirm('Chuyển sang Wi-Fi '+p.ssid+'?'))return;try{await policyJob('wifi_activate',{uuid:p.uuid,confirm:true});await profiles()}catch(e){policyExplain(e)}};const remove=document.createElement('button');remove.textContent='Quên mạng';remove.className='secondary';remove.disabled=p.active;remove.onclick=async()=>{if(!window.confirm('Xóa cấu hình và mật khẩu đã lưu của '+p.ssid+'?'))return;try{await policyJob('wifi_forget',{uuid:p.uuid,confirm:true});await profiles()}catch(e){policyExplain(e)}};row.append(label,connect,remove);box.append(row)}
  }catch(e){policyExplain(e)}
}
policyId('policy-refresh').onclick=refreshPolicy;policyId('profiles-refresh').onclick=profiles;
policyId('data-off').onclick=async()=>{if(!window.confirm('Tắt dữ liệu SIM và tự chuyển sang SIM? Kết nối Internet đang dùng SIM sẽ ngắt; SMS và Wi-Fi vẫn giữ.'))return;try{renderPolicy(await policyJob('data_off',{confirm:true}));policyId('policy-notice').textContent='Đã tắt dữ liệu SIM do OpenStick quản lý. SIM tiếp tục hoạt động cho SMS / USSD.'}catch(e){policyExplain(e)}};
policyId('policy-form').onsubmit=async event=>{event.preventDefault();if(!policyId('policy-confirm').checked)return;const values={mode:policyId('internet-mode').value,enabled:policyId('policy-enabled').checked,auto_wifi:policyId('policy-auto-wifi').checked,cellular_consent:policyId('policy-cellular').checked,confirm:true};if(values.enabled&&values.mode!=='wifi_only'&&!values.cellular_consent){policyId('policy-notice').textContent='Cần tích cho phép dữ liệu SIM khi bật chính sách có SIM.';return}policyId('policy-confirm').checked=false;try{renderPolicy(await policyJob('configure',values));policyId('policy-notice').textContent='Đã lưu và áp dụng chính sách.'}catch(e){policyExplain(e)}};
(async()=>{await refreshPolicy();await profiles()})();

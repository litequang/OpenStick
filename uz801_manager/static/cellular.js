(() => {
  'use strict';
  const el=id=>document.getElementById('cellular-'+id);
  const headers={'Content-Type':'application/json','X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
  let busy=false, settings=null;
  const errors={CELLULAR_ALREADY_ACTIVE:'Tắt dữ liệu SIM trước khi lưu APN.',HOTSPOT_ACTIVE:'Tắt phát Wi-Fi trước khi lưu APN.',POLICY_ACTIVE:'Tắt tự quản lý trong Nguồn Internet trước khi lưu APN.',NETWORK_BUSY:'USB đang đổi mạng. Đợi rồi thử lại.',ROLLBACK_FAILED:'Chưa xác nhận được hoàn tác. Giữ USB và kiểm tra cấu hình trước khi bật data.'};
  function mode(){
    const manual=el('mode').value==='manual',replace=el('password-action').value==='replace';
    el('manual').hidden=!manual;el('apn').required=manual;
    for(const key of ['apn','username','password-action','auth'])el(key).disabled=!manual;
    el('password').hidden=!manual||!replace;el('password').disabled=!manual||!replace;el('password').required=manual&&replace;
    if(!manual||!replace)el('password').value='';
  }
  function fill(s){
    settings=s;for(const key of ['name','apn','username','auth'])el(key).value=s[key]|| (key==='auth'?'auto':'');
    el('mode').value=s.apn?'manual':'auto';el('ip').value=s.ip_family||'auto';el('roaming').checked=s.roaming===true;
    el('password-action').value='keep';el('password').value='';
    el('secret-status').textContent=s.password_saved?'Đã lưu mật khẩu; không tải mật khẩu về trình duyệt.':'Chưa lưu mật khẩu APN.';mode();
  }
  async function load(){
    try{const r=await fetch('/api/cellular',{headers,cache:'no-store'});if(!r.ok)throw Error();const s=await r.json();fill(s.settings);
      el('fields').disabled=s.blocked;el('result').textContent=s.blocked?'Tắt dữ liệu SIM, phát Wi-Fi và tự quản lý mạng trước khi lưu cấu hình.':'Cấu hình chỉ có hiệu lực ở lần bật dữ liệu SIM tiếp theo.';
    }catch(_){el('fields').disabled=true;el('result').textContent='Chưa đọc được cấu hình. Tải lại trang sau khi kiểm tra kết nối USB.';}
  }
  el('mode').onchange=mode;el('password-action').onchange=mode;
  el('form').onsubmit=async event=>{
    event.preventDefault();if(busy||!settings)return;
    const manual=el('mode').value==='manual';
    const value={action:'configure_cellular',name:el('name').value,apn:manual?el('apn').value.trim():'',
      username:manual?el('username').value:'',password:manual?el('password').value:'',
      password_action:manual?el('password-action').value:'clear',auth:manual?el('auth').value:'auto',
      ip_family:el('ip').value,roaming:el('roaming').checked,confirm:true};
    if(!window.confirm('Lưu cấu hình APN cho lần bật data tiếp theo? Không tự kết nối SIM.'+(manual?'':' Tự nhận sẽ xóa tài khoản/mật khẩu APN thủ công.')+(value.roaming?' Bạn đang cho phép dữ liệu chuyển vùng có thể phát sinh cước.':'')))return;
    busy=true;el('fields').disabled=true;el('result').textContent='Đang lưu…';
    try{
      const r=await fetch('/api/hotspot',{method:'POST',headers,body:JSON.stringify(value)});
      if(!r.ok)throw Error('REQUEST_FAILED');
      const deadline=Date.now()+30000;
      while(Date.now()<deadline){
        const poll=await fetch('/api/hotspot/state',{headers,cache:'no-store'});if(!poll.ok)throw Error();const s=await poll.json();
        if(!s.busy){if(s.error)throw Error(s.error);if(s.last_operation?.action!=='configure_cellular')throw Error();await load();el('result').textContent='Đã lưu APN. Dữ liệu SIM chưa được bật.';return;}
        await new Promise(resolve=>setTimeout(resolve,700));
      }throw Error();
    }catch(error){el('result').textContent=errors[error.message]||'Chưa xác nhận được kết quả lưu. Kiểm tra lại cấu hình trước khi thử; không tự gửi lại.';}
    finally{value.password='';el('password').value='';busy=false;el('fields').disabled=false;mode();}
  };
  window.addEventListener('pagehide',()=>{el('password').value='';});load();
})();

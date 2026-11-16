(() => {
  'use strict';
  const el=id=>document.getElementById('cellular-'+id);
  const headers={'Content-Type':'application/json','X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
  let busy=false,snapshot=null,loaded=false,dirty=false;
  const errors={CELLULAR_ALREADY_ACTIVE:'Tắt dữ liệu SIM trước khi áp dụng APN.',HOTSPOT_ACTIVE:'Tắt phát Wi-Fi trước khi áp dụng APN.',POLICY_ACTIVE:'Tắt tự quản lý trong Nguồn Internet trước khi áp dụng APN.',NETWORK_BUSY:'USB đang đổi mạng. Đợi rồi thử lại.',ROLLBACK_FAILED:'Chưa xác nhận được hoàn tác. Giữ USB và kiểm tra cấu hình trước khi bật data.',APN_PROFILE_NAME_EXISTS:'Tên cấu hình đã tồn tại. Đặt tên khác hoặc chọn cấu hình đó để sửa.',APN_PROFILE_ACTIVE:'Cấu hình này đang áp dụng. Áp dụng một cấu hình khác trước khi xóa.',APN_PROFILE_NOT_FOUND:'Cấu hình không còn tồn tại. Bấm Đọc lại.',APN_PROFILE_LIMIT:'Đã lưu đủ 20 cấu hình. Xóa cấu hình không dùng trước.',APN_PROFILES_UNAVAILABLE:'Chưa đọc/ghi được danh sách riêng tư. Không tự ghi đè dữ liệu.'};
  const selected=()=>snapshot?.profiles.find(p=>p.id===el('profiles').value);
  function controls(){
    el('fields').disabled=busy||!loaded;el('profiles').disabled=busy||!loaded;
    el('new').disabled=busy||!loaded;el('refresh').disabled=busy;
    const p=selected();el('apply').disabled=busy||!loaded||!p||p.active||dirty||snapshot.blocked;
    el('delete').disabled=busy||!loaded||!p||p.active;
    el('apply-reason').textContent=!loaded?'Chưa đọc được trạng thái.':snapshot.blocked?'Vẫn tạo/sửa/lưu danh sách được. Tắt dữ liệu SIM, phát Wi-Fi và tự quản lý mạng trước khi áp dụng.':dirty?'Lưu các thay đổi trước khi áp dụng.':'Áp dụng chỉ thay cấu hình cho lần bật data tiếp theo; không tự bật dữ liệu SIM.';
  }
  function mode(){
    const manual=el('mode').value==='manual',replace=el('password-action').value==='replace';
    el('manual').hidden=!manual;el('apn').required=manual;
    for(const key of ['apn','username','password-action','auth'])el(key).disabled=!manual;
    el('password').hidden=!manual||!replace;el('password').disabled=!manual||!replace;el('password').required=manual&&replace;
    if(!manual||!replace)el('password').value='';
  }
  function fill(s){
    for(const key of ['name','apn','username','auth'])el(key).value=s[key]||(key==='auth'?'auto':'');
    el('mode').value=s.apn?'manual':'auto';el('ip').value=s.ip_family||'auto';el('roaming').checked=s.roaming===true;
    el('password-action').value='keep';el('password').value='';
    el('secret-status').textContent=s.password_saved?'Đã lưu mật khẩu; không tải mật khẩu về trình duyệt.':'Chưa lưu mật khẩu APN.';
    dirty=false;mode();controls();
  }
  function choose(){
    const p=selected(),isCurrent=el('profiles').value==='current';
    el('editor-title').textContent=p?'Sửa cấu hình đã lưu':isCurrent?'Lưu bản sao cấu hình đang áp dụng':'Tạo APN mới';
    fill(p||(isCurrent?snapshot.settings:{}));
    el('profiles').dataset.previous=el('profiles').value;
  }
  async function load(preferred=null){
    const r=await fetch('/api/cellular',{headers,cache:'no-store'});if(!r.ok)throw Error();
    snapshot=await r.json();snapshot.profiles=snapshot.profiles||[];loaded=true;
    const select=el('profiles');select.replaceChildren(new Option('Cấu hình mới',''));
    if(snapshot.settings?.available)select.add(new Option('Cấu hình đang áp dụng · lưu bản sao','current'));
    for(const p of snapshot.profiles)select.add(new Option(p.name+(p.active?' · đang áp dụng':''),p.id));
    const candidate=preferred??snapshot.profiles.find(p=>p.active)?.id??(snapshot.settings?.available?'current':'');
    select.value=Array.from(select.options).some(o=>o.value===candidate)?candidate:'';
    el('active').textContent=snapshot.settings?.available?'APN đang áp dụng: '+(snapshot.settings.name||'Chưa đặt tên')+' · '+(snapshot.settings.apn||'Tự nhận theo nhà mạng'):'Chưa có cấu hình áp dụng. Có thể tạo và lưu APN trước khi lắp SIM.';
    choose();
  }
  async function refresh(){
    if(busy||dirty&&!window.confirm('Đọc lại và bỏ các chỉnh sửa chưa lưu?'))return;
    try{await load();el('result').textContent='Đã đọc danh sách. Chọn cấu hình hoặc tạo APN mới.';}
    catch(_){loaded=false;el('result').textContent='Chưa đọc được cấu hình. Kiểm tra kết nối rồi bấm Đọc lại.';controls();}
  }
  async function operation(action,value,copy){
    if(busy||!loaded||!window.confirm(copy))return;
    busy=true;controls();el('result').textContent='Đang xử lý…';
    try{
      const r=await fetch('/api/hotspot',{method:'POST',headers,body:JSON.stringify({action,...value,confirm:true})});
      if(!r.ok)throw Error();const deadline=Date.now()+30000;
      while(Date.now()<deadline){
        const poll=await fetch('/api/hotspot/state',{headers,cache:'no-store'});if(!poll.ok)throw Error();const s=await poll.json();
        if(!s.busy){
          if(s.error)throw Error(s.error);if(s.last_operation?.action!==action)throw Error();
          await load(s.result?.saved_profile_id||value.profile_id);
          el('result').textContent=action==='apn_save'?'Đã lưu vào danh sách. APN đang áp dụng giữ nguyên.':action==='apn_apply'?'Đã áp dụng cấu hình. Dữ liệu SIM chưa được bật.':'Đã xóa cấu hình khỏi danh sách.';return;
        }await new Promise(resolve=>setTimeout(resolve,700));
      }throw Error();
    }catch(error){el('result').textContent=errors[error.message]||'Chưa xác nhận được kết quả. Bấm Đọc lại trước khi thử; không tự gửi lại.';}
    finally{value.password='';el('password').value='';busy=false;mode();controls();}
  }
  el('mode').onchange=mode;el('password-action').onchange=mode;
  el('form').addEventListener('input',()=>{dirty=true;controls();});
  el('form').addEventListener('change',()=>{dirty=true;controls();});
  el('profiles').onchange=()=>{if(dirty&&!window.confirm('Bỏ các chỉnh sửa chưa lưu để mở cấu hình khác?')){el('profiles').value=el('profiles').dataset.previous||'';return;}choose();el('profiles').dataset.previous=el('profiles').value;};
  el('new').onclick=()=>{if(dirty&&!window.confirm('Bỏ các chỉnh sửa chưa lưu để tạo cấu hình mới?'))return;el('profiles').value='';choose();el('name').focus();};
  el('refresh').onclick=refresh;
  el('form').onsubmit=event=>{
    event.preventDefault();const manual=el('mode').value==='manual';
    operation('apn_save',{profile_id:el('profiles').value,name:el('name').value.trim(),apn:manual?el('apn').value.trim():'',
      username:manual?el('username').value:'',password:manual?el('password').value:'',
      password_action:manual?el('password-action').value:'clear',auth:manual?el('auth').value:'auto',
      ip_family:el('ip').value,roaming:el('roaming').checked},'Lưu vào danh sách APN riêng? Không thay cấu hình đang áp dụng, không bật data.');
  };
  el('apply').onclick=()=>{const p=selected();if(!p||dirty||snapshot.blocked)return;operation('apn_apply',{profile_id:p.id},'Áp dụng cấu hình “'+p.name+'” cho lần bật data tiếp theo? Không tự kết nối SIM.'+(p.roaming?' Cấu hình này cho phép dữ liệu chuyển vùng có thể phát sinh cước.':''));};
  el('delete').onclick=()=>{const p=selected();if(!p||p.active)return;operation('apn_delete',{profile_id:p.id},'Xóa cấu hình “'+p.name+'” khỏi danh sách?'+(dirty?' Các chỉnh sửa chưa lưu sẽ bị bỏ.':''));};
  window.addEventListener('pagehide',()=>{el('password').value='';});refresh();
})();

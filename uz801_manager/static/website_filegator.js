/* Website metadata only. File operations belong exclusively to FileGator. */
(() => {
 const el=id=>document.getElementById(id),root=document.querySelector('.website-leaf');
 const headers={'Content-Type':'application/json','X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
 let inventory=null,siteId=new URL(location.href).searchParams.get('site')||'main',busy=false,creating=false,writing=false;
 const current=()=>inventory?.sites.find(s=>s.id===siteId);
 const notice=text=>{el('web-status').textContent=text};
 function controls(){root.querySelectorAll('button,input,select,textarea').forEach(n=>n.disabled=busy||!inventory);
  if(el('web-apply-domains'))el('web-apply-domains').disabled=busy||!inventory?.routing.available;
 }
 async function api(value){let response;
  try{response=await fetch('/api/websites',{method:'POST',headers,body:JSON.stringify(value)});}catch(_){throw Error('RESULT_UNKNOWN');}
  if(response.status===401){location.href='/login';throw Error('LOGIN_REQUIRED');}
  const body=await response.json();if(!response.ok)throw Error(body.error||'RESULT_UNKNOWN');return body;
 }
 async function job(work,mutating=false){if(busy)return;busy=true;writing=mutating;controls();
  try{await work();}catch(error){notice(({RESULT_UNKNOWN:'Mất kết nối hoặc hết thời gian chờ; chưa xác định kết quả. Không tự gửi lại.',REVISION_CONFLICT:'Danh sách đã thay đổi. Đọc lại trước khi lưu.',SITE_LIMIT:'Đã đạt giới hạn website.',DOMAIN_INVALID:'Tên miền chưa hợp lệ.',SITE_NAME_INVALID:'Tên website chưa hợp lệ.'})[error.message]||'Chưa hoàn tất. Đọc lại trạng thái trước khi thử lại.');}
  finally{busy=false;writing=false;controls();}
 }
 function draw(){if(!current())siteId=inventory.sites.some(s=>s.id==='main')?'main':inventory.sites[0]?.id;
  const chooser=el('web-site');chooser.replaceChildren();for(const s of inventory.sites){const option=document.createElement('option');option.value=s.id;option.textContent=s.name;chooser.append(option)}chooser.value=siteId;
  const s=current();if(!s)return;
  if(el('web-filegator')){
   const path='/files/'+encodeURIComponent(s.id)+'/';el('web-filegator').href=path;el('web-filegator').hidden=false;
   const frame=el('web-filegator-frame');
   if(frame.getAttribute('src')!==path){
    el('web-filegator-status').textContent='Đang mở trình quản lý file…';
    frame.onload=()=>{let ready=false;try{ready=!!frame.contentDocument?.querySelector('#app')}catch(_){}
     el('web-filegator-status').textContent=ready?'':'Chưa mở được FileGator. Kiểm tra kết nối/đăng nhập hoặc chọn Mở riêng; không tự gửi lại thao tác file.';};
    frame.src=path;frame.hidden=false;
   }
  }
  if(el('web-summary-text'))el('web-summary-text').textContent=s.name+' · '+s.domains.length+' tên miền. Mở File manager hoặc Tên miền từ danh mục cài đặt.';
  if(el('web-domains')){const list=el('web-domains');list.replaceChildren();for(const domain of s.domains){const row=document.createElement('p');row.textContent=domain;list.append(row)}if(!s.domains.length){const p=document.createElement('p');p.textContent='Chưa có tên miền.';list.append(p)}
   el('web-routing-note').textContent=inventory.routing.local==='CONFIG_SAVED'?'Đã lưu cấu hình; DNS và truy cập công khai chưa xác minh.':inventory.routing.available?'Các thay đổi tên miền chưa áp dụng.':'Chưa có backend áp dụng tự động.';
  }
  for(const a of document.querySelectorAll('[data-settings-parent="web"]')){const u=new URL(a.href,location.href);u.searchParams.set('site',siteId);a.href=u.pathname+u.search;}
  const u=new URL(location.href);u.searchParams.set('site',siteId);history.replaceState(null,'',u.pathname+u.search);
 }
 async function refresh(){inventory=await api({action:'sites'});draw();notice('Đã đọc danh sách. Chưa thay đổi website hoặc dịch vụ.');}
 el('web-refresh').onclick=()=>job(refresh);el('web-site').onchange=()=>{
  if(el('web-filegator-frame')?.getAttribute('src')&&!confirm('Đổi website trong FileGator? Hãy lưu bản sửa và chờ tải file hoàn tất trước khi chuyển.')){el('web-site').value=siteId;return;}
  siteId=el('web-site').value;draw();
 };
 function dialog(create){if(!inventory||busy)return;creating=create;el('web-site-title').textContent=create?'Tạo website':'Thông tin & tên miền';el('web-site-name').value=create?'':current().name;el('web-site-domains').value=create?'':current().domains.join('\n');el('web-site-dialog').showModal();el('web-site-name').focus();}
 if(el('web-create'))el('web-create').onclick=()=>dialog(true);
 for(const id of ['web-configure','web-edit-domains'])if(el(id))el(id).onclick=()=>dialog(false);
 if(el('web-site-cancel'))el('web-site-cancel').onclick=()=>el('web-site-dialog').close();
 if(el('web-site-form'))el('web-site-form').onsubmit=event=>{event.preventDefault();job(async()=>{
  const value={action:creating?'create':'configure',name:el('web-site-name').value,domains:el('web-site-domains').value.split(/[\n,]/).map(s=>s.trim()).filter(Boolean),expected:inventory.revision,confirm:true};if(!creating)value.site=siteId;
  inventory=await api(value);siteId=inventory.selected||siteId;draw();el('web-site-dialog').close();notice('Đã lưu website. Chưa áp dụng Nginx, Tunnel hoặc DNS.');
 },true)};
 if(el('web-apply-domains'))el('web-apply-domains').onclick=()=>{if(!confirm('Áp dụng tên miền cho tất cả website? Nginx sẽ nạp lại và Tunnel khởi động lại; website có thể gián đoạn ngắn. DNS vẫn cần cấu hình trên Cloudflare.'))return;job(async()=>{inventory=await api({action:'publish_domains',expected:inventory.revision,confirm:true});draw();notice('Đã lưu cấu hình. Hãy kiểm tra DNS và truy cập công khai.');},true)};
 window.addEventListener('beforeunload',event=>{if(writing){event.preventDefault();event.returnValue='';}});
 job(refresh);
})();

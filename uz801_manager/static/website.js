/* Static hosting panel. No publication, network or service mutation on load. */
(() => {
  const byId = id => document.getElementById(id), panel = document.querySelector('.web-panel');
  const headers = {'Content-Type':'application/json','X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
  const mib = 1048576;
  let inventory=null, siteId='main', listing=null, folder='', selected=null, version=null;
  let dirty=false, busy=false, creating=false, pathAction=null, uploads=[], uploadRevision=null, zipPreview=null;
  const messages = {
    FILE_CHANGED:'File hoặc danh sách đã thay đổi. Đọc lại và đối chiếu bản sửa trước khi xuất bản; chưa tự gửi lại.',
    PATH_INVALID:'Đường dẫn không hợp lệ. Không dùng đường dẫn tuyệt đối, dấu chấm đầu tên, ký tự đặc biệt hoặc liên kết.',
    FILE_TYPE_BLOCKED:'Loại file này không được phép xuất bản. Chỉ hỗ trợ mã và tài nguyên website tĩnh.',
    FILE_NOT_FOUND:'File không còn tồn tại. Đọc lại danh sách.', PATH_EXISTS:'Đường dẫn đích đã tồn tại. Chọn tên khác.',
    FILE_TOO_LARGE:'File vượt giới hạn 32 MiB, hoặc bản sửa văn bản vượt 2 MiB.',
    TEXT_NOT_EDITABLE:'Không thể sửa file này bằng trình văn bản. Bạn có thể tải xuống hoặc tải file thay thế.',
    SITE_TOO_LARGE:'Website vượt 256 MiB.', SITE_TOO_MANY_FILES:'Website vượt 2.000 file và thư mục.',
    DISK_SPACE_LOW:'USB thiếu dung lượng trống cho thao tác và vùng dự phòng. Xóa file không cần thiết trước.',
    ZIP_TOO_LARGE:'ZIP vượt 128 MiB.', ZIP_INVALID:'ZIP lỗi hoặc chứa kiểu file, liên kết hay cấu trúc không được hỗ trợ.',
    ZIP_DUPLICATE:'ZIP có đường dẫn trùng nhau. Sửa bộ mã rồi kiểm tra lại.',
    ZIP_PUBLISH_FAILED:'Giải nén thất bại; đã khôi phục các file vừa thay đổi.',
    ZIP_ROLLBACK_FAILED:'Giải nén và khôi phục chưa hoàn tất. Giữ nguyên USB, không gửi lại. Bản sao riêng được giữ để kiểm tra.',
    ZIP_RECOVERY_REQUIRED:'Có lần giải nén chưa hoàn tất. Khôi phục trước khi ghi thêm file.',
    ZIP_RECOVERY_CHANGED:'Có file đã thay đổi bên ngoài kể từ lần giải nén dở. Chưa ghi đè; cần đối chiếu bản sao qua USB.',
    ZIP_RECOVERY_INVALID:'Thông tin khôi phục không đầy đủ. Bản sao được giữ; cần kiểm tra qua USB.',
    DOMAIN_INVALID:'Nhập tên miền đầy đủ, không kèm http, đường dẫn, wildcard hoặc cổng.',
    DOMAIN_DUPLICATE:'Tên miền đã có trong danh sách hoặc thuộc website khác.',
    PRIMARY_DOMAIN_PROTECTED:'Giữ tên miền gốc của website hiện tại trong danh sách.',
    DOMAIN_PUBLISH_UNAVAILABLE:'Bộ áp dụng Nginx/Tunnel chưa có trên môi trường này. Chưa thay đổi cấu hình.',
    DOMAIN_CONFIG_UNSUPPORTED:'Cấu hình Nginx/Tunnel khác mẫu được hỗ trợ. Chưa tự ghi đè cấu hình đó.',
    DOMAIN_PUBLISH_FAILED:'Áp dụng tên miền thất bại; đã khôi phục cấu hình trước.',
    DOMAIN_ROLLBACK_FAILED:'Chưa khôi phục được dịch vụ sau lỗi. Giữ kết nối USB để kiểm tra, không tự gửi lại.',
    REGISTRY_INVALID:'Danh sách website bị lỗi; chưa ghi đè. Cần kiểm tra bản cấu hình cục bộ.',
    SITE_LIMIT:'Đã đạt giới hạn 8 website.', UNMANAGED_FILES:'Thư mục có file ngoài phạm vi quản lý. Không sao chép hoặc di chuyển tự động.',
    SITE_NAME_INVALID:'Tên website cần từ 1 đến 60 ký tự.',
    RESULT_UNKNOWN:'Mất kết nối hoặc hết thời gian chờ. Kết quả chưa xác minh; đọc lại, không tự gửi lại thao tác.'
  };
  const say = (text,error=false) => {byId('web-status').textContent=text;byId('web-status').dataset.error=String(error);};
  const size = bytes => bytes>=mib?(bytes/mib).toFixed(1)+' MiB':bytes>=1024?(bytes/1024).toFixed(1)+' KiB':bytes+' B';
  const currentSite = () => inventory?.sites.find(s=>s.id===siteId);
  function node(tag,text,cls) {const item=document.createElement(tag);if(text!==undefined)item.textContent=text;if(cls)item.className=cls;return item;}
  function canLeave(){return !dirty||confirm('Bỏ bản sửa file chưa xuất bản?');}
  function controls(){
    panel.querySelectorAll('button,input,select,textarea').forEach(item=>item.disabled=busy);
    const ready=!!listing && !!inventory;
    if(!busy){
      byId('web-site').disabled=!inventory;
      for(const id of ['site-new','web-mkdir','web-download-all','site-refresh','site-path','site-text'])byId(id).disabled=!ready;
      const editable=!selected||(selected.kind==='file'&&selected.editable);
      byId('site-path').disabled=!ready||!editable;
      byId('site-text').disabled=!ready||!editable;
      byId('site-save').disabled=!ready||!editable;
      for(const id of ['web-download','web-rename','web-move','web-copy','site-delete'])byId(id).disabled=!ready||!selected;
      byId('site-upload-send').disabled=!ready||!uploads.length||!uploadRevision||uploads.some(f=>f.file.size>32*mib);
      byId('web-zip-publish').disabled=!ready||!zipPreview;
      byId('web-zip-inspect').disabled=!ready||!byId('web-zip').files.length;
      byId('web-apply-domains').disabled=!inventory?.routing.available;
      byId('web-configure').disabled=!inventory;byId('web-edit-domains').disabled=!inventory;
      if(listing?.recovery_required)for(const id of ['site-save','site-delete','web-rename','web-move','web-copy','web-mkdir','site-upload-send','web-zip-inspect','web-zip-publish'])byId(id).disabled=true;
    }
    byId('web-open-folder').hidden=selected?.kind!=='directory';
    byId('web-draft').textContent=dirty?'Chưa xuất bản':selected?'Đã mở':'File mới';
    byId('web-draft').dataset.dirty=String(dirty);
  }
  async function jsonResponse(response){
    if(response.status===401){location.href='/login';throw Error('RESULT_UNKNOWN');}
    if(response.status===413)throw Error('FILE_TOO_LARGE');
    let data;try{data=await response.json();}catch(_){throw Error('RESULT_UNKNOWN');}
    if(!response.ok)throw Error(data.error||'RESULT_UNKNOWN');return data;
  }
  async function api(value){
    let response;try{response=await fetch('/api/websites',{method:'POST',headers,body:JSON.stringify(value)});}catch(_){throw Error('RESULT_UNKNOWN');}
    return jsonResponse(response);
  }
  async function job(work){
    if(busy)return;busy=true;controls();
    try{await work();}catch(error){say((error.completed!==undefined?'Đã xuất bản '+error.completed+' file trong lượt này. ':'')+(messages[error.message]||'Thao tác chưa hoàn tất. Đọc lại trạng thái; không tự gửi lại.'),true);}
    finally{busy=false;controls();}
  }
  function tab(name){
    panel.querySelectorAll('[data-web-tab]').forEach(item=>item.setAttribute('aria-pressed',String(item.dataset.webTab===name)));
    for(const key of ['files','uploads','domains'])byId('web-pane-'+key).hidden=key!==name;
  }
  panel.querySelectorAll('[data-web-tab]').forEach(item=>item.onclick=()=>tab(item.dataset.webTab));
  function drawInventory(){
    const chooser=byId('web-site');chooser.replaceChildren();
    for(const site of inventory.sites){const option=node('option',site.name);option.value=site.id;chooser.append(option);}
    chooser.value=siteId;
    const site=currentSite();if(!site)return;
    byId('web-domain-count').textContent=site.domains.length+' tên miền';
    const routing=inventory.routing;
    byId('web-route-state').textContent=routing.local==='CONFIG_SAVED'?'Đã lưu cấu hình · DNS chưa xác minh':routing.available?'Chờ áp dụng cấu hình':'Cần cấu hình Nginx/Tunnel';
    const publicLink=byId('web-public');publicLink.hidden=!site.domains.length;
    if(site.domains.length){publicLink.href='https://'+site.domains[0];publicLink.textContent=site.domains[0]+' ↗';}
    const target=byId('web-domains');target.replaceChildren();
    for(const domain of site.domains){const row=node('div',undefined,'web-domain'),link=node('a',domain+' ↗');link.href='https://'+domain;link.target='_blank';link.rel='noopener noreferrer';row.append(link,node('small','DNS chưa xác minh'));target.append(row);}
    if(!site.domains.length)target.append(node('p','Website này chưa có tên miền. Có thể quản lý file trước.','web-empty'));
    byId('web-routing-note').textContent=routing.local==='CONFIG_SAVED'?'Cấu hình đã được lưu cho Nginx và Tunnel. Việc này chưa chứng minh tên miền đã truy cập được từ Internet.':routing.available?'Các thay đổi tên miền đang chờ áp dụng. Nút bên dưới áp dụng cấu hình cho tất cả website.':'Chưa thể áp dụng tự động trên môi trường này ('+routing.local+'). File và danh sách tên miền vẫn quản lý được.';
  }
  function resetEditor(){selected=null;version=null;dirty=false;byId('site-path').value=folder?folder+'/':'';byId('site-text').value='';byId('site-heading').textContent='File mới';byId('web-editor-note').textContent='Bản sửa nằm trong tab này. Chỉ xuất bản khi bạn xác nhận.';}
  function resetTransfers(){uploads=[];uploadRevision=null;zipPreview=null;byId('site-upload').value='';byId('web-upload-folder').value='';byId('web-zip').value='';byId('web-upload-list').replaceChildren();byId('web-zip-list').replaceChildren();byId('web-zip-summary').textContent='Kiểm tra ZIP chỉ đọc bộ mã, chưa thay đổi website.';}
  function drawFiles(){
    if(!listing)return;
    byId('web-recovery').hidden=!listing.recovery_required;
    byId('web-usage').textContent=size(listing.bytes)+' / 256 MiB';byId('web-meter').value=listing.bytes;
    const files=listing.entries.filter(e=>e.kind==='file').length;
    byId('web-count').textContent=files+' file · '+(listing.entries.length-files)+' thư mục';
    const breadcrumbs=byId('web-breadcrumbs');breadcrumbs.replaceChildren();
    let part='';const root=node('button','Gốc');root.onclick=()=>navigate('');breadcrumbs.append(root);
    for(const name of folder.split('/').filter(Boolean)){part+=(part?'/':'')+name;const path=part,b=node('button',name);b.onclick=()=>navigate(path);breadcrumbs.append(b);}
    const search=byId('web-search').value.trim().toLocaleLowerCase(), prefix=folder?folder+'/':'';
    const entries=listing.entries.filter(e=>search?e.path.toLocaleLowerCase().includes(search):e.path.startsWith(prefix)&&!e.path.slice(prefix.length).includes('/'))
      .sort((a,b)=>(a.kind===b.kind?0:a.kind==='directory'?-1:1)||a.path.localeCompare(b.path));
    const target=byId('site-files');target.replaceChildren();
    for(const entry of entries){
      const button=node('button',undefined,'web-file');button.dataset.path=entry.path;
      button.setAttribute('aria-pressed',String(selected?.path===entry.path));
      button.append(node('span',entry.kind==='directory'?'▱':'⌑','web-file-symbol'),node('span',search?entry.path:entry.path.slice(prefix.length),'web-file-name'),node('small',entry.kind==='directory'?'Thư mục':size(entry.bytes)));
      button.onclick=()=>openEntry(entry);target.append(button);
    }
    if(!entries.length)target.append(node('p',search?'Không có kết quả phù hợp.':'Thư mục trống. Tạo file hoặc tải bộ mã lên.','web-empty'));
    byId('web-list-note').textContent=search?entries.length+' kết quả trong website':'Đang xem /'+folder;
  }
  async function loadFiles(){listing=await api({action:'list',site:siteId});drawFiles();}
  async function loadInventory(){inventory=await api({action:'sites'});if(!inventory.sites.some(s=>s.id===siteId))siteId='main';drawInventory();}
  async function refresh(){await loadInventory();await loadFiles();}
  function navigate(path){if(!canLeave())return;folder=path;resetEditor();byId('web-search').value='';drawFiles();controls();}
  async function openEntry(entry){
    if(!canLeave())return;
    await job(async()=>{
      let data=null;if(entry.editable)data=await api({action:'get',site:siteId,path:entry.path});
      selected=entry;version=data?.etag??null;dirty=false;byId('site-path').value=entry.path;byId('site-text').value=data?.text??'';byId('site-heading').textContent=entry.path;
      byId('web-editor-note').textContent=entry.kind==='directory'?'Chọn Mở thư mục để xem bên trong; các nút phía trên thao tác cả thư mục.':data?'Nội dung chưa thay đổi. Chỉ xuất bản khi bạn xác nhận.':'File nhị phân hoặc quá lớn cho trình sửa. Tải xuống hoặc tải file thay thế ở mục Tải lên.';
      drawFiles();say('Đã chọn '+entry.path+'.');
    });
  }
  byId('web-search').oninput=drawFiles;
  byId('web-open-folder').onclick=()=>navigate(selected.path);
  byId('site-new').onclick=()=>{if(!canLeave())return;resetEditor();drawFiles();controls();byId('site-path').focus();};
  const markDirty=()=>{dirty=true;controls();};byId('site-text').oninput=markDirty;byId('site-path').oninput=markDirty;
  byId('site-refresh').onclick=()=>job(async()=>{await refresh();say('Đã đọc lại danh sách. Bản sửa chưa xuất bản vẫn giữ trong trình sửa.');});
  byId('web-recover-zip').onclick=()=>job(async()=>{if(!confirm('Khôi phục website về trước lần giải nén bị gián đoạn? Các file trong lần giải nén đó sẽ được trả lại bản cũ.'))return;listing=await api({action:'recover_zip',site:siteId,confirm:true});resetEditor();drawFiles();say('Đã khôi phục website trước lần giải nén dở.');});
  byId('web-site').onchange=()=>{
    const next=byId('web-site').value;if(!canLeave()){byId('web-site').value=siteId;return;}
    job(async()=>{siteId=next;folder='';listing=null;resetEditor();resetTransfers();byId('web-search').value='';drawInventory();await loadFiles();say('Đang quản lý '+currentSite().name+'.');});
  };
  byId('site-save').onclick=()=>job(async()=>{
    const path=byId('site-path').value.trim();
    if(!confirm('Xuất bản '+path+' vào website '+currentSite().name+'? Nội dung công khai sẽ thay đổi ngay.'))return;
    listing=await api({action:'put',site:siteId,path,text:byId('site-text').value,expected:path===selected?.path?version:null,revision:listing.revision,confirm:true});
    const data=await api({action:'get',site:siteId,path});version=data.etag;selected=listing.entries.find(e=>e.path===path);dirty=false;byId('site-heading').textContent=path;
    drawFiles();say('Đã xuất bản file. Bộ nhớ đệm của trình duyệt hoặc Cloudflare có thể còn bản cũ.');
  });
  byId('site-delete').onclick=()=>{if(!selected||!canLeave())return;job(async()=>{
    if(!confirm('Xóa vĩnh viễn '+selected.path+(selected.kind==='directory'?' và toàn bộ nội dung bên trong':'')+' khỏi website '+currentSite().name+'?'))return;
    listing=await api({action:'delete',site:siteId,path:selected.path,revision:listing.revision,confirm:true});resetEditor();drawFiles();say('Đã xóa.');
  });};
  function pathDialog(action){
    if(!listing||!canLeave())return;pathAction=action;
    const labels={mkdir:'Tạo thư mục',move:'Di chuyển / đổi tên',copy:'Sao chép'};
    byId('web-path-title').textContent=labels[action];byId('web-target').value=action==='mkdir'?(folder?folder+'/':''):selected?.path||'';
    byId('web-path-help').textContent=action==='mkdir'?'Đường dẫn tính từ gốc website. Có thể tạo nhiều cấp thư mục.':'Nhập đường dẫn đầy đủ từ gốc website. Không ghi đè đường dẫn đích đã tồn tại.';
    byId('web-path-dialog').showModal();byId('web-target').focus();
  }
  byId('web-mkdir').onclick=()=>pathDialog('mkdir');byId('web-move').onclick=()=>pathDialog('move');byId('web-rename').onclick=()=>pathDialog('move');byId('web-copy').onclick=()=>pathDialog('copy');
  byId('web-path-cancel').onclick=()=>byId('web-path-dialog').close();
  byId('web-path-form').onsubmit=event=>{
    event.preventDefault();const target=byId('web-target').value.trim(),action=pathAction;
    job(async()=>{const value={action,site:siteId,path:action==='mkdir'?target:selected.path,revision:listing.revision,confirm:true};if(action!=='mkdir')value.target=target;
      listing=await api(value);byId('web-path-dialog').close();resetEditor();drawFiles();say('Đã hoàn tất thao tác.');});
  };
  async function download(path){
    let response;try{response=await fetch('/api/websites/download',{method:'POST',headers,body:JSON.stringify({site:siteId,path,revision:listing.revision})});}catch(_){throw Error('RESULT_UNKNOWN');}
    if(!response.ok){await jsonResponse(response);return;}
    const blob=await response.blob(),url=URL.createObjectURL(blob),link=node('a');link.href=url;
    const entry=listing.entries.find(e=>e.path===path);link.download=(path.split('/').pop()||'website')+(entry?.kind==='file'?'':'.zip');
    document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);say('Đã tải nội dung xuống.');
  }
  byId('web-download').onclick=()=>job(()=>download(selected.path));byId('web-download-all').onclick=()=>job(()=>download(folder));

  function siteDialog(create){
    if(!inventory)return;creating=create;const site=currentSite();
    byId('web-site-title').textContent=create?'Tạo website':'Thông tin & tên miền';byId('web-site-name').value=create?'':site.name;byId('web-site-domains').value=create?'':site.domains.join('\n');
    byId('web-site-dialog').showModal();byId('web-site-name').focus();
  }
  byId('web-create').onclick=()=>{if(canLeave())siteDialog(true);};byId('web-configure').onclick=()=>siteDialog(false);byId('web-edit-domains').onclick=()=>siteDialog(false);byId('web-site-cancel').onclick=()=>byId('web-site-dialog').close();
  byId('web-site-form').onsubmit=event=>{
    event.preventDefault();job(async()=>{
      const value={action:creating?'create':'configure',name:byId('web-site-name').value,domains:byId('web-site-domains').value.split(/[\n,]/).map(s=>s.trim()).filter(Boolean),expected:inventory.revision,confirm:true};
      if(!creating)value.site=siteId;
      const data=await api(value);inventory=data;siteId=data.selected;drawInventory();
      if(creating){folder='';resetEditor();resetTransfers();await loadFiles();}
      byId('web-site-dialog').close();say('Đã lưu website. Chưa thay đổi Nginx, Tunnel hoặc DNS.');
    });
  };
  byId('web-apply-domains').onclick=()=>job(async()=>{
    if(!confirm('Áp dụng tên miền cho tất cả website? Nginx sẽ nạp lại và Tunnel khởi động lại; website công khai có thể ngắt ngắn. Cấu hình gốc được giữ và sao lưu. DNS vẫn cần cấu hình trên Cloudflare.'))return;
    inventory=await api({action:'publish_domains',expected:inventory.revision,confirm:true});drawInventory();say('Đã lưu cấu hình Nginx/Tunnel. Hãy cấu hình DNS và thử tên miền công khai.');
  });

  function transfer(file,values){
    return new Promise((resolve,reject)=>{
      const xhr=new XMLHttpRequest(),data=new FormData();for(const [key,value] of Object.entries(values))data.append(key,value);data.append('file',file);
      xhr.open('POST','/api/websites/transfer');xhr.setRequestHeader('X-OpenStick-Token',headers['X-OpenStick-Token']);xhr.timeout=300000;
      xhr.upload.onprogress=event=>{if(event.lengthComputable)say('Đang tải dữ liệu: '+Math.round(event.loaded/event.total*100)+'%. Đợi USB xử lý xong; không tải lại trang.');};
      xhr.onerror=xhr.ontimeout=()=>reject(Error('RESULT_UNKNOWN'));
      xhr.onload=()=>{if(xhr.status===401){location.href='/login';reject(Error('RESULT_UNKNOWN'));return;}let result;try{result=JSON.parse(xhr.responseText);}catch(_){reject(Error(xhr.status===413?'FILE_TOO_LARGE':'RESULT_UNKNOWN'));return;}if(xhr.status>=200&&xhr.status<300)resolve(result);else reject(Error(result.error||'RESULT_UNKNOWN'));};
      xhr.send(data);
    });
  }
  function transferRow(path,bytes,overwrite){const row=node('div',undefined,'web-transfer-row');row.dataset.overwrite=String(overwrite);row.append(node('span',path),node('small',(overwrite?'Ghi đè · ':'Mới · ')+size(bytes)));return row;}
  function chooseUploads(input){
    uploads=Array.from(input.files).map(file=>({file,path:file.webkitRelativePath||file.name}));uploadRevision=listing?.revision;drawUploads();controls();
  }
  function drawUploads(){
    const target=byId('web-upload-list');target.replaceChildren();const prefix=byId('web-upload-path').value.trim();
    for(const file of uploads){const path=(prefix?prefix+'/':'')+file.path;target.append(transferRow(path,file.file.size,!!listing?.entries.some(e=>e.path===path)));}
  }
  byId('site-upload').onchange=()=>chooseUploads(byId('site-upload'));byId('web-upload-folder').onchange=()=>chooseUploads(byId('web-upload-folder'));byId('web-upload-path').oninput=drawUploads;
  byId('web-clear-uploads').onclick=()=>{uploads=[];byId('site-upload').value='';byId('web-upload-folder').value='';drawUploads();controls();};
  byId('web-check-uploads').onclick=()=>job(async()=>{await loadFiles();uploadRevision=listing.revision;drawUploads();say('Đã đọc lại file đích. Xem các file ghi đè trước khi xác nhận xuất bản.');});
  byId('site-upload-send').onclick=()=>{
    if(!canLeave())return;job(async()=>{
      if(!uploads.length)return;
      if(uploads.length>2000)throw Error('SITE_TOO_MANY_FILES');
      if(uploads.some(item=>item.file.size>32*mib))throw Error('FILE_TOO_LARGE');
      const prefix=byId('web-upload-path').value.trim();
      if(!confirm('Xuất bản '+uploads.length+' file vào '+currentSite().name+'? File trùng đường dẫn trong danh sách sẽ bị thay thế. Nếu lỗi giữa chừng, các file đã xong vẫn được giữ.'))return;
      let completed=0;
      try{
        let revision=uploadRevision;
        for(const item of uploads){listing=await transfer(item.file,{action:'upload',site:siteId,path:(prefix?prefix+'/':'')+item.path,revision,confirm:'true'});revision=listing.revision;completed++;}
      }catch(error){error.completed=completed;throw error;}finally{
        // Remove successful entries; never auto-retry a request of unknown outcome.
        uploads=uploads.slice(completed);uploadRevision=null;drawUploads();drawFiles();
      }
      uploads=[];resetEditor();await loadInventory();drawFiles();say('Đã xuất bản '+completed+' file.');
    });
  };
  function clearZip(){zipPreview=null;byId('web-zip-list').replaceChildren();byId('web-zip-summary').textContent='Kiểm tra ZIP chỉ đọc bộ mã, chưa thay đổi website.';controls();}
  byId('web-zip').onchange=clearZip;byId('web-zip-path').oninput=clearZip;
  byId('web-zip-inspect').onclick=()=>job(async()=>{
    const file=byId('web-zip').files[0];if(!file)return;if(file.size>128*mib)throw Error('ZIP_TOO_LARGE');
    zipPreview=null;const destination=byId('web-zip-path').value.trim(),result=await transfer(file,{action:'inspect_zip',site:siteId,path:destination});
    zipPreview={...result,file,destination,site:siteId};const target=byId('web-zip-list');target.replaceChildren();
    for(const entry of result.files)target.append(transferRow(entry.path,entry.bytes,entry.overwrite));
    const overwrites=result.files.filter(e=>e.overwrite&&e.kind==='file').length;
    byId('web-zip-summary').textContent=result.files.length+' mục · '+size(result.bytes)+' · '+overwrites+' file bị ghi đè. '+(!result.files.some(e=>e.path===(destination?destination+'/':'')+'index.html')?'Không có index.html ngay tại thư mục đích.':'Có index.html tại thư mục đích.');
    say('Đã kiểm tra ZIP. Website chưa thay đổi. Xem danh sách rồi xác nhận giải nén.');
  });
  byId('web-zip-publish').onclick=()=>{
    if(!zipPreview||!canLeave())return;job(async()=>{
      const preview=zipPreview;
      if(!confirm('Giải nén và xuất bản '+preview.files.length+' mục vào '+currentSite().name+'? File trùng đường dẫn sẽ bị ghi đè. Không rút nguồn hoặc đóng trang trong lúc ghi.'))return;
      zipPreview=null;listing=await transfer(preview.file,{action:'unzip',site:preview.site,path:preview.destination,revision:preview.revision,digest:preview.digest,confirm:'true'});
      resetEditor();clearZip();drawFiles();await loadInventory();say('Đã giải nén và xuất bản '+listing.published+' file. Các file cũ không có trong ZIP được giữ.');
    });
  };
  window.addEventListener('beforeunload',event=>{if(dirty||busy){event.preventDefault();event.returnValue='';}});
  job(async()=>{await refresh();resetEditor();say('Sẵn sàng quản lý website. Chưa có thay đổi nào được xuất bản.');});
})();

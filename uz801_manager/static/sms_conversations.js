/* SMS content and drafts stay in memory; archive persistence belongs to USB. */
class SmsApp {
  constructor(root) {
    this.root=root;this.token=root.dataset.token;this.messages=[];this.busy=false;this.cap=null;
    this.drafts=new Map();this.currentKey=null;this.attempts=new Set();this.loaded=false;
    this.el=id=>document.getElementById(id);
    this.errors={SIM_REQUIRED:'Chưa có SIM.',SIM_LOCKED:'SIM đang khóa.',NOT_REGISTERED:'Modem chưa đăng ký mạng.',MODEM_BUSY:'Modem đang bận. Đợi rồi đồng bộ lại.',ALREADY_ATTEMPTED:'Tin này đã được yêu cầu gửi. Kiểm tra lịch sử trước khi cân nhắc soạn lại.',RESULT_UNKNOWN:'Chưa xác định kết quả gửi. Không tự gửi lại; kiểm tra hội thoại và modem.',MESSAGE_NOT_ON_MODEM:'Không tìm thấy bản tương ứng trên modem. Có thể bỏ tùy chọn xóa trên modem.',MESSAGE_CHANGED:'Tin trên modem đã thay đổi. Đồng bộ lại trước khi xóa.',MESSAGE_NOT_FOUND:'Tin đã được xóa khỏi lịch sử.'};
  }
  explain(error){return this.errors[error.message]||'Chưa nhận được kết quả. Kiểm tra USB và đồng bộ lại.'}
  notice(text){this.el('sms-notice').textContent=text}
  node(tag,className,text){const n=document.createElement(tag);if(className)n.className=className;if(text!=null)n.textContent=text;return n}
  validNumber(number){return /^\+?[0-9]{3,20}$/.test(number)}
  fingerprint(){return JSON.stringify([this.el('sms-recipient').value.trim(),this.el('sms-body').value])}
  controls(){
    this.el('sms-sync').disabled=this.busy;
    const body=this.el('sms-body').value,number=this.el('sms-recipient').value.trim();
    this.el('sms-send').disabled=this.busy||!this.cap?.can_send||!this.validNumber(number)||!body.trim()||body.length>70||this.attempts.has(this.fingerprint());
    this.el('sms-character-count').textContent=body.length+'/70';
  }
  operation(){const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const h=Array.from(b,v=>v.toString(16).padStart(2,'0')).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`}
  async job(action,values={},wifi=false){
    if(this.busy)throw Error('MODEM_BUSY');this.busy=true;this.controls();
    try{
      const response=await fetch(wifi?'/api/wifi':'/api/modem',{method:'POST',headers:{'Content-Type':'application/json','X-OpenStick-Token':this.token},body:JSON.stringify({action,...values})});
      if(!response.ok)throw Error(response.status===409?'MODEM_BUSY':'RESULT_UNKNOWN');
      const end=Date.now()+90000;
      while(Date.now()<end){
        const poll=await fetch(wifi?'/api/state':'/api/modem/state'+(values.operation?'?operation='+encodeURIComponent(values.operation):''),{headers:{'X-OpenStick-Token':this.token}});
        if(!poll.ok)throw Error('RESULT_UNKNOWN');const state=await poll.json();
        if(!state.busy){if(state.error)throw Error(typeof state.error==='string'?state.error:'RESULT_UNKNOWN');return state.result}
        await new Promise(resolve=>setTimeout(resolve,650));
      }
      throw Error('RESULT_UNKNOWN');
    }finally{this.busy=false;this.controls()}
  }
  time(value,short=false){const date=new Date(value);if(!value||!Number.isFinite(date.getTime()))return short?'':'Chưa có thời gian';return short?(date.toDateString()===new Date().toDateString()?date.toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'}):date.toLocaleDateString('vi-VN',{day:'2-digit',month:'2-digit'})):date.toLocaleString('vi-VN')}
  groups(){const groups=new Map();for(const m of this.messages){if(!groups.has(m.number))groups.set(m.number,[]);groups.get(m.number).push(m)}return groups}
  renderList(){
    const list=this.el('sms-conversations');list.replaceChildren();
    const query=this.el('sms-search').value.trim().toLocaleLowerCase('vi');let count=0;
    for(const [number,rows] of this.groups()){
      if(query&&!number.toLocaleLowerCase('vi').includes(query)&&!rows.some(m=>m.text.toLocaleLowerCase('vi').includes(query)))continue;
      const latest=rows[0],row=this.node('button','sms-conversation');row.type='button';
      const avatar=this.node('span','sms-avatar',number.replace(/^\+/,'').slice(-2)||'?');avatar.setAttribute('aria-hidden','true');
      const text=this.node('span','sms-conversation-text'),top=this.node('span','sms-conversation-top');
      top.append(this.node('span','sms-conversation-name',number||'Không rõ người gửi'),this.node('span','sms-conversation-time',this.time(latest.timestamp,true)));
      text.append(top,this.node('span','sms-preview',(latest.direction==='sent'?'Bạn: ':'')+latest.text));row.append(avatar,text);
      row.onclick=()=>this.navigate('thread/'+latest.id);list.append(row);count++;
    }
    if(!count)list.append(this.node('p','sms-empty',query?'Không có hội thoại phù hợp.':'Chưa có tin nhắn. Bấm Soạn tin để bắt đầu.'));
    if(this.limited)list.append(this.node('p','sms-limit','Hiển thị tối đa 1.000 tin đã lưu; mỗi lần đồng bộ đọc tối đa 200 tin trên modem.'));
  }
  renderThread(number){
    const rows=this.groups().get(number)||[],log=this.el('sms-thread-messages');
    const atBottom=log.scrollHeight-log.scrollTop-log.clientHeight<80;log.replaceChildren();
    this.el('sms-thread-title').textContent=number||'Không rõ người gửi';this.el('sms-thread-count').textContent=rows.length+' tin nhắn';
    const labels={received:'Đã nhận',submitted:'Đã gửi tới modem · chưa xác nhận giao',unknown:'Chưa rõ kết quả · không tự gửi lại',not_submitted:'Chưa gửi tới modem'};
    let day=null;
    for(const m of [...rows].reverse()){
      const date=new Date(m.timestamp),nextDay=m.timestamp&&Number.isFinite(date.getTime())?date.toLocaleDateString('vi-VN'):null;
      if(nextDay&&nextDay!==day){log.append(this.node('div','sms-day',nextDay));day=nextDay}
      const row=this.node('div','sms-message-row'+(m.direction==='sent'?' is-sent':'')),bubble=this.node('div','sms-message-bubble');
      bubble.append(this.node('p','sms-message-body',m.text),this.node('div','sms-message-meta',this.time(m.timestamp)+'\n'+(labels[m.outcome]||'Chưa rõ trạng thái')));
      const menu=this.node('details','sms-message-actions'),summary=this.node('summary',null,'⋮');summary.setAttribute('aria-label','Tùy chọn tin nhắn');
      const remove=this.node('button','secondary','Xóa tin');remove.type='button';remove.onclick=()=>this.remove(m,number);menu.append(summary,remove);bubble.append(menu);row.append(bubble);log.append(row);
    }
    if(atBottom||this.newThread)log.scrollTop=log.scrollHeight;this.newThread=false;
  }
  saveDraft(){if(this.currentKey)this.drafts.set(this.currentKey,{number:this.el('sms-recipient').value,text:this.el('sms-body').value})}
  navigate(route){window.location.hash=route?'#'+route:''}
  route(){
    if(!this.loaded)return;
    const hash=window.location.hash.replace(/^#\/?/,'');let view='list',number=null;
    if(hash==='new')view='new';
    else if(/^thread\/[0-9a-f-]{36}$/.test(hash)){
      const row=this.messages.find(m=>m.id===hash.slice(7));if(row){view='thread';number=row.number}
    }
    const key=view==='thread'?'thread:'+number:view==='new'?'new':null;
    if(key!==this.currentKey){
      this.saveDraft();this.currentKey=key;this.newThread=true;
      const draft=this.drafts.get(key)||{number:number||'',text:''};
      this.el('sms-recipient').value=number==null?draft.number:number;this.el('sms-body').value=draft.text;
      this.el('sms-send-result').textContent='';
    }
    document.body.dataset.smsView=view;
    for(const name of ['list','thread','new'])this.el('sms-'+name+'-view').hidden=view!==name;
    const form=this.el('sms-compose-form');this.el(view==='thread'?'sms-thread-composer':'sms-new-composer').append(form);
    form.hidden=view==='thread'&&!this.validNumber(number);
    this.el('sms-recipient-field').hidden=view==='thread';this.el('sms-no-reply').hidden=!(view==='thread'&&!this.validNumber(number));
    if(view==='thread')this.renderThread(number);this.controls();
  }
  async loadArchive(){const result=await this.job('archive');this.update(result)}
  update(result){
    this.messages=result.messages||[];this.limited=result.limited||result.modem_limited;this.loaded=true;
    this.renderList();this.route();
  }
  async refresh(sync=true){
    if(this.busy)return;
    try{
      if(!this.loaded)await this.loadArchive();
      this.cap=await this.job('status');renderHeader(this.cap);this.controls();
      if(sync&&this.cap.sms_available){this.update(await this.job('messages'));this.notice('Đã đồng bộ lúc '+new Date().toLocaleTimeString('vi-VN'))}
      else{await this.loadArchive();this.notice(this.cap.sms_available?'Lịch sử trên USB.':'Đang xem lịch sử trên USB. Modem chưa sẵn sàng để gửi hoặc đồng bộ.')}
    }catch(e){this.notice(this.explain(e))}
  }
  async send(event){
    event.preventDefault();this.controls();if(this.el('sms-send').disabled)return;
    const number=this.el('sms-recipient').value.trim(),text=this.el('sms-body').value,fingerprint=this.fingerprint(),output=this.el('sms-send-result');
    this.attempts.add(fingerprint);output.textContent='Đang gửi…';
    let submitted=false;
    try{
      const result=await this.job('send',{number,text,operation:this.operation(),confirm:true});
      submitted=result.submitted===true;
      output.textContent=submitted?'Modem đã nhận yêu cầu gửi. Chưa xác nhận người nhận đã nhận tin.':'Chưa xác định kết quả gửi.';
      if(submitted){this.attempts.delete(fingerprint);this.el('sms-body').value='';this.saveDraft()}
    }catch(e){
      if(['SIM_REQUIRED','SIM_LOCKED','NOT_REGISTERED','MODEM_BUSY','MODEM_UNAVAILABLE','MODEM_AMBIGUOUS','UNSUPPORTED'].includes(e.message))this.attempts.delete(fingerprint);
      output.textContent=this.errors[e.message]||this.errors.RESULT_UNKNOWN;
    }
    // Refresh the durable attempt, including unknown outcomes, without resend.
    try{
      await this.loadArchive();
      if(submitted){const row=this.messages.find(m=>m.number===number);if(row)this.navigate('thread/'+row.id)}
    }catch(_){this.notice('Chưa tải lại được lịch sử. Không tự gửi lại tin.')}
    this.controls();
  }
  async remove(message,number){
    if(this.busy)return;const fromModem=this.el('sms-delete-modem').checked;
    if(!window.confirm(fromModem?'Xóa tin này khỏi lịch sử và modem?':'Xóa tin này khỏi lịch sử trên USB? Bản trên modem được giữ lại.'))return;
    try{
      await this.job('archive_delete',{id:message.id,delete_modem:fromModem,confirm:true});
      const result=await this.job('archive');this.messages=result.messages||[];
      const next=this.messages.find(m=>m.number===number);this.update(result);this.navigate(next?'thread/'+next.id:'');
    }catch(e){this.notice(this.explain(e))}
  }
  start(){
    this.el('sms-new').onclick=()=>this.navigate('new');
    for(const id of ['sms-thread-back','sms-new-back'])this.el(id).onclick=()=>this.navigate('');
    this.el('sms-compose-form').onsubmit=e=>this.send(e);
    this.el('sms-search').oninput=()=>this.renderList();
    for(const id of ['sms-body','sms-recipient'])this.el(id).oninput=()=>this.controls();
    this.el('sms-sync').onclick=()=>this.refresh();window.addEventListener('hashchange',()=>this.route());
    this.el('sms-tariff').onsubmit=async e=>{e.preventDefault();try{await this.job('tariff',{unit_vnd:Number(this.el('sms-unit-vnd').value)},true);this.el('sms-tariff-result').textContent='Đã lưu đơn giá ước tính.'}catch(e){this.el('sms-tariff-result').textContent=this.explain(e)}};
    setInterval(()=>{if(!this.busy&&!document.hidden&&this.el('sms-auto').checked)this.refresh()},15000);
    this.ready=this.refresh();return this.ready;
  }
}
const smsApp=new SmsApp(document.getElementById('sms-app'));smsApp.start();

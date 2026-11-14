// Exercise the shipped SMS controller with synthetic messages, no real sends.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const {webcrypto}=require('node:crypto'),html=fs.readFileSync(process.argv[2],'utf8');
class Element{
 constructor(){this.children=[];this.dataset={};this.value='';this.textContent='';this.hidden=false;this.disabled=false;this.checked=false;this.scrollTop=0;this.scrollHeight=900;this.clientHeight=300;}
 append(...items){for(const item of items){if(item.parentNode)item.parentNode.children=item.parentNode.children.filter(n=>n!==item);item.parentNode=this;this.children.push(item);}}
 replaceChildren(...items){for(const c of this.children)c.parentNode=null;this.children=[];this.append(...items);}
 setAttribute(name,value){this[name]=value;}
 set innerHTML(_){throw Error('SMS content must use textContent');}
}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
elements['sms-app'].dataset.token='fixture';elements['sms-auto'].checked=true;
const ids=['f0000000-0000-4000-8000-000000000001','f0000000-0000-4000-8000-000000000002','f0000000-0000-4000-8000-000000000003'];
let rows=[{id:ids[0],number:'+84900111222',text:'<script>private fixture</script>',timestamp:'2026-11-14T10:00:00Z',direction:'received',outcome:'received'},
 {id:ids[1],number:'BRAND',text:'Synthetic notification',timestamp:'2026-11-14T09:00:00Z',direction:'received',outcome:'received'}];
const events={},posts=[];let result={},failSend=false,serial=10;
const location={};let hash='';Object.defineProperty(location,'hash',{get:()=>hash,set:value=>{hash=value;for(const fn of events.hashchange||[])fn();}});
const context={console,Date,setTimeout,clearTimeout,Uint8Array,crypto:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},setInterval:()=>0,
 window:{location,confirm:()=>true,addEventListener:(name,fn)=>(events[name]??=[]).push(fn)},
 document:{hidden:false,body:new Element(),getElementById:id=>elements[id]||null,createElement:()=>new Element()},
 fetch:async(url,options={})=>{
  if(options.method==='POST'){
   const body=JSON.parse(options.body);posts.push(body);
   if(body.action==='archive'||body.action==='messages')result={messages:rows.map(r=>({...r})),archived:true};
   else if(body.action==='status')result={can_send:true,sms_available:true,registered:true,sim_present:true,signal_percent:64,signal_recent:true};
   else if(body.action==='send'){
    assert(body.confirm);assert.match(body.operation,/^[0-9a-f-]{36}$/);
    rows.unshift({id:'f0000000-0000-4000-8000-'+String(serial++).padStart(12,'0'),number:body.number,text:body.text,timestamp:'2026-11-14T11:00:00Z',direction:'sent',outcome:failSend?'unknown':'submitted'});
    if(failSend)throw Error('synthetic lost response');result={submitted:true,delivery_verified:false};
   }else if(body.action==='archive_delete'){rows=rows.filter(r=>r.id!==body.id);result={deleted:true};}
   else throw Error('Unexpected synthetic action '+body.action);
   return {ok:true};
  }
  assert(url==='/api/modem/state'||/^\/api\/modem\/state\?operation=[0-9a-f-]{36}$/.test(url));return {ok:true,json:async()=>({busy:false,error:null,result})};
 }};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../uz801_manager/static/sms_conversations.js'),'utf8'),context);
const app=vm.runInContext('smsApp',context),text=node=>node.textContent+node.children.map(text).join('');
(async()=>{
 await app.ready;
 assert.equal(posts.filter(p=>p.action==='send').length,0);
 assert.equal(context.document.body.dataset.smsView,'list');
 assert(elements['sms-thread-view'].hidden&&elements['sms-new-view'].hidden);
 assert.equal(elements['sms-compose-form'].parentNode,elements['sms-new-composer']);
 assert.equal(elements['sms-conversations'].children.length,2);
 assert(text(elements['sms-conversations']).includes('<script>private fixture</script>'));
 elements['sms-conversations'].children[0].onclick();
 assert.equal(context.document.body.dataset.smsView,'thread');
 assert(elements['sms-list-view'].hidden&&elements['sms-new-view'].hidden);
 assert.equal(elements['sms-compose-form'].parentNode,elements['sms-thread-composer']);
 assert.equal(elements['sms-recipient'].value,'+84900111222');
 elements['sms-body'].value='draft in conversation';elements['sms-body'].oninput();
 await app.refresh();assert.equal(elements['sms-body'].value,'draft in conversation');
 elements['sms-thread-back'].onclick();elements['sms-new'].onclick();
 assert.equal(context.document.body.dataset.smsView,'new');
 assert.equal(elements['sms-recipient'].value,'');assert.equal(elements['sms-body'].value,'');
 elements['sms-recipient'].value='+84900999888';elements['sms-body'].value='new synthetic message';elements['sms-body'].oninput();
 await elements['sms-compose-form'].onsubmit({preventDefault(){}});
 assert.equal(posts.filter(p=>p.action==='send').length,1);
 assert.equal(context.document.body.dataset.smsView,'thread');assert.equal(elements['sms-body'].value,'');
 assert(text(elements['sms-thread-messages']).includes('chưa xác nhận giao'));
 elements['sms-body'].value='uncertain synthetic message';failSend=true;elements['sms-body'].oninput();
 await app.send({preventDefault(){}});assert.equal(posts.filter(p=>p.action==='send').length,2);
 assert(elements['sms-send'].disabled);assert(text(elements['sms-thread-messages']).includes('không tự gửi lại'));
 await app.send({preventDefault(){}});assert.equal(posts.filter(p=>p.action==='send').length,2);
 elements['sms-thread-back'].onclick();app.navigate('thread/'+ids[0]);
 assert.equal(elements['sms-body'].value,'draft in conversation');
 app.navigate('thread/'+ids[1]);assert(elements['sms-compose-form'].hidden);assert(!elements['sms-no-reply'].hidden);
 const before=rows.length;context.window.confirm=()=>false;await app.remove(rows[0],rows[0].number);assert.equal(rows.length,before);
 app.navigate('');elements['sms-search'].value='no matching content';elements['sms-search'].oninput();
 assert.equal(elements['sms-conversations'].children[0].className,'sms-empty');
 assert.equal(posts.filter(p=>p.action==='send').length,2);
 console.log('SMS list, thread, composer, draft and uncertain-send fixture: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

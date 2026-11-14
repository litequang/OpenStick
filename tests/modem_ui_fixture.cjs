// Exercise the real inline UI script with synthetic DOM/HTTP, not a browser
// or a modem. In particular, private HTTP has no crypto.randomUUID().
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const html=fs.readFileSync(process.argv[2],'utf8');
const section=process.argv[3];
class Element{
 constructor(){this.disabled=false;this.hidden=false;this.dataset={};this.checked=false;this.value='';this.options=[];this.children=[];this.textContent='';}
 replaceChildren(...nodes){this.children=nodes;this.options=nodes;this.value='';}
 add(option){this.options.push(option);}
 append(...nodes){this.children.push(...nodes);}
 set innerHTML(value){throw Error('Use textContent for SMS/network content');}
}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const posts=[];
let result={},failSend=false;
let status={state:'failed',sim_missing:true,sim_present:false,sim_locked:false,registered:false,
 sms_available:false,can_send:false,ussd_available:false,can_ussd:false,ussd_state:0,
 can_enable:false,can_set_mode:false,supported_modes:[[4,0],[8,0],[12,8],[12,4]],current_mode:[8,0]};
const context={console,Date,setTimeout,clearTimeout,Uint8Array,
 crypto:{getRandomValues:webcrypto.getRandomValues.bind(webcrypto)},setInterval:()=>0,
 Option:class extends Element{constructor(text,value){super();this.textContent=text;this.value=value;}},
 document:{hidden:false,getElementById:id=>elements[id]||null,
 createElement:()=>new Element(),createTextNode:text=>({textContent:text})},
 fetch:async(url,options={})=>{
  if(options.method==='POST'){
   const body=JSON.parse(options.body);posts.push(body);
   if(body.action==='status')result=status;
   if(body.action==='send'){if(failSend)throw Error('synthetic lost reply');result={submitted:true,delivery_verified:false};}
   if(body.action==='mode'){status={...status,current_mode:[body.allowed,body.preferred]};result={saved:true};}
   if(body.action==='messages')result={messages:[{number:'fixture',text:'<script>synthetic OTP</script>',state:3,timestamp:''}]};
   if(body.action==='ussd_start')result={reply:'Synthetic USSD reply'};
   return {ok:true};
  }
  return {ok:true,json:async()=>({busy:false,error:null,result})};
 }};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),context);
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));
 for(const id of ['sms-fields','ussd-fields','mode-fields'])if(elements[id])assert(elements[id].disabled);
 assert.equal(posts.length,1);assert.equal(posts[0].action,'status');
 if(section==='network'){
  assert(elements['radio-mode'].options.some(o=>o.textContent==='Chỉ 4G'));
  assert(elements['radio-mode'].options.some(o=>o.textContent==='Chỉ 3G'));
 }
 assert.equal(context.crypto.randomUUID,undefined);
 status={...status,state:'registered',sim_missing:false,sim_present:true,registered:true,
 sms_available:true,can_send:true,ussd_available:true,can_ussd:true,ussd_state:1,can_set_mode:true,secondary_lock:'pin2',
 signal_percent:64,signal_recent:true,operator_name:'Fixture operator',registration_state:1,access_technologies:16384};
 await context.refresh();
 assert.match(elements['network-status'].textContent,/4G LTE/);
 assert.match(elements['network-status'].textContent,/64%/);
 assert.match(elements['modem-status'].textContent,/PIN2/);
 assert(!elements['modem-status'].textContent.includes('SIM đang khóa'));
 assert.equal(elements['chip-network-label'].textContent,'4G');
 if(elements.enable)assert(elements.enable.hidden);
 if(section==='sms'){
 assert.equal(elements['sms-fields'].disabled,false);
 await elements.sms.onsubmit({preventDefault(){}});
 assert.equal(posts.filter(p=>p.action==='send').length,0);
 elements.number.value='+84900111222';elements['sms-text'].value='synthetic';elements['sms-confirm'].checked=true;
 failSend=true;
 await elements.sms.onsubmit({preventDefault(){}});
 const send=posts.find(p=>p.action==='send');assert(send&&send.confirm);
 assert.match(send.operation,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
 assert.equal(elements['sms-confirm'].checked,false);
 await elements.sms.onsubmit({preventDefault(){}});
 assert.equal(posts.filter(p=>p.action==='send').length,1);
 await context.inbox();
 assert.equal(elements.messages.children[0].children[1].textContent,'<script>synthetic OTP</script>');
 }
 if(section==='network'){
 elements['mode-confirm'].checked=true;elements['radio-mode'].value='8,0';
 await elements.mode.onsubmit({preventDefault(){}});
 const mode=posts.find(p=>p.action==='mode');assert.equal(mode.allowed,8);assert.equal(mode.preferred,0);
 assert.equal(elements['mode-confirm'].checked,false);
 }
 if(section==='ussd'){
  assert.equal(elements['ussd-fields'].disabled,false);
  elements.ussd.onsubmit({preventDefault(){}});
  assert.equal(posts.filter(p=>p.action==='ussd_start').length,0);
  await context.ussd('ussd_start',{code:'*101#'});
  assert.equal(elements['ussd-result'].textContent,'Synthetic USSD reply');
  status={...status,ussd_notification:'<script>late account notification</script>'};
  await context.refresh();
  assert.equal(elements['ussd-notification-box'].hidden,false);
  assert.equal(elements['ussd-notification'].textContent,'<script>late account notification</script>');
  assert.equal(elements['ussd-result'].textContent,'Synthetic USSD reply');
  status={...status,ussd_state:2};
  await context.refresh();
  assert.match(elements['ussd-state'].textContent,/đang chờ/);
  assert(elements['ussd-fields'].disabled&&!elements['ussd-cancel'].disabled);
  assert.equal(elements['ussd-result'].textContent,'Synthetic USSD reply');
 }
 status={...status,signal_recent:false};await context.refresh();
 assert.match(elements['network-status'].textContent,/số liệu cũ/);
 status={...status,signal_percent:null,access_technologies:null};await context.refresh();
 assert.match(elements['network-status'].textContent,/Mức sóng: chưa có số liệu/);
 console.log('Modem UI fixture: PASS (no browser, no device, no messages sent)');
})().catch(error=>{console.error(error);process.exitCode=1;});

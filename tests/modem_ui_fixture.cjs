// Exercise the real inline UI script with synthetic DOM/HTTP, not a browser
// or a modem. In particular, private HTTP has no crypto.randomUUID().
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {webcrypto}=require('node:crypto');
const html=fs.readFileSync(process.argv[2],'utf8');
class Element{
 constructor(){this.disabled=false;this.checked=false;this.value='';this.options=[];this.children=[];this.textContent='';}
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
   return {ok:true};
  }
  return {ok:true,json:async()=>({busy:false,error:null,result})};
 }};
vm.createContext(context);
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));
 assert(elements['sms-fields'].disabled&&elements['ussd-fields'].disabled&&elements['mode-fields'].disabled);
 assert.equal(posts.length,1);assert.equal(posts[0].action,'status');
 assert(elements['radio-mode'].options.some(o=>o.textContent==='Chỉ 4G'));
 assert(elements['radio-mode'].options.some(o=>o.textContent==='Chỉ 3G'));
 assert.equal(context.crypto.randomUUID,undefined);
 status={...status,state:'registered',sim_missing:false,sim_present:true,registered:true,
 sms_available:true,can_send:true,ussd_available:true,can_ussd:true,ussd_state:1,can_set_mode:true,secondary_lock:'pin2'};
 await context.refresh();
 assert.equal(elements['sms-fields'].disabled,false);
 assert.match(elements['modem-status'].textContent,/PIN2/);
 assert(!elements['modem-status'].textContent.includes('SIM đang khóa'));
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
 elements['mode-confirm'].checked=true;elements['radio-mode'].value='8,0';
 await elements.mode.onsubmit({preventDefault(){}});
 const mode=posts.find(p=>p.action==='mode');assert.equal(mode.allowed,8);assert.equal(mode.preferred,0);
 assert.equal(elements['mode-confirm'].checked,false);
 await context.inbox();
 assert.equal(elements.messages.children[0].children[1].textContent,'<script>synthetic OTP</script>');
 console.log('Modem UI fixture: PASS (no browser, no device, no messages sent)');
})().catch(error=>{console.error(error);process.exitCode=1;});

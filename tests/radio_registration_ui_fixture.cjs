// Real Quick Settings render/refresh/timer code; delayed SIM readiness, no device.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('uz801_manager/static/quick.js','utf8');
const draw=source.match(/function draw\(s\) \{([\s\S]*?)\n  \}\n  let modeStatus/);assert(draw);
const refresh=source.slice(source.indexOf('  function scheduleStateRead(s)'),source.indexOf('  function ask(action, copy'));
assert(refresh.includes('async function refresh'));
function fixture(){
 let clock=0,next=1,calls=0,mutations=0,reply;
 const timers=new Map(),nodes=new Map();
 const el=id=>{if(!nodes.has(id))nodes.set(id,{dataset:{},disabled:true,textContent:'',open:false});return nodes.get(id)};
 class Clock extends Date{static now(){return clock}}
 const c={Date:Clock,el,compact:false,busy:false,current:null,refreshing:false,refreshAgain:false,
  recoveryTimer:null,radioReadUntil:null,readFailed:false,drawMode:()=>{},readMode:()=>{},document:{hidden:false},
  notice:text=>el('quick-notice').textContent=text,
  tile:(id,text,active,disabled)=>Object.assign(el(id),{text,active,disabled}),
  setTimeout:(fn,ms)=>{const id=next++;timers.set(id,{fn,ms});return id},clearTimeout:id=>timers.delete(id),
  fetch:()=>{mutations++;throw Error('No fetch/mutation expected')},
  portalReadTelemetry:async path=>{assert.equal(path,'/api/quick');calls++;return reply()},
 };
 vm.createContext(c);vm.runInContext(source.match(/const radioReadWindow=\d+;/)[0],c);
 vm.runInContext('function draw(s){'+draw[1]+'\n}\n'+refresh,c);
 return {c,el,timers,set reply(fn){reply=fn},get calls(){return calls},get mutations(){return mutations},
  set time(n){clock=n},
  async next(){assert.equal(timers.size,1);const [id,t]=timers.entries().next().value;timers.delete(id);clock+=t.ms;t.fn();for(let i=0;i<8;i++)await Promise.resolve()},
 };
}
const state=(state=7,ready=true,registered=false)=>({intent:{airplane:false,data_allowed:false},radio:{state,sim_ready:ready,registered},
 mobile_data_connected:false,wifi_role:'local_ap',usb_tethering:{available:true,enabled:false},_telemetry:{stale:false}});
(async()=>{
 const f=fixture();let sample=state(5,false);f.reply=()=>sample;
 await f.c.refresh();assert(f.el('quick-data').disabled);assert.match(f.el('quick-data').text,/chờ modem/);
 sample=state();await f.next();assert(f.el('quick-data').disabled);assert.match(f.el('quick-data').text,/chờ đăng ký/);
 sample=state(8,true,true);await f.next();assert(!f.el('quick-data').disabled);
 assert.equal(f.calls,3);assert.equal(f.timers.size,0,'stop fast reads when radio is ready even though data stays off');
 assert.equal(f.c.current.intent.data_allowed,false);assert.equal(f.mutations,0);
 const airplane=fixture();airplane.reply=()=>({...state(3,false),intent:{airplane:true,data_allowed:false}});
 await airplane.c.refresh();assert.equal(airplane.timers.size,0);assert(airplane.el('quick-data').disabled);
 assert.match(airplane.el('quick-data').text,/máy bay/);
 const missing=fixture();missing.reply=()=>state(-1,false);await missing.c.refresh();assert.equal(missing.timers.size,0);
 const bounded=fixture();bounded.reply=()=>state();await bounded.c.refresh();assert.equal(bounded.timers.size,1);
 bounded.time=120001;await bounded.next();assert.equal(bounded.timers.size,0,'registration wait never creates an endless two-second loop');
 await bounded.c.refresh(true);assert.equal(bounded.timers.size,1,'explicit Read Again rearms only reads');assert.equal(bounded.mutations,0);
 for(const suppressed of ['hidden','confirm','wifi']){
  const x=fixture();x.reply=()=>state();
  if(suppressed==='hidden')x.c.document.hidden=true;
  else x.el(suppressed==='confirm'?'quick-dialog':'quick-wifi-dialog').open=true;
  await x.c.refresh();assert.equal(x.timers.size,0);assert.equal(x.mutations,0);
 }
 const hidden=fixture();hidden.reply=()=>state();await hidden.c.refresh();hidden.c.document.hidden=true;
 await hidden.next();assert.equal(hidden.calls,1,'a previously armed timer must not read in background');
 const stale=fixture();let fresh=false;stale.reply=()=>fresh?state(8,true,true):({...state(),_telemetry:{stale:true}});
 await stale.c.refresh();assert(stale.el('quick-data').disabled);fresh=true;await stale.next();
 assert(!stale.el('quick-data').disabled);assert.equal(stale.timers.size,0);
 console.log('Delayed radio readiness, data-off veto, bounded visible-page GET and fresh unlock: PASS');
})().catch(error=>{console.error(error);process.exitCode=1});

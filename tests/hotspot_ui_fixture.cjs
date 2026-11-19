// Old combined activation is gone. Only an existing trial can be kept/rolled back.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
assert(!html.includes('id="hotspot-start"'));assert(!html.includes('id="hotspot-apn-settings"'));
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],{disabled:false,hidden:false,textContent:''}]));
let state={pending:false,hotspot_active:false,cellular_connected:false,enabled:false},interval,confirmed=false;
const writes=[],tick=()=>new Promise(r=>setImmediate(r));
const context={console,Date,setTimeout,setInterval:fn=>{interval=fn},location:{},window:{confirm:()=>confirmed},
 document:{hidden:false,getElementById:id=>elements[id],querySelector:selector=>selector==='.portal-header'?{dataset:{statusToken:'fixture'}}:null},
 fetch:async(url,options={})=>{
  if(options.method==='POST'){const value=JSON.parse(options.body);writes.push(value);state={...state,pending:false};return {ok:true};}
  if(url==='/api/hotspot/state')return {ok:true,json:async()=>({busy:false,last_operation:{action:writes.at(-1)?.action},result:state})};
  assert.equal(url,'/api/hotspot/summary');return {ok:true,status:200,json:async()=>state};
 }};
vm.createContext(context);vm.runInContext(fs.readFileSync('uz801_manager/static/hotspot_page.js','utf8'),context);
(async()=>{
 await tick();assert.equal(writes.length,0);assert(elements['hotspot-pending'].hidden);assert(elements['hotspot-keep'].disabled);
 state={...state,pending:true,hotspot_active:true,cellular_connected:true,seconds_remaining:60,attempt:'fixture-attempt'};
 interval();await tick();assert(!elements['hotspot-pending'].hidden);assert(!elements['hotspot-keep'].disabled);
 await elements['hotspot-keep'].onclick();assert.equal(writes.length,0);
 confirmed=true;await elements['hotspot-keep'].onclick();assert.equal(writes.length,1);
 assert.deepEqual(writes[0],{action:'keep',confirm:true,attempt:'fixture-attempt'});
 assert(elements['hotspot-pending'].hidden);
 state={...state,pending:true};interval();await tick();await elements['hotspot-rollback'].onclick();
 assert.deepEqual(writes[1],{action:'stop',confirm:true});
 assert(!writes.some(v=>v.action==='start'||v.action==='configure_apn'));
 console.log('Hotspot read-only page and legacy trial consent PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Node{constructor(){this.children=[];this.textContent=''}replaceChildren(){this.children=[]}append(...nodes){this.children.push(...nodes)}}
const nodes=Object.fromEntries(['usage-refresh','usage-status','usage-values'].map(id=>[id,new Node()]));
let sample={_telemetry:{stale:true},system:{sim_usage:{available:false,stale:true}}},saved=null,followup=null,fail=false;
const c={document:{hidden:false,getElementById:id=>nodes[id],createElement:()=>new Node()},
 portalReadTelemetry:async path=>{assert.equal(path,'/api/overview');if(fail)throw Error('offline');return sample},
 portalRememberSettings:(kind,value)=>{assert.equal(kind,'usage');saved=value},portalRestoreSettings:()=>saved?{...saved,_display_cached:true}:null,
 setTimeout:(fn,ms)=>{assert.equal(ms,2000);followup=fn;return 1},setInterval:()=>0};
vm.createContext(c);vm.runInContext(fs.readFileSync('uz801_manager/static/sim_usage.js','utf8'),c);
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{await tick();assert(saved&&saved.available===false);assert.equal(nodes['usage-values'].children.length,8);assert(followup);
 const amount={total_bytes:1048576,download_bytes:1048576,upload_bytes:0};sample={system:{sim_usage:{available:true,today:amount,month:amount,session:amount,total:amount}}};
 followup();await tick();assert(saved.available);assert.match(nodes['usage-values'].children[1].textContent,/1.00 MiB/);
 fail=true;nodes['usage-refresh'].onclick();await tick();assert.match(nodes['usage-values'].children[1].textContent,/1.00 MiB/);
 console.log('SIM usage cache handles initial stale/unavailable, one follow-up, fresh and failed reads: PASS');
})().catch(e=>{console.error(e);process.exitCode=1});

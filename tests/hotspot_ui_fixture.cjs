const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],{value:'',checked:false,hidden:false}]));
const calls=[];let confirmed=false,result={configured:true,ssid:'Fixture USB',channel:6,apn:'',ap_supported:true,enabled:false,hotspot_active:false,cellular_connected:false,pending:false,verification:'UNVERIFIED'};
const context={console,Date,setTimeout,setInterval:()=>0,location:{},confirm:()=>confirmed,
 document:{hidden:false,getElementById:id=>elements[id],querySelectorAll:()=>[]},
 fetch:async(url,options={})=>{if(options.method==='POST'){assert.equal(url,'/api/hotspot');const data=JSON.parse(options.body);calls.push(data);if(data.action==='start')result={...result,pending:true,hotspot_active:true,attempt:'a'.repeat(32),seconds_remaining:280};return {ok:true,status:202};}assert.equal(url,'/api/hotspot/state');return {ok:true,json:async()=>({busy:false,result})};}};
vm.createContext(context);vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
const tick=()=>new Promise(r=>setImmediate(r));
(async()=>{await tick();assert.deepEqual(calls.map(v=>v.action),['status']);assert(elements['hotspot-start'].disabled);
 elements['hotspot-start'].onclick();await tick();assert.equal(calls.length,1);
 elements['hotspot-consent'].checked=true;elements['hotspot-consent'].onchange();assert(!elements['hotspot-start'].disabled);
 elements['hotspot-start'].onclick();await tick();assert.equal(calls.length,1);
 elements['hotspot-password'].value='private-fixture-password';elements['hotspot-settings'].onsubmit({preventDefault(){}});await tick();
 assert.equal(calls[1].action,'configure');assert.equal(elements['hotspot-password'].value,'');assert(!calls.some(v=>v.action==='start'));
 confirmed=true;elements['hotspot-start'].onclick();await tick();const start=calls.find(v=>v.action==='start');
 assert(start.confirm&&start.cellular_consent&&start.switch_wifi);assert.equal(elements['hotspot-pending'].hidden,false);
 assert(!calls.some(v=>v.action==='keep'));assert.equal(elements['hotspot-consent'].checked,false);
 console.log('Hotspot explicit consent fixture: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

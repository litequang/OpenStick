// Shared display reads only: never retry a mutation or fetch credentials.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
let clock=100000,calls=[],reply=()=>({ok:true,status:200,json:async()=>({connected:true,_telemetry:{age_seconds:0,stale:false}})});
class Clock extends Date{static now(){return clock}}
const context={Date:Clock,console,AbortController,location:{},
 setTimeout:(fn,ms)=>{if(ms<=4000)setImmediate(()=>{clock+=ms;fn()});return 0},clearTimeout:()=>{},setInterval:()=>0,
 sessionStorage:{getItem:()=>null,setItem:()=>{}},
 document:{hidden:false,getElementById:()=>null,querySelector:()=>({dataset:{statusToken:'fixture'}})},
 fetch:async(path,options)=>{assert(!options.method||options.method==='GET');assert.equal(options.cache,'no-store');assert.equal(options.headers['X-OpenStick-Token'],'fixture');calls.push(path);return reply(path)}};
vm.createContext(context);vm.runInContext(fs.readFileSync('uz801_manager/static/portal_nav.js','utf8'),context);
(async()=>{
 const values=await Promise.all(Array.from({length:8},()=>context.portalReadTelemetry('/api/header')));
 assert.equal(calls.length,1);assert(values.every(v=>v.connected));
 let pending=true;calls=[];
 reply=()=>{if(pending){pending=false;return {ok:false,status:503,json:async()=>({error:'STATUS_PENDING'})}}return {ok:true,status:200,json:async()=>({services:{modemmanager:true}})}};
 assert((await context.portalReadTelemetry('/api/services')).services.modemmanager);
 assert.equal(calls.length,2);
 calls=[];reply=()=>({ok:true,status:200,json:async()=>({_telemetry:{stale:true},old:true})});
 assert((await context.portalReadTelemetry('/api/quick')).old);
 assert.equal(calls.length,1,'retained stale data must render immediately without a retry burst');
 calls=[];reply=()=>({ok:false,status:503,json:async()=>({error:'STATUS_PENDING'})});
 await assert.rejects(context.portalReadTelemetry('/api/quick'));
 assert.equal(calls.length,5,'pending reads back off with a finite deadline');
 calls=[];reply=()=>({ok:true,status:200,json:async()=>({connected:true,_telemetry:{age_seconds:0,stale:false}})});
 await Promise.all([context.portalLoadHeader(),context.portalLoadHeader(),context.portalLoadHeader()]);
 await context.portalLoadHeader();assert.equal(calls.length,1);
 clock+=5001;await context.portalLoadHeader();assert.equal(calls.length,2);
 for(const path of ['/api/setup/credentials','/api/device/power','/api/modem'])await assert.rejects(context.portalReadTelemetry(path));
 assert.equal(calls.length,2);
 calls=[];context.document.hidden=true;reply=()=>({ok:false,status:503,json:async()=>({error:'STATUS_PENDING'})});
 await assert.rejects(context.portalReadTelemetry('/api/overview'));assert.equal(calls.length,1);
 context.document.hidden=false;calls=[];reply=()=>({ok:false,status:401,json:async()=>({error:'UNAUTHORIZED'})});
 await assert.rejects(context.portalReadTelemetry('/api/overview'));assert.equal(context.location.href,'/login');assert.equal(calls.length,1);
 reply=()=>{throw Error('offline fixture')};await assert.rejects(context.portalReadTelemetry('/api/overview'));
 reply=()=>({ok:true,status:200,json:async()=>({recovered:true})});
 assert((await context.portalReadTelemetry('/api/overview')).recovered,'failed requests must release the in-flight slot');
 console.log('Shared telemetry GET, coalescing, TTL, pending/stale/error/auth fixture: PASS');
})().catch(error=>{console.error(error);process.exitCode=1});

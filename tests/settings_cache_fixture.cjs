// Explicit projection and navigation persistence; no backend or device writes.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
function storage(){const data=new Map();return {getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v),removeItem:k=>data.delete(k),values:()=>[...data.values()]}}
const disk=storage();let clock=100000,csrf='';
class Clock extends Date{static now(){return clock}}
function context(){const session=storage(),c={Date:Clock,console,sessionStorage:session,localStorage:disk,
 document:{getElementById:()=>null,querySelector:selector=>selector.includes('csrf')&&csrf?{value:csrf}:null},setInterval:()=>0};
 vm.createContext(c);vm.runInContext(fs.readFileSync('uz801_manager/static/portal_nav.js','utf8'),c);return c}
const first=context();
const secret={password:'never-cache-password',username:'never-cache-user',imsi:'never-cache-imsi',text:'never-cache-sms',reply:'never-cache-ussd',operation:'never-cache-receipt'};
first.portalRememberSettings('quick',{...secret,intent:{airplane:false,data_allowed:true,...secret},radio:{state:11,registered:true,sim_ready:true,...secret},wifi_role:'sim_ap',mobile_data_connected:true,usb_tethering:{available:true,enabled:true,...secret}});
const next=context(),value=next.portalRestoreSettings('quick');
assert(value._display_cached&&value.wifi_role==='sim_ap'&&value.radio.state===11);
assert(!disk.values().join('').includes('never-cache'));
next.portalRememberSettings('cellular',{settings:{available:true,apn:'fixture',...secret},profiles:[{id:'fixture-profile',name:'Fixture',...secret}]});
next.portalRememberSettings('modem',{supported_modes:[[8,0],[4,0]],current_mode:[8,0],can_set_mode:true,ussd_prompt:'never-cache-prompt',...secret});
assert.equal(context().portalRestoreSettings('modem').current_mode[0],8);
assert(!disk.values().join('').includes('never-cache'));
next.portalRememberSettings('clients',{count:1,blocked:[],clients:[{mac:'02:00:00:00:00:01',name:'session-only-client'}]});
assert(next.portalRestoreSettings('clients'));
assert.equal(context().portalRestoreSettings('clients'),null);
assert(!disk.values().join('').includes('session-only-client'));
csrf='another-login';assert.equal(context().portalRestoreSettings('quick'),null);
csrf='';clock+=8*3600000;assert.equal(context().portalRestoreSettings('quick'),null);
assert.equal(context().portalRestoreSettings('unknown'),null);
console.log('Settings cache projections, cross-navigation/new-tab, auth scope, TTL, credentials exclusion: PASS');

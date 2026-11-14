// Synthetic DOM fixture only: no real LEDs, network changes or visual acceptance.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
class Element{
 constructor(){this.children=[];this.style={};this.value='';this.disabled=false;this.hidden=false;this.textContent='';}
 append(...nodes){this.children.push(...nodes)}replaceChildren(...nodes){this.children=nodes}
 set innerHTML(_){throw Error('Use textContent')}
}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const status={supported:true,saved:false,leds:['red','green','blue'].map(id=>({id,label:id,modes:['default','off','on','blink'],settings:{mode:'default',on_ms:500,off_ms:500},lit:id==='red',controlled:false}))};
const posts=[],gets=[];
const context={console,location:{},Option:class{constructor(text,value){this.textContent=text;this.value=value}},
 document:{getElementById:id=>elements[id],createElement:()=>new Element()},
 fetch:async(url,options)=>{assert.equal(url,'/api/leds');assert.equal(options.headers['X-OpenStick-Token'],'fixture');
  if(options.method==='POST'){const body=JSON.parse(options.body);posts.push(body);status.saved=true;for(const led of status.leds)led.settings=body.settings[led.id]}
  else gets.push(url);
  return {ok:true,json:async()=>status};}};
vm.createContext(context);vm.runInContext(html.match(/<script>(const ledToken=[\s\S]*?)<\/script>/)[1],context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../uz801_manager/static/leds.js'),'utf8'),context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));assert.equal(posts.length,0);assert.equal(gets.length,1);
 const controls=()=>vm.runInContext('ledControls',context);
 const blue=controls().find(c=>c.id==='blue');blue.select.value='blink';blue.select.onchange();blue.inputs.on_ms.value='250';blue.inputs.off_ms.value='750';
 assert.equal(blue.inputs.on_ms.disabled,false);assert.equal(posts.length,0);
 await elements['led-form'].onsubmit({preventDefault(){}});
 assert.equal(posts.length,1);assert.equal(posts[0].confirm,true);
 assert.deepEqual(posts[0].settings.blue,{mode:'blink',on_ms:250,off_ms:750});
 elements['led-all-off'].onclick();assert(controls().every(c=>c.select.value==='off'));assert.equal(posts.length,1);
 elements['led-default'].onclick();assert(controls().every(c=>c.select.value==='default'));assert.equal(posts.length,1);
 await elements['led-form'].onsubmit({preventDefault(){}});assert.equal(posts.length,2);
 await elements['led-refresh'].onclick();assert.equal(posts.length,2);assert.equal(gets.length,2);
 assert.match(elements['led-notice'].textContent,/Đã đọc/);
 console.log('LED UI fixture: PASS (synthetic only)');
})().catch(error=>{console.error(error);process.exitCode=1});

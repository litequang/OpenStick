// Synthetic DOM fixture only: no browser, USB, Wi-Fi changes or downloads.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8'),connected=process.argv[3]==='connected';
class Element {
 constructor(){this.disabled=false;this.dataset={};this.value='';this.open=true;this.options=[];this.textContent='';}
 replaceChildren(...nodes){this.options=nodes;}
 add(node){this.options.push(node);}
 set innerHTML(_){throw Error('Render network data as text');}
}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const posts=[];let result={},timer;
const state={state:connected?'100 (connected)':'30 (disconnected)',connected,
 ssid:connected?'fixture <script>':null,signal_percent:64,signal_dbm:-65,tx_mbps:90,rx_mbps:121.5,
 ipv4:['192.0.2.2/24'],gateway:'192.0.2.1'};
const context={Date,console,setTimeout,clearTimeout,
 location:{hash:'',pathname:'/'},sessionStorage:{getItem:()=>'',setItem(){}},history:{replaceState(){}},
 setInterval:fn=>{timer=fn;return 0;},Option:class {constructor(text,value){this.textContent=text;this.value=value;}},
 document:{hidden:false,getElementById:id=>elements[id]||null,querySelectorAll:()=>['check','speed','scan','connect'].map(k=>elements[k])},
 fetch:async(_,options={})=>{
  if(options.method==='POST'){
   const body=JSON.parse(options.body);posts.push(body);
   if(body.action==='status')result=state;
   if(body.action==='speed')result={download_mbps:10,duration_s:1.68,bytes:2097152};
   if(body.action==='scan')result={networks:[]};
   return {ok:true};
  }
  return {ok:true,json:async()=>({busy:false,error:false,result})};
 }};
vm.createContext(context);
vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),context);
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(posts.length,1);assert.equal(posts[0].action,'status');
 assert.equal(elements['wifi-settings'].open,!connected);
 assert.equal(elements.speed.disabled,!connected);
 if(connected){
  assert.match(elements.status.textContent,/fixture <script>/);
  assert.match(elements.status.textContent,/-65 dBm/);
  assert.match(elements.status.textContent,/90 Mbps/);
  assert.equal(elements['wifi-summary'].textContent,'Đổi Wi-Fi');
  await elements.speed.onclick();
  assert.match(elements['speed-result'].textContent,/10 Mbps/);
  elements['wifi-settings'].open=true; // Preserve an owner's explicit expansion.
 }
 timer();await new Promise(resolve=>setImmediate(resolve));
 assert.equal(posts.filter(p=>p.action==='speed').length,connected?1:0);
 assert.equal(posts.filter(p=>p.action==='scan').length,0);
 if(connected)assert(elements['wifi-settings'].open);
 await elements.scan.onclick();
 assert(elements['wifi-settings'].open);
 console.log('Wi-Fi UI fixture: PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});

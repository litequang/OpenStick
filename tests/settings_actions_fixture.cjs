// Behavioral regressions for settings drafts, consent and duplicate submissions.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element {
 constructor(){this.value='';this.checked=false;this.disabled=false;this.hidden=false;this.textContent='';this.children=[]}
 append(...v){this.children.push(...v)}replaceChildren(...v){this.children=v}
 addEventListener(name,fn){this[name]=fn}focus(){this.focused=true}
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function policy(){
 const html=fs.readFileSync('uz801_manager/templates/internet.html','utf8');
 const els=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const posts=[];let confirmed=false;
 const state={config:{mode:'wifi_preferred',enabled:false,auto_wifi:true},runtime:{source:'wifi',health:{wifi:true}}};
 const context={Date,console,setTimeout,policyToken:'fixture',location:{},confirm:()=>confirmed,window:{confirm:()=>confirmed},
  document:{getElementById:id=>els[id]},fetch:async(url,options={})=>{
   if(options.method==='POST')posts.push(JSON.parse(options.body));
   return {ok:true,json:async()=>({busy:false,result:state})};
  }};
 vm.createContext(context);vm.runInContext(fs.readFileSync('uz801_manager/static/internet.js','utf8'),context);await tick();
 assert.deepEqual(posts.map(x=>x.action),['status']);
 els['internet-mode'].value='sim_only';els['internet-mode'].onchange();els['policy-form'].input();
 els['policy-refresh'].onclick();await tick();assert.equal(posts.length,1);assert.equal(els['internet-mode'].value,'sim_only');
 els['policy-enabled'].checked=true;els['policy-confirm'].checked=true;
 await els['policy-form'].onsubmit({preventDefault(){}});assert.equal(posts.length,1);assert.match(els['policy-notice'].textContent,/cho phép dữ liệu/);
 confirmed=true;els['policy-refresh'].onclick();await tick();assert.equal(posts.length,2);assert.equal(els['internet-mode'].value,'wifi_preferred');
 els['internet-mode'].value='wifi_only';els['policy-cellular'].checked=true;els['internet-mode'].onchange();
 assert.equal(els['policy-cellular'].checked,false);assert.equal(els['policy-cellular'].disabled,true);
}
async function lan(){
 const html=fs.readFileSync('uz801_manager/templates/lan_settings.html','utf8');
 const els=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
 const posts=[];let finish;
 const context={console,token:'fixture',confirm:()=>false,document:{getElementById:id=>els[id],createElement:()=>new Element()},
  fetch:async(url,options)=>{const data=JSON.parse(options.body);posts.push(data);if(data.action==='configure')await new Promise(resolve=>{finish=resolve});return {ok:true,json:async()=>({enabled:true,url:'http://192.0.2.2:8765',stable_url:'http://example.invalid:8765'})}}};
 vm.createContext(context);vm.runInContext(fs.readFileSync('uz801_manager/static/lan_settings.js','utf8'),context);await tick();
 els['lan-password'].value='fictional-password';els['lan-password-repeat'].value='wrong-password';
 els['lan-settings'].onsubmit({preventDefault(){}});assert.equal(posts.length,1);assert(els['lan-password-repeat'].focused);
 els['lan-password-repeat'].value='fictional-password';const pending=els['lan-settings'].onsubmit({preventDefault(){}});
 assert.equal(els['lan-fields'].disabled,true);assert.equal(els['lan-password'].value,'');
 els['lan-settings'].onsubmit({preventDefault(){}});els['lan-refresh'].onclick();assert.equal(posts.length,2);
 finish();await pending;assert.equal(els['lan-fields'].disabled,false);assert.equal(posts[1].action,'configure');
 assert.equal(els['lan-password-repeat'].value,'');
}
(async()=>{await policy();await lan();console.log('Settings consent/draft/duplicate protection PASS')})().catch(e=>{console.error(e);process.exitCode=1});

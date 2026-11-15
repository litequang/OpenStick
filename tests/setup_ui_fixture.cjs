// Synthetic setup flow: choosing an SSID must never submit a connection.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class Element{constructor(){this.disabled=false;this.value='';this.textContent='';this.options=[];this.hidden=false;this.type='password';this.attrs={};this.dataset={}}replaceChildren(...v){this.options=v}add(v){this.options.push(v)}setAttribute(k,v){this.attrs[k]=v}}
const html=fs.readFileSync('uz801_manager/templates/setup.html','utf8');
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const posts=[];const state={enabled:true,configured:true,setup_active:true,busy:false,ssid:'fixture-ap',url:'http://192.0.2.1:8765/setup',networks:[{ssid:'fixture <script>',signal:70,security:'WPA2'}],scan_at:100};
const context={Date,console,setTimeout,URL,location:{},confirm:()=>true,
 Option:class{constructor(text,value){this.textContent=text;this.value=value}},setInterval:()=>0,
 document:{hidden:false,getElementById:id=>elements[id],querySelector:()=>({dataset:{statusToken:'fixture-token'}})},
 fetch:async(url,opts={})=>{if(opts.method==='POST'){
  const post=JSON.parse(opts.body);posts.push(post);
  if(post.action==='enable')state.enabled=true;
  if(post.action==='disable')state.enabled=false;
  if(post.action==='start')state.setup_active=true;
  if(post.action==='stop')state.setup_active=false;
 }return {ok:true,json:async()=>state}}
};
vm.createContext(context);vm.runInContext(fs.readFileSync('uz801_manager/static/setup.js','utf8'),context);
(async()=>{
 await new Promise(r=>setImmediate(r));assert.equal(posts.length,0);
 assert.match(html,/class="setup-panel-grid"/);assert.match(html,/for="setup-ap-ssid"/);
 assert.match(html,/id="setup-auto-state"/);assert.match(html,/id="setup-ap-state"/);
 assert.equal(elements['setup-auto-state'].dataset.active,'true');
 assert.equal(elements['setup-ap-state'].dataset.active,'true');
 assert.equal(elements['setup-enable'].hidden,true);assert.equal(elements['setup-disable'].hidden,false);
 assert.equal(elements['setup-start'].hidden,true);assert.equal(elements['setup-stop'].hidden,false);
 elements['setup-password-toggle'].onclick();assert.equal(elements['setup-password'].type,'text');
 assert.equal(elements['setup-password-toggle'].attrs['aria-pressed'],'true');
 elements['setup-password-toggle'].onclick();assert.equal(elements['setup-password'].type,'password');
 elements['setup-ap-password-toggle'].onclick();assert.equal(elements['setup-ap-password'].type,'text');
 assert.equal(posts.length,0);
 assert.match(elements['setup-networks'].options[1].textContent,/fixture <script>/);
 elements['setup-networks'].value='fixture <script>';elements['setup-networks'].onchange();
 assert.equal(elements['setup-ssid'].value,'fixture <script>');assert.equal(posts.length,0);
 elements['setup-ssid'].value='hidden fixture';elements['setup-password'].value='fixture-password';
 elements['setup-connect'].onsubmit({preventDefault(){}});await new Promise(r=>setImmediate(r));
 assert.equal(posts.length,1);assert.equal(posts[0].action,'connect');assert.equal(posts[0].ssid,'hidden fixture');
 assert.equal(posts[0].password,'fixture-password');assert.equal(elements['setup-password'].value,'');
 elements['setup-scan'].onclick();await new Promise(r=>setImmediate(r));
 assert.equal(posts[1].action,'scan');assert.equal(posts[1].confirm,true);
 elements['setup-disable'].onclick();await new Promise(r=>setImmediate(r));
 assert.equal(posts[2].action,'disable');assert.equal(elements['setup-auto-state'].dataset.active,'false');
 assert.equal(elements['setup-enable'].hidden,false);assert.equal(elements['setup-disable'].hidden,true);
 elements['setup-stop'].onclick();await new Promise(r=>setImmediate(r));
 assert.equal(posts[3].action,'stop');assert.equal(elements['setup-ap-state'].dataset.active,'false');
 assert.equal(elements['setup-start'].hidden,false);assert.equal(elements['setup-stop'].hidden,true);
 elements['setup-enable'].onclick();await new Promise(r=>setImmediate(r));
 assert.equal(posts[4].action,'enable');assert.equal(elements['setup-auto-state'].dataset.active,'true');
 assert.equal(elements['setup-enable'].hidden,true);assert.equal(elements['setup-disable'].hidden,false);
 elements['setup-start'].onclick();await new Promise(r=>setImmediate(r));
 assert.equal(posts[5].action,'start');assert.equal(elements['setup-ap-state'].dataset.active,'true');
 assert.equal(elements['setup-start'].hidden,true);assert.equal(elements['setup-stop'].hidden,false);
 console.log('setup selection/manual entry/explicit handoff/scan/advanced state PASS');
})().catch(e=>{console.error(e);process.exitCode=1});

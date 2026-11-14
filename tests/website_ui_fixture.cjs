// Execute the rendered editor script; no browser/visual acceptance is implied.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
class Element{constructor(){this.textContent='';this.value='';this.children=[];this.files=[];}replaceChildren(){this.children=[];}append(item){this.children.push(item);}focus(){}set innerHTML(_){throw Error('Unsafe markup rendering');}}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const calls=[],version='a'.repeat(64),content='<script>private-editor-fixture</script>';
let confirmed=false;
const context={console,Uint8Array,confirm:()=>confirmed,window:{addEventListener(){}},location:{},
 document:{getElementById:id=>elements[id],querySelectorAll:()=>[],createElement:()=>new Element()},
 fetch:async(url,options)=>{assert.equal(url,'/api/site');const value=JSON.parse(options.body);calls.push(value);
  const data=value.action==='list'?{files:[{path:'index.html',bytes:content.length}],bytes:content.length}:
   value.action==='get'?{text:content,etag:version}:{saved:true,etag:'b'.repeat(64)};
  return {ok:true,status:200,json:async()=>data};}};
vm.createContext(context);vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async()=>{await new Promise(r=>setImmediate(r));assert.deepEqual(calls.map(v=>v.action),['list']);
 await elements['site-files'].children[0].onclick();assert.equal(elements['site-text'].value,content);
 await elements['site-save'].onclick();assert.equal(calls.filter(v=>v.action==='put').length,0);
 confirmed=true;elements['site-text'].value='<h1>Changed</h1>';await elements['site-save'].onclick();
 const saved=calls.find(v=>v.action==='put');assert.equal(saved.expected,version);assert.equal(saved.confirm,true);
 assert.equal(saved.text,'<h1>Changed</h1>');assert(!calls.some(v=>v.action==='delete'));
 console.log('Static website editor fixture: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

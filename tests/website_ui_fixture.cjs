// Execute the actual panel asset against a small synthetic DOM/API.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(process.argv[2],'utf8');
class Element{constructor(){this.textContent='';this.value='';this.children=[];this.files=[];this.dataset={};this.attrs={};}replaceChildren(){this.children=[];}append(...items){this.children.push(...items);}focus(){}scrollIntoView(){}setAttribute(k,v){this.attrs[k]=v;}querySelectorAll(){return [];}set innerHTML(_){throw Error('Unsafe markup rendering');}}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
const calls=[],version='a'.repeat(64),content='<script>private-editor-fixture</script>';
let confirmed=false;
const entry={path:'index.html',bytes:content.length,kind:'file',editable:true};
const listing={entries:[entry],bytes:content.length,revision:'r'};
const main=new Element(),header=new Element();header.dataset.statusToken='fixture';
const transfers=[];let nextTransferError=null;
class Data{constructor(){this.values={};}append(k,v){this.values[k]=v;}}
class Xhr{constructor(){this.upload={};}open(method,url){assert.equal(url,'/api/websites/transfer');}setRequestHeader(){}send(data){transfers.push(data.values.action);this.status=nextTransferError==='HTTP_413'?413:nextTransferError?400:200;this.responseText=JSON.stringify(nextTransferError?{error:nextTransferError}:{files:[{path:'index.html',bytes:20,kind:'file',overwrite:true}],bytes:20,digest:'zip',revision:'r'});this.onload();}}
const context={console,Uint8Array,setTimeout,FormData:Data,XMLHttpRequest:Xhr,confirm:()=>confirmed,window:{addEventListener(){}},location:{},
 document:{getElementById:id=>elements[id],querySelector:selector=>selector==='.web-panel'?main:header,createElement:()=>new Element()},
 fetch:async(url,options)=>{assert.equal(url,'/api/websites');const value=JSON.parse(options.body);calls.push(value);
  const data=value.action==='sites'?{sites:[{id:'main',name:'Fixture',domains:['example.com']}],revision:'inventory',routing:{available:false,local:'NOT_INSTALLED'}}:
   value.action==='list'||value.action==='put'?listing:value.action==='get'?{text:content,etag:version}:{};
  return {ok:true,status:200,json:async()=>data};}};
assert(html.includes('/static/website.js'));
vm.createContext(context);vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../uz801_manager/static/website.js'),'utf8'),context);
(async()=>{await new Promise(r=>setImmediate(r));assert.deepEqual(calls.map(v=>v.action),['sites','list']);
 await elements['site-files'].children[0].onclick();assert.equal(elements['site-text'].value,content);
 await elements['site-save'].onclick();assert.equal(calls.filter(v=>v.action==='put').length,0);
 confirmed=true;elements['site-text'].value='<h1>Changed</h1>';await elements['site-save'].onclick();
 const saved=calls.find(v=>v.action==='put');assert.equal(saved.expected,version);assert.equal(saved.confirm,true);
 assert.equal(saved.text,'<h1>Changed</h1>');assert(!calls.some(v=>v.action==='delete'));
 assert.equal(saved.site,'main');assert.equal(saved.revision,'r');
 // A ZIP in the normal picker must trigger only inspection, with visible feedback.
 elements['site-upload'].files=[{name:'bundle.ZIP',size:123}];elements['site-upload'].onchange();
 await new Promise(r=>setImmediate(r));assert.deepEqual(transfers,['inspect_zip']);
 assert.equal(elements['web-zip-publish'].disabled,false);
 assert(elements['web-upload-status'].textContent.includes('kiểm tra thành công'));
 confirmed=false;await elements['web-zip-publish'].onclick();assert.deepEqual(transfers,['inspect_zip']);
 nextTransferError='ZIP_INVALID';elements['web-zip'].files=[{name:'bad.zip',size:5}];elements['web-zip'].onchange();
 await new Promise(r=>setImmediate(r));assert.equal(elements['web-zip-publish'].disabled,true);
 assert.equal(elements['web-upload-status'].dataset.error,'true');
 nextTransferError='HTTP_413';await elements['web-zip-inspect'].onclick();
 assert(elements['web-upload-status'].textContent.includes('HTTP 413'));
 assert(!elements['web-upload-status'].textContent.includes('ZIP vượt 128 MiB'));
 console.log('Static website editor fixture: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

// Render the actual dashboard script with fixtures; not a visual browser test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(process.argv[2],'utf8');
class Element{constructor(){this.textContent='';this.style={};this.dataset={};this.children=[];}replaceChildren(){this.children=[];}append(...items){this.children.push(...items);}setAttribute(name,value){this[name]=value;}set innerHTML(_){throw Error('Use textContent');}}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
let posts=0,failFetch=false,busyOnce=false,onBusy=null;
const data={system:{ram:{used:150*1048576,total:400*1048576},storage:{used:1073741824,total:2*1073741824},
 temperature_c:41,load:[.08,.29,.47],sms:{submitted_today:1,submitted_month:2,unknown_today:1,estimated_today_vnd:null},
 emmc:{life_used_ranges:[],pre_eol:'unknown',written_since_boot:1048576,estimated_daily_write:113*1048576},
 swap:{used:0,total:500*1048576,zram_used:0,zram_total:500*1048576,other_used:0,other_total:0},
 sim_usage:{available:true,status:'connected',stale:false,error:null,started_at:1795000000,sampled_at:1795000100,saved_at:1795000050,continuity_gaps:0,
 today:{download_bytes:1048576,upload_bytes:1048576,total_bytes:2097152},
 month:{download_bytes:3145728,upload_bytes:1048576,total_bytes:4194304},
 total:{download_bytes:5242880,upload_bytes:1048576,total_bytes:6291456},
 session:{download_bytes:1048576,upload_bytes:1048576,total_bytes:2097152},undated:{download_bytes:0,upload_bytes:0,total_bytes:0},imsi:'private-usage-fixture'},
 uptime_s:2400,os:'<script>Fixture Linux</script>',kernel:'fixture'},
 wifi:{connected:true,ssid:'fixture',ipv4:['192.0.2.2/24'],modem_status:{operator_name:'Fixture carrier',registered:true,sim_present:true,signal_percent:64,signal_recent:true,access_technologies:16384,imsi:'not-for-browser-cache'}},
 services:{'openstick-web':true,'cloudflared':null}};
const saved=new Map(),sessionStorage={getItem:key=>saved.get(key)||null,setItem:(key,value)=>saved.set(key,value)};
let telemetryClock=Date.now();class TelemetryDate extends Date{static now(){return telemetryClock}}
const telemetryTimer=(fn,ms)=>{if([1000,2000,4000].includes(ms)){setImmediate(()=>{telemetryClock+=ms;fn()});return 0}return setTimeout(fn,ms)};
const context={console,Date:TelemetryDate,setTimeout:telemetryTimer,clearTimeout,AbortController,setInterval:()=>0,sessionStorage,document:{hidden:false,getElementById:id=>elements[id]||null,createElement:()=>new Element(),querySelector:()=>({dataset:{statusToken:'fixture'}})},
 fetch:async(url,options={})=>{if(failFetch)throw Error('offline fixture');if(options.method==='POST')posts++;assert.notEqual(options.method,'POST','opening Overview must only read');assert.equal(url,'/api/overview');if(busyOnce){busyOnce=false;if(onBusy)onBusy();return {ok:false,status:503,json:async()=>({error:'STATUS_PENDING'})}}return {ok:true,status:200,json:async()=>data};}};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),context);
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));assert.equal(posts,0);
 assert.equal(elements['metric-ram'].textContent,'150 MiB');
 assert.equal(elements['metric-sim-usage'].textContent,'2.00 MiB');
 assert.match(elements['note-sim-usage'].textContent,/hôm nay.*1.00 MiB/);
 assert.match(elements['sim-usage-detail'].textContent,/Tháng này.*Tổng từ lúc bắt đầu/);
 assert.equal(elements['card-emmc'].hidden,true);
 assert.match(elements['note-sms'].textContent,/chưa cài đơn giá/);
 assert.equal(elements['overview-os'].textContent,'<script>Fixture Linux</script>');
 assert.equal(elements['chip-network-label'].textContent,'4G');
 assert.equal(elements['chip-sim-label'].textContent,'Fixture carrier');
 assert.equal(elements['chip-network'].dataset.bars,'3');
 assert.match(elements['signal-status'].textContent,/3\/4.*64%/);
 assert.match(elements['chip-network-summary']['aria-label'],/3\/4/);
 assert(!JSON.stringify([...saved.values()]).includes('not-for-browser-cache'));
 assert(!JSON.stringify([...saved.values()]).includes('private-usage-fixture'));
 // Simulate returning from another full-page route while both API requests are pending.
 const restored=Object.fromEntries(Object.keys(elements).map(id=>[id,new Element()]));
 const warm={console,Date,sessionStorage,setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,AbortController,
  document:{hidden:false,getElementById:id=>restored[id]||null,createElement:()=>new Element(),
   querySelector:selector=>selector==='.portal-header'?{dataset:{statusToken:'fixture-token'}}:null,addEventListener:()=>{}},
  fetch:()=>new Promise(()=>{})};
 vm.createContext(warm);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),warm);
 warm.setupHeaderStatus();
 assert.equal(restored['chip-sim-label'].textContent,'Fixture carrier');
 assert.equal(restored['chip-network'].dataset.bars,'3');
 assert.equal(restored['chip-wifi'].dataset.stale,'true');
 vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],warm);
 assert.equal(restored['metric-ram'].textContent,'150 MiB');
 assert.equal(restored['metric-sim-usage'].textContent,'2.00 MiB');
 assert.equal(restored['metric-sim-usage'].dataset.stale,'true');
 assert.equal(restored['overview-wifi'].textContent,'Đã kết nối fixture');
 assert.equal(restored['metric-ram'].dataset.stale,'true');
 assert.match(restored['overview-status'].textContent,/lần gần nhất/);
 assert(!restored['overview-status'].textContent.includes('Đang đọc'));
 for(const [percent,bars] of [[0,'0'],[1,'1'],[25,'1'],[26,'2'],[50,'2'],[51,'3'],[75,'3'],[76,'4'],[100,'4']]){
  context.renderHeader({...data.wifi.modem_status,signal_percent:percent});
  assert.equal(elements['chip-network'].dataset.bars,bars);
 }
 for(const changes of [{signal_percent:null},{signal_percent:101},{signal_percent:-1},{signal_recent:false}]){
  context.renderHeader({...data.wifi.modem_status,...changes});
  assert.equal(elements['chip-network'].dataset.bars,'4');assert.equal(elements['chip-network'].dataset.stale,'true');
 }
 context.renderHeader({...data.wifi.modem_status,registered:false,signal_recent:false,signal_percent:null,operator_name:null,access_technologies:0});
 assert.equal(elements['chip-network'].dataset.bars,'4');
 assert.equal(elements['chip-network-label'].textContent,'4G');
 assert.equal(elements['chip-sim-label'].textContent,'Fixture carrier');
 assert.equal(elements['chip-network'].dataset.stale,'true');
 context.portalRememberHeader({modem_status:{...data.wifi.modem_status,registered:false,signal_recent:false,signal_percent:null,operator_name:null,access_technologies:0}});
 const warmSignal=Object.fromEntries(Object.keys(elements).map(id=>[id,new Element()]));
 const signalContext={console,Date,sessionStorage,setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,AbortController,
  document:{hidden:false,getElementById:id=>warmSignal[id]||null,createElement:()=>new Element(),
   querySelector:selector=>selector==='.portal-header'?{dataset:{statusToken:'fixture-token'}}:null,addEventListener:()=>{}},fetch:()=>new Promise(()=>{})};
 vm.createContext(signalContext);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),signalContext);
 signalContext.setupHeaderStatus();
 assert.equal(warmSignal['chip-network'].dataset.bars,'4');
 assert.equal(warmSignal['chip-network-label'].textContent,'4G');
 assert.equal(warmSignal['chip-sim-label'].textContent,'Fixture carrier');
 for(const changes of [{sim_present:false},{sim_locked:true}]){
  context.renderHeader({...data.wifi.modem_status,...changes});
  assert.equal(elements['chip-network'].dataset.bars,'unknown');
 }
 context.renderHeader(data.wifi.modem_status);
 context.renderHeader({...data.wifi.modem_status,operator_name:'Other carrier',signal_recent:false,signal_percent:null});
 assert.equal(elements['chip-network'].dataset.bars,'unknown','confirmed carrier change invalidates previous bars');
 context.renderHeader({...data.wifi.modem_status,operator_name:'<script>Fixture carrier</script>'});
 assert.equal(elements['chip-sim-label'].textContent,'<script>Fixture carrier</script>');
 context.renderHeader(null);
 assert.equal(elements['chip-network'].dataset.bars,'3');
 assert.equal(elements['chip-sim-label'].textContent,'<script>Fixture carrier</script>');
 assert.equal(elements['chip-network'].dataset.stale,'true');
 context.renderHeader(data.wifi.modem_status);
 assert.equal(elements['chip-signal'],undefined);
 context.renderWifiHeader(data.wifi);
 assert.match(elements['wifi-status'].textContent,/fixture/);
 assert.equal(elements['wifi-settings-link'].href,'/setup');
 context.renderWifiHeader({hotspot_active:true,connected:false,ssid:'<script>USB hotspot</script>',channel:6,ipv4:['192.168.8.1/24']});
 assert.equal(elements['chip-wifi-label'].textContent,'Hotspot');
 assert.match(elements['wifi-status'].textContent,/<script>USB hotspot<\/script>/);
 assert.equal(elements['wifi-settings-link'].href,'/setup#usb-ap-settings');
 context.renderWifiHeader(null);
 assert.equal(elements['chip-wifi-label'].textContent,'Hotspot');assert.equal(elements['chip-wifi'].dataset.state,'ready');
 assert.equal(elements['chip-wifi'].dataset.stale,'true');
 assert.equal(elements['bar-ram'].style.width,'37.5%');
 data.system.emmc.life_used_ranges=[{min:100,max:null}];context.renderOverview(data);
 assert.equal(elements['metric-emmc'].textContent,'>100%');
 assert.equal(elements['card-emmc'].hidden,false);
 const before=Object.fromEntries(['metric-ram','metric-temperature','metric-signal','metric-emmc','overview-modem','overview-ip'].map(id=>[id,elements[id].textContent]));
 const partial=JSON.parse(JSON.stringify(data));partial.system.ram={used:null,total:null};partial.system.temperature_c=null;partial.system.emmc.life_used_ranges=[];partial.wifi={};
 context.renderOverview(partial);
 for(const [id,text] of Object.entries(before))assert.equal(elements[id].textContent,text);
 assert.equal(elements['metric-ram'].dataset.stale,'true');assert.equal(elements['card-emmc'].hidden,false);
 const usageBefore=elements['metric-sim-usage'].textContent;
 partial.system.sim_usage={available:false,error:'USAGE_STATE_INVALID'};context.renderOverview(partial);
 assert.equal(elements['metric-sim-usage'].textContent,usageBefore);assert.equal(elements['metric-sim-usage'].dataset.stale,'true');
 assert.match(elements['sim-usage-detail'].textContent,/không coi.*0 byte/);
 partial.system.sim_usage={...data.system.sim_usage,stale:true,error:'USAGE_SOURCE_UNAVAILABLE'};context.renderOverview(partial);
 assert.equal(elements['metric-sim-usage'].dataset.stale,'true');
 partial.system.sim_usage={...data.system.sim_usage,today:null,month:null,stale:false};context.renderOverview(partial);
 assert.equal(elements['metric-sim-usage'].textContent,'—');assert.match(elements['note-sim-usage'].textContent,/Chờ đồng bộ/);
 partial.system.sim_usage={...data.system.sim_usage,today:{download_bytes:0,upload_bytes:0,total_bytes:0},status:'idle'};context.renderOverview(partial);
 assert.equal(elements['metric-sim-usage'].textContent,'0 B');
 const serviceNode=elements['service-list'].children[1];partial.services={'openstick-web':null};context.renderOverview(partial);assert.equal(serviceNode.textContent,'đang chạy');
 partial.services={'openstick-web':false};context.renderOverview(partial);assert.equal(serviceNode.textContent,'đã dừng');
 assert.equal(elements['service-list'].children[1],serviceNode);
 partial.services={modemmanager:true};context.renderOverview(partial);
 const modemService=elements['service-list'].children.at(-1);
 assert.equal(modemService.textContent,'đang chạy (D-Bus)');
 partial.services={modemmanager:false};context.renderOverview(partial);
 assert.equal(modemService.textContent,'chưa sẵn sàng trên D-Bus');
 partial.services={modemmanager:null};context.renderOverview(partial);
 assert.equal(modemService.textContent,'chưa xác định (không đọc được D-Bus)');
 partial.services={modemmanager:true};context.renderOverview(partial);
 const mmNode=elements['service-list'].children.at(-1);assert.equal(mmNode.textContent,'đang chạy (D-Bus)');
 partial.services={modemmanager:false};context.renderOverview(partial);assert.equal(mmNode.textContent,'chưa sẵn sàng trên D-Bus');
 partial.services={modemmanager:null};context.renderOverview(partial);assert.equal(mmNode.textContent,'chưa xác định (không đọc được D-Bus)');
 onBusy=()=>{assert.equal(elements['metric-ram'].textContent,before['metric-ram'])};busyOnce=true;await context.refreshOverview();
 failFetch=true;await context.refreshOverview();assert.equal(elements['metric-ram'].textContent,before['metric-ram']);assert.match(elements['overview-status'].textContent,/giữ số liệu/);failFetch=false;
 data.system.ram.used=0;data.wifi={connected:false,hotspot_active:false,ipv4:[],modem_status:{registered:false,sim_present:false}};
 await context.refreshOverview();assert.equal(elements['metric-ram'].textContent,'0 MiB');assert.equal(elements['overview-wifi'].textContent,'Chưa kết nối');
 assert.equal(elements['chip-sim-label'].textContent,'No SIM');assert.equal(elements['chip-network'].dataset.bars,'unknown');
 const Tracker=vm.runInContext('BottomNavScrollTracker',context),t=new Tracker(50,0);
 assert.equal(t.sample(80,20),false);assert.equal(t.sample(110,40),false);assert.equal(t.sample(140,60),true);
 assert.equal(t.sample(140,5000),true);assert.equal(t.sample(122,9000),false);
 const slow=new Tracker(0,0);for(let i=1;i<50;i++)assert.equal(slow.sample(i*10,i*100),false);
 const events={},chips=[0,1,2].map(id=>({open:false,events:{},contains:target=>target===id,addEventListener(type,fn){this.events[type]=fn;}}));
 context.setupStatusPopovers({querySelectorAll:()=>chips,addEventListener:(type,fn)=>events[type]=fn});
 chips[0].open=true;chips[1].open=true;chips[1].events.toggle();
 assert(!chips[0].open&&chips[1].open);
 events.click({target:1});assert(chips[1].open);
 events.click({target:'outside'});assert(chips.every(c=>!c.open));
 chips[2].open=true;events.keydown({key:'Escape'});assert(!chips[2].open);
 console.log('Overview and bottom navigation fixture: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

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
 uptime_s:2400,os:'<script>Fixture Linux</script>',kernel:'fixture'},
 wifi:{connected:true,ssid:'fixture',ipv4:['192.0.2.2/24'],modem_status:{operator_name:'Fixture carrier',registered:true,sim_present:true,signal_percent:64,signal_recent:true,access_technologies:16384}},
 services:{'openstick-web':true,'cloudflared':null}};
const context={console,Date,setTimeout,setInterval:()=>0,document:{hidden:false,getElementById:id=>elements[id]||null,createElement:()=>new Element()},
 fetch:async(_,options={})=>{if(failFetch)throw Error('offline fixture');if(options.method==='POST'){assert.equal(JSON.parse(options.body).action,'overview');posts++;return {ok:true};}if(busyOnce){busyOnce=false;if(onBusy)onBusy();return {ok:true,json:async()=>({busy:true,result:{}})}}return {ok:true,json:async()=>({busy:false,error:false,result:data})};}};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),context);
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));assert.equal(posts,1);
 assert.equal(elements['metric-ram'].textContent,'150 MiB');
 assert.equal(elements['card-emmc'].hidden,true);
 assert.match(elements['note-sms'].textContent,/chưa cài đơn giá/);
 assert.equal(elements['overview-os'].textContent,'<script>Fixture Linux</script>');
 assert.equal(elements['chip-network-label'].textContent,'4G');
 assert.equal(elements['chip-sim-label'].textContent,'Fixture carrier');
 assert.equal(elements['chip-network'].dataset.bars,'3');
 assert.match(elements['signal-status'].textContent,/3\/4.*64%/);
 assert.match(elements['chip-network-summary']['aria-label'],/3\/4/);
 for(const [percent,bars] of [[0,'0'],[1,'1'],[25,'1'],[26,'2'],[50,'2'],[51,'3'],[75,'3'],[76,'4'],[100,'4']]){
  context.renderHeader({...data.wifi.modem_status,signal_percent:percent});
  assert.equal(elements['chip-network'].dataset.bars,bars);
 }
 for(const changes of [{signal_percent:null},{signal_percent:101},{signal_percent:-1},{signal_recent:false}]){
  context.renderHeader({...data.wifi.modem_status,...changes});
  assert.equal(elements['chip-network'].dataset.bars,'4');assert.equal(elements['chip-network'].dataset.stale,'true');
 }
 for(const changes of [{registered:false},{sim_present:false},{sim_locked:true}]){
  context.renderHeader({...data.wifi.modem_status,...changes});
  assert.equal(elements['chip-network'].dataset.bars,'unknown');
 }
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
 assert.equal(elements['wifi-settings-link'].href,'/');
 context.renderWifiHeader({hotspot_active:true,connected:false,ssid:'<script>USB hotspot</script>',channel:6,ipv4:['192.168.8.1/24']});
 assert.equal(elements['chip-wifi-label'].textContent,'Hotspot');
 assert.match(elements['wifi-status'].textContent,/<script>USB hotspot<\/script>/);
 assert.equal(elements['wifi-settings-link'].href,'/hotspot');
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
 const serviceNode=elements['service-list'].children[1];partial.services={'openstick-web':null};context.renderOverview(partial);assert.equal(serviceNode.textContent,'đang chạy');
 partial.services={'openstick-web':false};context.renderOverview(partial);assert.equal(serviceNode.textContent,'đã dừng');
 assert.equal(elements['service-list'].children[1],serviceNode);
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

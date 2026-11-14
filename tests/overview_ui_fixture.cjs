// Render the actual dashboard script with fixtures; not a visual browser test.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const html=fs.readFileSync(process.argv[2],'utf8');
class Element{constructor(){this.textContent='';this.style={};this.dataset={};this.children=[];}replaceChildren(){this.children=[];}append(...items){this.children.push(...items);}set innerHTML(_){throw Error('Use textContent');}}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element()]));
let posts=0;
const data={system:{ram:{used:150*1048576,total:400*1048576},storage:{used:1073741824,total:2*1073741824},
 temperature_c:41,load:[.08,.29,.47],sms:{submitted_today:1,submitted_month:2,unknown_today:1,estimated_today_vnd:null},
 emmc:{life_used_ranges:[],pre_eol:'unknown',written_since_boot:1048576,estimated_daily_write:113*1048576},
 swap:{used:0,total:500*1048576,zram_used:0,zram_total:500*1048576,other_used:0,other_total:0},
 uptime_s:2400,os:'<script>Fixture Linux</script>',kernel:'fixture'},
 wifi:{connected:true,ssid:'fixture',ipv4:['192.0.2.2/24'],modem_status:{registered:true,sim_present:true,signal_percent:64,signal_recent:true,access_technologies:16384}},
 services:{'openstick-web':true,'cloudflared':null}};
const context={console,Date,setTimeout,setInterval:()=>0,document:{hidden:false,getElementById:id=>elements[id]||null,createElement:()=>new Element()},
 fetch:async(_,options={})=>{if(options.method==='POST'){assert.equal(JSON.parse(options.body).action,'overview');posts++;return {ok:true};}return {ok:true,json:async()=>({busy:false,error:false,result:data})};}};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(__dirname,'../uz801_manager/static/portal_nav.js'),'utf8'),context);
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));assert.equal(posts,1);
 assert.equal(elements['metric-ram'].textContent,'150 MiB');
 assert.equal(elements['metric-emmc'].textContent,'Chưa có dữ liệu');
 assert.match(elements['note-sms'].textContent,/chưa cài đơn giá/);
 assert.equal(elements['overview-os'].textContent,'<script>Fixture Linux</script>');
 assert.equal(elements['chip-network-label'].textContent,'4G');
 assert.equal(elements['bar-ram'].style.width,'37.5%');
 data.system.emmc.life_used_ranges=[{min:100,max:null}];context.renderOverview(data);
 assert.equal(elements['metric-emmc'].textContent,'>100%');
 const Tracker=vm.runInContext('BottomNavScrollTracker',context),t=new Tracker(50,0);
 assert.equal(t.sample(80,20),false);assert.equal(t.sample(110,40),false);assert.equal(t.sample(140,60),true);
 assert.equal(t.sample(140,5000),true);assert.equal(t.sample(122,9000),false);
 const slow=new Tracker(0,0);for(let i=1;i<50;i++)assert.equal(slow.sample(i*10,i*100),false);
 console.log('Overview and bottom navigation fixture: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});

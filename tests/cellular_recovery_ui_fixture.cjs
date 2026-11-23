// Execute the real draw/click functions without making network mutations.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../uz801_manager/static/quick.js'),'utf8');
const nodes=new Map(),tiles={},actions=[];
const el=id=>{if(!nodes.has(id))nodes.set(id,{dataset:{}});return nodes.get(id)};
const context={el,compact:false,busy:false,current:null,drawMode:()=>{},
 tile:(id,text,active,disabled)=>tiles[id]={text,active,disabled},
 ask:action=>actions.push(action),fetch:()=>{throw Error('No network request during render')}};
vm.createContext(context);
const draw=source.match(/function draw\(s\) \{([\s\S]*?)\n  \}\n  let modeStatus/);assert(draw);
vm.runInContext('function draw(s){'+draw[1]+'\n}',context);
const click=source.split('\n').find(line=>line.includes("el('quick-data').onclick="));assert(click);vm.runInContext(click,context);
const state={intent:{data_allowed:true,airplane:false},radio:{registered:false,sim_ready:true,state:11},
 mobile_data_connected:false,wifi_role:'sim_ap',usb_tethering:{available:true,enabled:true},
 cellular_recovery:{phase:'WAITING_NETWORK'}};
context.draw(state);
assert.equal(tiles['quick-data'].active,true);
assert.equal(el('quick-data').dataset.connection,'pending');
assert.equal(tiles['quick-data'].disabled,false,'the owner can turn data off even without registration');
assert.match(tiles['quick-data'].text,/chờ đăng ký/);
assert.match(tiles['quick-ap'].text,/SIM mất kết nối/);
assert(!el('quick-details').textContent.includes('Đã kết nối dữ liệu'));
el('quick-data').onclick();assert.deepEqual(actions,['data_off']);
context.draw({...state,cellular_recovery:{phase:'UNKNOWN'}});
assert.match(tiles['quick-data'].text,/tắt\/bật/);
context.draw({...state,intent:{data_allowed:false,airplane:false}});
assert.equal(tiles['quick-data'].disabled,true);
context.draw({...state,radio:{registered:true,sim_ready:true,state:8},intent:{data_allowed:false,airplane:false}});
el('quick-data').onclick();assert.deepEqual(actions,['data_off','data_on']);
context.draw({...state,radio:{registered:true,sim_ready:true,state:11},mobile_data_connected:true});
assert.equal(el('quick-data').dataset.connection,'connected');
assert.match(tiles['quick-data'].text,/Internet chưa xác minh/);
assert.match(tiles['quick-ap'].text,/có phiên SIM/);
console.log('Recovery state and explicit data-off UI: PASS');

/* Local LED controls. Opening the page never changes or saves hardware state. */
const ledEl=id=>document.getElementById(id);
const ledModes={default:'Mặc định ban đầu',off:'Tắt',on:'Luôn sáng',blink:'Nhấp nháy',
  heartbeat:'Nhịp hoạt động hệ thống',wifi_on:'Theo Wi-Fi đang bật',
  wifi_link:'Theo liên kết Wi-Fi của driver',wifi_rx:'Theo hoạt động nhận Wi-Fi',wifi_tx:'Theo hoạt động gửi Wi-Fi'};
const ledStates={setup_hotspot:'Phát hotspot cài đặt',sim_hotspot:'Phát hotspot từ SIM',
  wifi_station:'USB đang nhận Wi-Fi',cellular_data:'Kết nối dữ liệu SIM, không dùng Wi-Fi',
  offline:'Chưa có kết nối',unknown:'Chưa đọc được trạng thái mạng'};
/* Three discrete binary LEDs: presets intentionally use only supported on/off/timer.
   No PWM, true 24-bit RGB gradients, software-driven frame loop or extra sysfs writes. */
const ledPresetStyles=[
  {id:'emerald',name:'Emerald Calm',group:'calm',recommended:true,description:'Xanh lá sáng ổn định, dễ nhìn cả ngày.',red:['off',500,500],green:['on',500,500],blue:['off',500,500]},
  {id:'ocean',name:'Ocean Beacon',group:'calm',recommended:true,description:'Xanh dương nền, chớp xanh lá thật nhẹ.',red:['off',500,500],green:['blink',250,1750],blue:['on',500,500]},
  {id:'aurora',name:'Aurora Drift',group:'calm',recommended:true,description:'Hai nhịp xanh lá và xanh dương xen nhau.',red:['off',500,500],green:['blink',650,1350],blue:['blink',1250,750]},
  {id:'ice',name:'Ice Pulse',group:'calm',recommended:false,description:'Xanh lá đều, xanh dương nhấp nháy chậm.',red:['off',500,500],green:['on',500,500],blue:['blink',900,1100]},
  {id:'starlight',name:'Starlight',group:'calm',recommended:false,description:'Hai tia sáng ngắn giữa khoảng tối dài.',red:['off',500,500],green:['blink',120,2880],blue:['blink',120,1880]},
  {id:'violet',name:'Violet Neon',group:'vivid',recommended:true,description:'Đỏ và xanh dương cùng sáng, tương phản mạnh.',red:['on',500,500],green:['off',500,500],blue:['on',500,500]},
  {id:'cyber',name:'Cyber Pulse',group:'vivid',recommended:true,description:'Đỏ chớp nhanh, xanh dương nhịp chậm hơn.',red:['blink',200,1000],green:['off',500,500],blue:['blink',550,650]},
  {id:'triad',name:'Triad Rhythm',group:'vivid',recommended:false,description:'Ba kênh nhấp nháy với ba nhịp khác nhau.',red:['blink',200,800],green:['blink',500,500],blue:['blink',800,200]},
  {id:'sunrise',name:'Sunrise',group:'vivid',recommended:false,description:'Đỏ nền, xanh lá phát sáng từng nhịp dài.',red:['on',500,500],green:['blink',1300,700],blue:['off',500,500]},
  {id:'link',name:'Blue Link',group:'signal',recommended:false,description:'Chỉ xanh dương sáng liên tục, tối giản.',red:['off',500,500],green:['off',500,500],blue:['on',500,500]},
  {id:'alert',name:'Alert Crimson',group:'signal',recommended:true,description:'Đỏ nhấp nháy rõ, hợp cho mất kết nối.',red:['blink',250,250],green:['off',500,500],blue:['off',500,500]},
  {id:'silent',name:'Silent Night',group:'signal',recommended:true,description:'Tắt cả ba đèn khi cần yên tĩnh.',red:['off',500,500],green:['off',500,500],blue:['off',500,500]}
];
/* A theme pack is a draft-only mapping; the existing backend still saves
   the exact allowlisted per-state on/off/blink rules after explicit consent. */
const ledThemePacks={
  signature:{setup_hotspot:'sunrise',sim_hotspot:'ocean',wifi_station:'emerald',cellular_data:'link',offline:'alert',unknown:'starlight'},
  aurora:{setup_hotspot:'starlight',sim_hotspot:'aurora',wifi_station:'ice',cellular_data:'ocean',offline:'sunrise',unknown:'silent'},
  cyber:{setup_hotspot:'triad',sim_hotspot:'cyber',wifi_station:'violet',cellular_data:'ice',offline:'alert',unknown:'starlight'},
  night:{setup_hotspot:'silent',sim_hotspot:'silent',wifi_station:'silent',cellular_data:'silent',offline:'silent',unknown:'silent'}
};
function ledPresetRule(style){
  const reading=key=>({mode:style[key][0],on_ms:style[key][1],off_ms:style[key][2]});
  return {red:reading('red'),green:reading('green'),blue:reading('blue')};
}
function ledMatchedStyle(settings){
  return ledPresetStyles.find(style=>['red','green','blue'].every(color=>
    ['mode','on_ms','off_ms'].every(key=>settings[color][key]===ledPresetRule(style)[color][key])))||null;
}
function ledStyleDot(color,reading){
  const dot=ledNode('span');
  dot.className='led-style-dot led-style-'+color+' led-style-'+reading.mode;
  dot.setAttribute('aria-hidden','true');
  if(reading.mode==='blink')dot.style.animationDuration=(reading.on_ms+reading.off_ms)+'ms';
  return dot;
}
function drawLedStyleGallery(){
  const box=ledEl('led-style-gallery');
  if(!networkDraft||!networkSelected||!box)return;
  const current=networkDraft[networkSelected];
  const active=ledMatchedStyle(current);
  const category=ledEl('led-style-filter').value||'recommended';
  box.replaceChildren();
  for(const style of ledPresetStyles){
    if(category!=='all' && (category==='recommended'?!style.recommended:style.group!==category))continue;
    const item=ledNode('button');item.type='button';item.className='led-style-card';
    const chosen=active?.id===style.id;item.setAttribute('aria-pressed',chosen?'true':'false');
    const colors=ledNode('span');colors.className='led-style-colors';
    for(const color of ['red','green','blue'])colors.append(ledStyleDot(color,ledPresetRule(style)[color]));
    const title=ledNode('strong',style.name),caption=ledNode('span',style.description);
    item.append(colors,title,caption);
    item.onclick=()=>{
      if(ledBusy||!networkReady)return;
      captureNetwork();networkDraft[networkSelected]=ledPresetRule(style);
      drawNetworkRule();drawLedStyleGallery();
      ledEl('led-notice').textContent='Đã chọn '+style.name+' cho '+ledStates[networkSelected]+'. Chưa đổi LED thật; bấm Lưu quy tắc để áp dụng.';
    };
    box.append(item);
  }
  ledEl('led-style-current-name').textContent=active?active.name:'Tùy chỉnh';
  ledEl('led-style-current-info').textContent=active?active.description+' Mẫu chỉ mô phỏng ba LED bật/tắt; chưa lưu cho USB.':'Quy tắc đang tự chỉnh. Mở phần nâng cao để kiểm tra từng kênh; chưa lưu cho USB.';
}

let networkDraft=null,networkOriginal=null,networkControls=[],networkSelected=null,networkReady=false;
const ledErrors={LED_BUSY:'Đèn đang được cập nhật. Đợi một chút rồi thử lại.',
  LED_UNAVAILABLE:'Không tìm thấy đèn đã chọn. Bấm Đọc lại để kiểm tra.',
  LED_MODE_UNSUPPORTED:'Thiết bị chưa hỗ trợ chế độ đã chọn. Bấm Đọc lại.',
  LED_APPLY_FAILED:'Chưa áp dụng được. Đã yêu cầu khôi phục trạng thái trước đó.',
  LED_ROLLBACK_FAILED:'Chưa khôi phục được toàn bộ đèn. Bấm Đọc lại để kiểm tra.',
  LED_CONFIG_INVALID:'Cấu hình đèn đã lưu không hợp lệ. Cần kiểm tra trên USB.',
  INPUT_INVALID:'Kiểm tra nhịp sáng/tắt: mỗi khoảng từ 100 đến 5000 ms.'};
let ledControls=[],ledBusy=false,ledRevision=0;
function ledNode(tag,text){const node=document.createElement(tag);if(text)node.textContent=text;return node}
function drawLeds(status){globalThis.portalRememberSettings?.('leds',status);
  const box=ledEl('led-controls');box.replaceChildren();ledControls=[];
  for(const led of status.leds){
    if(!['red','green','blue'].includes(led.id))continue;
    const card=ledNode('section'),heading=ledNode('h2','Đèn '+led.label);
    const select=ledNode('select');select.id='led-mode-'+led.id;select.style.width='100%';
    const label=ledNode('label','Chế độ');label.htmlFor=select.id;
    for(const mode of led.modes){if(ledModes[mode])select.append(new Option(ledModes[mode],mode))}
    select.value=led.settings.mode;
    const timing=ledNode('div'),inputs={};
    for(const [key,text] of [['on_ms','Thời gian sáng (ms)'],['off_ms','Thời gian tắt (ms)']]){
      const input=ledNode('input');input.type='number';input.min='100';input.max='5000';input.step='1';
      input.id='led-'+led.id+'-'+key;input.value=led.settings[key];input.style.width='100%';
      const caption=ledNode('label',text);caption.htmlFor=input.id;timing.append(caption,input);inputs[key]=input;
    }
    const update=()=>{const blink=select.value==='blink';timing.hidden=!blink;for(const input of Object.values(inputs)){input.disabled=!blink;input.required=blink}};
    select.onchange=update;update();
    const state=ledNode('p',led.controlled?'Đang chạy theo chế độ đã chọn.':led.lit?'Hiện đang sáng.':'Hiện đang tắt.');state.className='metric-note';
    card.append(heading,label,select,timing,state);box.append(card);ledControls.push({id:led.id,select,inputs,update});
  }
  ledEl('led-fields').disabled=!ledControls.length;
  ledEl('led-notice').textContent=ledControls.length?(status.saved?'Đã đọc cấu hình đèn đã lưu.':'Chưa có tùy chỉnh. Đèn đang giữ trạng thái hiện tại.'):'Thiết bị chưa cung cấp đèn thông báo có thể điều khiển.';
  drawNetwork(status);
}
async function ledRequest(options={}){if(options.method==='POST')ledRevision++;
  const response=await fetch('/api/leds',{cache:'no-store',...options,headers:{'X-OpenStick-Token':ledToken,...options.headers}});
  if(response.status===401){location.href='/login';throw Error('LOGIN_REQUIRED')}
  const value=await response.json();if(!response.ok)throw Error(value.error||'LED_OPERATION_FAILED');return value;
}
function ledError(error){ledEl('led-notice').textContent=ledErrors[error.message]||'Chưa đọc hoặc cập nhật được đèn. Kiểm tra kết nối rồi thử lại.'}
function ledSetBusy(busy){ledBusy=busy;ledEl('led-fields').disabled=busy||!ledControls.length;ledEl('led-network-fields').disabled=busy||!networkReady;ledEl('led-refresh').disabled=busy}
let ledReading=false,ledDraftTouched=false;
async function refreshLeds(){if(ledBusy||ledReading)return;ledReading=true;const generation=ledRevision;try{const status=await ledRequest();if(generation!==ledRevision)return;globalThis.portalRememberSettings?.('leds',status);if(!ledBusy&&!ledDraftTouched)drawLeds(status)}catch(error){ledError(error)}finally{ledReading=false;ledSetBusy(ledBusy)}}
ledEl('led-refresh').onclick=()=>{if(ledDraftTouched&&!confirm('Đọc lại và bỏ bản chỉnh sửa đèn?'))return;ledDraftTouched=false;return refreshLeds()};
for(const [id,mode] of [['led-all-off','off'],['led-default','default']])ledEl(id).onclick=()=>{
  if(ledBusy)return;for(const control of ledControls){control.select.value=mode;control.update()}
  ledEl('led-notice').textContent='Lựa chọn chưa lưu. Bấm Lưu và áp dụng để đổi đèn.';
};
ledEl('led-form').onsubmit=async event=>{
  event.preventDefault();if(ledBusy||!ledControls.length)return;
  const settings={};for(const control of ledControls){
    const mode=control.select.value,reading={mode};
    for(const key of ['on_ms','off_ms']){const value=Number(control.inputs[key].value);reading[key]=mode==='blink'||(Number.isInteger(value)&&value>=100&&value<=5000)?value:500}
    settings[control.id]=reading;
  }
  ledSetBusy(true);
  try{drawLeds(await ledRequest({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'configure',settings,confirm:true})}));ledEl('led-notice').textContent='Đã lưu chế độ cố định; tự đổi theo trạng thái đã tắt. Cấu hình sẽ được dùng lại sau khi cấp nguồn.'}
  catch(error){ledError(error)}finally{ledSetBusy(false)}
};
function captureNetwork(){
  if(!networkDraft||!networkSelected)return;
  for(const control of networkControls){
    const reading={mode:control.select.value};
    for(const key of ['on_ms','off_ms']){const value=Number(control.inputs[key].value);reading[key]=reading.mode==='blink'?value:500}
    networkDraft[networkSelected][control.id]=reading;
  }
}
function drawNetwork(status){
  networkReady=!!status.network&&['red','green','blue'].every(id=>status.leds.some(led=>led.id===id));
  ledEl('led-network-fields').disabled=!networkReady;
  if(!networkReady)return;
  networkDraft=JSON.parse(JSON.stringify(status.network.rules));networkOriginal=JSON.parse(JSON.stringify(networkDraft));
  if(!networkSelected)networkSelected=ledStates[status.network.state]?status.network.state:'sim_hotspot';
  ledEl('led-network-current').textContent=(status.network.enabled?'Đang tự đổi theo trạng thái. ':'Đang dùng chế độ cố định. ')+'Trạng thái lúc đọc: '+(ledStates[status.network.state]||'chưa xác định')+'.';
  ledEl('led-network-state').value=networkSelected;drawNetworkRule();drawLedStyleGallery();
}
function drawNetworkRule(){
  const box=ledEl('led-network-controls');box.replaceChildren();networkControls=[];
  for(const [id,label] of [['red','Đỏ'],['green','Xanh lá'],['blue','Xanh dương']]){
    const card=ledNode('section'),heading=ledNode('h3','Đèn '+label),select=ledNode('select');
    select.id='led-rule-'+id;select.style.width='100%';
    const caption=ledNode('label','Cách hoạt động');caption.htmlFor=select.id;
    for(const [mode,text] of [['off','Tắt'],['on','Sáng liên tục'],['blink','Nhấp nháy']])select.append(new Option(text,mode));
    const item=networkDraft[networkSelected][id];select.value=item.mode;
    const timing=ledNode('div'),inputs={};
    for(const [key,text] of [['on_ms','Thời gian sáng (ms)'],['off_ms','Thời gian tắt (ms)']]){
      const input=ledNode('input');input.type='number';input.min='100';input.max='5000';input.step='1';input.value=item[key];
      input.id='led-rule-'+id+'-'+key;input.style.width='100%';
      const label=ledNode('label',text);label.htmlFor=input.id;timing.append(label,input);inputs[key]=input;
    }
    const update=()=>{const blink=select.value==='blink';timing.hidden=!blink;for(const input of Object.values(inputs)){input.disabled=!blink;input.required=blink}};
    select.onchange=()=>{update();captureNetwork();drawLedStyleGallery()};update();
    for(const input of Object.values(inputs))input.oninput=()=>{captureNetwork();drawLedStyleGallery()};
    card.append(heading,caption,select,timing);box.append(card);networkControls.push({id,select,inputs,update});
  }
}
ledEl('led-network-state').onchange=()=>{captureNetwork();networkSelected=ledEl('led-network-state').value;drawNetworkRule();drawLedStyleGallery();ledEl('led-notice').textContent='Đang sửa lựa chọn; đèn chưa thay đổi. Bấm Lưu quy tắc để áp dụng.'};
ledEl('led-style-filter').onchange=drawLedStyleGallery;
ledEl('led-theme-apply').onclick=()=>{
  if(ledBusy||!networkReady)return;
  const pack=ledThemePacks[ledEl('led-theme-select').value];if(!pack)return;
  captureNetwork();
  for(const [state,id] of Object.entries(pack)){
    const style=ledPresetStyles.find(candidate=>candidate.id===id);
    if(!style)return;
    networkDraft[state]=ledPresetRule(style);
  }
  drawNetworkRule();drawLedStyleGallery();
  ledEl('led-notice').textContent='Đã điền bộ style cho cả 6 trạng thái. Chưa áp dụng lên LED thật; bấm Lưu quy tắc để kích hoạt.';
};
ledEl('led-network-off').onclick=()=>{if(ledBusy)return;for(const control of networkControls){control.select.value='off';control.update()}captureNetwork();drawLedStyleGallery();ledEl('led-notice').textContent='Đã chọn tắt cả ba đèn cho trạng thái này; chưa lưu.'};
async function saveNetwork(enabled){
  if(ledBusy||!networkReady)return;
  if(enabled)captureNetwork();
  const rules=enabled?networkDraft:networkOriginal;
  ledSetBusy(true);
  try{drawLeds(await ledRequest({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'configure_network',enabled,rules,confirm:true})}));ledEl('led-notice').textContent=enabled?'Đã lưu các trạng thái. USB tự áp dụng bộ ba đèn tương ứng, kể cả sau khi cấp nguồn.':'Đã tắt tự động và dùng lại cấu hình cố định.'}
  catch(error){ledError(error)}finally{ledSetBusy(false)}
}
ledEl('led-network-form').onsubmit=event=>{event.preventDefault();return saveNetwork(true)};
ledEl('led-network-disable').onclick=()=>saveNetwork(false);
for(const id of ['led-fields','led-network-fields'])for(const event of ['input','change','pointerdown'])ledEl(id)?.addEventListener?.(event,()=>{ledDraftTouched=true});
const rememberedLeds=globalThis.portalRestoreSettings?.('leds');if(rememberedLeds)try{drawLeds(rememberedLeds);globalThis.portalSettingsNote?.(ledEl('led-notice'))}catch(_){}
refreshLeds();

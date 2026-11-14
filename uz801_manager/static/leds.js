/* Local LED controls. Opening the page never changes or saves hardware state. */
const ledEl=id=>document.getElementById(id);
const ledModes={default:'Mặc định ban đầu',off:'Tắt',on:'Luôn sáng',blink:'Nhấp nháy',
  heartbeat:'Nhịp hoạt động hệ thống',wifi_on:'Theo Wi-Fi đang bật',
  wifi_link:'Theo kết nối Wi-Fi nhận',wifi_rx:'Theo hoạt động nhận Wi-Fi',wifi_tx:'Theo hoạt động gửi Wi-Fi'};
const ledErrors={LED_BUSY:'Đèn đang được cập nhật. Đợi một chút rồi thử lại.',
  LED_UNAVAILABLE:'Không tìm thấy đèn đã chọn. Bấm Đọc lại để kiểm tra.',
  LED_MODE_UNSUPPORTED:'Thiết bị chưa hỗ trợ chế độ đã chọn. Bấm Đọc lại.',
  LED_APPLY_FAILED:'Chưa áp dụng được. Đã yêu cầu khôi phục trạng thái trước đó.',
  LED_ROLLBACK_FAILED:'Chưa khôi phục được toàn bộ đèn. Bấm Đọc lại để kiểm tra.',
  LED_CONFIG_INVALID:'Cấu hình đèn đã lưu không hợp lệ. Cần kiểm tra trên USB.',
  INPUT_INVALID:'Kiểm tra nhịp sáng/tắt: mỗi khoảng từ 100 đến 5000 ms.'};
let ledControls=[],ledBusy=false;
function ledNode(tag,text){const node=document.createElement(tag);if(text)node.textContent=text;return node}
function drawLeds(status){
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
}
async function ledRequest(options={}){
  const response=await fetch('/api/leds',{cache:'no-store',...options,headers:{'X-OpenStick-Token':ledToken,...options.headers}});
  if(response.status===401){location.href='/login';throw Error('LOGIN_REQUIRED')}
  const value=await response.json();if(!response.ok)throw Error(value.error||'LED_OPERATION_FAILED');return value;
}
function ledError(error){ledEl('led-notice').textContent=ledErrors[error.message]||'Chưa đọc hoặc cập nhật được đèn. Kiểm tra kết nối rồi thử lại.'}
function ledSetBusy(busy){ledBusy=busy;ledEl('led-fields').disabled=busy||!ledControls.length;ledEl('led-refresh').disabled=busy}
async function refreshLeds(){if(ledBusy)return;ledSetBusy(true);try{drawLeds(await ledRequest())}catch(error){ledError(error)}finally{ledSetBusy(false)}}
ledEl('led-refresh').onclick=refreshLeds;
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
  try{drawLeds(await ledRequest({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'configure',settings,confirm:true})}));ledEl('led-notice').textContent='Đã lưu và áp dụng. Cấu hình sẽ được dùng lại sau khi cấp nguồn.'}
  catch(error){ledError(error)}finally{ledSetBusy(false)}
};
refreshLeds();

/* USB/LAN-only, read-only saved Wi-Fi overview. SSIDs are always plain text. */
const savedWifiBox=document.getElementById('saved-wifi-list');
const savedWifiCount=document.getElementById('saved-wifi-count');
const savedWifiRefresh=document.getElementById('saved-wifi-refresh');

async function loadSavedWifi(){
  savedWifiRefresh.disabled=true;
  savedWifiBox.textContent='Đang tải danh sách…';
  savedWifiCount.hidden=true;
  try{
    const response=await fetch('/api/wifi/saved',{headers:{'X-OpenStick-Token':savedWifiToken},cache:'no-store'});
    if(!response.ok)throw Error('READ_FAILED');
    const result=await response.json();
    if(!Array.isArray(result.profiles))throw Error('READ_FAILED');
    savedWifiCount.textContent=String(result.profiles.length);
    savedWifiCount.hidden=false;
    savedWifiBox.replaceChildren();
    if(!result.profiles.length){savedWifiBox.textContent='USB chưa có Wi-Fi đã lưu.';return}
    for(const profile of result.profiles){
      const row=document.createElement('div');row.className='manage-wifi-item';
      const name=document.createElement('span');name.className='manage-wifi-name';name.textContent=profile.ssid;
      row.append(name);
      if(profile.active){const status=document.createElement('span');status.className='manage-wifi-active';status.textContent='Đang kết nối';row.append(status)}
      savedWifiBox.append(row);
    }
  }catch(_){savedWifiBox.textContent='Chưa đọc được các Wi-Fi đã lưu. Kiểm tra kết nối USB rồi thử lại.'}
  finally{savedWifiRefresh.disabled=false}
}

savedWifiRefresh.addEventListener('click',loadSavedWifi);
loadSavedWifi();

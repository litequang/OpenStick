(() => {
 const el=id=>document.getElementById(id);let busy=false;
 function drawUsage(v){
   const target=el('usage-values');target.replaceChildren();
   for(const [label,part] of [['Hôm nay',v.today],['Tháng này',v.month],['Phiên hiện tại',v.session],['Tổng từ khi bắt đầu',v.total]]){
    const term=document.createElement('dt'),value=document.createElement('dd');term.textContent=label;
    value.textContent=size(part?.total_bytes)+' · ↓ '+size(part?.download_bytes)+' · ↑ '+size(part?.upload_bytes);target.append(term,value);
   }
   el('usage-status').textContent=v._display_cached?'Số liệu gần nhất · đang cập nhật nền.':!v.available?'Chưa có thống kê SIM; tự kiểm tra lại ở nền.':'Đã cập nhật · tự làm mới mỗi 60 giây.';
 }
 const size=value=>typeof value==='number'?(value/1048576).toFixed(2)+' MiB':'Chưa có số liệu';
 let followupTimer=null;
 async function refresh(followup=false){if(busy)return;busy=true;
  try{const sample=await portalReadTelemetry('/api/overview'),v=sample.system.sim_usage;
   if(!v||typeof v!=='object')throw Error();
   const retained=sample._telemetry?.stale||v.stale||v.error;
   const previous=globalThis.portalRestoreSettings?.('usage');
   if(retained&&previous?.available)drawUsage(previous);
   else {globalThis.portalRememberSettings?.('usage',v);drawUsage(retained?{...v,_display_cached:true}:v);}
   if(retained&&!followup&&followupTimer===null)followupTimer=setTimeout(()=>{followupTimer=null;if(!document.hidden)refresh(true)},2000);
  }catch(_){el('usage-status').textContent='Chưa cập nhật được. Giữ số liệu lần gần nhất; không phải 0 byte.'}
  finally{busy=false;el('usage-refresh').disabled=false;}
 }
 el('usage-refresh').onclick=()=>refresh();const rememberedUsage=globalThis.portalRestoreSettings?.('usage');if(rememberedUsage)try{drawUsage(rememberedUsage)}catch(_){}refresh();setInterval(()=>{if(!document.hidden)refresh()},60000);
})();

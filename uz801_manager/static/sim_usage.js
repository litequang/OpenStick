(() => {
 const el=id=>document.getElementById(id);let busy=false;
 const size=value=>typeof value==='number'?(value/1048576).toFixed(2)+' MiB':'Chưa có số liệu';
 async function refresh(){if(busy)return;busy=true;el('usage-refresh').disabled=true;
  try{const sample=await portalReadTelemetry('/api/overview'),v=sample.system.sim_usage;
   if(sample._telemetry?.stale||!v?.available||v.stale||v.error)throw Error();
   const target=el('usage-values');target.replaceChildren();
   for(const [label,part] of [['Hôm nay',v.today],['Tháng này',v.month],['Phiên hiện tại',v.session],['Tổng từ khi bắt đầu',v.total]]){
    const term=document.createElement('dt'),value=document.createElement('dd');term.textContent=label;
    value.textContent=size(part?.total_bytes)+' · ↓ '+size(part?.download_bytes)+' · ↑ '+size(part?.upload_bytes);target.append(term,value);
   }
   el('usage-status').textContent='Đã cập nhật · tự làm mới mỗi 15 giây.';
  }catch(_){el('usage-status').textContent='Chưa cập nhật được. Giữ số liệu lần gần nhất; không phải 0 byte.'}
  finally{busy=false;el('usage-refresh').disabled=false;}
 }
 el('usage-refresh').onclick=refresh;refresh();setInterval(()=>{if(!document.hidden)refresh()},15000);
})();

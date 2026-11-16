(() => {
  'use strict';
  const el=id=>document.getElementById('hotspot-'+id);
  const headers={'Content-Type':'application/json','X-OpenStick-Token':document.querySelector('.portal-header').dataset.statusToken};
  let current=null,busy=false;
  function controls(){
    el('refresh').disabled=busy;
    el('keep').disabled=busy||!current?.pending||!current.hotspot_active||!current.cellular_connected||current.seconds_remaining<=0;
    el('rollback').disabled=busy||!current?.pending;
  }
  async function refresh(){
    try{
      const r=await fetch('/api/hotspot/summary',{headers,cache:'no-store'});
      if(r.status===401){location.href='/login';return;}if(!r.ok)throw Error();current=await r.json();
      el('status').textContent='Wi-Fi USB: '+(current.hotspot_active?'đang phát':current.setup_active?'đang phát quản trị':'chưa phát')+'\nDữ liệu SIM: '+(current.cellular_connected?'đã kết nối (Internet cần kiểm tra riêng)':'chưa kết nối');
      el('pending').hidden=!current.pending;el('legacy-note').hidden=!current.enabled;
      el('countdown').textContent=current.pending?'Còn khoảng '+current.seconds_remaining+' giây để giữ phiên.':'';
    }catch(_){current=null;el('status').textContent='Chưa đọc được trạng thái. Kiểm tra kết nối rồi bấm Đọc lại.';}
    controls();
  }
  async function finish(action){
    if(busy||!current?.pending)return;
    const copy=action==='keep'?'Giữ phiên hotspot cũ sau khi bạn đã kiểm tra Internet?':'Hủy phiên thử cũ? Điểm phát và dữ liệu do phiên tạo sẽ dừng; USB cố gắng khôi phục mạng trước.';
    if(!window.confirm(copy))return;
    busy=true;controls();el('notice').textContent='Đang xử lý phiên cũ…';
    try{
      const r=await fetch('/api/hotspot',{method:'POST',headers,body:JSON.stringify({action,confirm:true,...(action==='keep'?{attempt:current.attempt}:{})})});
      if(!r.ok)throw Error();const end=Date.now()+90000;
      while(Date.now()<end){
        const poll=await fetch('/api/hotspot/state',{headers,cache:'no-store'});if(!poll.ok)throw Error();const s=await poll.json();
        if(!s.busy){if(s.error||s.last_operation?.action!==action)throw Error();el('notice').textContent='Đã hoàn tất yêu cầu cho phiên cũ.';return;}
        await new Promise(resolve=>setTimeout(resolve,1000));
      }throw Error();
    }catch(_){el('notice').textContent='Chưa xác nhận được kết quả. Đọc lại qua USB; không tự gửi lại.';}
    finally{busy=false;await refresh();}
  }
  el('refresh').onclick=()=>{if(!busy)refresh();};
  el('keep').onclick=()=>finish('keep');el('rollback').onclick=()=>finish('stop');
  refresh();setInterval(()=>{if(!busy&&!document.hidden)refresh();},15000);
})();

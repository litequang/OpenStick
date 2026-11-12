"use strict";
const $ = (id) => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has("token")) {
  sessionStorage.setItem("uz801-token", fragment.get("token"));
  history.replaceState(null, "", location.pathname);
}
const token = sessionStorage.getItem("uz801-token") || "";
let activeId = null, latest = null, polling = false, lastAutoCheck = Date.now(), seenVerification = "";
const labels = {inspect:"Kiểm tra USB", backup:"Sao lưu", verify:"Xác minh", edl:"Kiểm tra EDL", running:"Đang chạy", complete:"Hoàn tất", failed:"Lỗi", cancelled:"Đã hủy", interrupted:"Bị gián đoạn", PASS:"PASS", FAIL:"FAIL", NOT_TESTED:"Chưa kiểm thử", UNKNOWN:"Chưa xác minh", MISSING:"Chưa có", NOT_VERIFIED:"Chưa xác minh", NOT_REQUESTED:"Chưa yêu cầu", REVIEW_REQUIRED:"Cần kiểm tra thêm", STRUCTURAL_CHECK_ONLY:"Chỉ kiểm tra cấu trúc"};
function label(v) {return labels[v] || v || "—";}
function bytes(n) {if (!Number.isFinite(n)) return "—"; const units=["B","KiB","MiB","GiB","TiB"];let i=0;while(n>=1024&&i<units.length-1){n/=1024;i++;}return n.toFixed(i?2:0)+" "+units[i];}
function text(tag, value, className) {const el=document.createElement(tag);el.textContent=value;if(className)el.className=className;return el;}
function error(message) {$ ("error").textContent=message;$("error").hidden=false;}
async function api(path, data) {
  const response=await fetch(path,{method:data===undefined?"GET":"POST",headers:{"X-UZ801-Token":token,...(data===undefined?{}:{"Content-Type":"application/json"})},...(data===undefined?{}:{body:JSON.stringify(data)})});
  const value=await response.json();
  if(!response.ok)throw new Error(value.message||value.code||"Không thể thực hiện yêu cầu.");
  return value;
}
async function action(path,data){$("error").hidden=true;try{await api(path,data);await refresh();}catch(e){error(e.message);}}
function consent(){if(!$("consent").checked){error("Hãy cho phép đọc thiết bị trước khi tiếp tục.");return false;}return true;}
function hardware(device){
  $("hardware").replaceChildren();
  if(!device){const block=text("div","");block.append(text("dt","Chưa có dữ liệu"),text("dd","Chọn Kiểm tra USB để đọc thông tin thiết bị."));$("hardware").append(block);return;}
  const notTested=device.demo?"Mô phỏng":"Chưa kiểm tra";
  const fields=[["Model",device.model],["Product",device.product],["Board do Android báo",device.board||"Không cung cấp"],["Chipset",device.chipset],["Android",device.android],["Quyền root",device.root?"Có · uid=0":"Không có"],["RAM khả dụng",bytes(device.ram_kb*1024)],["Số sector × 512 byte",device.sectors.toLocaleString("vi-VN")],["Kernel",device.kernel],["Luồng nhị phân",device.binary_transport||notTested],["exec-out",device.exec_out||notTested],["GPT chính",device.gpt_primary||notTested],["GPT dự phòng",device.gpt_secondary==="DEFERRED_UNTIL_FULL_BACKUP"?"Chờ xác minh từ backup full":device.gpt_secondary||notTested]];
  for(const [key,value] of fields){const block=text("div","");block.append(text("dt",key),text("dd",value));$("hardware").append(block);}
}
function renderVerification(job){
  const value=job.detail.verification;if(!value)return;
  const box=$("verification");box.replaceChildren(text("strong","Kết quả: "+label(value.status)));
  const dl=document.createElement("dl");
  for(const [key,name] of [["sha256","SHA-256"],["gpt","GPT chính + dự phòng"],["readback","Đọc lại"],["critical_content","Dữ liệu modem"],["restore_test","Thử khôi phục"],["source","Nguồn dữ liệu"]]){const cell=document.createElement("div");cell.append(text("dt",name),text("dd",label(value[key])));dl.append(cell);}
  box.append(dl,text("p","Tính nhất quán live ADB chưa được bảo đảm. Flash vẫn khóa.","muted"));
}
function render(state){
  latest=state;const d=state.device;const jobs=state.jobs;const active=jobs.find(j=>j.status==="running");activeId=active?.id||null;
  $("connection").textContent=d?"Đã nhận ADB":state.connection_error?"Chưa kết nối":"Chưa kiểm tra";
  $("checked").textContent=state.last_checked?"Lần đọc: "+new Date(state.last_checked*1000).toLocaleTimeString("vi-VN"):state.adb_found?"ADB sẵn có · chưa đọc USB":"Chưa tìm thấy ADB";
  $("capacity").textContent=d?bytes(d.emmc_bytes):"—";$("emmc-name").textContent=d?.emmc_name||"Dung lượng đọc từ thiết bị";$("partition-count").textContent=d?d.partitions.length:"—";
  hardware(d);$("warnings").replaceChildren();for(const warning of d?.warnings||[])$("warnings").append(text("li",warning));if(d?.backup_error)$("warnings").append(text("li","Sao lưu bị khóa: "+d.backup_error));if(state.connection_error)$("warnings").append(text("li",state.connection_error));
  $("partitions").replaceChildren();for(const p of d?.partitions||[]){const row=document.createElement("tr");for(const value of [p.number,p.name,p.block,p.first_lba,bytes(p.size)])row.append(text("td",value));$("partitions").append(row);}
  if(!$("backup-folder").value)$("backup-folder").value=state.default_folder;
  $("mode").options[1].disabled=d?.gpt_secondary==="DEFERRED_UNTIL_FULL_BACKUP";if($("mode").options[1].disabled)$("mode").value="full";
  $("start-backup").disabled=!!active||!d?.backup_allowed||!$("consent").checked||!$("backup-consent").checked;
  for(const id of ["inspect","verify","edl"] )$(id).disabled=!!active;
  $("cancel").disabled=!active||["inspect","edl"].includes(active?.kind);
  const running=active?.detail||{};$("progress-title").textContent=active?(running.phase||label(active.kind)):"Sẵn sàng";
  $("progress").value=active&&running.total?Math.min(100,100*(running.bytes||0)/running.total):0;
  $("progress-bytes").textContent=active?running.total?bytes(running.bytes||0)+" / "+bytes(running.total):"Đang kiểm tra…":"Chưa có tác vụ đang chạy";
  $("progress-speed").textContent=active&&running.speed?bytes(running.speed)+"/s":"—";
  $("history-rows").replaceChildren();for(const job of jobs.slice(0,20)){const row=document.createElement("tr");const note=job.detail.message||job.detail.phase||job.detail.code||"—";for(const value of [new Date(job.created*1000).toLocaleString("vi-VN"),label(job.kind),label(job.status),note])row.append(text("td",value));$("history-rows").append(row);}
  if(!jobs.length){const td=text("td","Chưa có tác vụ.");td.colSpan=4;const row=document.createElement("tr");row.append(td);$("history-rows").append(row);}
  const verified=jobs.find(j=>["backup","verify"].includes(j.kind));
  if(verified&&seenVerification!==verified.id+verified.status){
    seenVerification=verified.id+verified.status;
    if(verified.detail.verification)renderVerification(verified);
    else $("verification").replaceChildren(text("strong","Lần gần nhất: "+label(verified.status)),text("p",verified.detail.message||"Chưa có kết quả xác minh của tác vụ này.","muted"));
    if(verified.detail.folder)$("verify-folder").value=verified.detail.folder;
  }
  $("readiness").replaceChildren();for(const check of state.readiness.checks){const li=document.createElement("li");li.append(text("span",check.name),text("span",label(check.status)));$("readiness").append(li);}
  if(state.edl){const e=state.edl;$("edl-result").replaceChildren();for(const s of ["USB 9008: "+(e.edl_detected?"Đã phát hiện":"Chưa phát hiện"),"Driver: "+label(e.driver_status),"Công cụ EDL: "+label(e.tool.status),"Programmer tương thích: "+label(e.programmer.compatibility),e.programmer.sha256?"SHA-256 programmer: "+e.programmer.sha256:null,e.guidance].filter(Boolean))$("edl-result").append(text("p",s));}
}
async function refresh(){if(polling)return;polling=true;try{render(await api("/api/state"));}catch(e){error(e.message);}finally{polling=false;}}
async function pick(id,kind="directory"){try{const result=await api("/api/pick",{kind});if(result.path)$(id).value=result.path;}catch(e){error(e.message);}}
$("inspect").addEventListener("click",()=>{if(consent()){lastAutoCheck=Date.now();action("/api/inspect",{consent:true});}});
$("consent").addEventListener("change",()=>{if(!$("consent").checked)$("monitor").checked=false;if(latest)render(latest);});
$("backup-consent").addEventListener("change",()=>{if(latest)render(latest);});
$("start-backup").addEventListener("click",()=>{if(consent()&&$("backup-consent").checked)action("/api/backup",{consent:true,backup_approved:true,folder:$("backup-folder").value,mode:$("mode").value});});
$("verify").addEventListener("click",()=>action("/api/verify",{folder:$("verify-folder").value}));
$("edl").addEventListener("click",()=>{if(consent())action("/api/edl",{consent:true,programmer:$("programmer").value});});
$("cancel").addEventListener("click",()=>{if(activeId)action("/api/cancel",{job_id:activeId});});
$("pick-backup").addEventListener("click",()=>pick("backup-folder"));$("pick-verify").addEventListener("click",()=>pick("verify-folder"));$("pick-programmer").addEventListener("click",()=>pick("programmer","programmer"));
refresh();setInterval(async()=>{await refresh();if($("monitor").checked&&$("consent").checked&&!activeId&&Date.now()-lastAutoCheck>30000){lastAutoCheck=Date.now();await action("/api/inspect",{consent:true});}},1500);
if(document.body.dataset.demo==="true"&&token)action("/api/inspect",{consent:true});

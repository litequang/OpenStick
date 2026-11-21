/* USB-only password settings. Never store the password in browser storage. */
(() => {
  const get = id => document.getElementById(id);
  let busy = false,reading=false,revision=0;
  const status = text => { get('lan-status').textContent = text; };
  async function call(action, extra = {}) {
    const response = await fetch('/api/lan', {
      method: 'POST', headers: {'Content-Type': 'application/json', 'X-OpenStick-Token': token},
      body: JSON.stringify({action, ...extra})
    });
    if (!response.ok) throw Error('LAN_FAILED');
    return response.json();
  }
  function render(s) {globalThis.portalRememberSettings?.('lan',s);
    status(s.enabled ? 'Đã bật quản trị qua Wi-Fi — yêu cầu đăng nhập.' : 'Chưa bật. Đặt mật khẩu để mở quản trị qua Wi-Fi.');
    const box = get('lan-url'); box.replaceChildren();
    for (const [label, url] of [['Địa chỉ cố định: ', s.stable_url], ['IP Wi-Fi dự phòng: ', s.url]]) {
      if (!url) continue;
      const line = document.createElement('p'), link = document.createElement('a');
      link.href = url; link.textContent = url; line.append(label, link); box.append(line);
    }
    if (!s.url) box.append('Chưa có địa chỉ Wi-Fi. Kết nối Wi-Fi trước.');
    get('lan-disable').hidden = !s.enabled;
  }
  async function run(action, extra = {}) {
    if (busy||(action==='status'&&reading)) return;
    const generation=revision;if(action==='status')reading=true;else{revision++;busy = true; get('lan-fields').disabled = true;}
    if(action!=='status')status('Đang lưu, vui lòng chờ…');
    try { const value=await call(action, extra);if(action!=='status'||generation===revision)render(value); }
    catch (_) { status('Chưa xác nhận được kết quả. Giữ kết nối USB và đọc lại trạng thái trước khi thử tiếp.'); }
    finally { if(action==='status')reading=false;else busy=false; get('lan-fields').disabled = busy; }
  }
  get('lan-settings').onsubmit = event => {
    event.preventDefault(); if (busy) return;
    const password = get('lan-password'), repeat = get('lan-password-repeat');
    if (password.value !== repeat.value) {
      status('Hai mật khẩu chưa trùng nhau. Nhập lại mật khẩu xác nhận.'); repeat.focus(); return;
    }
    const pending = run('configure', {password: password.value, confirm: true});
    password.value = ''; repeat.value = ''; return pending;
  };
  get('lan-disable').onclick = () => {
    if (!busy && confirm('Tắt truy cập quản trị qua Wi-Fi? Quản trị qua USB vẫn hoạt động.')) return run('disable', {confirm: true});
  };
  get('lan-refresh').onclick = () => run('status');
  const rememberedLan=globalThis.portalRestoreSettings?.('lan');if(rememberedLan)try{render(rememberedLan);get('lan-fields').disabled=false;globalThis.portalSettingsNote?.(get('lan-status'))}catch(_){}
  run('status');
})();

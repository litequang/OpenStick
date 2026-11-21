// Saved station profiles belong next to the connection form; secrets never enter the DOM.
(() => {
  const byId = id => document.getElementById(id);
  const list = byId('saved-wifi-list');
  const count = byId('saved-wifi-count');
  const refresh = byId('saved-wifi-refresh');
  const notice = byId('saved-wifi-notice');
  let busy = false,reading=false;

  const errors = {
    HOTSPOT_ACTIVE: 'USB đang phát Wi-Fi. Cần dừng chế độ phát trước khi chuyển sang nhận Wi-Fi; không thể làm cả hai cùng lúc.',
    POLICY_CONFLICT: 'Chính sách Internet đang đặt Chỉ SIM. Hãy đổi chính sách nguồn Internet trước.',
    PROFILE_ACTIVE: 'Đang kết nối mạng này. Chọn mạng khác trước khi quên.',
    PROFILE_NOT_FOUND: 'Mạng này không còn trong danh sách. Hãy làm mới.',
    WIFI_SWITCH_FAILED: 'Không kiểm chứng được Internet trên Wi-Fi mới; USB đã yêu cầu hoàn tác.',
    ROLLBACK_FAILED: 'Chưa hoàn tác được. Hãy kiểm tra kết nối qua cáp USB.',
    NETWORK_BUSY: 'USB đang thực hiện một thao tác mạng khác. Hãy thử lại sau.',
    BUSY: 'USB đang thực hiện một thao tác mạng khác. Hãy thử lại sau.'
  };
  const explanation = error => errors[error.message] ||
    'Không xác minh được kết quả. Hãy kiểm tra kết nối hiện tại hoặc mở quản trị qua cáp USB trước khi thử lại.';

  function setBusy(value) {
    busy = value;
    refresh.disabled = value;
    list.querySelectorAll('button').forEach(button => { button.disabled = value || button.dataset.inactive === 'true'; });
  }

  async function request(action, values = {}) {
    const response = await fetch('/api/internet', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-OpenStick-Token': savedWifiActionToken },
      body: JSON.stringify({ action, ...values })
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw Error(body.error || 'REQUEST_FAILED');
    }
    const deadline = Date.now() + 290000;
    while (Date.now() < deadline) {
      const status = await fetch('/api/internet/state', {
        headers: { 'X-OpenStick-Token': savedWifiActionToken }
      });
      if (!status.ok) throw Error('RESULT_UNKNOWN');
      const state = await status.json();
      if (!state.busy) {
        if (state.error) throw Error(state.error);
        return state.result;
      }
      await new Promise(resolve => setTimeout(resolve, 900));
    }
    throw Error('RESULT_UNKNOWN');
  }

  function drawProfiles(result){globalThis.portalRememberSettings?.('saved_profiles',result);
      list.replaceChildren();
      count.hidden = false;
      count.textContent = String(result.profiles.length);
      if (!result.profiles.length) {
        list.textContent = 'Chưa lưu mạng Wi-Fi nào.';
        return;
      }
      for (const profile of result.profiles) {
        const row = document.createElement('div');
        row.className = 'setup-saved-row';
        const identity = document.createElement('div');
        identity.className = 'setup-saved-identity';
        const name = document.createElement('strong');
        name.textContent = profile.ssid;
        identity.append(name);
        if (profile.active) {
          const current = document.createElement('span');
          current.className = 'setup-saved-active';
          current.textContent = '● Đang kết nối';
          identity.append(current);
        }
        const actions = document.createElement('div');
        actions.className = 'setup-saved-actions';
        const connect = document.createElement('button');
        connect.type = 'button';
        connect.textContent = 'Kết nối';
        connect.dataset.inactive = String(!!profile.active);
        connect.disabled = !!profile.active;
        connect.addEventListener('click', () => changeProfile('wifi_activate', profile));
        const forget = document.createElement('button');
        forget.type = 'button';
        forget.className = 'secondary';
        forget.textContent = 'Quên';
        forget.dataset.inactive = String(!!profile.active);
        forget.disabled = !!profile.active;
        forget.addEventListener('click', () => changeProfile('wifi_forget', profile));
        actions.append(connect, forget);
        row.append(identity, actions);
        list.append(row);
      }
      notice.textContent = '';
  }
  async function loadProfiles() {
    if (busy||reading) return;
    reading=true;
    try {
      const result = typeof portalReadTelemetry==='function'?await portalReadTelemetry('/api/wifi/profiles'):await request('profiles');
      if (!Array.isArray(result.profiles)) throw Error('INVALID_PROFILES');
      if(!busy)drawProfiles(result);
    } catch (error) {
      notice.textContent = explanation(error);
      if (!list.children.length) list.textContent = 'Không đọc được Wi-Fi đã lưu.';
    } finally {
      reading=false;
    }
  }

  async function changeProfile(action, profile) {
    if (busy) return;
    const connecting = action === 'wifi_activate';
    const question = connecting
      ? `Chuyển USB sang mạng “${profile.ssid}”? Kết nối hiện tại có thể ngắt; USB sẽ kiểm tra Internet và cố gắng hoàn tác nếu thất bại.`
      : `Quên mạng “${profile.ssid}” và xóa mật khẩu đã lưu trên USB?`;
    if (!window.confirm(question)) return;
    setBusy(true);
    notice.textContent = connecting ? 'Đang kiểm tra kết nối Wi-Fi mới…' : 'Đang xóa mạng đã lưu…';
    try {
      await request(action, { uuid: profile.uuid, confirm: true });
      setBusy(false);
      await loadProfiles();
      if (!notice.textContent) notice.textContent = connecting
        ? 'Đã xác nhận kết nối. Danh sách đã cập nhật.' : 'Đã quên mạng. Danh sách đã cập nhật.';
    } catch (error) {
      notice.textContent = explanation(error);
    } finally {
      setBusy(false);
    }
  }

  refresh.addEventListener('click', loadProfiles);
  const rememberedProfiles=globalThis.portalRestoreSettings?.('saved_profiles');if(rememberedProfiles)try{drawProfiles(rememberedProfiles);globalThis.portalSettingsNote?.(notice)}catch(_){}
  loadProfiles();
})();

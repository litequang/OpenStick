// Synthetic DOM checks for saved Wi-Fi management next to station setup.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

class Element {
  constructor() {
    this.children = [];
    this.dataset = {};
    this.disabled = false;
    this.hidden = false;
    this.events = {};
    this._textContent = '';
  }
  get textContent() { return this._textContent; }
  set textContent(value) { this._textContent = String(value); this.children = []; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this._textContent = ''; this.children = [...children]; }
  addEventListener(type, handler) { this.events[type] = handler; }
  querySelectorAll(selector) {
    assert.equal(selector, 'button');
    const found = [];
    for (const child of this.children) {
      if (child.tag === 'button') found.push(child);
      found.push(...child.querySelectorAll(selector));
    }
    return found;
  }
}

const html = fs.readFileSync('uz801_manager/templates/setup.html', 'utf8');
const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
const elements = Object.fromEntries(ids.map(id => [id, new Element()]));
const maliciousSsid = '<img src=x onerror=alert(1)>';
let profiles = [{ uuid: 'active-id', ssid: 'current', active: true },
                { uuid: 'other-id', ssid: maliciousSsid, active: false }];
const requests = [];
const confirmations = [];
let allow = false;
let result = {};

const context = {
  savedWifiActionToken: 'fixture-token', Date, setTimeout,
  window: { confirm: question => { confirmations.push(question); return allow; } },
  document: {
    getElementById: id => elements[id],
    createElement: tag => { const el = new Element(); el.tag = tag; return el; }
  },
  fetch: async (url, opts = {}) => {
    assert.equal(opts.headers['X-OpenStick-Token'], 'fixture-token');
    if (url === '/api/internet') {
      assert.equal(opts.method, 'POST');
      const body = JSON.parse(opts.body);
      requests.push(body);
      if (body.action === 'profiles') result = { profiles };
      if (body.action === 'wifi_activate') {
        assert.equal(body.confirm, true);
        profiles = profiles.map(p => ({ ...p, active: p.uuid === body.uuid }));
        result = { connected: true };
      }
      if (body.action === 'wifi_forget') {
        assert.equal(body.confirm, true);
        profiles = profiles.filter(p => p.uuid !== body.uuid);
        result = { deleted: true };
      }
      return { ok: true };
    }
    assert.equal(url, '/api/internet/state');
    return { ok: true, json: async () => ({ busy: false, result, error: null }) };
  }
};

vm.runInNewContext(fs.readFileSync('uz801_manager/static/saved_wifi.js', 'utf8'), context);
const flush = async () => { await new Promise(resolve => setImmediate(resolve)); };

(async () => {
  await flush();
  assert.deepEqual(requests.map(r => r.action), ['profiles']);
  assert.equal(elements['saved-wifi-count'].textContent, '2');
  assert.equal(elements['saved-wifi-count'].hidden, false);
  const rows = elements['saved-wifi-list'].children;
  assert.equal(rows.length, 2);
  assert.equal(rows[1].children[0].children[0].textContent, maliciousSsid);
  assert.equal(rows[1].children[0].children[0].children.length, 0);
  assert.equal(rows[0].children[1].children[0].disabled, true);
  assert.equal(rows[0].children[1].children[1].disabled, true);

  // Cancellation must leave both saved networks and the current connection alone.
  await rows[1].children[1].children[0].events.click();
  assert.deepEqual(requests.map(r => r.action), ['profiles']);
  allow = true;
  await rows[1].children[1].children[0].events.click();
  assert.deepEqual(requests.map(r => r.action), ['profiles', 'wifi_activate', 'profiles']);
  assert.equal(requests[1].uuid, 'other-id');
  assert.equal(elements['saved-wifi-list'].children[1].children[1].children[0].disabled, true);

  await elements['saved-wifi-list'].children[0].children[1].children[1].events.click();
  assert.deepEqual(requests.map(r => r.action), ['profiles', 'wifi_activate', 'profiles', 'wifi_forget', 'profiles']);
  assert.equal(requests[3].uuid, 'active-id');
  assert.equal(elements['saved-wifi-count'].textContent, '1');
  await elements['saved-wifi-refresh'].events.click();
  assert.equal(requests.at(-1).action, 'profiles');
  assert.equal(confirmations.length, 3);
  console.log('saved Wi-Fi load / safe SSID / confirmation / connect / forget / refresh PASS');
})().catch(err => { console.error(err); process.exitCode = 1; });

// Giả lập service worker (web/sw.js) bằng cache/fetch giả: trần ảnh, SWR, khác origin, số báo 7 ngày, dọn cache cũ, offline mở trang chủ.
const fs = require('fs'), vm = require('vm'), path = require('path');
const src = fs.readFileSync(path.join(__dirname, '../web/sw.js'), 'utf8').replaceAll('__VER__', 'v2').replaceAll('__SHELL__', JSON.stringify(['index.html', 'offline.html', 'icon.svg']));
const ORIGIN = 'https://press.test';
function mkCache() {
  const m = new Map();
  return { m,
    async put(r, res) { const k = typeof r === 'string' ? r : r.url; m.delete(k); m.set(k, res); },
    async add(u) { await this.put(ORIGIN + '/' + u, new Response('shell:' + u)); },
    async addAll(us) { for (const u of us) await this.add(u); },
    async match(r) { const k = typeof r === 'string' ? (r.startsWith('http') ? r : ORIGIN + '/' + r) : r.url; const x = m.get(k) || (r.url && m.get(k.split('?')[0])); return x ? x.clone() : undefined; },
    async keys() { return [...m.keys()].map(u => ({ url: u })); },
    async delete(r) { return m.delete(typeof r === 'string' ? r : r.url); } };
}
function env() {
  const store = new Map(), ls = {}, hits = { net: 0 }; let online = true, body = 'v1';
  const caches = { async open(n) { if (!store.has(n)) store.set(n, mkCache()); return store.get(n); }, async keys() { return [...store.keys()]; }, async delete(n) { return store.delete(n); } };
  const self = { addEventListener: (t, f) => ls[t] = f, skipWaiting() {}, clients: { claim() {} } };
  const fetchF = async u => { hits.net++; if (!online) throw new Error('off'); const url = u.url || u; return new Response(url.endsWith('.json') ? '{}' : url.includes('/pages/') ? '<html>home</html>' : body, { status: 200 }); };
  vm.runInNewContext(src, { self, caches, fetch: fetchF, location: { origin: ORIGIN }, Response, Headers, URL, Promise, Date, Set, Number, Math, console });
  const req = (url, o = {}) => ({ url, method: 'GET', mode: o.mode || 'cors', clone() { return this; } });
  async function go(url, o) {
    let p; const pend = []; ls.fetch({ request: req(url, o), respondWith: x => p = x, waitUntil: x => pend.push(x) });
    if (!p) return null; const res = await p; await Promise.all(pend); await new Promise(r => setTimeout(r, 5)); return res;
  }
  return { store, ls, go, hits, off: () => online = false, setBody: b => body = b, caches };
}
(async () => {
  const out = {}, e = env();
  await e.ls.install({ waitUntil: p => p }); const cache = await e.caches.open('press-v2');
  // trần ảnh
  for (let i = 0; i < 75; i++) await e.go(`${ORIGIN}/img/${String(i).padStart(3, '0')}.png`);
  const imgs = [...cache.m.keys()].filter(k => k.endsWith('.png'));
  out.img_cap = imgs.length === 60; out.img_evict_oldest = !cache.m.has(`${ORIGIN}/img/000.png`) && cache.m.has(`${ORIGIN}/img/074.png`);
  out.shell_kept = cache.m.has(ORIGIN + '/index.html') && cache.m.has(ORIGIN + '/icon.svg');
  // SWR: trả bản cũ ngay, nền cập nhật
  e.setBody('v2'); const r1 = await e.go(`${ORIGIN}/img/074.png`); out.swr_stale = await r1.text() === 'v1';
  const r2 = await e.go(`${ORIGIN}/img/074.png`); out.swr_refreshed = await r2.text() === 'v2';
  // truy cập lại → mục đi cuối hàng, không bị bỏ trước
  await e.go(`${ORIGIN}/img/015.png`); await e.go(`${ORIGIN}/img/new.png`);
  out.img_lru_touch = cache.m.has(`${ORIGIN}/img/015.png`) && !cache.m.has(`${ORIGIN}/img/016.png`);
  // khác origin: không cache, không can thiệp
  const before = cache.m.size; const x = await e.go('https://cdn.other/pic.png'); out.cross_origin = x === null && cache.m.size === before;
  // số báo: ≤7 mục, quá 7 ngày bị dọn
  for (let d = 1; d <= 10; d++) await e.go(`${ORIGIN}/issues/2026-11-${String(d).padStart(2, '0')}.json`);
  const iss = () => [...cache.m.keys()].filter(k => /issues\/[\d-]+\.json$/.test(k));
  out.issues_cap = iss().length === 7 && !cache.m.has(`${ORIGIN}/issues/2026-11-01.json`);
  const k = iss()[0], old = new Response('{}', { headers: { 'x-sw-at': String(Date.now() - 8 * 864e5) } }); await cache.put(k, old);
  await e.go(`${ORIGIN}/issues/2026-11-11.json`); out.issues_age = !cache.m.has(k);
  // offline: trang chủ vẫn mở (đã lưu) + trang chưa lưu → offline.html
  await e.go(`${ORIGIN}/index.html`, { mode: 'navigate' }); e.off();
  const h = await e.go(`${ORIGIN}/index.html`, { mode: 'navigate' }); out.offline_home = (await h.text()).length > 0 && h.status === 200;
  const o = await e.go(`${ORIGIN}/nope.html`, { mode: 'navigate' }); out.offline_fallback = (await o.text()) === 'shell:offline.html';
  const im = await e.go(`${ORIGIN}/img/074.png`); out.offline_img = im.status === 200;
  const im2 = await e.go(`${ORIGIN}/img/never.png`); out.offline_img_miss = im2.status === 503;
  // activate: chỉ xoá press-* cũ, không đụng cache khác
  await e.caches.open('press-v1'); await e.caches.open('other-app');
  await e.ls.activate({ waitUntil: p => p }); await new Promise(r => setTimeout(r, 5));
  const ks = await e.caches.keys(); out.activate_scoped = ks.includes('press-v2') && ks.includes('other-app') && !ks.includes('press-v1');
  console.log(JSON.stringify(out)); if (Object.values(out).some(v => v !== true)) process.exit(1);
})();

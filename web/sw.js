/* Service worker Bản Tin: cache vỏ + số báo gần nhất, đọc offline. Phiên bản = băm nội dung build (__VER__) → đổi bản là cache cũ tự xoá.
   Chiến lược: HTML/JSON = mạng trước (có bản mới thì lấy), rớt mạng → bản đã lưu; JS/CSS/ảnh icon = lưu trước. Chỉ cùng origin; không cache API/Worker. */
const VER = '__VER__', SHELL = __SHELL__, CACHE = 'press-' + VER, MAX_ISSUES = 7;
const netFirst = /\.(html|json)$|\/$/;
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => Promise.all(SHELL.map(u => c.add(u).catch(() => 0))))).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('press-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
async function trimIssues(c) { const ks = (await c.keys()).filter(r => /\/issues\/[\d-]+\.json$/.test(r.url)).sort((a, b) => a.url < b.url ? 1 : -1); await Promise.all(ks.slice(MAX_ISSUES).map(r => c.delete(r))); }
self.addEventListener('fetch', e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin) return;
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    if (netFirst.test(u.pathname)) {
      try { const n = await fetch(r); if (n.ok) { c.put(r, n.clone()); if (/\/issues\//.test(u.pathname)) trimIssues(c); } return n; }
      catch (x) { const m = await c.match(r, { ignoreSearch: true }); if (m) return m; if (r.mode === 'navigate') return (await c.match('offline.html')) || new Response('Offline', { status: 503 }); return new Response('{}', { status: 503, headers: { 'content-type': 'application/json' } }); }
    }
    const m = await c.match(r); if (m) return m;
    try { const n = await fetch(r); if (n.ok) c.put(r, n.clone()); return n; } catch (x) { return new Response('', { status: 503 }); }
  })());
});

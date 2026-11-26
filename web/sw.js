/* Service worker Bản Tin: cache vỏ + số báo gần nhất, đọc offline. Phiên bản = băm nội dung build (__VER__) → đổi bản là cache cũ tự xoá.
   Chiến lược: HTML/JSON = mạng trước (có bản mới thì lấy), rớt mạng → bản đã lưu; JS/CSS = lưu trước; ảnh cùng origin = stale-while-revalidate, trần MAX_IMGS mục (bỏ mục cũ nhất).
   Số báo giữ ≤ MAX_ISSUES và ≤ 7 ngày. Chỉ cùng origin (ảnh khác origin không cache); không cache API/Worker. Đổi bản chỉ xoá cache 'press-*' phiên bản cũ. */
const VER = '__VER__', SHELL = __SHELL__, CACHE = 'press-' + VER, MAX_ISSUES = 7, MAX_AGE = 7 * 864e5, MAX_IMGS = 60, SHELL_SET = new Set(SHELL);
const isImg = u => /\.(png|jpe?g|gif|webp|avif|svg|ico)$/i.test(u.pathname) && !SHELL_SET.has(u.pathname.replace(/^.*\//, '')) && !SHELL_SET.has(u.pathname.replace(/^\//, ''));
const netFirst = /\.(html|json)$|\/$/;
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL).catch(() => Promise.all(SHELL.map(u => c.add(u).catch(() => 0))))).then(() => self.skipWaiting())); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('press-') && k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
async function stamp(n) { const h = new Headers(n.headers); h.set('x-sw-at', String(Date.now())); return new Response(await n.blob(), { status: n.status, statusText: n.statusText, headers: h }); }
async function trimIssues(c) {
  const ks = (await c.keys()).filter(r => /\/issues\/[\d-]+\.json$/.test(r.url)).sort((a, b) => a.url < b.url ? 1 : -1), old = [];
  for (const [i, r] of ks.entries()) { const m = await c.match(r), t = m && Number(m.headers.get('x-sw-at')); if (i >= MAX_ISSUES || (t && Date.now() - t > MAX_AGE)) old.push(r); }
  await Promise.all(old.map(r => c.delete(r)));
}
async function trimImgs(c) { const ks = (await c.keys()).filter(r => isImg(new URL(r.url))); await Promise.all(ks.slice(0, Math.max(0, ks.length - MAX_IMGS)).map(r => c.delete(r))); }
self.addEventListener('fetch', e => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin) return;
  e.respondWith((async () => {
    const c = await caches.open(CACHE);
    if (netFirst.test(u.pathname)) {
      try { const n = await fetch(r); if (n.ok) { if (/\/issues\//.test(u.pathname)) { await c.put(r, await stamp(n.clone())); await trimIssues(c); } else await c.put(r, n.clone()); } return n; }
      catch (x) { const m = await c.match(r, { ignoreSearch: true }); if (m) return m; if (r.mode === 'navigate') return (await c.match('offline.html')) || new Response('Offline', { status: 503 }); return new Response('{}', { status: 503, headers: { 'content-type': 'application/json' } }); }
    }
    if (isImg(u)) {
      const m = await c.match(r), up = fetch(r).then(async n => { if (n.ok && n.type !== 'opaque') { await c.put(r, n.clone()); await trimImgs(c); } return n; }).catch(() => null);
      if (m) { e.waitUntil(up); return m; }
      return (await up) || new Response('', { status: 503 });
    }
    const m = await c.match(r); if (m) return m;
    try { const n = await fetch(r); if (n.ok) c.put(r, n.clone()); return n; } catch (x) { return new Response('', { status: 503 }); }
  })());
});

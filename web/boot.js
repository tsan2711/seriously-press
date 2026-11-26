/* Khởi động nhẹ (eager, ~1 KB): đăng ký service worker (offline), banner offline, nạp x/ui.js lúc rảnh hoặc ngay khi bấm phím tắt / nút Tìm. */
(() => {
  const D = document;
  if ('serviceWorker' in navigator && location.protocol.startsWith('http')) addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
  const bar = () => { let b = D.getElementById('off'); if (!b) { b = D.createElement('p'); b.id = 'off'; b.setAttribute('role', 'status'); b.hidden = true; b.textContent = 'Bạn đang offline — đang hiển thị bản đã lưu trên máy.'; D.body.prepend(b); } return b; };
  const sync = () => { bar().hidden = navigator.onLine !== false; };
  addEventListener('online', sync); addEventListener('offline', sync); if (navigator.onLine === false) sync();
  let loading = null; const load = () => loading || (loading = new Promise(res => { const s = D.createElement('script'); s.src = 'x/ui.js'; s.onload = res; s.onerror = () => { loading = null; res(); }; D.head.append(s); }));
  window.PressLoadUI = load;
  const idle = f => ('requestIdleCallback' in window ? requestIdleCallback(f, { timeout: 3000 }) : setTimeout(f, 600));
  addEventListener('load', () => idle(load));
  D.addEventListener('keydown', ev => { if (window.PressUI) return; const k = ev.key, m = ev.ctrlKey || ev.metaKey, e = ev.target || {}, t = /^(INPUT|TEXTAREA|SELECT)$/.test(e.tagName) || e.isContentEditable, s = m ? k.toLowerCase() === 'k' : k === '/' && !ev.altKey && !ev.isComposing && !t; if (s || (!m && !t && 'jkos?'.includes(k))) { if (s) ev.preventDefault(); load().then(() => window.PressUI && window.PressUI.key(ev)); } });
  D.addEventListener('click', ev => { if (!window.PressUI && ev.target.closest('[data-search],[data-b60],[data-save],[data-lang],[data-readall],[data-readall-undo-btn],.thumb')) load().then(() => window.PressUI && window.PressUI.click(ev)); });
})();

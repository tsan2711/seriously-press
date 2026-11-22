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
  D.addEventListener('keydown', ev => { const k = ev.key; if (!window.PressUI && (k === '/' || ((ev.ctrlKey || ev.metaKey) && k.toLowerCase() === 'k') || 'jkos'.includes(k) && !ev.ctrlKey && !ev.metaKey && !/^(INPUT|TEXTAREA|SELECT)$/.test((ev.target || {}).tagName))) { if (k === '/' || k === 'k' || k === 'K') ev.preventDefault(); load().then(() => window.PressUI && window.PressUI.key(ev)); } });
  D.addEventListener('click', ev => { if (!window.PressUI && ev.target.closest('[data-search],[data-b60],[data-lang],.thumb')) load().then(() => window.PressUI && window.PressUI.click(ev)); });
})();

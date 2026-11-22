/* Hiệu ứng nhẹ (11-22): chỉ transform/opacity; IntersectionObserver một lần; tắt khi reduced-motion; dừng khi tab ẩn. Không đụng dữ liệu người đọc. */
(() => {
  'use strict';
  const D = document, H = D.documentElement, RM = matchMedia('(prefers-reduced-motion:reduce)');
  D.addEventListener('visibilitychange', () => H.classList.toggle('fx-paused', D.hidden));
  if (RM.matches) return;
  const MAX = 48;   // ≤ 60 phần tử animate cùng lúc
  let io = null;
  const settle = c => { c.addEventListener('transitionend', function f(e) { if (e.propertyName !== 'transform') return; c.removeEventListener('transitionend', f); c.classList.add('done'); c.style.willChange = ''; }); };
  const reveal = (cards) => {
    if (!('IntersectionObserver' in window)) return;
    io = io || new IntersectionObserver(es => {
      let k = 0;
      es.forEach(en => { if (!en.isIntersecting) return; const c = en.target; io.unobserve(c); c.style.setProperty('--d', Math.min(k++, 8) * 55 + 'ms'); c.style.willChange = 'transform,opacity'; settle(c); requestAnimationFrame(() => c.classList.add('in')); });
    }, { rootMargin: '0px 0px -6% 0px' });
    cards.slice(0, MAX).forEach(c => { if (c.classList.contains('fx')) return; c.classList.add('fx'); io.observe(c); });
    cards.slice(MAX).forEach(c => c.classList.add('done'));
  };
  const scan = () => reveal([...D.querySelectorAll('.grid .card')]);
  // thẻ vào + chuyển số báo trượt (grid được thay nội dung bởi issues.js)
  const grid = D.querySelector('.grid');
  if (grid) {
    scan();
    new MutationObserver(ms => {
      if (!ms.some(m => m.addedNodes.length)) return;
      const fresh = [...grid.querySelectorAll('.card:not(.fx)')]; if (!fresh.length) return;
      if (!grid.classList.contains('sk-load')) { grid.classList.remove('slide'); void grid.offsetWidth; grid.classList.add('slide'); setTimeout(() => grid.classList.remove('slide'), 450); }
      reveal(fresh);
    }).observe(grid, { childList: true });
  }
  // ghim cắm khi lưu
  const plug = c => { if (!c) return; c.classList.remove('pinned'); void c.offsetWidth; c.classList.add('pinned'); };
  D.addEventListener('click', ev => {
    const s = ev.target.closest('[data-save]'); if (s) setTimeout(() => { if (s.getAttribute('aria-pressed') === 'true') plug(s.closest('.card')); }, 0);
    const sc = ev.target.closest('.scheme'); if (sc) fade();
  });
  D.addEventListener('press:save', ev => { const id = ev.detail && ev.detail.id; if (id) plug(D.querySelector('.card[data-id="' + CSS.escape(id) + '"]')); });
  // đổi theme: lớp phủ màu bảng cũ mờ dần (opacity)
  function fade() {
    const bg = getComputedStyle(H).getPropertyValue('--board').trim() || getComputedStyle(D.body).backgroundColor;
    const o = D.createElement('div'); o.className = 'fade-ov'; o.style.background = bg; D.body.append(o);
    requestAnimationFrame(() => requestAnimationFrame(() => { o.style.transition = 'opacity .35s ease-out'; o.style.opacity = '0'; }));
    setTimeout(() => o.remove(), 500);
  }
  // nút chạy báo: thanh tiến độ mượt (scaleX) thay <progress> nhảy bậc
  const prog = D.querySelector('[data-run-prog]');
  if (prog) {
    const w = D.createElement('div'), f = D.createElement('div'); w.className = 'pg'; f.className = 'pg-f'; w.append(f); w.setAttribute('aria-hidden', 'true'); prog.after(w);
    const upd = () => { w.classList.toggle('on', !prog.hidden); f.style.transform = 'scaleX(' + Math.max(.04, Math.min(1, (+prog.value || 0) / (+prog.max || 1))) + ')'; };
    new MutationObserver(upd).observe(prog, { attributes: true, attributeFilter: ['value', 'max', 'hidden'] }); upd();
  }
})();

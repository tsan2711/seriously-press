// Trang Nhật ký (journal.html): xem lại từng ngày + tổng 30 ngày + xuất/nhập. Chỉ đọc localStorage, không mạng.
(() => {
  const D = document, root = D.querySelector('[data-diary]'); if (!root) return;
  const PP = window.PressProfiles, PJ = window.PressJournal, PR = window.PressRank; if (!PP || !PJ) return;
  const db = PP.open(), id = db.active() || 'me', who = db.list().find(x => x.id === id) || { name: 'Tôi' };
  const jr = PJ.open(null, id), $ = s => root.querySelector(s), esc = t => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  { const w = D.querySelector('[data-dy-who]'); if (w) w.textContent = who.name; }
  let topics = {}; fetch('today.json').then(r => r.json()).then(d => { topics = d.topics || {}; draw(); }).catch(() => {});
  const lab = t => (topics[t] || {}).label || t, EV = { seen: 'thấy', open: 'mở', skip: 'bỏ qua', like: 'thích', save: 'lưu', less: 'ít tin này', hide: 'ẩn', rate: 'chấm' };
  const day = (J, k) => {
    const d = J.days[k], box = $('[data-dy-detail]'); box.textContent = '';
    const p = D.createElement('p'); p.className = 'm'; const n = d.n;
    p.textContent = `${k}: thấy ${n.seen + n.open + n.skip}, mở ${n.open}, bỏ qua ${n.skip}, lưu ${n.save + n.like}` + (d.dwell_s ? ` · đọc ${Math.round(d.dwell_s / 60)} phút` : '');
    const hrs = Object.keys(d.h || {}).sort((a, b) => d.h[b] - d.h[a]).slice(0, 3); if (hrs.length) p.textContent += ' · hay đọc lúc ' + hrs.map(h => h + 'h').join(', ');
    const ul = D.createElement('ul'); ul.className = 'fy';
    Object.values(d.items).sort((a, b) => (b.ev.open || 0) - (a.ev.open || 0)).forEach(it => {
      const li = D.createElement('li'), ev = Object.keys(it.ev).map(e => (EV[e] || e) + (e === 'dwell' ? ' ' + it.ev[e] + 's' : e === 'rate' ? ' ' + it.ev[e] + '★' : '')).join(', ');
      li.textContent = it.t; const sm = D.createElement('small'); sm.textContent = ' — ' + [it.s, (it.topics || []).map(lab).join('/'), ev].filter(Boolean).join(' · '); li.append(D.createElement('br'), sm); ul.append(li);
    });
    box.append(p, ul);
  };
  const draw = () => {
    const J = jr.load(), ks = Object.keys(J.days).sort().reverse(), bx = $('[data-dy-days]'); bx.textContent = '';
    ks.slice(0, 30).forEach((k, i) => { const b = D.createElement('button'); b.type = 'button'; b.className = 'chip'; b.textContent = k.slice(5); b.setAttribute('aria-pressed', i === 0 ? 'true' : 'false'); b.dataset.k = k; bx.append(b); });
    if (ks.length) day(J, ks[0]);
    const t = Date.now(), sp = PJ.span(J, PJ.dkey(t - 30 * 86400000), PJ.dkey(t)), sm = $('[data-dy-sum]');
    if (!sp.days) return; sm.textContent = '';
    const top = Object.entries(sp.topics).sort((a, b) => b[1].open - a[1].open).slice(0, 5), ig = Object.entries(sp.topics).filter(([, x]) => x.skip >= 6 && !x.open).slice(0, 3);
    const p = D.createElement('p'); p.className = 'm'; p.textContent = `${sp.days} ngày có hoạt động · mở ${sp.n.open} · bỏ qua ${sp.n.skip}` + (top.length ? ' · chủ đề hay mở: ' + top.map(([k, x]) => lab(k) + ' (' + x.open + ')').join(', ') : '') + (ig.length ? ' · hay bị bỏ qua: ' + ig.map(([k]) => lab(k)).join(', ') : '');
    sm.append(p);
  };
  $('[data-dy-days]').addEventListener('click', ev => { const b = ev.target.closest('[data-k]'); if (!b) return; $('[data-dy-days]').querySelectorAll('.chip').forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false')); day(jr.load(), b.dataset.k); });
  $('[data-dy-out]').addEventListener('click', () => { const a = D.createElement('a'); a.href = URL.createObjectURL(new Blob([jr.exportJSON()], { type: 'application/json' })); a.download = 'ban-tin-nhat-ky-' + PJ.dkey(Date.now()) + '.json'; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); });
  $('[data-dy-in]').addEventListener('change', ev => { const f = ev.target.files[0]; if (!f) return; f.text().then(t => { const r = jr.importJSON(t); $('[data-dy-msg]').textContent = r.error || `Đã nhập ${r.added} ngày mới.`; draw(); }); });
  draw();
})();

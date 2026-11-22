/* Press · bảng tin (không 3D): sáng/tối, chọn người đọc (profiles.js), bảng ghim (thẻ rơi, dây, đèn) của theme C. */
(() => {
  const D = document, R = D.documentElement, PAGE = R.dataset.page;
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  // ---------- sáng / tối ----------
  const MODES = ['light', 'dark', 'auto'];
  const setMode = (m, save) => {
    R.dataset.scheme = m; if (save) { try { localStorage.setItem('press.scheme', m); } catch (e) {} }
    D.querySelectorAll('.scheme').forEach(x => x.setAttribute('aria-pressed', x.dataset.mode === m ? 'true' : 'false'));
  };
  setMode(MODES.includes(R.dataset.scheme) ? R.dataset.scheme : 'auto', false);
  D.addEventListener('click', ev => {
    const b = ev.target.closest('.scheme');
    if (b && MODES.includes(b.dataset.mode)) setMode(b.dataset.mode, true);
    const ch = ev.target.closest('.chip'); if (ch && !ch.closest('[data-picker]')) ch.setAttribute('aria-pressed', ch.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
    const go = ev.target.closest('[data-go]'); if (go) { const i = D.getElementById(go.dataset.go); if (i) { i.scrollIntoView({ behavior: RM ? 'auto' : 'smooth', block: 'center' }); i.focus({ preventScroll: true }); } }
  });

  // ---------- người đọc: nối profiles.js (cục bộ, localStorage). Không có PressProfiles → bỏ qua ----------
  const PP = window.PressProfiles, PR = window.PressRank;
  const db = PP ? PP.open() : null;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const who = db && (db.list().find(x => x.id === db.active()) || null);
  const wl = D.querySelector('.who i'); if (wl && who) wl.textContent = who.name.slice(0, 1).toUpperCase();
  const wipe = D.querySelector('[data-wipe]');
  if (wipe && db) wipe.addEventListener('click', ev => { ev.preventDefault(); const id = db.active() || 'me'; if (confirm('Xoá sở thích của người đọc này trên thiết bị?')) db.clear(id); });
  let DATA = null; const dataP = fetch('today.json').then(r => r.json()).then(d => (DATA = d)).catch(() => null);
  window.PressData = dataP;
  const mine = () => { const id = db && db.active(); return id ? { id, p: PR.ensure(db.load(id) || PR.newProfile(null, [])) } : null; };
  const PD = window.PressDedup, PM = window.PressMemory;
  const PJ = window.PressJournal, jr = id => (PJ && id ? PJ.open(null, id) : null);
  const fb = (artId, sig, amount) => { const m = mine(), a = DATA && DATA.articles.find(x => x.id === artId); if (!m || !a) return; PR.feedback(m.p, a, sig, null, Date.now(), amount); db.save(m.id, m.p); const j = jr(m.id); if (j) j.record(sig, a, Date.now(), amount); if (PM) { const tl = t => (DATA.topics && DATA.topics[t] && DATA.topics[t].label) || t; PM.open(null, m.id).record(sig, a, Date.now(), amount, tl); } if (PD && (sig === 'open' || sig === 'save' || sig === 'like')) PD.open(null, m.id).mark(a, true); };
  if (db && PR) D.addEventListener('click', ev => {
    const el = ev.target.closest('[data-save],[data-less]');
    if (el) { dataP.then(() => fb(el.dataset.id, el.hasAttribute('data-save') ? (el.getAttribute('aria-pressed') === 'true' ? 'save' : 'like') : 'less')); return; }
    const rt = ev.target.closest('[data-rate]');
    if (rt) { const box = rt.closest('[data-rate-box]'); box.querySelectorAll('[data-rate]').forEach(b => b.setAttribute('aria-pressed', b === rt ? 'true' : 'false')); dataP.then(() => fb(box.dataset.id, 'rate', +rt.dataset.rate)); return; }
    const lk = ev.target.closest('.card[data-id] a[href^="http"]'); if (lk) { const c = lk.closest('.card'); opened.add(c.dataset.id); dataP.then(() => fb(c.dataset.id, 'open')); }
  });

  // ---------- bộ đo: hiện ≥1,2 s mà không mở = bỏ qua (nhẹ); thời gian ở lại trang bài = dwell. Chỉ khi đã chọn người đọc ----------
  const opened = new Set(), seen = new Set(); let t0 = Date.now(), vis = true, dwell = 0, flushed = false;
  if (db && PR && db.active() && 'IntersectionObserver' in window) {
    const timers = new Map(), io = new IntersectionObserver(es => es.forEach(en => {
      const id = en.target.dataset.id; if (!id || en.target.classList.contains('feature')) return;
      if (en.isIntersecting && en.intersectionRatio >= .5) { if (!timers.has(id)) timers.set(id, setTimeout(() => seen.add(id), 1200)); }
      else if (timers.has(id)) { clearTimeout(timers.get(id)); timers.delete(id); }
    }), { threshold: [.5] });
    D.querySelectorAll('.card[data-id]').forEach(c => io.observe(c));
  }
  const flush = () => {
    if (flushed || !DATA || !db || !PR || !db.active()) return; flushed = true;
    if (vis) dwell += (Date.now() - t0) / 1000;
    if (PAGE === 'article') { const f = D.querySelector('.feature[data-id]'); if (f && dwell >= 5) fb(f.dataset.id, 'dwell', dwell); }
    else { if (PD) { const sd = PD.open(null, db.active()); [...seen].forEach(i => { const a = DATA.articles.find(x => x.id === i); if (a) sd.mark(a, false); }); } const j = jr(db.active()); [...seen].slice(0, 60).forEach(i => { const a = DATA.articles.find(x => x.id === i); if (j && a) j.record('seen', a); }); [...seen].filter(i => !opened.has(i)).slice(0, 30).forEach(i => fb(i, 'skip')); }
  };
  D.addEventListener('visibilitychange', () => { if (D.hidden) { if (vis) dwell += (Date.now() - t0) / 1000; vis = false; flush(); } else { vis = true; t0 = Date.now(); flushed = false; seen.clear(); } });
  addEventListener('pagehide', flush);

  // ---------- nhật ký → thích nghi hằng ngày: tổng hợp 14 ngày trước hôm nay (adapt) + 30 ngày (giải thích, thứ tự ban) ----------
  const spans = id => {
    const j = jr(id); if (!j) return null; const L = j.load(), t = Date.now(), k = n => PJ.dkey(t - n * 86400000);
    return { p14: PJ.span(L, k(14), k(1)), p30: PJ.span(L, k(30), k(0)) };
  };
  if (db && PR && PJ && db.active()) {
    const sp = spans(db.active()), m = db.load(db.active());
    // thứ tự ban theo vai trò + nhật ký (chỉ sắp lại thanh ban; không đổi nội dung)
    dataP.then(data => {
      const nav = D.querySelector('nav.desks'); if (!nav || !data || !m) return;
      const links = [...nav.querySelectorAll('a[href^="desk-"]')], ids = links.map(a => a.getAttribute('href').replace(/^desk-|\.html$/g, ''));
      const ord = PR.deskOrder(PR.ensure(m), sp && sp.p30, data.roles, ids);
      ord.forEach(id => { const a = links[ids.indexOf(id)]; if (a) nav.append(a); });
    });
  }
  // ---------- Nóng 30 ngày: chủ đề hợp gu lên trước (xếp lại ở trình duyệt, tĩnh vẫn đủ) ----------
  const hotBox = D.querySelector('[data-hot-list]');
  if (hotBox && db && PR) dataP.then(data => {
    const m = db.active() && db.load(db.active()); if (!m || !data) return; PR.ensure(m);
    const li = [...hotBox.children], score = x => PR.weight(m, x.dataset.topic, Date.now()) * 10 + (+x.dataset.heat || 0) * 0.01;
    li.sort((a, b) => score(b) - score(a)).forEach(x => hotBox.append(x));
    const note = D.querySelector('[data-hot-note]'); if (note && li.some(x => PR.weight(m, x.dataset.topic, Date.now()) > 0.3)) note.textContent = '— xếp theo gu của bạn';
  });

  // ---------- không lặp qua ngày: ẩn thẻ đã thấy hôm trước (trừ tin có cập nhật), gắn nhãn Mới/Cập nhật/Đã đọc ----------
  if (db && PD && PAGE !== 'article') dataP.then(data => {
    const id = db.active(); if (!data || !id) return; const sd = PD.open(null, id), st = sd.load(), cards = [...D.querySelectorAll('.card[data-id]:not(.feature)')]; if (!cards.length) return;
    const by = {}; (data.articles || []).forEach(a => { by[a.id] = a; });
    const arts = cards.map(c => by[c.dataset.id]).filter(Boolean), r = PD.filter(st, arts, Date.now(), data.dedup), hid = new Set(r.hidden.map(a => a.id));
    // không ẩn hết: giữ tối thiểu 6 thẻ
    let keep = cards.length - hid.size; const hidList = r.hidden.filter(a => a._lab !== 'trùng'); if (keep < 6) hidList.slice(0, 6 - keep).forEach(a => hid.delete(a.id));
    let n = 0; cards.forEach(c => { if (hid.has(c.dataset.id)) { c.hidden = true; n++; } });
    r.show.forEach(a => { const c = cards.find(x => x.dataset.id === a.id); if (!c || c.querySelector('.lab')) return; if (a._lab === 'Mới' || a._lab === 'Đã đọc') { const s = D.createElement('span'); s.className = 'lab lab-' + (a._lab === 'Mới' ? 'new' : 'seen'); s.textContent = a._lab; const k = c.querySelector('.kicker'); if (k) k.after(s); } });
    const note = D.querySelector('[data-dd-note]'); if (note && n) { note.hidden = false; note.textContent = 'Đã ẩn ' + n + ' tin bạn đã đọc hôm trước. '; const b = D.createElement('button'); b.type = 'button'; b.textContent = 'Hiện lại'; b.addEventListener('click', () => { cards.forEach(c => { c.hidden = false; }); note.hidden = true; }); note.append(b); }
  });

  // ---------- Dành cho bạn (trang chủ): xếp hạng cục bộ theo hồ sơ + vai trò + mật độ ----------
  const fy = D.querySelector('[data-foryou]');
  if (fy && db && PR) dataP.then(data => {
    const m = db.active() && db.load(db.active()); if (!data || !m) return; PR.ensure(m);
    const sp = spans(db.active()); if (sp) { PR.adaptDaily(m, sp.p14, Date.now()); db.save(db.active(), m); }
    let mm = null; if (PM) { const mo = PM.open(null, db.active()); mm = mo.load(); const tl = t => (data.topics && data.topics[t] && data.topics[t].label) || t; if (sp && sp.p30 && PM.seedFromSpan(mm, sp.p30, Date.now(), tl)) mo.save(mm); if (PM.consolidate(mm, Date.now()).changed) mo.save(mm); }
    const sdn = PD ? PD.open(null, db.active()).load() : null, pool = sdn ? PD.filter(sdn, data.articles, Date.now(), data.dedup).show : data.articles;
    const out = PR.rank(pool.length >= 6 ? pool : data.articles, m, data.topics, null, Date.now(), { hot: data.hot, ew: data.engagement_weight, sp: sp && sp.p30, adj: mm ? a => PM.adjust(mm, a, Date.now()) : null, explain: mm ? a => PM.explain(mm, a, Date.now()) : null }).slice(0, m.density === 'compact' ? 5 : m.density === 'rich' ? 12 : 8);
    if (!out.length) return;
    const who = db.list().find(x => x.id === db.active()), rl = m.role && data.roles && data.roles.role[m.role];
    fy.querySelector('[data-fy-who]').textContent = who ? who.name.toUpperCase() : 'BẠN'; fy.querySelector('[data-fy-role]').textContent = rl ? '· ' + rl.label : '';
    const ol = fy.querySelector('[data-fy-list]'); ol.textContent = '';
    out.forEach(x => { const li = D.createElement('li'), a = D.createElement('a'), w = D.createElement('small'); a.href = x.a.url; a.rel = 'noopener'; a.textContent = x.a.title; a.dataset.id = x.a.id;
      w.textContent = x.why + ' · ' + x.a.source; li.append(a, D.createElement('br'), w); ol.append(li); });
    ol.addEventListener('click', ev => { const a = ev.target.closest('a[data-id]'); if (a) fb(a.dataset.id, 'open'); });
    fy.hidden = false;
  });

  const pk = D.querySelector('[data-picker]');
  if (pk && db) {
    const list = pk.querySelector('[data-list]'), now = pk.querySelector('[data-now]'), msg = pk.querySelector('[data-msg]'), fm = pk.querySelector('[data-new]');
    const say = t => { if (msg) msg.textContent = t; };
    let cur = db.active() || 'me';
    const chips = () => [...pk.querySelectorAll('.chip[data-topic]')];
    const showTaste = id => { const p = db.load(id), set = new Set(p ? Object.keys(p.w) : []); chips().forEach(c => c.setAttribute('aria-pressed', set.has(c.dataset.topic) ? 'true' : 'false')); };
    const draw = () => {
      list.querySelectorAll('li:not(.nw)').forEach(l => l.remove());
      db.list().forEach(x => {
        const li = D.createElement('li'), b = D.createElement('button'); b.type = 'button'; b.className = 'pf'; b.dataset.id = x.id; b.dataset.name = x.name;
        b.setAttribute('aria-pressed', x.id === cur ? 'true' : 'false'); b.innerHTML = `<span class="av" aria-hidden="true">${esc(x.name.slice(0, 1).toUpperCase())}</span><span class="pn">${esc(x.name)}</span><span class="ps">${x.hasData ? 'Đã chọn chủ đề' : 'Chưa chọn chủ đề'}</span>`;
        li.append(b); list.insertBefore(li, list.querySelector('.new').closest('li'));
      });
      const nw = list.querySelector('.new').closest('li'); nw.classList.add('nw'); nw.hidden = !db.canCreate();
      const me = db.list().find(x => x.id === cur) || { name: 'Tôi' }; if (now) now.textContent = me.name;
      const dl = pk.querySelector('[data-del]'); if (dl) dl.textContent = me.kind === 'me' ? 'Xoá dữ liệu của Tôi' : 'Xoá người đọc này';
      showTaste(cur); showRole(cur);
    };
    list.addEventListener('click', ev => { const b = ev.target.closest('.pf[data-id]'); if (!b) return; cur = b.dataset.id; db.select(cur); say(''); draw(); });
    const pressed = (el, on) => el.setAttribute('aria-pressed', on ? 'true' : 'false');
    // Lưu từ giao diện: giữ nguyên bộ đo/nguồn/đã lưu/ẩn, chỉ đổi chủ đề + vai trò + mật độ.
    const saveUI = () => {
      const on = chips().filter(x => x.getAttribute('aria-pressed') === 'true'), cnt = {};
      on.forEach(x => { cnt[x.dataset.desk] = (cnt[x.dataset.desk] || 0) + 1; });
      const desk = Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a])[0] || null;
      const role = (pk.querySelector('[data-role][aria-pressed=true]') || {}).dataset; const dn = (pk.querySelector('[data-density-pick][aria-pressed=true]') || { dataset: {} }).dataset.densityPick;
      const old = PR.ensure(db.load(cur)); const p = PR.newProfile(desk, on.map(x => x.dataset.topic), undefined, { role: role && role.role, density: dn });
      if (old) { ['saved', 'hidden', 'explored', 'bandit', 'src', 'stats', 'adapt'].forEach(k => { p[k] = old[k]; }); Object.keys(old.w).forEach(t => { if (p.w[t]) p.w[t] = old.w[t]; }); }
      if (old && dn !== old.density) p.densityAuto = false; else if (old && old.densityAuto === false) p.densityAuto = false;   // chọn tay → khoá tự đổi mật độ
      db.save(cur, p); say('Đã lưu cho người đọc này.'); drawTaste();
    };
    pk.addEventListener('click', ev => {
      const c = ev.target.closest('.chip[data-topic]'), r = ev.target.closest('[data-role]'), dn = ev.target.closest('[data-density-pick]');
      if (c) { pressed(c, c.getAttribute('aria-pressed') !== 'true'); saveUI(); }
      else if (r) {   // câu 1: vai trò → chọn sẵn chủ đề + mật độ gợi ý (sửa được)
        pk.querySelectorAll('[data-role]').forEach(b => pressed(b, b === r));
        const ts = (r.dataset.topics || '').split(',').filter(Boolean); chips().forEach(x => pressed(x, ts.includes(x.dataset.topic)));
        pk.querySelectorAll('[data-density-pick]').forEach(b => pressed(b, b.dataset.densityPick === r.dataset.density)); saveUI();
      } else if (dn) { pk.querySelectorAll('[data-density-pick]').forEach(b => pressed(b, b === dn)); saveUI(); }
    });
    // Gu của tôi: số liệu + chủ đề top (ngắn vs dài hạn)
    const drawTaste = () => {
      const box = pk.querySelector('[data-taste]'); if (!box) return;
      dataP.then(data => {
        const p = db.load(cur); if (!p || !data) return; const rp = PR.report(PR.ensure(p), data.topics, Date.now(), 8);
        if (!rp.top.length && !rp.stats.open) return;
        const T = { rising: '↑ đang lên', fading: '↓ nhạt dần', steady: '→ ổn định' }, mx = Math.max(...rp.top.map(x => x.score), 1);
        box.textContent = ''; const ul = D.createElement('ul'); ul.className = 'taste';
        rp.top.forEach(x => { const li = D.createElement('li'), b = D.createElement('i'); b.style.width = Math.round(100 * x.score / mx) + '%'; b.setAttribute('aria-hidden', 'true');
          li.append(b, D.createTextNode(x.label + ' · ' + T[x.trend])); ul.append(li); });
        const st = D.createElement('p'); st.className = 'm';
        st.textContent = `${rp.days} ngày có hoạt động · mở ${rp.stats.open}, bỏ qua ${rp.stats.skip}` + (rp.open_rate != null ? ` (tỉ lệ mở ${Math.round(rp.open_rate * 100)}%)` : '')
          + (rp.avg_dwell_s ? ` · đọc trung bình ${Math.round(rp.avg_dwell_s)} giây` : '') + (rp.avg_rating ? ` · chấm TB ${rp.avg_rating.toFixed(1)}★` : '') + (rp.sources.length ? ` · nguồn hay mở: ${rp.sources.join(', ')}` : '');
        box.append(ul, st);
      });
    };
    const showRole = id => { const p = db.load(id); pk.querySelectorAll('[data-role]').forEach(b => pressed(b, !!p && p.role === b.dataset.role)); pk.querySelectorAll('[data-density-pick]').forEach(b => pressed(b, (p ? p.density || 'normal' : 'normal') === b.dataset.densityPick)); };
    // Đồng bộ
    const sc = pk.querySelector('[data-sync-code]'), sm = pk.querySelector('[data-sync-msg]');
    const so = pk.querySelector('[data-sync-out]'), si = pk.querySelector('[data-sync-in]');
    if (so) so.addEventListener('click', () => { sc.value = db.exportAll(); sc.select(); sm.textContent = 'Đã tạo mã. Sao chép và dán ở máy kia. Mã chứa sở thích của bạn — đừng đăng công khai.'; });
    if (si) si.addEventListener('click', () => { const r = db.importAll(sc.value); sm.textContent = r.error || `Đã nhập: ${r.added} người đọc mới, ${r.merged} hồ sơ "Tôi".`; if (!r.error) { sc.value = ''; draw(); drawTaste(); } });
    if (fm) fm.addEventListener('submit', ev => {
      ev.preventDefault(); const v = fm.nm.value.trim().slice(0, 24);
      if (!v) { say('Nhập tên người đọc.'); return; }
      const id = db.canCreate() ? db.create(v) : null;
      if (!id) { say('Đã đủ 8 người đọc.'); return; }
      cur = id; db.select(id); fm.nm.value = ''; say(`Đã tạo “${v}”. Chọn chủ đề bên dưới.`); draw();
    });
    const dl = pk.querySelector('[data-del]');
    if (dl) dl.addEventListener('click', () => {
      const x = db.list().find(y => y.id === cur); if (!x) return;
      if (!confirm(x.kind === 'me' ? 'Xoá sạch dữ liệu của "Tôi"?' : `Xoá "${x.name}" và toàn bộ dữ liệu? Không khôi phục được.`)) return;
      db.remove(cur); cur = 'me'; db.select('me'); say('Đã xoá.'); draw();
    });
    const go = pk.querySelector('a[href="index.html"]'); if (go) go.addEventListener('click', () => db.select(cur));
    db.select(cur); draw(); drawTaste();
  }

})();

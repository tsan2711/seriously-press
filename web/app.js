/* Press · bảng tin (không 3D): sáng/tối, chọn người đọc (profiles.js), bảng ghim (thẻ rơi, dây, đèn) của theme C. */
(() => {
  const D = document, R = D.documentElement, PAGE = R.dataset.page;
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  const MODES = ['light', 'dark', 'auto'];
  const setMode = (m, save) => {
    R.dataset.scheme = m; if (save) { try { localStorage.setItem('press.scheme', m); } catch (e) {} }
    D.querySelectorAll('.scheme').forEach(x => x.setAttribute('aria-pressed', x.dataset.mode === m ? 'true' : 'false'));
  };
  setMode(MODES.includes(R.dataset.scheme) ? R.dataset.scheme : 'auto', false);
  D.addEventListener('click', ev => {
    const b = ev.target.closest('.scheme');
    if (b && MODES.includes(b.dataset.mode)) setMode(b.dataset.mode, true);
    const ch = ev.target.closest('.chip'); if (ch && !ch.closest('[data-picker]') && !ch.matches('.scheme,[data-fs]')) ch.setAttribute('aria-pressed', ch.getAttribute('aria-pressed') === 'true' ? 'false' : 'true');
    const go = ev.target.closest('[data-go]'); if (go) { const i = D.getElementById(go.dataset.go); if (i) { i.scrollIntoView({ behavior: RM ? 'auto' : 'smooth', block: 'center' }); i.focus({ preventScroll: true }); } }
  });

  // ---------- tab: #lich-su | #bo-nho | #cai-dat ----------
  const tb = D.querySelector('[data-tabs]');
  if (tb) {
    const tabs = [...tb.querySelectorAll('[role=tab]')], pick = (k, focus) => {
      const t = tabs.find(x => x.dataset.tab === k) || tabs[0];
      tabs.forEach(x => { const on = x === t; x.setAttribute('aria-selected', on ? 'true' : 'false'); x.tabIndex = on ? 0 : -1; const p = D.getElementById(x.getAttribute('aria-controls')); if (p) p.hidden = !on; });
      if (focus) t.focus();
    };
    tb.addEventListener('click', ev => { const t = ev.target.closest('[role=tab]'); if (t) { pick(t.dataset.tab); history.replaceState(null, '', '#' + t.dataset.tab); } });
    tb.addEventListener('keydown', ev => { const i = tabs.indexOf(D.activeElement); if (i < 0 || !['ArrowLeft', 'ArrowRight'].includes(ev.key)) return; ev.preventDefault(); const n = tabs[(i + (ev.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]; pick(n.dataset.tab, true); history.replaceState(null, '', '#' + n.dataset.tab); });
    addEventListener('hashchange', () => pick(location.hash.slice(1)));
    pick(location.hash.slice(1));
  }

  // ---------- người đọc (profiles.js) ----------
  const PP = window.PressProfiles, PR = window.PressRank;
  const db = PP ? PP.open() : null;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const who = db && (db.list().find(x => x.id === db.active()) || null);
  const wl = D.querySelector('.who i'); if (wl && who) wl.textContent = who.name.slice(0, 1).toUpperCase();
  const wipe = D.querySelector('[data-wipe]');
  if (wipe && db) wipe.addEventListener('click', ev => { ev.preventDefault(); const id = db.active() || 'me'; if (confirm('Xoá sở thích của người đọc này trên thiết bị?')) db.clear(id); });
  let DATA = null; const idle = f => ('requestIdleCallback' in window ? requestIdleCallback(f, { timeout: 1500 }) : setTimeout(f, 200));
  const dataP = new Promise(res => addEventListener('load', () => idle(res))).then(() => fetch('today.json')).then(r => r.json()).then(d => (DATA = d)).catch(() => (D.body.prepend(Object.assign(D.createElement('p'), { id: 'derr', textContent: 'Chưa tải được dữ liệu cá nhân hoá — bản tin vẫn đọc được.' })), null));
  window.PressData = dataP;
  // lô nhỏ ≤8 ms rồi nhường luồng chính
  const batch = (list, fn) => new Promise(res => { let i = 0; const step = () => { const t = performance.now(); while (i < list.length && performance.now() - t < 8) { fn(list[i], i); i++; } if (i < list.length) idle(step); else res(); }; step(); });
  // thẻ ngoài 12 đầu nằm trong <template data-more>: thêm khi bấm 'Xem thêm' hoặc cuộn gần cuối
  const moreT = D.querySelector('template[data-more]');
  if (moreT) {
    const box = D.querySelector('[data-more-box]'), grid = moreT.previousElementSibling; let done = false;
    const more = () => { if (done) return; done = true; if (grid) grid.append(moreT.content); moreT.remove(); if (box) box.remove(); D.dispatchEvent(new Event('press:more')); };
    const mb = D.querySelector('[data-more-btn]'); if (mb) mb.addEventListener('click', more);
    if (box && 'IntersectionObserver' in window) { const io = new IntersectionObserver(es => { if (es.some(x => x.isIntersecting)) { io.disconnect(); idle(more); } }, { rootMargin: '400px 0px' }); io.observe(box); }
  }
  const mine = () => { const id = db && db.active(); return id ? { id, p: PR.ensure(db.load(id) || PR.newProfile(null, [])) } : null; };
  const PD = window.PressDedup, PM = window.PressMemory;
  const PJ = window.PressJournal, jr = id => (PJ && id ? PJ.open(null, id) : null);
  const fb = (artId, sig, amount) => { const m = mine(), a = DATA && DATA.articles.find(x => x.id === artId); if (!m || !a) return; PR.feedback(m.p, a, sig, null, Date.now(), amount); db.save(m.id, m.p); const j = jr(m.id); if (j) j.record(sig, a, Date.now(), amount); if (PM) { const tl = t => (DATA.topics && DATA.topics[t] && DATA.topics[t].label) || t; PM.open(null, m.id).record(sig, a, Date.now(), amount, tl); } if (PD && (sig === 'open' || sig === 'save' || sig === 'like')) PD.open(null, m.id).mark(a, true); };
  D.addEventListener('press:save', ev => { dataP.then(() => fb(ev.detail.id, 'save')); });   // 'Đọc sau' (x/ui.js) cũng là tín hiệu lưu
  if (db && PR) D.addEventListener('click', ev => {
    const el = ev.target.closest('[data-save],[data-less]');
    if (el) { dataP.then(() => fb(el.dataset.id, el.hasAttribute('data-save') ? (el.getAttribute('aria-pressed') === 'true' ? 'save' : 'like') : 'less')); return; }
    const rt = ev.target.closest('[data-rate]');
    if (rt) { const box = rt.closest('[data-rate-box]'); box.querySelectorAll('[data-rate]').forEach(b => b.setAttribute('aria-pressed', b === rt ? 'true' : 'false')); dataP.then(() => fb(box.dataset.id, 'rate', +rt.dataset.rate)); return; }
    const lk = ev.target.closest('.card[data-id] a[href^="http"]'); if (lk) { const c = lk.closest('.card'); opened.add(c.dataset.id); dataP.then(() => fb(c.dataset.id, 'open')); }
  });

  // ---------- bộ đo: ≥1,2 s không mở = bỏ qua; dwell ----------
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

  // ---------- nhật ký → thích nghi (14/30 ngày) ----------
  const spans = id => {
    const j = jr(id); if (!j) return null; const L = j.load(), t = Date.now(), k = n => PJ.dkey(t - n * 86400000);
    return { p14: PJ.span(L, k(14), k(1)), p30: PJ.span(L, k(30), k(0)) };
  };
  if (db && PR && PJ && db.active()) {
    const sp = spans(db.active()), m = db.load(db.active());
    // thứ tự ban theo vai trò + nhật ký
    dataP.then(data => {
      const nav = D.querySelector('nav.desks'); if (!nav || !data || !m) return;
      const links = [...nav.querySelectorAll('a[href^="desk-"]')], ids = links.map(a => a.getAttribute('href').replace(/^desk-|\.html$/g, ''));
      const ord = PR.deskOrder(PR.ensure(m), sp && sp.p30, data.roles, ids);
      ord.forEach(id => { const a = links[ids.indexOf(id)]; if (a) nav.append(a); });
    });
  }
  // ---------- Nóng 30 ngày: chủ đề hợp gu lên trước ----------
  const hotBox = D.querySelector('[data-hot-list]');
  if (hotBox && db && PR) dataP.then(data => {
    const m = db.active() && db.load(db.active()); if (!m || !data) return; PR.ensure(m);
    const li = [...hotBox.children], score = x => PR.weight(m, x.dataset.topic, Date.now()) * 10 + (+x.dataset.heat || 0) * 0.01;
    li.sort((a, b) => score(b) - score(a)).forEach(x => hotBox.append(x));
    const note = D.querySelector('[data-hot-note]'); if (note && li.some(x => PR.weight(m, x.dataset.topic, Date.now()) > 0.3)) note.textContent = '— xếp theo gu của bạn';
  });

  // ---------- không lặp qua ngày: ẩn thẻ đã thấy, nhãn Mới/Đã đọc ----------
  const dedupe = () => dataP.then(data => {
    const id = db.active(); if (!data || !id) return; const sd = PD.open(null, id), st = sd.load(), cards = [...D.querySelectorAll('.card[data-id]:not(.feature)')]; if (!cards.length) return;
    const by = {}; (data.articles || []).forEach(a => { by[a.id] = a; });
    const arts = cards.map(c => by[c.dataset.id]).filter(Boolean), r = PD.filter(st, arts, Date.now(), data.dedup), hid = new Set(r.hidden.map(a => a.id));
    // giữ ≥6 thẻ
    let keep = cards.length - hid.size; const hidList = r.hidden.filter(a => a._lab !== 'trùng'); if (keep < 6) hidList.slice(0, 6 - keep).forEach(a => hid.delete(a.id));
    let n = 0; cards.forEach(c => { if (hid.has(c.dataset.id)) { c.hidden = true; n++; } });
    r.show.forEach(a => { const c = cards.find(x => x.dataset.id === a.id); if (!c || c.querySelector('.lab')) return; if (a._lab === 'Mới' || a._lab === 'Đã đọc') { const s = D.createElement('span'); s.className = 'lab lab-' + (a._lab === 'Mới' ? 'new' : 'seen'); s.textContent = a._lab; const k = c.querySelector('.kicker'); if (k) k.after(s); } });
    const note = D.querySelector('[data-dd-note]'); if (note && n) { note.hidden = false; note.textContent = 'Đã ẩn ' + n + ' tin bạn đã đọc hôm trước. '; const b = D.createElement('button'); b.type = 'button'; b.textContent = 'Hiện lại'; b.addEventListener('click', () => { cards.forEach(c => { c.hidden = false; }); note.hidden = true; }); note.append(b); }
  });

  if (db && PD && PAGE !== 'article') { dedupe(); D.addEventListener('press:more', dedupe); }

  // ---------- Dành cho bạn: xếp hạng cục bộ theo hồ sơ + vai trò + mật độ ----------
  const fy = D.querySelector('[data-foryou]');
  // khung chờ (template, cao bằng thẻ thật); bỏ khi dữ liệu về/lỗi
  const fyList = fy && fy.querySelector('[data-fy-list]'), gen0 = D.querySelector('main .grid[data-gen]'), skT = fy && fy.querySelector('template[data-fy-sk]');
  const busy = (e, on) => e && (on ? e.setAttribute('aria-busy', 'true') : e.removeAttribute('aria-busy')), prof = () => { try { return Object.keys(db.load(db.active()).w || {}).length > 0; } catch (e) { return false; } };
  const skOn = skT && db && PR && prof();
  if (skOn) { busy(fyList, 1); busy(gen0, 1); fyList.append(skT.content.cloneNode(true)); fy.hidden = false; }
  const skOff = () => { if (!skOn) return; busy(fyList); busy(gen0); fyList.querySelectorAll('.sk-card').forEach(x => x.remove()); if (!fyList.children.length && fy.querySelector('[data-fy-empty]').hidden) fy.hidden = true; };
  if (fy && db && PR) dataP.then(async data => {
    const m = db.active() && db.load(db.active()); if (!data) return;
    const emp = fy.querySelector('[data-fy-empty]'), showEmpty = () => { if (emp) { emp.hidden = false; fy.querySelector('[data-fy-list]').hidden = true; fy.hidden = false; } };
    if (!m || !Object.keys(m.w || {}).length) { showEmpty(); return; }
    PR.ensure(m);
    const sp = spans(db.active()); if (sp) { PR.adaptDaily(m, sp.p14, Date.now()); db.save(db.active(), m); }
    let mm = null; if (PM) { const mo = PM.open(null, db.active()); mm = mo.load(); const tl = t => (data.topics && data.topics[t] && data.topics[t].label) || t; if (sp && sp.p30 && PM.seedFromSpan(mm, sp.p30, Date.now(), tl)) mo.save(mm); if (PM.consolidate(mm, Date.now()).changed) mo.save(mm); }
    const sdn = PD ? PD.open(null, db.active()).load() : null, pool = sdn ? PD.filter(sdn, data.articles, Date.now(), data.dedup).show : data.articles;
    const out = PR.rank(pool.length >= 6 ? pool : data.articles, m, data.topics, null, Date.now(), { hot: data.hot, ew: data.engagement_weight, sp: sp && sp.p30, adj: mm ? a => PM.adjust(mm, a, Date.now()) : null, explain: mm ? a => PM.explain(mm, a, Date.now()) : null }).slice(0, m.density === 'compact' ? 6 : m.density === 'rich' ? 18 : 12);
    if (!out.length) { showEmpty(); return; }
    const who = db.list().find(x => x.id === db.active()), rl = m.role && data.roles && data.roles.role[m.role];
    fy.querySelector('[data-fy-who]').textContent = who ? who.name : 'tôi'; fy.querySelector('[data-fy-role]').textContent = rl ? '· ' + rl.label : '';
    const ol = fy.querySelector('[data-fy-list]'); ol.textContent = '';
    const hue = t => { let h = 0; for (const c of String(t || '')) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
    await batch(out, (x, i) => { const a = x.a, c = D.createElement('article'), th = D.createElement('div'), cb = D.createElement('div'), h3 = D.createElement('h3'), l = D.createElement('a'), mt = D.createElement('p'), why = D.createElement('p');
      c.className = 'card' + (i === 0 ? ' lead' : ''); c.dataset.id = a.id; c.dataset.st = a.status || 'new'; c.style.setProperty('--i', i);
      th.className = 'thumb'; th.setAttribute('aria-hidden', 'true'); th.style.setProperty('--h', hue((a.topics || [])[0]));
      if (/^https?:\/\//i.test(a.img || '')) { const im = D.createElement('img'); im.src = a.img; im.alt = ''; im.width = 640; im.height = 360; im.loading = i < 2 ? 'eager' : 'lazy'; im.decoding = 'async'; im.referrerPolicy = 'no-referrer'; im.addEventListener('error', () => im.remove()); th.append(im); }
      cb.className = 'cb'; l.href = /^https?:\/\//i.test(a.url) ? a.url : '#'; l.rel = 'noopener'; l.textContent = a.title; l.dataset.id = a.id; h3.append(l);
      mt.className = 'meta'; mt.textContent = a.source || ''; why.className = 'chip-why';
      const tp = (a.topics || []).find(t => m.w && m.w[t]) || (a.topics || [])[0], tn = tp && ((data.topics && data.topics[tp] && data.topics[tp].label) || tp);
      if (tn) { const ch = D.createElement('a'); ch.href = 'me.html?topic=' + encodeURIComponent(tp) + '#bo-nho'; ch.textContent = 'vì bạn theo: ' + tn; ch.title = (x.why || '') + ' — bấm để chỉnh chủ đề này'; why.append(ch); } else why.textContent = x.why || ''; why.title = x.why || '';
      cb.append(h3, mt); if (a.summary) { const ex = D.createElement('p'); ex.className = 'ex'; ex.textContent = String(a.summary).slice(0, 240); cb.append(ex); } if (why.firstChild) cb.append(why); c.append(th, cb); ol.append(c); });
    ol.addEventListener('click', ev => { const a = ev.target.closest('a[data-id]'); if (a) fb(a.dataset.id, 'open'); });
    fy.hidden = false;
    D.getElementById('live-dyn').textContent = 'Dành cho bạn: ' + out.length + ' bài.';
    // bài đã lên 'Dành cho bạn' ẩn khỏi 'Tin chung' (giữ ≥6 thẻ); 'Hiện lại' trả đủ
    const gen = D.querySelector('main .grid[data-gen]'), fn = D.querySelector('[data-fy-note]');
    if (gen && fn) {
      const ids = new Set(out.map(x => x.a.id)), vis = [...gen.querySelectorAll('.card[data-id]')].filter(c => !c.hidden), dup = vis.filter(c => ids.has(c.dataset.id));
      const mv = dup.slice(0, Math.max(0, Math.min(dup.length, vis.length - 6)));
      if (mv.length) {
        mv.forEach(c => { c.hidden = true; });
        fn.hidden = false; fn.textContent = 'Đã chuyển ' + mv.length + ' bài lên Dành cho bạn. ';
        const b = D.createElement('button'); b.type = 'button'; b.textContent = 'Hiện lại'; b.addEventListener('click', () => { mv.forEach(c => { c.hidden = false; }); fn.hidden = true; }); fn.append(b);
      }
    }
  }).then(skOff, skOff);

  // ---------- người mới: banner dẫn tới picker (đóng được) ----------
  const fr = D.querySelector('[data-firstrun]');
  if (fr && db) {
    const FRK = 'press.fr.x', gone = () => { try { return localStorage.getItem(FRK) === '1'; } catch (e) { return false; } };
    const p0 = db.active() && db.load(db.active()), has = !!p0 && Object.keys(p0.w || {}).length > 0;
    if (!has && !gone()) fr.hidden = false;
    fr.querySelector('[data-fr-x]').addEventListener('click', () => { fr.hidden = true; try { localStorage.setItem(FRK, '1'); } catch (e) {} });
  }

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
      showTaste(cur); showRole(cur); syncEnter();
    };
    list.addEventListener('click', ev => { const b = ev.target.closest('.pf[data-id]'); if (!b) return; cur = b.dataset.id; db.select(cur); say(''); draw(); });
    const ent = pk.querySelector('[data-enter]');   // 'Vào đọc' dính đáy (mobile) khi đã có ≥1 chủ đề
    const cntEl = pk.querySelector('[data-count]');
    const syncEnter = () => { const n = chips().filter(x => x.getAttribute('aria-pressed') === 'true').length; if (ent) ent.classList.toggle('ready', n > 0); if (cntEl) cntEl.textContent = `Đã chọn ${n} chủ đề`; };
    const pressed = (el, on) => el.setAttribute('aria-pressed', on ? 'true' : 'false');
    // Lưu từ giao diện: chỉ đổi chủ đề + vai trò + mật độ.
    const saveUI = () => {
      const on = chips().filter(x => x.getAttribute('aria-pressed') === 'true'), cnt = {};
      on.forEach(x => { cnt[x.dataset.desk] = (cnt[x.dataset.desk] || 0) + 1; });
      const desk = Object.keys(cnt).sort((a, b) => cnt[b] - cnt[a])[0] || null;
      const role = (pk.querySelector('[data-role][aria-pressed=true]') || {}).dataset; const dn = (pk.querySelector('[data-density-pick][aria-pressed=true]') || { dataset: {} }).dataset.densityPick;
      const old = PR.ensure(db.load(cur)); const p = PR.newProfile(desk, on.map(x => x.dataset.topic), undefined, { role: role && role.role, density: dn });
      if (old) { ['saved', 'hidden', 'explored', 'bandit', 'src', 'stats', 'adapt'].forEach(k => { p[k] = old[k]; }); Object.keys(old.w).forEach(t => { if (p.w[t]) p.w[t] = old.w[t]; }); }
      if (old && dn !== old.density) p.densityAuto = false; else if (old && old.densityAuto === false) p.densityAuto = false;
      db.save(cur, p); say('Đã lưu cho người đọc này.'); drawTaste(); syncEnter();
    };
    const tf = pk.querySelector('[data-topic-filter]');
    let tfT = 0; if (tf) tf.addEventListener('input', () => { clearTimeout(tfT); tfT = setTimeout(() => { const q = tf.value.trim().toLowerCase(); let n = 0;
      chips().forEach(c => { const h = !q || c.textContent.toLowerCase().includes(q) || c.dataset.topic.includes(q); c.hidden = !h; if (c.parentElement.classList.contains('chipw')) c.parentElement.hidden = !h; if (h) n++; });
      pk.querySelectorAll('.sg').forEach(g => { g.hidden = !g.querySelector('.chip[data-topic]:not([hidden])'); });
      const em = pk.querySelector('[data-tf-empty]'); if (em) em.hidden = n > 0; }, 120); });
    pk.addEventListener('click', ev => {
      const c = ev.target.closest('.chip[data-topic]'), r = ev.target.closest('[data-role]'), dn = ev.target.closest('[data-density-pick]');
      if (c) { pressed(c, c.getAttribute('aria-pressed') !== 'true'); saveUI(); }
      else if (r) {
        pk.querySelectorAll('[data-role]').forEach(b => pressed(b, b === r));
        const ts = (r.dataset.topics || '').split(',').filter(Boolean); chips().forEach(x => pressed(x, ts.includes(x.dataset.topic)));
        pk.querySelectorAll('[data-density-pick]').forEach(b => pressed(b, b.dataset.densityPick === r.dataset.density)); saveUI();
      } else if (dn) { pk.querySelectorAll('[data-density-pick]').forEach(b => pressed(b, b === dn)); saveUI(); }
    });
    // Gu của tôi
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
    // ----- onboarding 3 bước; lựa chọn lưu ngay, bước dở nhớ trong localStorage.
    const cr = pk.querySelector('[data-create]'), ob = pk.querySelector('[data-ob]'), steps = [...pk.querySelectorAll('[data-step]')], cnt = pk.querySelector('[data-count]');
    const obWho = pk.querySelector('[data-ob-who]');
    const showStep = n => {
      if (!n) { ob.hidden = true; db.doneStep(cur); say('Xong. Bấm Vào đọc.'); return; }
      ob.hidden = false; db.setStep(cur, n);
      steps.forEach(f => { f.hidden = +f.dataset.step !== n; });
      const pvb = ob.querySelector('[data-prev]'), nxb = ob.querySelector('[data-next]'); pvb.hidden = n === 1; nxb.textContent = n === 3 ? 'Xong ✓' : 'Tiếp →';
      const x = db.list().find(y => y.id === cur); if (obWho) obWho.textContent = 'Đang chọn cho: ' + (x ? x.name : '');
      const h = steps[n - 1].querySelector('legend'); if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); }
    };
    pk.addEventListener('click', ev => {
      if (ev.target.closest('[data-open-create]')) { cr.hidden = false; if (fm && fm.nm) fm.nm.focus(); return; }
      if (ev.target.closest('[data-edit]')) { showStep(db.step(cur) || 1); return; }
      const nx = ev.target.closest('[data-next]'), pv = ev.target.closest('[data-prev]');
      if (nx || pv) { const f = steps.find(y => !y.hidden); showStep(PP.nav(f ? +f.dataset.step : 1, pv ? -1 : 1)); }
    });
    if (fm) fm.addEventListener('submit', ev => {
      ev.preventDefault(); const v = fm.nm.value.trim().slice(0, 24);
      if (!v) { say('Nhập tên người đọc.'); return; }
      const id = db.canCreate() ? db.create(v) : null;
      if (!id) { say('Đã đủ 8 người đọc.'); return; }
      cur = id; db.select(id); fm.nm.value = ''; cr.hidden = true; say(`Đã tạo “${v}”.`); draw(); showStep(1);
    });
    const dl = pk.querySelector('[data-del]');
    if (dl) dl.addEventListener('click', () => {
      const x = db.list().find(y => y.id === cur); if (!x) return;
      if (!confirm(x.kind === 'me' ? 'Xoá sạch dữ liệu của "Tôi"?' : `Xoá "${x.name}" và toàn bộ dữ liệu? Không khôi phục được.`)) return;
      db.remove(cur); cur = 'me'; db.select('me'); say('Đã xoá.'); ob.hidden = true; draw();
    });
    const go = pk.querySelector('a[href="index.html"]'); if (go) go.addEventListener('click', () => db.select(cur));
    db.select(cur); draw(); drawTaste();
    const pend = db.pending(); if (pend) { cur = pend; db.select(cur); draw(); showStep(db.step(pend)); }
  }

})();

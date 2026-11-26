/* Giao diện cho U2–U7 (nạp lazy): palette tìm kiếm ⌘K, reader (đọc sạch), Đọc sau/thư viện, Tóm 60 giây/digest tuần, theo dõi, mật độ/giờ đọc/quá tải,
   xuất/nhập hồ sơ, VN/EN. Mọi chữ từ nguồn ngoài đưa vào bằng textContent. Dữ liệu cá nhân: localStorage (press.*), không gửi đi đâu. */
(() => {
  const D = document, S = window.PressSearch, F = window.PressFeatures, P = window.PressPersona, PP = window.PressProfiles, PJ = window.PressJournal;
  if (window.PressUI) return;
  const $ = (s, r) => (r || D).querySelector(s), $$ = (s, r) => [...(r || D).querySelectorAll(s)];
  const el = (t, c, x, at) => { const n = D.createElement(t); if (c) n.className = c; if (x != null) n.textContent = x; if (at) Object.keys(at).forEach(k => n.setAttribute(k, at[k])); return n; };
  const ls = { get: k => { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: (k, v) => { try { localStorage.setItem(k, v); return true; } catch (e) { return false; } }, del: k => { try { localStorage.removeItem(k); } catch (e) {} } };
  const rd = (k, d) => { try { const v = JSON.parse(ls.get(k)); return v == null ? d : v; } catch (e) { return d; } };
  const today = () => new Date().toISOString().slice(0, 10);
  const httpOk = u => /^https?:\/\//i.test(u || '');
  const pid = () => { try { return (PP && PP.open().active()) || 'me'; } catch (e) { return 'me'; } };
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let lang = ls.get('press.lang') === 'en' ? 'en' : 'vi';
  const T = (vi, en) => (lang === 'en' && en ? en : vi);

  // ---------- dữ liệu: search.json + stories.json (tải một lần, lúc cần) ----------
  let IX = null, META = null, STORIES = null, loadP = null;
  const load = () => loadP || (loadP = Promise.all([fetch('search.json').then(r => r.json()), fetch('stories.json').then(r => r.json()).catch(() => ({}))]).then(([s, st]) => { META = s; IX = S.build(s.rows); STORIES = st; }).catch(() => { loadP = null; }));
  const rowById = id => IX && IX.rows.find(r => r[S.R.id] === id);

  // ---------- thư viện Đọc sau ----------
  const LK = () => 'press.lib.' + pid();
  const lib = () => { const l = rd(LK(), []); return Array.isArray(l) ? l : []; };
  const saveLib = l => ls.set(LK(), JSON.stringify(l.slice(0, 300)));
  const inLib = id => lib().find(x => x.id === id);
  function toggleLater(a) {
    const before = lib(); let l = before.slice(); const has = l.find(x => x.id === a.id);
    if (has) l = l.filter(x => x.id !== a.id); else l.unshift({ id: a.id, t: String(a.t).slice(0, 160), u: httpOk(a.u) ? a.u : '', s: String(a.s || '').slice(0, 40), d: today(), sid: a.sid || '', st: 'later' });
    if (!saveLib(l)) { toast(T('Không lưu được (bộ nhớ trình duyệt đầy hoặc bị chặn). Đã giữ nguyên như cũ.', 'Could not save (browser storage full or blocked). Left as it was.')); return !!has; }
    if (!has) D.dispatchEvent(new CustomEvent('press:save', { detail: { id: a.id } }));
    const sync = () => D.querySelectorAll('[data-later-id]').forEach(b => { if (b.dataset.laterId !== a.id) return; const on = !!inLib(a.id); b.textContent = on ? T('Đã lưu ✓', 'Saved ✓') : T('Đọc sau', 'Read later'); b.setAttribute('aria-pressed', String(on)); });
    toast(has ? T('Đã bỏ khỏi “Đọc sau”.', 'Removed from Read later.') : T('Đã lưu vào “Đọc sau” — xem ở Của tôi → Đã lưu.', 'Saved to Read later — see Me → Saved.'), { undo: () => { saveLib(before); sync(); }, undoLabel: T('Hoàn tác', 'Undo') });
    return !has;
  }

  // ---------- toast ----------
  const FBK = window.PressFeedback; let TS = null;
  const toast = (m, o) => { if (FBK && !TS) TS = FBK.toaster({ doc: D, setTimeout, clearTimeout }); if (TS) TS.show(m, o); };

  // ---------- hộp thoại dùng chung (focus trap, Esc, trả focus) ----------
  let dlg = null, back = null, onKey = null;
  function open(title, build, cls) {
    close(); back = D.activeElement;
    dlg = el('div', 'pp ' + (cls || ''), '', { role: 'dialog', 'aria-modal': 'true', 'aria-label': title });
    const box = el('div', 'pp-b'); dlg.append(box); build(box, dlg); D.body.append(dlg); D.documentElement.classList.add('pp-open');
    const f = $('[data-autofocus]', dlg) || $('button,a[href],input,select', dlg); f && f.focus();
    dlg.addEventListener('mousedown', e => { if (e.target === dlg) close(); });
    dlg.addEventListener('keydown', e => {
      if (e.key === 'Escape') { e.stopPropagation(); close(); return; }
      if (e.key === 'Tab') { const fs = $$('button:not([disabled]),a[href],input,select,textarea', dlg).filter(x => x.offsetParent !== null || x === D.activeElement); if (!fs.length) return; const i = fs.indexOf(D.activeElement); if (e.shiftKey && i <= 0) { e.preventDefault(); fs[fs.length - 1].focus(); } else if (!e.shiftKey && i === fs.length - 1) { e.preventDefault(); fs[0].focus(); } }
      if (onKey) onKey(e);
    });
  }
  function close() { if (!dlg) return; dlg.remove(); dlg = null; onKey = null; D.documentElement.classList.remove('pp-open'); if (back && back.isConnected) back.focus(); back = null; }
  const btn = (txt, fn, at) => { const b = el('button', 'btn', txt, Object.assign({ type: 'button' }, at || {})); b.addEventListener('click', fn); return b; };

  // ---------- Palette tìm kiếm (Ctrl/Cmd-K, "/") ----------
  const CMDS = () => [
    [T('Báo hôm nay', 'Today’s issue'), 'index.html'], [T('Của tôi', 'Me'), 'me.html'], [T('Đã lưu / Đọc sau', 'Saved / Read later'), 'me.html#da-luu'],
    [T('Chạy báo hôm nay', 'Run today’s report'), 'me.html#cai-dat'], [T('Xuất / nhập hồ sơ', 'Export / import profile'), 'me.html#cai-dat'],
  ];
  function palette(q0) {
    open(T('Tìm kiếm', 'Search'), (box, d) => {
      box.append(el('h2', 'vh', T('Tìm kiếm', 'Search')));
      const inp = el('input', 'pp-q', '', { type: 'search', role: 'combobox', 'aria-expanded': 'true', 'aria-controls': 'pp-list', 'aria-autocomplete': 'list', placeholder: T('Tìm trong mọi số báo và kho tin… (Esc để đóng)', 'Search all issues and the archive… (Esc to close)'), 'aria-label': T('Từ khoá', 'Keywords'), autocomplete: 'off', 'data-autofocus': '' });
      const fl = el('div', 'pp-f'), sel = (nm, lab) => { const s = el('select', '', '', { 'aria-label': lab }); s.append(new Option(lab, '')); s.dataset.f = nm; fl.append(s); return s; };
      const sT = sel('topic', T('Chủ đề', 'Topic')), sD = sel('desk', T('Ban', 'Desk')), sS = sel('source', T('Nguồn', 'Source')), sW = sel('when', T('Thời gian', 'When'));
      [['7', T('7 ngày', '7 days')], ['30', T('30 ngày', '30 days')]].forEach(([v, l]) => sW.append(new Option(l, v)));
      const list = el('ul', 'pp-l', '', { id: 'pp-list', role: 'listbox', 'aria-label': T('Kết quả', 'Results') }), st = el('p', 'pp-s', '', { role: 'status', 'aria-live': 'polite' });
      box.append(inp, fl, st, list); let sel_i = -1, items = [], uid = 0;
      const RK = 'press.recent', recents = () => S.pushRecent(rd(RK, []), '');
      const mark = (parent, text, T) => S.segments(text, T).forEach(([t, m]) => parent.append(m ? el('mark', '', t) : D.createTextNode(t)));   // chỉ textContent / <mark>
      const head = t => list.append(el('li', 'pp-g', t, { role: 'presentation' }));
      const add = (li, act) => { li.id = 'pp-o' + (uid++); li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false'); li.addEventListener('mousemove', () => pick(items.findIndex(x => x.li === li))); li.addEventListener('click', e => { e.preventDefault(); act(); }); list.append(li); items.push({ li, act }); };
      const pick = i => { if (i === sel_i) return; if (items[sel_i]) { items[sel_i].li.classList.remove('sel'); items[sel_i].li.setAttribute('aria-selected', 'false'); } sel_i = i; const it = items[i]; if (it) { it.li.classList.add('sel'); it.li.setAttribute('aria-selected', 'true'); inp.setAttribute('aria-activedescendant', it.li.id); it.li.scrollIntoView && it.li.scrollIntoView({ block: 'nearest' }); } else inp.removeAttribute('aria-activedescendant'); };
      const remember = () => { const q = inp.value.trim(); if (q) ls.set(RK, JSON.stringify(S.pushRecent(rd(RK, []), q))); };
      const go = h => { remember(); location.href = h; };
      const setQ = (v, focus) => { inp.value = v; run(); focus && inp.focus(); };
      const setFilter = (s, v) => { if (![...s.options].some(o => o.value === v)) return; s.value = v; setQ('', true); };
      const cmd = (n, h) => { const li = el('li', 'pp-i'); li.append(el('a', '', n, { href: h, tabindex: '-1' })); add(li, () => go(h)); };
      const chip = (id, name, act, tag) => { const li = el('li', 'pp-i'); li.append(el('span', 'pp-n', name), el('small', '', tag)); add(li, act); };
      let failed = false;
      const run = () => {
        list.textContent = ''; items = []; sel_i = -1; inp.removeAttribute('aria-activedescendant'); const q = inp.value.trim(), T = S.toks(q);
        const f = { topic: sT.value, desk: sD.value, source: sS.value }; if (sW.value) f.from = new Date(Date.now() - (+sW.value) * 864e5).toISOString().slice(0, 10);
        const filtered = f.topic || f.desk || f.source || f.from;
        if (!q && !filtered) {
          st.textContent = T('Gõ để tìm, hoặc chọn một gợi ý:', 'Type to search, or pick a suggestion:');
          const rc = recents(); if (rc.length) { head(T('Tìm gần đây', 'Recent searches')); rc.forEach(x => { const li = el('li', 'pp-i'); li.append(el('span', 'pp-n', x)); add(li, () => setQ(x, true)); }); }
          const fw = META ? S.followedTopics(((PRK0() || {}).w), META.topics, 5) : []; if (fw.length) { head(T('Chủ đề bạn theo dõi', 'Topics you follow')); fw.forEach(o => chip(o.id, o.name, () => setFilter(sT, o.id), T('chủ đề', 'topic'))); }
          head(T('Lệnh', 'Commands')); CMDS().forEach(([n, h]) => cmd(n, h)); pick(items.length ? 0 : -1); return;
        }
        list.removeAttribute('aria-busy');
        if (!IX) {
          if (failed) { st.textContent = T('Không tải được kho tin. Kiểm tra mạng.', 'Could not load archive. Check your connection.'); return; }
          st.textContent = T('Đang tải kho tin…', 'Loading archive…'); list.setAttribute('aria-busy', 'true');   // khung chờ cao bằng dòng kết quả thật
          for (let i = 0; i < 4; i++) { const li = el('li', 'pp-i sk-row', '', { 'aria-hidden': 'true' }); li.append(el('span', 'sk-bar'), el('span', 'sk-bar sk-s')); list.append(li); } return;
        }
        const t0 = performance.now(), g = S.groups(IX, q, f, META, 12), ms = Math.round(performance.now() - t0), n = g.articles.length + g.topics.length + g.desks.length;
        st.textContent = n ? g.articles.length + T(' bài', ' stories') + (g.fuzzy ? T(' (gần đúng)', ' (approximate)') : '') + ' · ' + ms + ' ms' : T('Không thấy kết quả. Thử bớt từ khoá hoặc bỏ bộ lọc.', 'No results. Try fewer keywords or clear filters.');
        if (g.topics.length) { head(T('Chủ đề', 'Topics')); g.topics.forEach(o => { const li = el('li', 'pp-i'), nm = el('span', 'pp-n'); mark(nm, o.name, T); li.append(nm, el('small', '', T('lọc theo chủ đề', 'filter by topic'))); add(li, () => setFilter(sT, o.id)); }); }
        if (g.desks.length) { head(T('Ban', 'Desks')); g.desks.forEach(o => { const li = el('li', 'pp-i'), nm = el('span', 'pp-n'); mark(nm, o.name, T); li.append(nm, el('small', '', T('lọc theo ban', 'filter by desk'))); add(li, () => setFilter(sD, o.id)); }); }
        if (g.articles.length) head(T('Bài', 'Stories'));
        g.articles.forEach(o => { const r = o.r, h = httpOk(r[S.R.u]) ? r[S.R.u] : '#', li = el('li', 'pp-i'), a = el('a', '', '', { href: h, rel: 'noopener', tabindex: '-1' });
          mark(a, r[S.R.t], T); const sn = el('span', 'pp-sn'); sn.append(o.snip[0]); if (o.snip[1]) sn.append(el('mark', '', o.snip[1])); sn.append(o.snip[2]);
          li.append(a, el('small', '', r[S.R.s] + ' · ' + r[S.R.d]), sn); add(li, () => { remember(); if (h !== '#') window.open(h, '_blank', 'noopener'); }); });
        pick(items.length ? 0 : -1);
      };
      const PRK0 = () => { try { const db = PP.open(), pr = window.PressRank; const pf = db.load(db.active() || 'me'); return pr && pf ? pr.ensure(pf) : null; } catch (e) { return null; } };
      const fill = () => { const c = S.facets(IX), put = (s, o, lab) => Object.keys(o).sort((a, b) => o[b] - o[a]).slice(0, 40).forEach(k => s.append(new Option(lab(k) + ' (' + o[k] + ')', k))); put(sT, c.topics, k => META.topics[k] || k); put(sD, c.desks, k => META.desks[k] || k); put(sS, c.sources, k => k); };
      let to = null; inp.addEventListener('input', () => { clearTimeout(to); to = setTimeout(run, 30); }); fl.addEventListener('change', run);
      // focus ở lại ô nhập (combobox): mũi tên đổi mục chọn, Enter mở mục chọn; Esc đóng + trả focus do open()
      inp.addEventListener('keydown', e => {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { if (!items.length) return; e.preventDefault(); pick(S.step(sel_i, items.length, e.key === 'ArrowDown' ? 1 : -1)); }
        else if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); if (items[sel_i]) items[sel_i].act(); }
      });
      if (q0) inp.value = q0; run(); load().then(() => { if (!dlg) return; if (!IX) failed = true; if (failed || !sT.options[1]) { if (IX) fill(); run(); } });
    });
  }

  // ---------- Reader ----------
  let RCARDS = [], RI = 0;
  const cardData = c => { const a = $('h3 a', c) || $('a', c), im = $('img', c), id = c.dataset.id, r = rowById(id), m = ($('.meta', c) || {}).textContent || '';
    return { id, t: a ? a.textContent : '', u: a ? a.href : '', s: m.split(' · ')[0], img: im && httpOk(im.src) ? im.src : '', x: r ? r[S.R.x] : '', sid: r ? (r[9] || r[S.R.id]) : c.dataset.sid || id, d: r ? r[S.R.d] : '', st: c.dataset.st }; };
  const cards = () => $$('main .card[data-id]').filter(c => c.querySelector('a[href^="http"]'));
  const cur = () => { const a = D.activeElement && D.activeElement.closest && D.activeElement.closest('.card[data-id]'); return a || $('.card.kb') || null; };
  function markRead(c) {
    const PD = window.PressDedup; if (!PD || !c) return; c.classList.add('read');
    try { const sd = PD.open(null, pid()), l = $('h3 a', c); sd.mark({ id: c.dataset.id, sid: c.dataset.sid || '', rev: +c.dataset.rev || 0, title: l ? l.textContent : '', url: l ? l.href : '' }, true, Date.now()); } catch (e) {}
  }
  function reader(c) {
    RCARDS = cards(); RI = Math.max(0, RCARDS.indexOf(c)); const pr = rd('press.reader', { size: 1, wide: false });
    const draw = () => {
      const a = cardData(RCARDS[RI]); markRead(RCARDS[RI]); rememberCard(RCARDS[RI]);
      open(T('Đọc nhanh', 'Quick read'), (box, d) => {
        d.classList.toggle('wide', !!pr.wide); box.style.setProperty('--rs', 1 + pr.size * 0.12);
        const bar = el('div', 'pp-bar'); bar.append(
          btn('A−', () => { pr.size = Math.max(-2, pr.size - 1); ls.set('press.reader', JSON.stringify(pr)); draw(); }, { 'aria-label': T('Chữ nhỏ hơn', 'Smaller text') }),
          btn('A+', () => { pr.size = Math.min(4, pr.size + 1); ls.set('press.reader', JSON.stringify(pr)); draw(); }, { 'aria-label': T('Chữ lớn hơn', 'Larger text') }),
          btn(pr.wide ? T('Hẹp', 'Narrow') : T('Rộng', 'Wide'), () => { pr.wide = !pr.wide; ls.set('press.reader', JSON.stringify(pr)); draw(); }, { 'aria-label': T('Đổi độ rộng cột chữ', 'Toggle column width') }),
          btn(T('Đóng', 'Close'), close, { 'aria-label': T('Đóng (Esc)', 'Close (Esc)') }));
        box.append(bar);
        if (a.img) { const im = el('img', 'pp-img', '', { src: a.img, alt: '', width: 640, height: 360, referrerpolicy: 'no-referrer' }); im.onerror = () => im.remove(); box.append(im); }
        box.append(el('h2', 'pp-t', a.t), el('p', 'meta', a.s + (a.d ? ' · ' + a.d : '')), el('p', 'pp-x', a.x || T('Chưa có tóm tắt cho bài này — mở bài gốc để đọc.', 'No summary for this story — open the original to read.')));
        const act = el('div', 'pp-bar');
        act.append(el('a', 'btn pri', T('Đọc bài gốc ↗', 'Read original ↗'), { href: a.u, rel: 'noopener' }));
        const sv = btn(inLib(a.id) ? T('Đã lưu ✓', 'Saved ✓') : T('Đọc sau', 'Read later'), () => { const on = toggleLater(a); sv.textContent = on ? T('Đã lưu ✓', 'Saved ✓') : T('Đọc sau', 'Read later'); sv.setAttribute('aria-pressed', on); }, { 'aria-pressed': !!inLib(a.id), 'data-later-id': a.id }); act.append(sv);
        if (STORIES && STORIES[a.sid]) { const fo = (rd('press.follow.' + pid(), [])).some(x => x.sid === a.sid); const fb = btn(fo ? T('Đang theo dõi ✓', 'Following ✓') : T('Theo dõi', 'Follow'), () => { const k = 'press.follow.' + pid(), l = rd(k, []), on = !l.some(x => x.sid === a.sid); const paint = o => { fb.textContent = o ? T('Đang theo dõi ✓', 'Following ✓') : T('Theo dõi', 'Follow'); fb.setAttribute('aria-pressed', String(o)); };
          if (!ls.set(k, JSON.stringify(on ? F.follow(l, a.sid, STORIES, today()) : F.unfollow(l, a.sid)))) { toast(T('Không lưu được. Đã giữ nguyên như cũ.', 'Could not save. Left as it was.')); return; }
          paint(on); toast(on ? T('Sẽ báo khi câu chuyện này có tin mới.', 'You’ll see when this story has news.') : T('Đã bỏ theo dõi.', 'Unfollowed.'), { undo: () => { ls.set(k, JSON.stringify(l)); paint(!on); }, undoLabel: T('Hoàn tác', 'Undo') }); }, { 'aria-pressed': fo }); act.append(fb); }
        act.append(btn('◀', () => step(-1), { 'aria-label': T('Bài trước (k)', 'Previous (k)') }), btn('▶', () => step(1), { 'aria-label': T('Bài sau (j)', 'Next (j)') }));
        box.append(act, el('p', 'pp-h', T('Phím: j/k đổi bài · s đọc sau · +/- cỡ chữ · Esc đóng. Vuốt trái/phải trên điện thoại.', 'Keys: j/k next/prev · s read later · +/- text size · Esc close. Swipe on phones.')));
        let x0 = null, y0 = 0; box.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
        box.addEventListener('touchend', e => { if (x0 == null) return; const dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0; x0 = null; if (Math.abs(dx) > 60 && Math.abs(dy) < 40) step(dx < 0 ? 1 : -1); }, { passive: true });
        onKey = e => { if (e.key === 'j') step(1); else if (e.key === 'k') step(-1); else if (e.key === 's') sv.click(); else if (e.key === '+' || e.key === '=') { pr.size = Math.min(4, pr.size + 1); ls.set('press.reader', JSON.stringify(pr)); draw(); } else if (e.key === '-') { pr.size = Math.max(-2, pr.size - 1); ls.set('press.reader', JSON.stringify(pr)); draw(); } };
      }, 'reader');
      const keep = back; back = keep;
    };
    const step = d => { const n = RI + d; if (n < 0 || n >= RCARDS.length) return; RI = n; const b0 = back; draw(); back = b0 && b0.isConnected ? b0 : RCARDS[RI].querySelector('a'); };
    load().then(() => { if (dlg) { const b0 = back; draw(); back = b0; } });
    draw();
  }

  // ---------- Tóm 60 giây / Digest tuần ----------
  function brief(mode) {
    const draw = m => open(m === 'week' ? T('Digest tuần', 'Weekly digest') : T('Tóm 60 giây', '60-second brief'), (box) => {
      const j = (() => { try { return PJ && PJ.open(null, pid()).load(); } catch (e) { return null; } })(), sl = P && P.slot(j, today());
      box.append(el('h2', 'pp-t', (m === 'week' ? T('Digest tuần', 'Weekly digest') : T('Tóm 60 giây', '60-second brief')) + (sl && m !== 'week' ? ' · ' + T(P.SLOT[sl], { sang: 'Morning issue', chieu: 'Afternoon issue', toi: 'Evening issue' }[sl]) : '')));
      const tabs = el('div', 'pp-bar'); tabs.append(btn(T('Hôm nay', 'Today'), () => { close(); draw('day'); }, { 'aria-pressed': m !== 'week' }), btn(T('Tuần này', 'This week'), () => { close(); draw('week'); }, { 'aria-pressed': m === 'week' })); box.append(tabs);
      const ul = el('ol', 'pp-ol'); box.append(ul); const meta = el('p', 'meta', '', { role: 'status' }); box.append(meta);
      const fillList = items => { items.forEach(it => { const li = el('li'), a = el('a', '', it.title, { href: httpOk(it.url) ? it.url : '#', rel: 'noopener' }); li.append(a); if (it.extra) li.append(el('span', 'pp-sn', ' — ' + it.extra)); if (it.source) li.append(el('small', '', ' · ' + it.source)); ul.append(li); }); };
      if (m === 'week') { load().then(() => { if (!IX) { meta.textContent = T('Không tải được kho tin. Kiểm tra mạng.', 'Could not load archive. Check your connection.'); return; } const last = IX.rows.reduce((a, r) => r[S.R.d] > a ? r[S.R.d] : a, ''), d = F.digest(IX.rows, last, 8); ul.textContent = ''; fillList(d.rows.map(r => ({ title: r[S.R.t], url: r[S.R.u], source: r[S.R.s], extra: '' }))); meta.textContent = d.from + ' → ' + d.to + ' · ' + d.rows.length + T(' tin nổi bật, tối đa 2/chủ đề', ' top stories, max 2 per topic'); }); }
      else { const cs = cards().map(cardData), b = F.brief60(cs.map(c => ({ id: c.id, title: c.t, url: c.u, source: c.s, topics: [] })), { seconds: 60 }); fillList(b.items); meta.textContent = '≈ ' + b.secs + T(' giây đọc · ', 's read · ') + b.items.length + T(' tin đầu bảng', ' top stories'); if (!b.items.length) meta.textContent = T('Chưa có bài để tóm. Mở trang chủ khi có số báo mới.', 'Nothing to summarise yet. Open the home page when a new issue arrives.'); }
      box.append(btn(T('Đóng', 'Close'), close));
    });
    draw(mode || 'day');
  }

  // ---------- Của tôi: Đã lưu + Đang theo dõi + Cá nhân hoá + Tệp hồ sơ ----------
  function mePage() {
    const pn = $('#pn-da-luu'); if (pn) {
      const ul = $('[data-lib-list]', pn), q = $('[data-lib-q]', pn), fu = $('[data-follow-list]', pn), em = $('[data-lib-empty]', pn);
      const draw = () => {
        const f = S.fold(q.value), l = lib().filter(x => !f || S.fold(x.t + ' ' + x.s).includes(f)); ul.textContent = '';
        em.hidden = l.length > 0 || !!f; if (f && !l.length) { ul.append(el('li', 'm', T('Không có mục khớp.', 'No matches.'))); }
        l.forEach(x => { const li = el('li', 'lib' + (x.st === 'done' ? ' done' : '')), a = el('a', '', x.t, { href: httpOk(x.u) ? x.u : '#', rel: 'noopener' }); li.append(a, el('small', '', ' · ' + x.s + ' · ' + x.d));
          li.append(btn(x.st === 'done' ? T('Đọc lại', 'Unread') : T('Đã đọc', 'Done'), () => { const L = lib(), it = L.find(y => y.id === x.id); if (it) { it.st = it.st === 'done' ? 'later' : 'done'; saveLib(L); draw(); } }), btn(T('Bỏ', 'Remove'), () => { saveLib(lib().filter(y => y.id !== x.id)); draw(); }, { 'aria-label': T('Bỏ khỏi danh sách: ', 'Remove: ') + x.t })); ul.append(li); });
      };
      q.addEventListener('input', draw); draw();
      const drawF = () => { fu.textContent = ''; const l = rd('press.follow.' + pid(), []); if (!l.length) { fu.append(el('li', 'm', T('Chưa theo dõi câu chuyện nào — mở “Đọc nhanh” rồi bấm Theo dõi.', 'Not following any story — open Quick read and press Follow.'))); return; }
        if (!STORIES) { fu.append(el('li', 'm', T('Đang tải…', 'Loading…'))); return; }
        F.followUpdates(l, STORIES).forEach(u => { const li = el('li'); li.append(el('b', '', u.title), el('small', '', ' · ' + u.n + T(' mục', ' entries') + (u.fresh ? ' · ' + u.fresh + T(' mới', ' new') : '')));
          const tl = el('ul', 'tl'); F.timeline(STORIES, u.sid).slice(0, 6).forEach(t => { const x = el('li'); x.append(el('small', '', t.d + ' · '), el('a', '', t.t, { href: httpOk(t.u) ? t.u : '#', rel: 'noopener' })); tl.append(x); }); li.append(tl, btn(T('Bỏ theo dõi', 'Unfollow'), () => { ls.set('press.follow.' + pid(), JSON.stringify(F.unfollow(rd('press.follow.' + pid(), []), u.sid))); drawF(); })); fu.append(li); }); };
      drawF(); load().then(drawF);
    }
    const ps = $('[data-persona]'); if (ps) {
      const j = (() => { try { return PJ.open(null, pid()).load(); } catch (e) { return null; } })(), sl = P.slot(j, today()), ds = $('[data-pz-slot]');
      ds.textContent = sl ? T('Bạn thường đọc vào ' + { sang: 'buổi sáng', chieu: 'buổi chiều', toi: 'buổi tối' }[sl] + ' → hiển thị “' + P.SLOT[sl] + '”.', 'You usually read in the ' + { sang: 'morning', chieu: 'afternoon', toi: 'evening' }[sl] + ' → showing “' + { sang: 'Morning', chieu: 'Afternoon', toi: 'Evening' }[sl] + ' issue”.') : T('Chưa đủ dữ liệu giờ đọc (cần ≥ 3 ngày).', 'Not enough reading-time data yet (needs ≥ 3 days).');
      const dn = $('[data-pz-dens]'), prof = () => { try { const db = PP.open(), id = db.active() || 'me'; return { db, id, p: window.PressRank.ensure(db.load(id) || window.PressRank.newProfile(null, [])) }; } catch (e) { return null; } };
      const pf = prof(), sg = pf && P.suggestDensity(j, today(), pf.p.density), NM = { compact: T('Gọn', 'Compact'), normal: T('Vừa', 'Normal'), rich: T('Nhiều', 'Rich') };
      dn.textContent = ''; if (sg) { dn.append(el('span', '', T('Bạn mở ~' + sg.per + ' bài/ngày → gợi ý mật độ “' + NM[sg.to] + '”. ', 'You open ~' + sg.per + ' stories/day → suggested density “' + NM[sg.to] + '”. ')), btn(T('Áp dụng', 'Apply'), () => { const q = prof(); if (q) { q.p.density = sg.to; q.p.densityAuto = false; q.db.save(q.id, q.p); dn.textContent = T('Đã áp dụng.', 'Applied.'); } })); } else dn.textContent = pf ? T('Mật độ hiện tại hợp với cách bạn đọc.', 'Current density fits how you read.') : T('Chọn người đọc để có gợi ý.', 'Pick a reader to get a suggestion.');
      const lim = $('[data-pz-limit]'), msg = $('[data-pz-limit-msg]'), k = 'press.limit.' + pid(); lim.value = ls.get(k) || '';
      const ov = P.overload(j, today(), +lim.value || 0); msg.textContent = ov.suggest ? T('3 ngày liền bạn đọc > 25 bài/ngày — thử đặt giới hạn.', 'You read > 25 stories/day for 3 days — consider a limit.') : (+lim.value ? T('Hôm nay đã đọc ' + ov.read + '/' + lim.value + '.', 'Today ' + ov.read + '/' + lim.value + '.') : T('Tắt (0).', 'Off (0).'));
      lim.addEventListener('change', () => { const v = Math.max(0, Math.min(200, +lim.value || 0)); lim.value = v || ''; if (v) ls.set(k, String(v)); else ls.del(k); msg.textContent = v ? T('Đã đặt: ' + v + ' bài/ngày.', 'Set: ' + v + '/day.') : T('Đã tắt.', 'Off.'); });
      $('[data-pz-export]').addEventListener('click', () => { const st = {}; for (let i = 0; i < localStorage.length; i++) { const kk = localStorage.key(i); if (kk.startsWith('press.')) st[kk] = localStorage.getItem(kk); } const b = new Blob([F.exportProfile(st)], { type: 'application/json' }), a = el('a', '', '', { href: URL.createObjectURL(b), download: 'ban-tin-ho-so-' + today() + '.json' }); D.body.append(a); a.click(); a.remove(); $('[data-pz-file-msg]').textContent = T('Đã xuất. Tệp không chứa API key.', 'Exported. The file contains no API key.'); });
      $('[data-pz-import]').addEventListener('change', e => { const f = e.target.files[0]; if (!f) return; if (f.size > 3e6) { $('[data-pz-file-msg]').textContent = T('Tệp quá lớn.', 'File too large.'); return; } f.text().then(t => { const st = {}, r = F.importProfile(t, st); if (r.ok) Object.keys(st).forEach(k => ls.set(k, st[k])); $('[data-pz-file-msg]').textContent = r.ok ? T('Đã nhập ' + r.n + ' mục (bỏ qua ' + r.skip + '). Tải lại trang để áp dụng.', 'Imported ' + r.n + ' items (skipped ' + r.skip + '). Reload to apply.') : r.err; }); });
    }
  }

  // ---------- cảnh báo quá tải (trang chủ) ----------
  function overloadNote() { if (!$('[data-issues]')) return; const lim = +ls.get('press.limit.' + pid()) || 0; if (!lim || !PJ) return; const ov = P.overload(PJ.open(null, pid()).load(), today(), lim); if (ov.over && ls.get('press.limit.dismissed') !== today()) { toast(T('Bạn đã đọc ' + ov.read + ' bài hôm nay — đủ rồi, mai có số mới.', 'You’ve read ' + ov.read + ' stories today — enough, a new issue comes tomorrow.')); ls.set('press.limit.dismissed', today()); } }

  // ---------- VN/EN ----------
  let I18N = null; const attrs = ['aria-label', 'title', 'placeholder'];
  function applyLang(root) {
    if (!I18N) return; D.documentElement.lang = lang;
    const walk = n => { if (n.nodeType === 3) { const t = n.nodeValue.trim(); if (!t) return; const vi = n.__vi || t; const en = I18N[vi]; if (lang === 'en' && en) { n.__vi = vi; n.nodeValue = n.nodeValue.replace(t, en); } else if (lang === 'vi' && n.__vi) { n.nodeValue = n.nodeValue.replace(t, n.__vi); n.__vi = null; } return; } if (n.nodeType !== 1 || /^(SCRIPT|STYLE)$/.test(n.tagName) || n.hasAttribute('data-nt')) return; attrs.forEach(a => { const v = n.getAttribute(a); if (!v) return; const k = n['__' + a] || v; if (lang === 'en' && I18N[k]) { n['__' + a] = k; n.setAttribute(a, I18N[k]); } else if (lang === 'vi' && n['__' + a]) { n.setAttribute(a, n['__' + a]); n['__' + a] = null; } }); n.childNodes.forEach(walk); };
    walk(root || D.body); $$('[data-lang]').forEach(b => { b.setAttribute('aria-pressed', b.dataset.lang === lang ? 'true' : 'false'); });
  }
  const loadLang = () => I18N ? Promise.resolve() : fetch('x/en.json').then(r => r.json()).then(j => { I18N = j; }).catch(() => {});
  function setLang(l) { lang = l; ls.set('press.lang', l); loadLang().then(() => applyLang()); }

  // ---------- phím & click ----------
  const typing = e => /^(INPUT|TEXTAREA|SELECT)$/.test((e.target || {}).tagName) || (e.target && e.target.isContentEditable);
  let kbI = -1;
  // ---------- Công cụ đọc: phím j/k/o/s/? và "Đã đọc tất cả" + Hoàn tác (lõi: readtools.js) ----------
  const RT = window.PressReadTools;
  const RTX = {
    cards, cur, blocked: () => !!dlg,
    mark: t => { kbI = cards().indexOf(t); $$('.card.kb').forEach(x => x.classList.remove('kb')); t.classList.add('kb'); const a = $('a[href^="http"]', t); a && a.focus({ preventScroll: true }); t.scrollIntoView({ block: 'center', behavior: RM ? 'auto' : 'smooth' }); },
    open: t => reader(t), save: t => toggleLater(cardData(t)),
    help: () => open(T('Phím tắt', 'Keyboard shortcuts'), box => {
      box.append(el('h2', '', T('Phím tắt', 'Keyboard shortcuts')));
      const dl = el('dl', 'pp-keys'); RT.KEYS.forEach(([k, d]) => { const dt = el('dt'); dt.append(el('kbd', '', k)); dl.append(dt, el('dd', '', T(d))); });
      box.append(dl, btn(T('Đóng', 'Close'), close, { 'data-autofocus': '' }));
    }),
  };
  let RA = null;
  function readAll() {
    const PD = window.PressDedup, g = $('[data-general]'), bx = $('[data-readall-undo]'); if (!PD || !g || !bx) return;
    const sd = PD.open(null, pid());
    RA = RT.markAll({ store: localStorage, key: sd.key, cards: () => $$('.card[data-id]', g), clear: clearTimeout,
      art: c => ({ id: c.dataset.id, sid: c.dataset.sid || '', rev: +c.dataset.rev || 0, title: ($('h3 a', c) || {}).textContent || '', url: ($('h3 a', c) || {}).href || '' }),
      markRead: arts => { const j = sd.load(); arts.forEach(a => PD.mark(j, a, true)); sd.save(j); },
      timer: (f, ms) => setTimeout(() => { f(); bx.hidden = true; }, ms) });
    $('[data-readall-msg]', bx).textContent = T('Đã đánh dấu ' + RA.n + ' bài là đã đọc.', 'Marked ' + RA.n + ' stories as read.'); bx.hidden = false;
  }
  function undoReadAll() { const bx = $('[data-readall-undo]'); if (RA && RA.undo()) toast(T('Đã hoàn tác.', 'Undone.')); if (bx) bx.hidden = true; }
  const api = {
    key(e) {
      const k = e.key;
      const w = S.wantsOpen(e, { typing: typing(e), dialog: !!dlg }); if (w) { e.preventDefault(); if (w === 'toggle' && dlg && $('.pp-q')) close(); else palette(); return; }
      RT.handle(e, RTX);   // j/k/o/s/? — không bắt phím khi đang gõ hoặc đang mở hộp thoại
    },
    click(e) {
      if (saveBtn(e)) return;
      if (cardAct(e)) return;
      if (e.target.closest('[data-readall]')) { e.preventDefault(); readAll(); return; }
      if (e.target.closest('[data-readall-undo-btn]')) { e.preventDefault(); undoReadAll(); return; }
      const s = e.target.closest('[data-search]'); if (s) { e.preventDefault(); palette(); return; }
      const b = e.target.closest('[data-b60]'); if (b) { e.preventDefault(); brief(); return; }
      const l = e.target.closest('[data-lang]'); if (l) { setLang(l.dataset.lang); return; }
      const cd = e.target.closest('main .card[data-id]:not(.hub)');   // bấm vào thân thẻ (không phải liên kết/nút/⋯) → ngăn xem nhanh, không rời trang
      if (cd && !e.target.closest('a,button,summary,details,input,select,textarea') && cd.querySelector('a[href^="http"]')) { e.preventDefault(); reader(cd); return; }
      const t = e.target.closest('.card[data-id] .thumb'); if (t) { const c = t.closest('.card'); if (c.querySelector('a[href^="http"]')) { e.preventDefault(); reader(c); } }
    },
    palette, reader, brief, setLang, applyLang,
  };
  // Nút 'Lưu bài' (trang bài): cập nhật lạc quan — aria-pressed + nhãn đổi ngay, toast có Hoàn tác 6 giây. Bắt ở pha capture để app.js đọc đúng trạng thái mới.
  function saveBtn(e) {
    const b = e.target.closest && e.target.closest('[data-save]'); if (!b || b.dataset.laterId) return false;
    const was = b.getAttribute('aria-pressed') === 'true', paint = on => { b.setAttribute('aria-pressed', String(on)); b.textContent = on ? T('Đã lưu ✓', 'Saved ✓') : T('Lưu bài', 'Save'); };
    paint(!was); toast(was ? T('Đã bỏ lưu bài.', 'Removed from saved.') : T('Đã lưu bài.', 'Saved.'), { undo: () => paint(was), undoLabel: T('Hoàn tác', 'Undo') }); return true;
  }
  D.addEventListener('click', e => { saveBtn(e); }, true);
  // Thao tác ở thẻ: nút ⋯ mở Lưu · Bớt tin · Ẩn · Chia sẻ. Lưu/Bớt tin do app.js nghe ([data-save]/[data-less]); Ẩn ghi vào hồ sơ (hidden) + ẩn thẻ, Hoàn tác 6 s.
  const profDb = () => { try { return PP && PP.open(); } catch (e) { return null; } };
  const profMut = fn => { const db = profDb(), R = window.PressRank, id = db && (db.active() || 'me'); if (!id || !R) return; const p = R.ensure(db.load(id) || R.newProfile(null, [])); fn(p); db.save(id, p); };
  function cardActs() {
    D.querySelectorAll('.card[data-id]:not(.hub):not(.sk-card)').forEach(c => {
      const cb = c.querySelector('.cb'); if (!cb || c.querySelector('.cmore')) return; const id = c.dataset.id, d = D.createElement('details'); d.className = 'cmore';
      const mk = (tag, at, tx) => { const x = D.createElement(tag); Object.keys(at).forEach(k => x.setAttribute(k, at[k])); if (tx) x.textContent = tx; return x; };
      const row = mk('div', { class: 'cm-row', role: 'group' });
      [['data-save', T('Lưu bài', 'Save'), 'aria-pressed'], ['data-less', T('Bớt tin này', 'Show less')], ['data-hide', T('Ẩn', 'Hide')], ['data-cshare', T('Chia sẻ', 'Share')]].forEach(b => {
        const at = { class: 'ca', type: 'button', 'data-id': id }; at[b[0]] = ''; if (b[2]) at['aria-pressed'] = 'false'; row.append(mk('button', at, b[1])); });
      d.append(mk('summary', { 'aria-label': T('Thao tác với bài này', 'Actions for this story') }, '⋯'), row);
      cb.append(d);
    });
    profMut(p => { const H = new Set(p.hidden || []); if (H.size) D.querySelectorAll('.card[data-id]').forEach(c => { if (H.has(c.dataset.id)) c.hidden = true; }); });
  }
  function cardAct(e) {
    const t = e.target.closest && e.target.closest('.ca[data-less],[data-hide],[data-cshare]'); if (!t) return false;
    const c = t.closest('.card[data-id]'), id = t.dataset.id;
    if (t.hasAttribute('data-less')) { t.textContent = T('Đã bớt ✓', 'Done ✓'); t.disabled = true; return false; }   // để app.js ghi tín hiệu
    if (t.hasAttribute('data-hide')) {
      if (c) c.hidden = true; profMut(p => { if (!(p.hidden || (p.hidden = [])).includes(id)) p.hidden.push(id); });
      toast(T('Đã ẩn bài này.', 'Story hidden.'), { undo: () => { if (c) c.hidden = false; profMut(p => { p.hidden = (p.hidden || []).filter(x => x !== id); }); }, undoLabel: T('Hoàn tác', 'Undo') }); return true;
    }
    const a = c && c.querySelector('h3 a'); if (!a) return true; const data = { title: a.textContent.trim(), url: a.href };
    if (navigator.share) navigator.share(data).catch(() => {});
    else if (navigator.clipboard) navigator.clipboard.writeText(data.url).then(() => toast(T('Đã chép liên kết.', 'Link copied.')), () => toast(T('Không chép được liên kết.', "Couldn't copy the link.")));
    else toast(T('Trình duyệt này không hỗ trợ chia sẻ.', "This browser can't share."));
    return true;
  }
  // ---- Luồng đọc: nhớ bài + vị trí cuộn theo số báo; thanh "Tiếp tục đọc" ở đầu trang chủ ----
  const FK = () => RT.flow.key(pid()), gen = () => $('[data-general]');
  function rememberCard(c) { const l = c && $('h3 a', c); try { RT.flow.save(localStorage, FK(), { d: today(), id: c.dataset.id, t: l ? l.textContent : '', y: scrollY }); } catch (e) {} }
  if (gen()) {
    let tm = 0; addEventListener('scroll', () => { clearTimeout(tm); tm = setTimeout(() => { const cs = cards().filter(x => !x.hidden), i = RT.flow.firstVisible(cs.map(x => x.getBoundingClientRect()), 60); if (i >= 0 && scrollY > 200) rememberCard(cs[i]); }, 400); }, { passive: true });
    const f = RT.flow.load(localStorage, FK(), today());
    if (f && scrollY < 200) {
      const bar = el('p', 'resume'); bar.setAttribute('role', 'status');
      bar.append(el('span', '', T('Tiếp tục đọc: ', 'Continue reading: ') + (f.t ? '“' + f.t + '”' : '')),
        btn(T('Tiếp tục', 'Resume'), () => { const c = f.id && $('.card[data-id="' + CSS.escape(f.id) + '"]'); if (c) c.scrollIntoView({ block: 'center', behavior: RM ? 'auto' : 'smooth' }); else scrollTo({ top: f.y, behavior: RM ? 'auto' : 'smooth' }); bar.remove(); }, {}),
        btn('✕', () => bar.remove(), { 'aria-label': T('Bỏ qua', 'Dismiss') }));
      const g = gen(); const ra = g.querySelector('.readall'); ra ? ra.after(bar) : g.prepend(bar);
    }
  }
  { let q = 0; const run = () => { q = 0; cardActs(); }; new MutationObserver(() => { if (!q) q = setTimeout(run, 150); }).observe(D.body, { childList: true, subtree: true }); cardActs(); }
  window.PressUI = api;
  D.addEventListener('click', api.click); D.addEventListener('keydown', api.key);
  D.addEventListener('keydown', e => { const m = e.key === 'Escape' && !e.defaultPrevented && D.querySelector('details.menu[open]'); if (m) { m.open = false; m.querySelector('summary').focus(); } });
  window.PressToast = toast;
  if (lang === 'en') loadLang().then(() => applyLang());
  mePage(); overloadNote();
  new MutationObserver(() => { if (lang === 'en') applyLang(); }).observe(D.body, { childList: true, subtree: true });
  // Nút "Theo dõi chủ đề" (topic-<id>.html): bật/tắt w[chủ đề] trong hồ sơ đang chọn — cùng cơ chế với chip ở picker
  const fb = $('[data-follow-topic]'), PRK = window.PressRank;
  if (fb && PP && PRK) {
    const t = fb.dataset.followTopic, db = PP.open(), msg = $('[data-follow-msg]');
    const cur = () => { const id = db.active() || 'me'; return { id, p: PRK.ensure(db.load(id) || PRK.newProfile(null, [])) }; };
    const draw = () => { const on = !!cur().p.w[t]; fb.setAttribute('aria-pressed', String(on)); fb.textContent = on ? 'Đang theo dõi ✓' : 'Theo dõi chủ đề'; };
    fb.hidden = false; draw();
    const flip = on => { const m = cur(); if (on) m.p.w[t] = PRK.newProfile(null, [t]).w[t]; else delete m.p.w[t]; db.save(m.id, m.p); draw(); };
    fb.addEventListener('click', () => {
      const was = !!cur().p.w[t], snap = was ? cur().p.w[t] : null;
      const say = m => { if (msg) msg.textContent = m; };
      if (FBK) FBK.optimistic({ apply: () => { fb.setAttribute('aria-pressed', String(!was)); fb.textContent = !was ? 'Đang theo dõi ✓' : 'Theo dõi chủ đề'; }, commit: () => { flip(!was); return !!cur().p.w[t] === !was; }, revert: draw, onError: () => { say('Không lưu được. Đã giữ nguyên.'); toast('Không lưu được. Đã giữ nguyên như cũ.'); } }).then(ok => { if (!ok) return; say(was ? 'Đã bỏ theo dõi.' : 'Đã thêm vào hồ sơ của bạn.'); toast(was ? 'Đã bỏ theo dõi chủ đề.' : 'Đã theo dõi chủ đề.', { undo: () => { const m = cur(); if (was) m.p.w[t] = snap; else delete m.p.w[t]; db.save(m.id, m.p); draw(); say(''); } }); });
      else { flip(!was); say(was ? 'Đã bỏ theo dõi.' : 'Đã thêm vào hồ sơ của bạn.'); }
    });
  }
})();

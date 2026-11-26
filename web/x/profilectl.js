/* Điều khiển hồ sơ đọc: lõi thuần (setLevel/setTopic/setSource/resetTaste/xuất-nhập JSON) + UI tab 'Bộ nhớ' → 'Hồ sơ đọc của tôi'.
   Nạp lười qua x/ui.js (không tính vào ngân sách JS đầu trang). Mọi chữ hiển thị bằng textContent. */
(function (root) {
  const R = typeof module !== 'undefined' ? require('../rank.js') : root.PressRank;
  function setLevel(p, lv) { ensure(p); if (!LEVELS[lv]) return false; p.pz = lv; return true; }
  // Bật/tắt theo dõi một chủ đề. Tắt = giữ điểm nhưng không tính (off); bật lại khôi phục. Chủ đề chưa có mà bật → thêm mới.
  function setTopic(p, t, on, now) {
    ensure(p); if (!t || typeof t !== 'string') return false;
    if (!p.w[t]) { if (!on) return false; p.w[t] = { v: 1, l: 0, t: now || Date.now() }; return true; }
    if (on) delete p.w[t].off; else p.w[t].off = true;
    return true;
  }
  // mode: 'less' (giảm) | 'hide' (ẩn) | null (bình thường)
  function setSource(p, s, mode) {
    ensure(p); if (!s || typeof s !== 'string') return false;
    if (mode === 'less' || mode === 'hide') p.sm[s] = mode; else delete p.sm[s];
    return true;
  }
  // Chế độ đọc theo hồ sơ: cỡ chữ sm|md|lg, chỉ tiêu đề. Giá trị lạ bị bỏ qua.
  const FS = ['sm', 'md', 'lg'];
  // Chuẩn hoá p.view (hồ sơ cũ chưa có → md, không chỉ tiêu đề). Nằm ở đây (nạp lười) để không tăng JS đầu trang.
  function getView(p) { const v = p && p.view && typeof p.view === 'object' ? p.view : {}; return { fs: FS.includes(v.fs) ? v.fs : 'md', titles: v.titles === true }; }
  function setView(p, v) { ensure(p); if (!v || typeof v !== 'object') return false; const n = getView(p); if (FS.includes(v.fs)) n.fs = v.fs; if (typeof v.titles === 'boolean') n.titles = v.titles; p.view = n; return true; }
  // Đặt lại: xoá gu (chủ đề, nguồn, khám phá, thống kê, mức) — giữ bài đã lưu và vai trò/ban.
  function resetTaste(p) {
    ensure(p); p.w = {}; p.bandit = {}; p.src = {}; p.sm = {}; p.hidden = []; p.explored = {}; p.stats = newStats(); p.pz = 'mid'; delete p.adapt; return p;
  }
  const FMT = 'press-profile', LEVELS = R.LEVELS, ensure = R.ensure, newProfile = R.newProfile, newStats = R.newStats;
  function exportProfile(p) { ensure(p); return JSON.stringify({ format: FMT, v: 1, profile: p }, null, 1); }
  // Nhập: kiểm cấu trúc, ép kiểu, bỏ trường lạ. Trả {profile} hoặc {error}.
  function importProfile(text) {
    let o; try { if (typeof text !== 'string' || text.length > 400000) throw 0; o = JSON.parse(text); } catch (e) { return { error: 'Tệp không phải JSON hợp lệ.' }; }
    const q = o && o.format === FMT && o.v === 1 && o.profile;
    if (!q || typeof q !== 'object' || !q.w || typeof q.w !== 'object' || Array.isArray(q.w)) return { error: 'Không phải tệp hồ sơ đọc.' };
    const num = x => (typeof x === 'number' && isFinite(x) ? x : 0), strs = a => (Array.isArray(a) ? a.filter(x => typeof x === 'string').slice(0, 2000) : []);
    const p = newProfile(typeof q.desk === 'string' ? q.desk : null, [], 0, { role: typeof q.role === 'string' ? q.role : null, density: q.density });
    Object.keys(q.w).slice(0, 500).forEach(t => { const e = q.w[t]; if (!e || typeof e !== 'object') return; p.w[t] = { v: num(e.v), l: num(e.l), t: num(e.t) }; if (e.off) p.w[t].off = true; if (e.blocked) p.w[t].blocked = true; if (e.main) p.w[t].main = true; });
    if (q.view && typeof q.view === 'object') setView(p, q.view);
    p.saved = strs(q.saved); p.hidden = strs(q.hidden);
    if (q.src && typeof q.src === 'object') Object.keys(q.src).slice(0, 500).forEach(s => { p.src[s] = num(q.src[s]); });
    if (q.sm && typeof q.sm === 'object') Object.keys(q.sm).slice(0, 500).forEach(s => { if (q.sm[s] === 'less' || q.sm[s] === 'hide') p.sm[s] = q.sm[s]; });
    if (q.bandit && typeof q.bandit === 'object') Object.keys(q.bandit).slice(0, 500).forEach(t => { const b = q.bandit[t]; if (b && num(b.a) > 0 && num(b.b) > 0) p.bandit[t] = { a: b.a, b: b.b }; });
    if (LEVELS[q.pz]) p.pz = q.pz;
    if (q.stats && typeof q.stats === 'object') Object.keys(p.stats).forEach(k => { if (k !== 'days' && typeof q.stats[k] === 'number' && isFinite(q.stats[k])) p.stats[k] = q.stats[k]; });
    if (q.stats && q.stats.days && typeof q.stats.days === 'object') Object.keys(q.stats.days).slice(0, 400).forEach(k => { if (/^\d{4}-\d\d-\d\d$/.test(k)) p.stats.days[k] = num(q.stats.days[k]); });
    ['first', 'last'].forEach(k => { if (q.stats && /^\d{4}-\d\d-\d\d$/.test(q.stats[k])) p.stats[k] = q.stats[k]; });
    return { profile: ensure(p) };
  }
   // xoá sở thích = bỏ hồ sơ, về mặc định


  const api = { getView, setView, setLevel, setTopic, setSource, resetTaste, exportProfile, importProfile };
  if (typeof module !== 'undefined') { module.exports = api; return; }
  root.PressProfileCtl = api;
  const D = root.document, wire = () => {
    const rootEl = D.querySelector('[data-pc]'); if (!rootEl || rootEl.dataset.on) return;
    const PP = root.PressProfiles, PR = root.PressRank, PC = api; if (!PP || !PR) { root.addEventListener('load', wire, { once: true }); return; }
    rootEl.dataset.on = '1';
    const window = root, root_ = rootEl;

  const db = PP.open(), id = db.active() || 'me', $ = s => root_.querySelector(s);
  const msg = t => { $('[data-pc-msg]').textContent = t; };
  const load = () => PR.ensure(db.load(id) || PR.newProfile(null, []));
  const save = p => db.save(id, p);
  const el = (t, props, ...kids) => { const x = D.createElement(t); Object.assign(x, props || {}); x.append(...kids); return x; };
  const NOTE = { low: 'Ít: ưu tiên bài chung và khám phá (khoảng 30% là chủ đề mới), sở thích chỉ nhẹ tay.', mid: 'Vừa: cân bằng, khoảng 15% là chủ đề mới.', high: 'Nhiều: bám sát sở thích của bạn, chỉ khoảng 7% là chủ đề mới.' };
  const KEYS = ['low', 'mid', 'high'], NAME = { low: 'Ít', mid: 'Vừa', high: 'Nhiều' };
  let data = null; const focus = new URLSearchParams(location.search).get('topic');
  const tl = t => (data && data.topics && data.topics[t] && data.topics[t].label) || t;

  function paint() {
    const p = load();
    const sl = $('[data-pc-level]'); sl.value = String(Math.max(0, KEYS.indexOf(p.pz)));
    sl.setAttribute('aria-valuetext', NAME[p.pz]); $('[data-pc-level-note]').textContent = NOTE[p.pz];
    const ul = $('[data-pc-topics]'); ul.textContent = '';
    const ts = Object.keys(p.w).sort((a, b) => ((p.w[b].v || 0) + (p.w[b].l || 0)) - ((p.w[a].v || 0) + (p.w[a].l || 0)) || a.localeCompare(b));
    if (!ts.length) ul.append(el('li', { textContent: 'Chưa theo dõi chủ đề nào. Đọc vài bài hoặc chọn ở “đổi người đọc / chủ đề”.' }));
    ts.forEach(t => {
      const cb = el('input', { type: 'checkbox', id: 'pct-' + t, checked: !p.w[t].off }), lb = el('label', { htmlFor: cb.id, textContent: tl(t) }), li = el('li', { className: 'pc-row' }, cb, lb);
      li.dataset.topic = t; if (p.w[t].off) li.dataset.off = '1'; if (t === focus) li.dataset.focus = '1';
      cb.addEventListener('change', () => { const q = load(); PC.setTopic(q, t, cb.checked); save(q); msg((cb.checked ? 'Đã bật theo dõi “' : 'Đã tắt theo dõi “') + tl(t) + '”.'); paint(); const n = $('[data-topic="' + t + '"] input'); if (n) n.focus(); });
      ul.append(li);
    });
    const sul = $('[data-pc-sources]'); sul.textContent = '';
    const names = new Set(Object.keys(p.src).concat(Object.keys(p.sm)));
    if (data) { const c = {}; (data.articles || []).forEach(a => { if (a.source) c[a.source] = (c[a.source] || 0) + 1; }); Object.keys(c).sort((a, b) => c[b] - c[a]).slice(0, 12).forEach(s => names.add(s)); }
    if (!names.size) sul.append(el('li', { textContent: 'Chưa có nguồn nào để chỉnh.' }));
    [...names].sort().forEach(s => {
      const sel = el('select', { id: 'pcs-' + s }); [['', 'Bình thường'], ['less', 'Giảm'], ['hide', 'Ẩn']].forEach(o => sel.append(el('option', { value: o[0], textContent: o[1] }))); sel.value = p.sm[s] || '';
      sel.addEventListener('change', () => { const q = load(); PC.setSource(q, s, sel.value || null); save(q); msg('Nguồn “' + s + '”: ' + sel.options[sel.selectedIndex].textContent + '.'); paint(); });
      sul.append(el('li', { className: 'pc-row' }, el('label', { htmlFor: sel.id, textContent: s }), sel));
    });
    const f = ul.querySelector('[data-focus]'); if (f && !paint.done) { paint.done = 1; f.scrollIntoView && f.scrollIntoView({ block: 'center' }); f.querySelector('input').focus(); }
  }
  $('[data-pc-level]').addEventListener('input', e => { const q = load(); PC.setLevel(q, KEYS[+e.target.value] || 'mid'); save(q); msg('Mức cá nhân hoá: ' + NAME[q.pz] + '.'); paint(); });
  const applyView = v => { const R_ = D.documentElement; R_.dataset.fs = v.fs; if (v.titles) R_.dataset.titles = '1'; else delete R_.dataset.titles; };
  const paintView = () => { const v = PC.getView(load()); $('[data-pc-view]').querySelectorAll('[data-fs]').forEach(b => b.setAttribute('aria-pressed', b.dataset.fs === v.fs ? 'true' : 'false')); $('[data-pc-titles]').checked = v.titles; applyView(v); };
  $('[data-pc-view]').addEventListener('click', e => { const b = e.target.closest('[data-fs]'); if (!b) return; const q = load(); PC.setView(q, { fs: b.dataset.fs }); save(q); paintView(); msg('Cỡ chữ: ' + b.textContent + '.'); });
  $('[data-pc-titles]').addEventListener('change', e => { const q = load(); PC.setView(q, { titles: e.target.checked }); save(q); paintView(); msg(e.target.checked ? 'Chỉ hiện tiêu đề.' : 'Hiện đầy đủ thẻ bài.'); });
  paintView();
  $('[data-pc-reset]').addEventListener('click', () => { if (!confirm('Đặt lại gu đọc (chủ đề, nguồn, mức cá nhân hoá)? Bài đã lưu được giữ.')) return; const q = load(); PC.resetTaste(q); save(q); msg('Đã đặt lại hồ sơ đọc.'); paint(); });
  $('[data-pc-export]').addEventListener('click', () => { const a = el('a', { href: URL.createObjectURL(new Blob([PC.exportProfile(load())], { type: 'application/json' })), download: 'ban-tin-ho-so-doc.json' }); a.click(); msg('Đã tải hồ sơ đọc.'); });
  $('[data-pc-import]').addEventListener('change', e => { const f = e.target.files[0]; if (!f) return; f.text().then(t => { const r = PC.importProfile(t); if (r.error) { msg(r.error); return; } save(r.profile); msg('Đã nhập hồ sơ đọc.'); paint(); }); e.target.value = ''; });
  (window.PressData || Promise.resolve(null)).then(d => { data = d; paint(); });
  paint();
  };
  if (D) { if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', wire); else wire(); }
})(typeof self !== 'undefined' ? self : this);

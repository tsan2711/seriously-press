// Tìm kiếm tức thì — lõi thuần (không DOM, không mạng) để test bằng node; chạy cục bộ trên public/search.json.
// Hàng: [id, tiêu đề, url, nguồn, ngày, [chủ đề], ban, đoạn trích, engagement(0-100)]. Trần 5k bài <100 ms (tests/test_search.py).
(function (root) {
  const R = { id: 0, t: 1, u: 2, s: 3, d: 4, k: 5, b: 6, x: 7, e: 8, sid: 9 };
  const fold = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/đ/g, 'd');
  const toks = q => fold(q).split(/[^a-z0-9.+#]+/).filter(Boolean).slice(0, 6);
  function build(rows) { return { rows, n: rows.map(r => ' ' + fold(r[R.t]) + ' ' + fold(r[R.x]) + ' ' + fold(r[R.s])), nt: rows.map(r => ' ' + fold(r[R.t])) }; }
  // lọc: {topic, desk, source, from, to}; kết quả: [{r, score, snip:[trước, khớp, sau]}] — hiển thị bằng textContent, không innerHTML
  function search(ix, q, f, lim) {
    f = f || {}; lim = lim || 30; const T = toks(q), out = [];
    for (let i = 0; i < ix.rows.length; i++) {
      const r = ix.rows[i];
      if (f.topic && !(r[R.k] || []).includes(f.topic)) continue;
      if (f.desk && r[R.b] !== f.desk) continue;
      if (f.source && r[R.s] !== f.source) continue;
      if (f.from && r[R.d] < f.from) continue;
      if (f.to && r[R.d] > f.to) continue;
      let sc = 0, ok = true;
      for (const t of T) { if (ix.nt[i].includes(' ' + t)) sc += 5; else if (ix.n[i].includes(' ' + t)) sc += 2; else if (ix.n[i].includes(t)) sc += 1; else { ok = false; break; } }
      if (!ok) continue;
      sc += (r[R.e] || 0) / 50 + (r[R.d] > '2000' ? (Date.parse(r[R.d]) - 1.7e12) / 1e11 : 0);
      out.push({ r, score: sc });
    }
    out.sort((a, b) => b.score - a.score); const top = out.slice(0, lim);
    top.forEach(o => { o.snip = snippet(o.r[R.x] || o.r[R.t], T); });
    return top;
  }
  function snippet(text, T) {
    text = String(text || ''); if (!T.length) return [text.slice(0, 120), '', ''];
    const ft = fold(text); let at = -1, len = 0;
    for (const t of T) { const k = ft.indexOf(t); if (k >= 0 && (at < 0 || k < at)) { at = k; len = t.length; } }   // fold giữ độ dài (NFD bỏ dấu 1-1 với chữ thường VN trừ vài ca hiếm → chặn bằng min)
    if (at < 0) return [text.slice(0, 120), '', ''];
    const a = Math.max(0, at - 40); return [(a ? '…' : '') + text.slice(a, at), text.slice(at, at + len), text.slice(at + len, at + len + 80)];
  }
  const facets = ix => { const c = { topics: {}, sources: {}, desks: {} }; ix.rows.forEach(r => { (r[R.k] || []).forEach(k => c.topics[k] = (c.topics[k] || 0) + 1); c.sources[r[R.s]] = (c.sources[r[R.s]] || 0) + 1; if (r[R.b]) c.desks[r[R.b]] = (c.desks[r[R.b]] || 0) + 1; }); return c; };

  // ---- Bảng lệnh (palette): lõi thuần, test bằng node (tests/test_search_palette.py) ----
  // Tô sáng: [[chuỗi, khớp?], …] — dò trên bản bỏ dấu nhưng cắt trên chuỗi gốc (map từng ký tự, không lệch vị trí); UI chỉ nối textContent/<mark>.
  function segments(text, T) {
    text = String(text || ''); if (!T || !T.length) return [[text, false]];
    let f = '', map = []; for (let i = 0; i < text.length; i++) { const c = fold(text[i]); for (let j = 0; j < c.length; j++) { f += c[j]; map.push(i); } }
    const hit = new Array(text.length).fill(false);
    for (const t of T) { if (!t) continue; for (let k = f.indexOf(t); k >= 0; k = f.indexOf(t, k + 1)) for (let j = k; j < k + t.length; j++) hit[map[j]] = true; }
    const out = []; for (let i = 0; i < text.length; i++) { if (out.length && out[out.length - 1][1] === hit[i]) out[out.length - 1][0] += text[i]; else out.push([text[i], hit[i]]); }
    return out;
  }
  // khoảng cách sửa ≤ 1 (thêm/bớt/đổi/đảo 2 ký tự kề nhau)
  function near(a, b) {
    if (a === b) return true; const la = a.length, lb = b.length; if (Math.abs(la - lb) > 1) return false;
    let i = 0; while (i < la && i < lb && a[i] === b[i]) i++;
    if (la === lb) return a.slice(i + 1) === b.slice(i + 1) || (a[i] === b[i + 1] && a[i + 1] === b[i] && a.slice(i + 2) === b.slice(i + 2));
    return la > lb ? a.slice(i + 1) === b.slice(i) : b.slice(i + 1) === a.slice(i);
  }
  // Tìm gần đúng: mỗi từ khoá (≥4 ký tự) khớp 1 từ trong tiêu đề/nguồn sai lệch ≤1 ký tự, hoặc khớp chuỗi con như search(). Chỉ gọi khi tìm chặt ra rỗng.
  function fuzzy(ix, q, f, lim) {
    f = f || {}; lim = lim || 30; const T = toks(q), out = []; if (!T.length) return out;
    for (let i = 0; i < ix.rows.length; i++) {
      const r = ix.rows[i];
      if (f.topic && !(r[R.k] || []).includes(f.topic)) continue; if (f.desk && r[R.b] !== f.desk) continue; if (f.source && r[R.s] !== f.source) continue;
      if (f.from && r[R.d] < f.from) continue; if (f.to && r[R.d] > f.to) continue;
      const words = ix.n[i].split(/[^a-z0-9.+#]+/); let sc = 0, ok = true;
      for (const t of T) { if (ix.n[i].includes(t)) sc += 2; else if (t.length >= 4 && words.some(w => near(t, w))) sc += 1; else { ok = false; break; } }
      if (ok) out.push({ r, score: sc + (r[R.e] || 0) / 50 });
    }
    out.sort((a, b) => b.score - a.score); const top = out.slice(0, lim); top.forEach(o => { o.snip = snippet(o.r[R.x] || o.r[R.t], T); o.fuzzy = true; }); return top;
  }
  // Kết quả theo nhóm: {articles, topics, desks, fuzzy}. meta = {topics:{id:tên}, desks:{id:tên}}; chủ đề/ban khớp theo id hoặc tên (bỏ dấu, tiền tố từ).
  function groups(ix, q, f, meta, lim) {
    meta = meta || {}; const T = toks(q); let articles = search(ix, q, f, lim || 12), isFuzzy = false;
    if (!articles.length && T.length) { articles = fuzzy(ix, q, f, lim || 12); isFuzzy = articles.length > 0; }
    const pick = m => T.length ? Object.keys(m || {}).filter(id => { const h = ' ' + fold(id.replace(/-/g, ' ')) + ' ' + fold(m[id]); return T.every(t => h.includes(' ' + t)); }).map(id => ({ id, name: m[id] })) : [];
    return { articles, topics: pick(meta.topics).slice(0, 5), desks: pick(meta.desks).slice(0, 5), fuzzy: isFuzzy };
  }
  // 5 truy vấn gần nhất, mới nhất trước; bỏ rỗng/<2 ký tự; trùng (không phân biệt dấu/hoa) → đưa lên đầu
  function pushRecent(list, q, max) {
    q = String(q || '').trim().replace(/\s+/g, ' '); const out = Array.isArray(list) ? list.filter(x => typeof x === 'string') : [];
    if (q.length < 2) return out.slice(0, max || 5); const k = fold(q);
    return [q].concat(out.filter(x => fold(x) !== k)).slice(0, max || 5);
  }
  // Gợi ý khi ô trống: chủ đề đang theo dõi (w của hồ sơ) xếp theo trọng số giảm dần, chỉ giữ chủ đề có trong meta
  function followedTopics(w, meta, lim) {
    return Object.keys(w || {}).filter(id => (meta || {})[id]).sort((a, b) => ((w[b] && w[b].v) || +w[b] || 0) - ((w[a] && w[a].v) || +w[a] || 0)).slice(0, lim || 5).map(id => ({ id, name: meta[id] }));
  }
  // Phím mở hộp tìm: Ctrl/⌘+K luôn mở (kể cả đang gõ); "/" chỉ khi KHÔNG đang gõ, không phím bổ trợ, không đang có hộp thoại, không đang soạn IME
  function wantsOpen(e, st) {
    st = st || {}; const k = e.key || '';
    if ((e.ctrlKey || e.metaKey) && !e.altKey && k.toLowerCase() === 'k') return 'toggle';
    if (k === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !e.isComposing && !st.typing && !st.dialog) return 'open';
    return '';
  }
  // Đích Enter/mũi tên: chỉ số kế tiếp trong danh sách vòng (−1 = chưa chọn)
  const step = (i, n, dir) => n ? (i < 0 ? (dir > 0 ? 0 : n - 1) : (i + dir + n) % n) : -1;
  const api = { R, fold, toks, build, search, snippet, facets, segments, near, fuzzy, groups, pushRecent, followedTopics, wantsOpen, step };
  if (typeof module !== 'undefined') module.exports = api; else root.PressSearch = api;
})(typeof self !== 'undefined' ? self : this);

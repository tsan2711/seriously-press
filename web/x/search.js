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
  const api = { R, fold, toks, build, search, snippet, facets };
  if (typeof module !== 'undefined') module.exports = api; else root.PressSearch = api;
})(typeof self !== 'undefined' ? self : this);

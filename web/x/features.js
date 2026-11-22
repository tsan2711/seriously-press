// Tính năng tự cân nhắc (U5) — lõi thuần, không DOM/mạng: Tóm 60 giây · Theo dõi câu chuyện · Digest tuần · Xuất/nhập hồ sơ bằng tệp.
// Lý do chọn: plan-ux.md §U5. Dữ liệu cá nhân chỉ ở localStorage; tệp xuất KHÔNG chứa khoá API.
(function (root) {
  const words = s => (String(s || '').match(/\S+/g) || []).length;
  // ---- Tóm 60 giây: chọn bài đầu theo thứ tự đã xếp hạng tới khi hết ngân sách đọc (≈3,3 từ/giây), mỗi bài 1 dòng ≤ 90 ký tự
  function brief60(arts, opt) {
    opt = opt || {}; const budget = opt.seconds || 60, wps = 3.3, max = opt.max || 6, out = []; let used = 0;
    const seenT = new Set();
    for (const a of arts || []) {
      const title = String(a.title || a.t || '').trim(); if (!title) continue;
      const tp = (a.topics && a.topics[0]) || ''; if (tp && seenT.has(tp) && out.length >= 3) continue;   // đa dạng chủ đề
      let line = title.length > 90 ? title.slice(0, 89).replace(/\s+\S*$/, '') + '…' : title;
      const sum = String(a.summary || a.x || '').trim(), extra = sum && out.length < 3 ? sum.slice(0, 80).replace(/\s+\S*$/, '') : '';
      const cost = (words(line) + words(extra)) / wps + 1;
      if (used + cost > budget || out.length >= max) { if (out.length >= 3) break; else continue; }
      used += cost; seenT.add(tp); out.push({ id: a.id, title: line, extra, url: a.url || a.u, source: a.source || a.s, secs: Math.round(cost) });
    }
    return { items: out, secs: Math.round(used) };
  }
  // ---- Theo dõi: stories = {sid:[[ngày,tiêu đề,nguồn,url],…]}; follow = [{sid,at(ngày),n(số mục lúc theo dõi)}]
  const timeline = (stories, sid) => ((stories || {})[sid] || []).map(x => ({ d: x[0], t: x[1], s: x[2], u: x[3] })).sort((a, b) => a.d < b.d ? 1 : -1);
  function follow(list, sid, stories, today) {
    list = (list || []).filter(x => x.sid !== sid); const n = ((stories || {})[sid] || []).length;
    list.unshift({ sid: String(sid).slice(0, 32), at: today, n }); return list.slice(0, 40);
  }
  const unfollow = (list, sid) => (list || []).filter(x => x.sid !== sid);
  function followUpdates(list, stories) { return (list || []).map(f => { const tl = timeline(stories, f.sid); return { sid: f.sid, n: tl.length, fresh: Math.max(0, tl.length - (f.n || 0)), last: tl[0] || null, title: tl.length ? tl[tl.length - 1].t : f.sid }; }).sort((a, b) => b.fresh - a.fresh); }
  // ---- Digest tuần: rows kiểu search.json; lấy ≤ n bài, ≤ 2/chủ đề, trong 7 ngày kết thúc ở `today`
  function digest(rows, today, n) {
    n = n || 8; const to = Date.parse(today), from = new Date(to - 6 * 864e5).toISOString().slice(0, 10), per = {}, seen = new Set(), out = [];
    const cand = (rows || []).filter(r => r[4] >= from && r[4] <= today).sort((a, b) => (b[8] || 0) - (a[8] || 0) || (a[4] < b[4] ? 1 : -1));
    for (const r of cand) { const k = (r[5] || [])[0] || '_', key = r[1].toLowerCase().slice(0, 40); if (seen.has(key) || (per[k] || 0) >= 2) continue; seen.add(key); per[k] = (per[k] || 0) + 1; out.push(r); if (out.length >= n) break; }
    return { from, to: today, rows: out };
  }
  // ---- Xuất/nhập hồ sơ qua tệp (đổi máy). Chỉ khoá press.* ; loại khoá bí mật; nhập = hợp nhất, không ghi đè khoá bí mật
  const SECRET = /key|token|secret|pass/i, OK = /^press\.[\w.\-]{1,80}$/, MAXV = 400000, MAXK = 200;
  function exportProfile(store, now) {
    const data = {}; for (const k of Object.keys(store || {})) if (OK.test(k) && !SECRET.test(k) && String(store[k]).length <= MAXV) data[k] = String(store[k]);
    return JSON.stringify({ press: 'profile', v: 1, at: new Date(now || Date.now()).toISOString(), data });
  }
  function importProfile(text, store) {
    let o; try { o = JSON.parse(text); } catch (e) { return { ok: false, err: 'Tệp không đọc được.' }; }
    if (!o || o.press !== 'profile' || o.v !== 1 || typeof o.data !== 'object' || !o.data) return { ok: false, err: 'Không phải tệp hồ sơ Bản Tin.' };
    let n = 0, skip = 0; const ks = Object.keys(o.data);
    if (ks.length > MAXK) return { ok: false, err: 'Tệp quá nhiều mục.' };
    for (const k of ks) { const v = o.data[k]; if (!OK.test(k) || SECRET.test(k) || typeof v !== 'string' || v.length > MAXV) { skip++; continue; } store[k] = v; n++; }
    return { ok: true, n, skip };
  }
  const api = { brief60, timeline, follow, unfollow, followUpdates, digest, exportProfile, importProfile };
  if (typeof module !== 'undefined') module.exports = api; else root.PressFeatures = api;
})(typeof self !== 'undefined' ? self : this);

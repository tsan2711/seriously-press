// Xếp hạng + khám phá cục bộ (spec §1). Thuần hàm, dùng chung trình duyệt và test node. Hồ sơ chỉ ở localStorage.
(function (root) {
  const SIGNAL = { like: 1, save: 1.5, more: 1, hide: -2, less: -1.5, open: 0.2, skip: -0.04, dwell: 0.4, rate: 0 };
  // Gu có hai thang thời gian: ngắn (21 ngày, bắt sở thích nhất thời) + dài (180 ngày, giữ sở thích bền). Lâu ngày thì phần dài thắng.
  const HALF_LIFE_DAYS = 21, LT_HALF_DAYS = 180, LT_W = 0.3, PROMOTE = 2.5, PAGE = 24, EXPLORE_FRAC = 0.15;   // luôn ~15% khám phá: chống bong bóng lọc
  const SKIP_FLOOR = -0.4;
  const PAGES = { compact: 12, normal: 24, rich: 40 };
  const day = 86400000;

  // Hồ sơ v2: + role, density, src (nguồn hay mở), stats (bộ đo). extra = {role, density}.
  function newProfile(desk, interests, now, extra) {
    const p = { v: 2, desk: desk || null, role: null, density: 'normal', w: {}, bandit: {}, saved: [], hidden: [], explored: {}, src: {}, stats: newStats() };
    if (extra) { if (extra.role) p.role = extra.role; if (PAGES[extra.density]) p.density = extra.density; }
    (interests || []).forEach(t => { p.w[t] = { v: 1, l: 0, t: now || Date.now() }; });
    return p;
  }
  function newStats() { return { open: 0, skip: 0, like: 0, save: 0, hide: 0, less: 0, dwell_s: 0, rate_n: 0, rate_sum: 0, first: null, last: null, days: {} }; }
  // Hồ sơ cũ (v1) → v2, không mất dữ liệu.
  function ensure(p) {
    if (!p) return p;
    if (!p.role) p.role = null; if (!PAGES[p.density]) p.density = 'normal';
    p.src = p.src || {}; p.stats = Object.assign(newStats(), p.stats || {}); p.v = 2;
    return p;
  }
  function decay(x, t, half, now) { return x * Math.pow(0.5, ((now || Date.now()) - t) / (half * day)); }
  function parts(p, t, now) {
    const e = p.w[t]; if (!e) return { s: 0, l: 0 };
    return { s: decay(e.v, e.t, HALF_LIFE_DAYS, now), l: decay(e.l || 0, e.t, LT_HALF_DAYS, now) };
  }
  function weight(p, t, now) { const x = parts(p, t, now); return x.s + LT_W * x.l; }
  function bump(p, t, d, now) {
    now = now || Date.now();
    const x = parts(p, t, now);
    p.w[t] = { v: x.s + d, l: x.l + Math.max(d, 0), t: now };   // phần dài chỉ tích luỹ tín hiệu dương; phản đối chỉ ăn vào phần ngắn
  }
  // Beta(a,b) mẫu — Thompson sampling (Gamma qua Marsaglia-Tsang, rng() ∈ [0,1))
  function gauss(rng) { let u = 0, v = 0; while (!u) u = rng(); v = rng(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v); }
  function gamma(k, rng) {
    if (k < 1) return gamma(k + 1, rng) * Math.pow(rng() || 1e-9, 1 / k);
    const d = k - 1 / 3, c = 1 / Math.sqrt(9 * d);
    for (;;) {
      let x = gauss(rng), v = 1 + c * x; if (v <= 0) continue; v = v * v * v;
      const u = rng() || 1e-9;
      if (Math.log(u) < 0.5 * x * x + d - d * v + d * Math.log(v)) return d * v;
    }
  }
  function beta(a, b, rng) { const x = gamma(a, rng), y = gamma(b, rng); return x / (x + y); }

  function baseScore(a, p, now, ew) {
    let s = 0;
    (a.topics || []).forEach(t => { s += weight(p, t, now); });
    if (p.src && a.source && p.src[a.source]) s += 0.12 * Math.min(p.src[a.source], 5);   // nguồn hay mở
    s += (ew === undefined ? 1 : ew) * (a.engagement || 0) * 0.4;   // tương tác công khai (0..1), trọng số từ config; không át sở thích
    return s;
  }
  function isMain(p, t, now) { return weight(p, t, now) >= PROMOTE || (p.w[t] && p.w[t].main); }

  // Trả về danh sách hiển thị: [{a, explore:bool, topic?, why}]
  function rank(arts, p, topics, rng, now, opts) {
    opts = opts || {}; const hot = opts.hot || [];
    now = now || Date.now(); rng = rng || Math.random;
    const hidden = new Set(p.hidden);
    const pool = arts.filter(a => !hidden.has(a.id) && (!p.desk || (a.desks || []).includes(p.desk) || hasLiked(a, p, now)));
    const main = pool.map(a => ({ a, s: baseScore(a, p, now, opts.ew) + (opts.adj ? opts.adj(a) : 0) })).sort((x, y) => y.s - x.s);
    const page = opts.page || PAGES[p.density] || PAGE;
    const nExplore = Math.round(page * EXPLORE_FRAC);
    const likedTopics = Object.keys(p.w).filter(t => weight(p, t, now) > 0.3);
    const out = [];
    // ứng viên khám phá: chủ đề kề sở thích, bản thân chưa phải chủ đề chính
    const cand = {};
    likedTopics.forEach(t => ((topics[t] || {}).adjacent || []).forEach(n => {
      if (!isMain(p, n, now) && weight(p, n, now) > -0.5 && !(p.w[n] && p.w[n].blocked)) (cand[n] = cand[n] || new Set()).add(t);
    }));
    // chủ đề đang nóng (30 ngày) cũng là nguồn khám phá, kể cả khi chưa kề sở thích
    hot.forEach(n => { if (topics[n] && !isMain(p, n, now) && weight(p, n, now) > -0.5 && !(p.w[n] && p.w[n].blocked) && likedTopics.length) (cand[n] = cand[n] || new Set()).add(likedTopics[0]); });
    const picks = [], used = new Set();
    if (nExplore && Object.keys(cand).length) {
      for (let i = 0; i < nExplore; i++) {
        let best = null, bs = -1;
        Object.keys(cand).forEach(n => {
          const b = p.bandit[n] || { a: 1, b: 1 }, s = beta(b.a, b.b, rng);
          const has = arts.some(x => !hidden.has(x.id) && !used.has(x.id) && (x.topics || []).includes(n));
          if (has && s > bs) { bs = s; best = n; }
        });
        if (!best) break;
        const art = arts.filter(x => !hidden.has(x.id) && !used.has(x.id) && (x.topics || []).includes(best))
          .sort((x, y) => (y.points || 0) - (x.points || 0))[0];
        used.add(art.id); picks.push({ a: art, explore: true, topic: best, from: [...cand[best]][0] });
      }
    }
    const rest = main.filter(m => !used.has(m.a.id)).slice(0, page - picks.length);
    rest.forEach(m => out.push({ a: m.a, explore: false, why: (opts.explain && opts.explain(m.a)) || why(m.a, p, topics, now, opts.sp) }));
    // rải khám phá đều trong danh sách, không đặt vị trí đầu
    picks.forEach((pk, i) => {
      const pos = Math.min(out.length, Math.floor((i + 1) * page / (picks.length + 1)));
      pk.why = 'Mới với bạn: ' + ((topics[pk.topic] || {}).label || pk.topic) + (hot.includes(pk.topic) ? ' — đang được bàn tán' : ' — kề với ' + ((topics[pk.from] || {}).label || pk.from));
      out.splice(pos, 0, pk);
    });
    return out;
  }
  function hasLiked(a, p, now) { return (a.topics || []).some(t => weight(p, t, now) >= PROMOTE); }
  // sp = tổng hợp nhật ký 30 ngày (journal.span) — tuỳ chọn; có thì lý do kèm số liệu của chính bạn.
  function why(a, p, topics, now, sp) {
    const ts = (a.topics || []).filter(t => weight(p, t, now) > 0.3).sort((x, y) => weight(p, y, now) - weight(p, x, now));
    const lab = t => (topics[t] || {}).label || t;
    if (ts.length) {
      const o = sp && sp.topics[ts[0]] ? sp.topics[ts[0]].open : 0;
      return 'Vì bạn quan tâm: ' + ts.slice(0, 2).map(lab).join(', ') + (o >= 2 ? ` (đã mở ${o} bài trong 30 ngày)` : '') + (p.src && a.source && p.src[a.source] >= 2 ? ` · bạn hay mở ${a.source}` : '');
    }
    if (a.engagement >= 0.6) return 'Đang được bàn tán nhiều trên ' + (a.source || 'nguồn');
    return 'Bài nổi bật hôm nay' + (p.desk ? ' của ban' : '');
  }
  function ymd(now) { return new Date(now || Date.now()).toISOString().slice(0, 10); }
  // Cập nhật gu từ nhật ký, tối đa 1 lần/ngày/hồ sơ (idempotent theo p.adapt.last).
  // sp14 = journal.span 14 ngày TRƯỚC hôm nay. Trả {changed, notes[]}.
  function adaptDaily(p, sp14, now) {
    now = now || Date.now(); ensure(p); const today = ymd(now), notes = [];
    if (p.adapt && p.adapt.last === today) return { changed: false, notes };
    p.adapt = { last: today };
    if (!sp14 || !sp14.days) return { changed: false, notes };
    Object.keys(sp14.topics).forEach(t => {
      const x = sp14.topics[t], w = weight(p, t, now);
      if (x.skip >= 6 && x.open === 0 && w > SKIP_FLOOR + 0.02) { bump(p, t, -Math.min(0.3, w - SKIP_FLOOR), now); notes.push('hạ ' + t); }          // bị bỏ qua đều → hạ nhẹ, không bao giờ về chặn
      else if (x.open >= 2 && w < PROMOTE / 2) { bump(p, t, 0.4, now); p.w[t].emerging = today; notes.push('nổi ' + t); }   // mở đều mà gu còn thấp → chủ đề mới nổi
    });
    if (p.densityAuto !== false && sp14.days >= 3) {
      const per = sp14.n.open / sp14.days, to = per >= 8 ? 'rich' : per <= 1.5 ? 'compact' : 'normal';
      if (to !== p.density) { p.density = to; notes.push('mật độ ' + to); }
    }
    return { changed: notes.length > 0, notes };
  }
  // Thứ tự ban: vai trò đặt nền (ban đầu tiên của vai trò cao nhất), nhật ký 30 ngày cộng thêm.
  function deskOrder(p, sp30, roles, deskIds) {
    const r = ((roles || {}).role || {})[p && p.role] || {}, base = r.desks || [];
    const sc = id => (base.includes(id) ? 3 - Math.min(base.indexOf(id), 2) : 0) + (sp30 && sp30.desks[id] ? sp30.desks[id].open + 0.1 * sp30.desks[id].seen : 0);
    return deskIds.slice().sort((a, b) => sc(b) - sc(a) || deskIds.indexOf(a) - deskIds.indexOf(b));
  }
  // Phản hồi. item = phần tử từ rank() hoặc bài thô.
  // amount: dwell = số giây đọc (đạt tối đa ở 90 s); rate = số sao 1..5 (3 = trung tính).
  function feedback(p, a, signal, explored, now, amount) {
    now = now || Date.now(); ensure(p);
    let d = SIGNAL[signal]; if (d === undefined) return p;
    if (signal === 'dwell') d *= Math.min(Math.max(amount || 0, 0), 90) / 90;
    if (signal === 'rate') d = (Math.min(Math.max(amount || 3, 1), 5) - 3) * 0.6;
    const st = p.stats, k = new Date(now).toISOString().slice(0, 10);
    st.first = st.first || k; st.last = k; st.days[k] = (st.days[k] || 0) + 1;
    if (signal in st) st[signal]++;
    if (signal === 'dwell') st.dwell_s += Math.min(Math.max(amount || 0, 0), 600);
    if (signal === 'rate') { st.rate_n++; st.rate_sum += amount || 3; }
    if (d > 0 && a.source) p.src[a.source] = (p.src[a.source] || 0) + (signal === 'open' || signal === 'dwell' ? 0.5 : 1);
    if (d === 0) return p;
    (a.topics || []).forEach(t => { if (signal === 'skip' && weight(p, t, now) <= SKIP_FLOOR) return; bump(p, t, d, now); });   // bỏ qua thụ động không đẩy chủ đề xuống dưới sàn → còn cơ hội được khám phá lại
    if (signal === 'save' && !p.saved.includes(a.id)) p.saved.push(a.id);
    if (signal === 'hide' && !p.hidden.includes(a.id)) p.hidden.push(a.id);
    if (explored) {   // cập nhật bandit cho chủ đề được thử
      const t = explored, b = (p.bandit[t] = p.bandit[t] || { a: 1, b: 1 });
      if (d > 0) b.a += 1; else if (d < 0) { b.b += 1; if (signal === 'less') (p.w[t] = p.w[t] || { v: 0, t: now }).blocked = b.b >= 3; }
      if (d > 0 && weight(p, t, now) >= PROMOTE) { p.w[t].main = true; }
    }
    return p;
  }
  // Báo cáo 'gu của tôi': chủ đề top, ngắn vs dài hạn, xu hướng, số liệu bộ đo.
  function report(p, topics, now, n) {
    now = now || Date.now(); ensure(p);
    const rows = Object.keys(p.w).map(t => { const x = parts(p, t, now); return { topic: t, label: (topics[t] || {}).label || t, score: x.s + LT_W * x.l, short: x.s, long: x.l,
      trend: x.l > 0.5 && x.s < 0.15 * x.l ? 'fading' : x.s >= 1 && x.s > 0.5 * x.l ? 'rising' : 'steady' }; })
      .filter(r => r.score > 0.05).sort((a, b) => b.score - a.score).slice(0, n || 8);
    const st = p.stats, days = Object.keys(st.days).length, seen = st.open + st.skip;
    return { top: rows, days, open_rate: seen ? st.open / seen : null, avg_dwell_s: st.dwell_s && st.open ? st.dwell_s / Math.max(st.open, 1) : 0,
      avg_rating: st.rate_n ? st.rate_sum / st.rate_n : null, stats: st, sources: Object.entries(p.src).sort((a, b) => b[1] - a[1]).slice(0, 5).map(x => x[0]) };
  }
  // Theo vai trò: tạo hồ sơ khởi đầu từ cấu hình (roles.toml) — chủ đề + mật độ.
  function fromRole(roles, roleId, now) {
    const r = ((roles || {}).role || {})[roleId] || {};
    return newProfile((r.desks || [])[0] || null, r.topics || [], now, { role: roleId, density: r.density });
  }
  function reset() { return null; }   // xoá sở thích = bỏ hồ sơ, về mặc định

  const api = { adaptDaily, deskOrder, ymd, SIGNAL, PROMOTE, PAGE, PAGES, newProfile, newStats, ensure, weight, parts, rank, feedback, report, fromRole, reset, why, isMain };
  if (typeof module !== 'undefined') module.exports = api; else root.PressRank = api;
})(typeof self !== 'undefined' ? self : this);

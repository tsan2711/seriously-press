// Bộ nhớ người đọc (K4) — CỤC BỘ (localStorage 'press.mem.<người đọc>'), không gửi đi, không lên repo. Thuần hàm, test bằng node.
// Ba tầng: SHORT (hôm nay, nửa đời 1 ngày) · MID (30 ngày: chủ đề nóng/nguồn, nửa đời 14 ngày) · LONG (gu bền, vai trò, nguồn tin cậy, điều đã học; nửa đời 180 ngày).
// Mỗi mục: {id,tier,kind,key,label,s,n,days,t,user} — xem/sửa (ghim, tắt)/xoá/xuất bởi chính người đọc. Xoá = bia mộ (không tự học lại).
(function (root) {
  const DAY = 86400000, HALF = { short: 1, mid: 14, long: 180 }, KINDS = ['topic', 'source', 'habit', 'fact'];
  const MAX_ITEMS = 120, PROMOTE_S = 1.2, PROMOTE_DAYS = 5, SPAN_DAYS = 10, RECENT_DAYS = 8,   // lên tầng dài cần đọc rải ≥10 ngày VÀ còn đọc gần đây — cơn sốt 5 ngày không lọt
   DROP_S = 0.08;
  const SIG = { open: 0.35, like: 1, save: 1.2, more: 1, dwell: 0.5, rate: 0.6, skip: -0.03, less: -1, hide: -1.5 };
  const dkey = ms => new Date(ms).toISOString().slice(0, 10);
  const empty = () => ({ v: 1, items: [], tomb: [], last: null });
  const idOf = (kind, key) => kind + ':' + key;
  const strength = (it, now) => it.user && it.pin ? Math.max(it.s, 1.5) : it.s * Math.pow(0.5, Math.max(0, (now - it.t)) / (HALF[it.tier] * DAY));
  const find = (m, id) => m.items.find(x => x.id === id);
  function bump(m, tier, kind, key, label, d, now) {
    const id = idOf(kind, key); if (m.tomb.includes(id)) return;
    let it = find(m, id);
    if (!it) { it = { id, tier, kind, key, label: String(label || key).slice(0, 60), s: 0, n: 0, days: [], t: now, user: false }; m.items.push(it); }
    it.s = strength(it, now) + d; it.n++; it.t = now; if (it.tier === 'short' && tier !== 'short') it.tier = tier;
    const k = dkey(now); if (d > 0 && !it.days.includes(k)) it.days = [...it.days, k].slice(-30);
  }
  // Ghi nhận một phản hồi (gọi cạnh journal.record/rank.feedback). a = {topics, source, title}
  function record(m, ev, a, now, amount, topicLabel) {
    now = now || Date.now(); let d = SIG[ev]; if (d === undefined || !a) return m;
    if (ev === 'dwell') d *= Math.min(Math.max(+amount || 0, 0), 90) / 90; if (ev === 'rate') d = ((Math.min(Math.max(+amount || 3, 1), 5) - 3) / 2) * SIG.rate;
    (a.topics || []).slice(0, 3).forEach(t => bump(m, 'short', 'topic', t, topicLabel ? topicLabel(t) : t, d, now));
    if (a.source && d > 0) bump(m, 'short', 'source', a.source, a.source, d * 0.6, now);
    if (ev === 'less' || ev === 'hide') (a.topics || []).slice(0, 1).forEach(t => { const it = find(m, idOf('topic', t)); if (it && it.s < -1.5) learn(m, 'mute', t, 'Hay bị “ít tin này”: ' + (topicLabel ? topicLabel(t) : t), now); });
    m.last = dkey(now); return m;
  }
  function learn(m, kind, key, text, now) { const id = idOf('fact', kind + '-' + key); if (m.tomb.includes(id)) return; let it = find(m, id); if (!it) m.items.push({ id, tier: 'long', kind: 'fact', key: kind + '-' + key, label: text, s: 1, n: 1, days: [dkey(now)], t: now, user: false, mute: kind === 'mute' ? key : undefined }); else { it.n++; it.t = now; } }
  // Củng cố hằng ngày (idempotent theo m.cons): short cũ hơn 1 ngày → mid; mid đủ mạnh + đủ ngày → long; mục yếu bị bỏ; giờ đọc hay gặp → thói quen.
  function consolidate(m, now, ctx) {
    now = now || Date.now(); const today = dkey(now); if (m.cons === today) return { changed: false }; m.cons = today; let ch = 0;
    m.items.forEach(it => {
      const st = strength(it, now);
      if (it.tier === 'short' && dkey(it.t) < today) { it.s = st; it.t = now - 0; it.tier = 'mid'; ch++; }
      else if (it.tier === 'mid' && st >= PROMOTE_S && it.days.length >= PROMOTE_DAYS && it.kind !== 'fact' && (Date.parse(it.days[it.days.length - 1]) - Date.parse(it.days[0])) >= SPAN_DAYS * DAY && now - Date.parse(it.days[it.days.length - 1]) <= RECENT_DAYS * DAY) { it.s = st; it.t = now; it.tier = 'long'; ch++; }
    });
    const before = m.items.length; m.items = m.items.filter(it => it.user || it.kind === 'fact' || Math.abs(strength(it, now)) >= DROP_S);
    ch += before - m.items.length;
    if (ctx && ctx.hours) { const e = Object.entries(ctx.hours).sort((a, b) => b[1] - a[1]), tot = e.reduce((s, x) => s + x[1], 0);
      if (tot >= 20 && e[0][1] / tot >= 0.4) { const h = +e[0][0]; learn(m, 'hour', h < 12 ? 'sang' : h < 18 ? 'chieu' : 'toi', 'Hay đọc vào buổi ' + (h < 12 ? 'sáng' : h < 18 ? 'chiều' : 'tối'), now); ch++; } }
    if (m.items.length > MAX_ITEMS) { m.items.sort((a, b) => (b.user ? 99 : 0) + Math.abs(strength(b, now)) - ((a.user ? 99 : 0) + Math.abs(strength(a, now)))); m.items.length = MAX_ITEMS; ch++; }
    return { changed: ch > 0 };
  }
  // Điều chỉnh điểm xếp hạng cho một bài + lý do. Tầng nào mạnh hơn thì nặng hơn; tắt (mute) = trừ nhưng KHÔNG bao giờ ẩn hẳn.
  const W = { short: 0.15, mid: 0.3, long: 0.5 };
  function adjust(m, a, now) {
    now = now || Date.now(); let s = 0, best = null;
    (a.topics || []).forEach(t => { const it = find(m, idOf('topic', t)); if (!it || it.off) return; const v = strength(it, now) * W[it.tier]; s += Math.max(-1.2, Math.min(1.2, v)); if (v > 0.05 && (!best || v > best.v)) best = { v, it }; });
    const sr = a.source && find(m, idOf('source', a.source)); if (sr && !sr.off) s += Math.min(0.4, strength(sr, now) * 0.15);
    m.items.forEach(it => { if (it.mute && (a.topics || []).includes(it.mute) && !it.off) s -= 0.5; });
    return s;
  }
  const TIERN = { short: 'hôm nay', mid: '30 ngày qua', long: 'lâu dài' };
  function explain(m, a, now) {
    const adj = adjust(m, a, now), tops = (a.topics || []).map(t => find(m, idOf('topic', t))).filter(x => x && !x.off && strength(x, now) > 0.1).sort((x, y) => strength(y, now) * W[y.tier] - strength(x, now) * W[x.tier]);
    if (!tops.length || adj < 0.05) return '';
    const it = tops[0]; return 'Bạn nhớ: ' + it.label + ' (' + TIERN[it.tier] + (it.n > 1 ? ', ' + it.n + ' lần' : '') + ')';
  }
  // Danh sách để hiện + sửa. Sắp theo tầng rồi độ mạnh.
  function view(m, now) {
    now = now || Date.now(); const ord = { long: 0, mid: 1, short: 2 };
    return m.items.map(it => Object.assign({}, it, { strength: Math.round(strength(it, now) * 100) / 100 })).sort((a, b) => ord[a.tier] - ord[b.tier] || b.strength - a.strength);
  }
  function forget(m, id) { const n = m.items.length; m.items = m.items.filter(x => x.id !== id); if (!m.tomb.includes(id)) m.tomb = [...m.tomb, id].slice(-200); return n !== m.items.length; }
  function pin(m, id, on, now) { const it = find(m, id); if (!it) return false; it.user = !!on; it.pin = !!on; if (on) { it.tier = 'long'; it.t = now || Date.now(); } return true; }
  function off(m, id, on) { const it = find(m, id); if (!it) return false; it.off = !!on; it.user = true; return true; }
  function add(m, kind, key, label, now) { if (!['topic', 'source'].includes(kind) || !key) return false; const id = idOf(kind, key); m.tomb = m.tomb.filter(x => x !== id); if (find(m, id)) return pin(m, id, true, now); m.items.push({ id, tier: 'long', kind, key: String(key).slice(0, 60), label: String(label || key).slice(0, 60), s: 1.5, n: 1, days: [], t: now || Date.now(), user: true, pin: true }); return true; }
  function clear(m) { m.items = []; m.tomb = []; m.last = null; delete m.cons; return m; }
  // Khớp từ nhật ký/hồ sơ lúc mở trang: dựng lại mid từ journal.span 30 ngày nếu bộ nhớ trống (người dùng mới nhập nhật ký).
  function seedFromSpan(m, sp, now, topicLabel) {
    if (m.items.length || !sp || !sp.days) return 0; let n = 0;
    Object.entries(sp.topics).forEach(([t, x]) => { const d = x.open * 0.35 - x.skip * 0.03; if (d > 0.3) { bump(m, 'mid', 'topic', t, topicLabel ? topicLabel(t) : t, d, now); const it = find(m, idOf('topic', t)); it.n = x.open; n++; } });
    return n;
  }
  const memStore = () => { const x = {}; return { getItem: k => (k in x ? x[k] : null), setItem: (k, v) => { x[k] = String(v); }, removeItem: k => { delete x[k]; } }; };
  function open(store, id) {
    store = store || (typeof localStorage !== 'undefined' ? localStorage : memStore()); const key = 'press.mem.' + id;
    const load = () => { try { const j = JSON.parse(store.getItem(key)); return j && Array.isArray(j.items) ? Object.assign(empty(), j) : empty(); } catch (e) { return empty(); } };
    const save = m => { try { store.setItem(key, JSON.stringify(m)); return true; } catch (e) { return false; } };
    return { load, save, key, clear() { store.removeItem(key); },
      record(ev, a, now, amount, tl) { const m = load(); record(m, ev, a, now, amount, tl); return save(m); },
      exportJSON() { return JSON.stringify(load()); },
      importJSON(txt) { let o; try { if (String(txt).length > 2e6) throw 0; o = JSON.parse(txt); if (!Array.isArray(o.items)) throw 0; } catch (e) { return { added: 0, error: 'Tệp bộ nhớ không hợp lệ.' }; }
        const m = load(); let added = 0; o.items.slice(0, MAX_ITEMS).forEach(x => { if (x && KINDS.includes(x.kind) && typeof x.id === 'string' && !find(m, x.id) && !m.tomb.includes(x.id) && ['short', 'mid', 'long'].includes(x.tier)) { m.items.push({ id: x.id, tier: x.tier, kind: x.kind, key: String(x.key).slice(0, 60), label: String(x.label).slice(0, 60), s: +x.s || 0, n: +x.n || 1, days: (x.days || []).slice(-30), t: +x.t || Date.now(), user: !!x.user, pin: !!x.pin, off: !!x.off, mute: x.mute }); added++; } });
        save(m); return { added }; } };
  }
  const api = { open, record, consolidate, adjust, explain, view, forget, pin, off, add, clear, seedFromSpan, strength, empty, dkey, memStore, HALF, MAX_ITEMS };
  if (typeof module !== 'undefined') module.exports = api; else root.PressMemory = api;
})(typeof self !== 'undefined' ? self : this);

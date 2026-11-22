// K4: bộ nhớ 3 tầng. In JSON các kiểm tra.
const M = require('../web/memory.js'), R = require('../web/rank.js'), J = require('../web/journal.js'), r = {};
const D = 86400000, t0 = Date.parse('2026-03-01T09:00:00Z'), tl = t => ({ godot: 'Godot', fig: 'Figma', crypto: 'Crypto' }[t] || t);
const A = (t, s) => ({ id: t + s, title: t, topics: [t], source: s || 'S' });
// 1) ghi ngắn hạn → hôm sau lên mid → đọc đều 6 ngày lên long
let m = M.empty(); M.record(m, 'like', A('godot', 'HN'), t0, 0, tl);
r.short_first = m.items.find(x => x.id === 'topic:godot').tier === 'short' && m.items.some(x => x.id === 'source:HN');
M.consolidate(m, t0 + 0.5 * D); r.same_day_stays_short = m.items.find(x => x.id === 'topic:godot').tier === 'short';
M.consolidate(m, t0 + 1 * D + 3600e3); r.next_day_mid = m.items.find(x => x.id === 'topic:godot').tier === 'mid';
for (let d = 1; d <= 12; d++) { const t = t0 + d * D + 3600e3; M.record(m, 'save', A('godot', 'HN'), t, 0, tl); M.record(m, 'open', A('godot', 'HN'), t, 0, tl); M.consolidate(m, t + D + 1000); }
r.long_after_habit = m.items.find(x => x.id === 'topic:godot').tier === 'long';
// 2) decay: mid không củng cố tan sau ~4 tháng; long bền hơn mid
let d1 = M.empty(); M.record(d1, 'like', A('fig'), t0, 0, tl); M.consolidate(d1, t0 + D + 1); M.consolidate(d1, t0 + 100 * D);
r.decay_drops_stale = !d1.items.some(x => x.id === 'topic:fig');
const it = { tier: 'mid', s: 1, t: t0, user: false }, il = { tier: 'long', s: 1, t: t0, user: false };
r.long_outlasts_mid = M.strength(il, t0 + 60 * D) > 4 * M.strength(it, t0 + 60 * D);
// 3) xếp hạng: nhớ nâng điểm; mute trừ nhưng không ẩn; giải thích có tầng
const arts = [A('godot', 'HN'), A('fig', 'X'), A('crypto', 'Y')];
const ad = a => M.adjust(m, a, t0 + 13 * D);
r.adjust_favours_long = ad(arts[0]) > ad(arts[1]) && ad(arts[0]) > 0.3;
r.explain_text = /^Bạn nhớ: Godot \(lâu dài/.test(M.explain(m, arts[0], t0 + 13 * D)) && M.explain(m, arts[2], t0 + 13 * D) === '';
const prof = R.newProfile(null, [], t0), tp = { godot: { label: 'Godot', adjacent: [] }, fig: { label: 'Figma', adjacent: [] }, crypto: { label: 'Crypto', adjacent: [] } };
const rk = R.rank(arts, prof, tp, () => 0.5, t0 + 13 * D, { adj: a => ad(a), explain: a => M.explain(m, a, t0 + 13 * D), page: 3 });
r.rank_uses_memory = rk[0].a.topics[0] === 'godot' && /Bạn nhớ/.test(rk[0].why);
// 4) người dùng sửa: ghim, tắt, xoá = bia mộ (không tự học lại), thêm tay
let u = M.empty(); M.record(u, 'like', A('fig', 'X'), t0, 0, tl);
r.pin_long = M.pin(u, 'topic:fig', true, t0) && u.items[0].tier === 'long' && u.items[0].user && M.strength(u.items[0], t0 + 900 * D) >= 1.5;
M.off(u, 'topic:fig', true); r.off_ignored = M.adjust(u, A('fig'), t0) === 0;
M.forget(u, 'topic:fig'); M.record(u, 'like', A('fig', 'X'), t0 + D, 0, tl); r.forget_tombstone = !u.items.some(x => x.id === 'topic:fig');
r.add_removes_tomb = M.add(u, 'topic', 'fig', 'Figma', t0 + 2 * D) && u.items.some(x => x.id === 'topic:fig' && x.pin);
r.add_rejects_bad_kind = M.add(u, 'fact', 'x', 'x', t0) === false;
// 5) mute học từ "ít tin này"; không ẩn hẳn
let mu = M.empty(); for (let i = 0; i < 3; i++) M.record(mu, 'less', A('crypto'), t0 + i * 1000, 0, tl);
r.mute_learned = mu.items.some(x => x.mute === 'crypto') && M.adjust(mu, A('crypto'), t0 + 5000) < 0 && M.adjust(mu, A('crypto'), t0 + 5000) > -2.5;
// 6) thói quen giờ đọc
let hb = M.empty(); M.record(hb, 'open', A('godot'), t0, 0, tl); M.consolidate(hb, t0 + D, { hours: { 8: 18, 9: 8, 21: 2 } });
r.habit_morning = hb.items.some(x => /buổi sáng/.test(x.label));
// 7) seed từ nhật ký khi bộ nhớ trống (nhập nhật ký ở máy mới)
const j = J.empty(); for (let d = 0; d < 6; d++) { J.record(j, 'open', { id: 'a' + d, title: 't', source: 'S', topics: ['godot'], desks: ['gamedev'] }, t0 + d * D); J.record(j, 'open', { id: 'b' + d, title: 't', source: 'S', topics: ['godot'], desks: ['gamedev'] }, t0 + d * D); }
const sm = M.empty(); r.seed_journal = M.seedFromSpan(sm, J.span(j, J.dkey(t0), J.dkey(t0 + 13 * D)), t0 + 13 * D, tl) === 1 && sm.items[0].tier === 'mid'; r.seed_only_when_empty = M.seedFromSpan(sm, J.span(j, J.dkey(t0), J.dkey(t0 + 13 * D)), t0, tl) === 0;
// 8) kho: lưu/xuất/nhập/xoá; nhập từ chối rác; trần số mục; idempotent củng cố
const st = M.memStore(), db = M.open(st, 'me'); db.record('like', A('godot', 'HN'), t0, 0, tl); const ex = db.exportJSON();
const db2 = M.open(M.memStore(), 'b'); r.export_import = db2.importJSON(ex).added === 2 && db2.importJSON(ex).added === 0;
r.import_rejects = M.open(M.memStore(), 'c').importJSON('{"x":1}').error && M.open(M.memStore(), 'c').importJSON('not json').error;
r.import_sanitises = (() => { const d = M.open(M.memStore(), 'z'); d.importJSON(JSON.stringify({ items: [{ id: 'topic:x', tier: 'evil', kind: 'topic', key: 'x', label: 'x' }, { id: 'topic:y', tier: 'long', kind: 'topic', key: 'y', label: '<img>', s: 1 }] })); return d.load().items.length === 1; })();
r.clear_wipes = (() => { db.clear(); return db.load().items.length === 0 && st.getItem(db.key) === null; })();
let big = M.empty(); for (let i = 0; i < 300; i++) M.record(big, 'like', { topics: ['t' + i], source: 's' }, t0, 0); M.consolidate(big, t0 + D);
r.cap_items = big.items.length <= M.MAX_ITEMS;
const c1 = M.empty(); M.record(c1, 'like', A('godot'), t0); M.consolidate(c1, t0 + D); const s1 = JSON.stringify(c1); M.consolidate(c1, t0 + D + 5); r.consolidate_idempotent = JSON.stringify(c1) === s1;
// 9) riêng tư: không URL/tiêu đề bài trong bộ nhớ
const pr = M.empty(); M.record(pr, 'open', { id: 'x', title: 'SECRET TITLE', url: 'https://secret.example/x', topics: ['godot'], source: 'HN' }, t0, 0, tl); r.no_titles = !/SECRET|secret\.example/.test(JSON.stringify(pr));
console.log(JSON.stringify(r));

// Nhật ký + thích nghi hằng ngày: mô phỏng, KHÔNG mạng. In JSON {kiểm: bool}.
const J = require('../web/journal.js'), R = require('../web/rank.js'), day = 86400000, res = {};
const t0 = Date.UTC(2026, 0, 1, 9);
const mk = (id, topic, desk, src) => ({ id, title: 'Bài ' + id, source: src || 'HN', topics: [topic], desks: [desk || 'ai'], points: 10 });
// --- D1: ghi / giữ 365 ngày / giới hạn / xuất-nhập
const st = J.memStore(), jr = J.open(st, 'me');
jr.record('seen', mk('a', 'llm'), t0); jr.record('open', mk('a', 'llm'), t0); jr.record('dwell', mk('a', 'llm'), t0, 45);
const L = jr.load(), d0 = L.days[J.dkey(t0)];
res.journal_records_day = d0.n.seen === 1 && d0.n.open === 1 && d0.dwell_s === 45 && d0.items.a.ev.dwell === 45 && d0.h[new Date(t0).getHours()] === 3;
for (let i = 0; i < 400; i++) jr.record('open', mk('x' + i, 'llm'), t0 + (i + 1) * day);
const L2 = jr.load(); const nd = Object.keys(L2.days).length;
res.journal_keeps_365_days = nd <= 366 && nd >= 364 && !L2.days[J.dkey(t0)];
for (let i = 0; i < 200; i++) jr.record('open', mk('y' + i, 'llm'), t0 + 399 * day);
res.journal_caps_items_per_day = Object.keys(jr.load().days[J.dkey(t0 + 399 * day)].items).length <= J.MAX_ITEMS;
const j2 = J.open(J.memStore(), 'b'); j2.record('open', mk('q', 'ux-design', 'design'), t0 + 500 * day);
const out = j2.exportJSON(), j3 = J.open(J.memStore(), 'c'), imp = j3.importJSON(out);
res.journal_export_import = imp.added === 1 && Object.keys(j3.load().days).length === 1 && JSON.parse(out).days[J.dkey(t0 + 500 * day)].items.q.t === 'Bài q';
res.journal_rejects_garbage = !!j3.importJSON('{bad').error && !!j3.importJSON('{"days":5}').error;
res.journal_unknown_event_ignored = (() => { const j = J.empty(); J.record(j, 'hack', mk('z', 'llm'), t0); return Object.keys(j.days).length === 0; })();
res.journal_per_reader_isolated = J.open(st, 'other').load() && Object.keys(J.open(st, 'other').load().days).length === 0;
// --- D3: thích nghi 90 ngày. Người dùng mở agents, luôn bỏ qua finance, thấy lẫn ux-design.
const topics = { agents: { label: 'Agent', adjacent: ['llm', 'personal-finance'], desks: ['ai'] }, llm: { label: 'LLM', adjacent: ['agents'], desks: ['ai'] }, 'personal-finance': { label: 'Tài chính', adjacent: [], desks: ['finance'] }, 'ux-design': { label: 'UX', adjacent: ['ui-design'], desks: ['design'] }, 'ui-design': { label: 'UI', adjacent: ['ux-design'], desks: ['design'] }, godot: { label: 'Godot', adjacent: [], desks: ['gamedev'] } };
const arts = []; Object.keys(topics).forEach(t => { for (let i = 0; i < 12; i++) arts.push({ id: t + i, title: t + i, source: 'HN', topics: [t], desks: topics[t].desks, points: 10 + i, engagement: 0.2 }); });
const p = R.newProfile(null, ['agents'], t0), jj = J.open(J.memStore(), 'me');
let always_explore = true, min_explore = 99, seenFin = 0, rankRuns = 0;
for (let d = 0; d < 90; d++) {
  const now = t0 + d * day;
  const sp14 = J.span(jj.load(), J.dkey(now - 14 * day), J.dkey(now - day));
  R.adaptDaily(p, sp14, now);
  // idempotent trong ngày: gọi lần 2 không đổi
  const snap = JSON.stringify(p.w); R.adaptDaily(p, sp14, now); if (JSON.stringify(p.w) !== snap) res.adapt_not_idempotent = true;
  const rk = R.rank(arts, p, topics, (() => { let s = d + 1; return () => (s = (s * 16807) % 2147483647) / 2147483647; })(), now, { page: 24 });
  const ex = rk.filter(x => x.explore).length; min_explore = Math.min(min_explore, ex); rankRuns++;
  if (rk.some(x => (x.a.topics || []).includes('personal-finance'))) seenFin++;
  // hành vi hôm nay
  for (let i = 0; i < 3; i++) { const a = arts.find(x => x.id === 'agents' + i); jj.record('seen', a, now); jj.record('open', a, now); R.feedback(p, a, 'open', null, now); }
  for (let i = 0; i < 4; i++) { const a = arts.find(x => x.id === 'personal-finance' + i); jj.record('seen', a, now); jj.record('skip', a, now); R.feedback(p, a, 'skip', null, now); }
}
const now = t0 + 90 * day, w = t => R.weight(p, t, now);
res.adapt_converges_top_topic = w('agents') > w('personal-finance') && w('agents') > 1;
res.adapt_demotes_ignored_but_not_blocked = w('personal-finance') < 0.01 && w('personal-finance') > -0.5 && !(p.w['personal-finance'] && p.w['personal-finance'].blocked);
res.no_filter_bubble_explore_floor = min_explore >= 3;     // ≥ ~12% của 24 trên MỌI lượt
res.no_bubble_ignored_topic_still_surfaces = seenFin > 0;
res.adapt_density_auto = (() => { const q = R.newProfile(null, ['agents'], t0), j = J.open(J.memStore(), 'q'); for (let d = 0; d < 5; d++) for (let i = 0; i < 10; i++) j.record('open', arts[i + d], t0 + d * day);
  R.adaptDaily(q, J.span(j.load(), J.dkey(t0), J.dkey(t0 + 5 * day)), t0 + 6 * day); return q.density === 'rich'; })();
res.adapt_density_manual_lock = (() => { const q = R.newProfile(null, ['agents'], t0); q.densityAuto = false; const j = J.open(J.memStore(), 'q'); for (let d = 0; d < 5; d++) for (let i = 0; i < 10; i++) j.record('open', arts[i + d], t0 + d * day);
  R.adaptDaily(q, J.span(j.load(), J.dkey(t0), J.dkey(t0 + 5 * day)), t0 + 6 * day); return q.density === 'normal'; })();
res.adapt_emerging_topic = (() => { const q = R.newProfile(null, ['agents'], t0), j = J.open(J.memStore(), 'q'); for (let d = 0; d < 3; d++) { j.record('open', arts.find(x => x.id === 'godot' + d), t0 + d * day); j.record('open', arts.find(x => x.id === 'godot' + (d + 5)), t0 + d * day); }
  const b = R.weight(q, 'godot', t0 + 4 * day); R.adaptDaily(q, J.span(j.load(), J.dkey(t0), J.dkey(t0 + 3 * day)), t0 + 4 * day); return R.weight(q, 'godot', t0 + 4 * day) > b; })();
// giải thích
const sp30 = J.span(jj.load(), J.dkey(now - 30 * day), J.dkey(now));
const rk = R.rank(arts, p, topics, () => 0.5, now, { page: 24, sp: sp30 });
res.why_cites_own_numbers = rk.some(x => !x.explore && /đã mở \d+ bài trong 30 ngày/.test(x.why));
// thứ tự ban theo vai trò + nhật ký
const roles = { role: { designer: { desks: ['design', 'ai'] }, dev: { desks: ['gamedev'] } } }, ids = ['ai', 'design', 'gamedev', 'finance'];
res.desk_order_by_role = R.deskOrder({ role: 'designer' }, null, roles, ids)[0] === 'design' && R.deskOrder({ role: 'dev' }, null, roles, ids)[0] === 'gamedev';
res.desk_order_journal_moves = R.deskOrder({ role: 'designer' }, { desks: { finance: { seen: 100, open: 50 } } }, roles, ids)[0] === 'finance';
if (process.env.DBG) console.error(w("personal-finance"), seenFin, JSON.stringify(p.w["personal-finance"]));
console.log(JSON.stringify(res));

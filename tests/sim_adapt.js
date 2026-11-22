// M2+M3: vai trò → hồ sơ, bộ đo, mô phỏng 90 ngày hội tụ, báo cáo gu, xuất/nhập đồng bộ. In JSON.
const R = require('../web/rank.js'), P = require('../web/profiles.js'), fs = require('fs');
const day = JSON.parse(fs.readFileSync(__dirname + '/../public/today.json', 'utf8'));
const topics = day.topics, arts = day.articles, roles = day.roles, r = {};
const D = 86400000, t0 = Date.parse('2026-01-01T00:00:00Z');
function rng(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

// --- vai trò ---
const ids = Object.keys(roles.role);
r.roles_all = ['gamedev', 'art', 'design', 'marketing', 'other'].every(x => ids.includes(x));
r.roles_valid = ids.every(id => roles.role[id].topics.every(t => topics[t]) && roles.role[id].desks.every(d => day.desks[d]) && R.PAGES[roles.role[id].density]);
const pm = R.fromRole(roles, 'marketing', t0);
r.role_profile = pm.role === 'marketing' && pm.density === 'compact' && pm.v === 2 && Object.keys(pm.w).length === roles.role.marketing.topics.length;
r.density_page = R.rank(arts, R.fromRole(roles, 'marketing', t0), topics, rng(1), t0).length <= R.PAGES.compact
  && R.rank(arts, R.newProfile(null, [], t0, { density: 'rich' }), topics, rng(1), t0).length > R.PAGES.normal;
r.role_differs = R.rank(arts, R.fromRole(roles, 'design', Date.now()), topics, rng(1)).slice(0, 5).map(x => x.a.id).join() !== R.rank(arts, R.fromRole(roles, 'gamedev', Date.now()), topics, rng(1)).slice(0, 5).map(x => x.a.id).join();
const v1 = { v: 1, desk: null, w: { x: { v: 1, t: t0 } }, bandit: {}, saved: [], hidden: [], explored: {} };
R.ensure(v1); r.migrate_v1 = v1.v === 2 && v1.density === 'normal' && !!v1.stats && R.weight(v1, 'x', t0) > 0.9;

// --- bộ đo ---
const A = arts.find(a => a.topics.length), p = R.newProfile(null, [], t0);
R.feedback(p, A, 'open', null, t0); R.feedback(p, A, 'skip', null, t0); R.feedback(p, A, 'dwell', null, t0, 45); R.feedback(p, A, 'rate', null, t0, 5);
const w1 = R.weight(p, A.topics[0], t0);
r.meter_counts = p.stats.open === 1 && p.stats.skip === 1 && p.stats.rate_n === 1 && p.stats.dwell_s === 45 && p.src[A.source] > 0;
const pn = R.newProfile(null, [], t0); R.feedback(pn, A, 'rate', null, t0, 1);
r.rate_signs = w1 > 0 && R.weight(pn, A.topics[0], t0) < 0;
const pd = R.newProfile(null, [], t0); R.feedback(pd, A, 'dwell', null, t0, 5); const pd2 = R.newProfile(null, [], t0); R.feedback(pd2, A, 'dwell', null, t0, 90);
r.dwell_scales = R.weight(pd2, A.topics[0], t0) > 3 * R.weight(pd, A.topics[0], t0);

// --- 90 ngày: gu thật = {T1,T2} (đọc đều), nhất thời = T3 (đọc dồn 10 ngày đầu rồi bỏ). Cuối kỳ: T1,T2 thắng T3; báo cáo đúng ---
const cnt = {}; arts.forEach(a => a.topics.forEach(t => cnt[t] = (cnt[t] || 0) + 1));
const tops = Object.keys(cnt).filter(t => cnt[t] >= 4).sort((a, b) => cnt[b] - cnt[a]); const [T1, T2, T3] = [tops[0], tops[1], tops[tops.length - 1]];
const q = R.newProfile(null, [], t0), g = rng(42);
const pick = t => { const l = arts.filter(a => a.topics.includes(t)); return l[Math.floor(g() * l.length)]; };
for (let d = 0; d < 90; d++) {
  const now = t0 + d * D;
  [T1, T2].forEach(t => { if (g() < 0.7) { const a = pick(t); R.feedback(q, a, 'open', null, now); R.feedback(q, a, 'dwell', null, now, 60); if (g() < 0.4) R.feedback(q, a, 'like', null, now); } });
  if (d < 10) { const a = pick(T3); for (let k = 0; k < 3; k++) R.feedback(q, a, 'like', null, now); }
  const other = arts.filter(a => !a.topics.some(t => [T1, T2, T3].includes(t)))[d % 5]; if (other) R.feedback(q, other, 'skip', null, now);
}
const end = t0 + 90 * D, rep = R.report(q, topics, end);
const wr = t => R.weight(q, t, end);
r.conv_long_beats_fad = wr(T1) > wr(T3) && wr(T2) > wr(T3);
r.conv_top2 = rep.top.slice(0, 2).map(x => x.topic).sort().join() === [T1, T2].sort().join();
r.conv_fad_fading = (rep.top.find(x => x.topic === T3) || { trend: 'fading' }).trend === 'fading';
r.conv_rank_top = (() => { const out = R.rank(arts, q, topics, rng(5), end); return out.slice(0, 6).filter(x => x.a.topics.includes(T1) || x.a.topics.includes(T2)).length >= 4; })();
r.report_fields = rep.days > 50 && rep.open_rate > 0 && rep.open_rate < 1 && rep.avg_dwell_s > 30 && rep.sources.length > 0;
// phần dài làm gu sống lâu hơn nhất thời: sau 90 ngày không đọc, T1 (đều) còn trên T3 và vẫn > 0
const later = end + 90 * D; r.long_outlives_short = R.weight(q, T1, later) > 0.2 && R.weight(q, T1, later) > R.weight(q, T3, later);

// --- đồng bộ ---
const s1 = P.memStore(), a = P.open(s1); a.select('me'); a.save('me', pm); const idB = a.create('Hà', R.fromRole(roles, 'art', t0)); a.save(idB, R.fromRole(roles, 'art', t0));
const code = a.exportAll(); r.export_code = code.startsWith('press1.') && !code.includes('Hà');
const b = P.open(P.memStore()); const res = b.importAll(code);
r.import_roundtrip = res.merged === 1 && res.added === 1 && b.list().length === 2 && b.load('me').role === 'marketing' && b.load(b.list().find(x => x.name === 'Hà').id).role === 'art';
r.import_bad = P.open(P.memStore()).importAll('rác').error && P.open(P.memStore()).importAll('press1.@@').error;
const c = P.open(P.memStore()); c.select('me'); c.save('me', R.newProfile(null, ['zz'], t0)); c.importAll(code);
r.import_keeps_me = !!c.load('me').w.zz && !c.load('me').role;
console.log(JSON.stringify(r));

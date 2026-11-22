// 30 ngày end-to-end: dedup (seen-store) + memory + rank. Gu thật {godot,fig} đọc đều; crypto nhất thời 5 ngày đầu rồi bỏ. Mỗi ngày có tin mới + tin lặp.
const M = require('../web/memory.js'), R = require('../web/rank.js'), DD = require('../web/dedup.js'), r = {};
const D = 86400000, t0 = Date.parse('2026-05-01T09:00:00Z'), T = ['godot', 'fig', 'crypto', 'ai', 'seo'];
const tp = Object.fromEntries(T.map(t => [t, { label: t, adjacent: T.filter(x => x !== t), desks: [] }]));
function rng(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rg = rng(11), uniq = n => { const h = require('crypto').createHash('sha1').update('w' + String(n)).digest('hex'); return Array.from({ length: 7 }, (_, i) => String.fromCharCode(97 + parseInt(h[i * 2] + h[i * 2 + 1], 16) % 26)).join(''); };
const mem = M.empty(), seen = DD.empty(), prof = R.newProfile(null, [], t0); let published = [], dupShown = 0, kbN = 0; const shownKeys = new Set(); const topShare = [];
for (let d = 0; d < 30; d++) {
  const now = t0 + d * D, day = [];
  T.forEach((t, ti) => { for (let k = 0; k < 3; k++) { const n = d * 50 + ti * 5 + k; day.push({ id: 'a' + n, sid: 's' + n, rev: 0, title: `${uniq(n)} ${uniq('b' + n)} ${t} news ${uniq('c' + n)} ${uniq('d' + n)}`, url: `https://x.example/${n}`, topics: [t], source: 'Src' + ti }); } });
  published.slice(-20).forEach(a => day.push(Object.assign({}, a)));                    // tin cũ xuất hiện lại trong feed
  const f = DD.filter(seen, day, now);
  f.show.forEach(a => { const key = a.sid + ':' + (a.rev || 0); if (shownKeys.has(key)) dupShown++; shownKeys.add(key); });
  M.consolidate(mem, now); const adj = a => M.adjust(mem, a, now);
  const ranked = R.rank(f.show, prof, tp, rg, now, { adj, page: 8 });
  topShare.push(ranked.slice(0, 5).filter(x => ['godot', 'fig'].includes(x.a.topics[0])).length / 5);
  ranked.forEach(x => { const t = x.a.topics[0], like = ['godot', 'fig'].includes(t) || (t === 'crypto' && d < 5), ev = like ? 'open' : 'skip';
    DD.mark(seen, x.a, ev === 'open', now); M.record(mem, ev, x.a, now + 1000); R.feedback(prof, x.a, ev, null, now);
    if (like && rg() < 0.5) M.record(mem, 'save', x.a, now + 2000);
    if (ev === 'open') published.push(x.a); });
  kbN = mem.items.length;
}
const late = topShare.slice(-8).reduce((a, b) => a + b, 0) / 8, early = topShare.slice(0, 3).reduce((a, b) => a + b, 0) / 3;
const v = M.view(mem, t0 + 30 * D), lg = v.filter(x => x.tier === 'long' && x.kind === 'topic').map(x => x.key);
r.zero_dupes_30d = dupShown === 0;
r.taste_converges = late >= 0.6; r.early_share = +early.toFixed(2);
r.long_has_true_taste = lg.includes('godot') && lg.includes('fig');
r.fad_not_long = !lg.includes('crypto');
const sv = k => (v.find(x => x.id === 'topic:' + k) || { strength: 0 }).strength; r.fad_faded = sv('crypto') < 0.4 * sv('godot');
r.memory_bounded = kbN <= M.MAX_ITEMS;
r.seen_bounded = Object.keys(seen.st).length <= DD.CAP;
r.late_share = +late.toFixed(2);
console.log(JSON.stringify(r));

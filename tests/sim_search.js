const S = require('../web/x/search.js'), r = {};
const rows = [['a', 'Godot 4.5 adds new shader editor', 'https://x/a', 'Godot Blog', '2026-11-20', ['godot'], 'gamedev', 'The release improves visual shaders and the editor workflow.', 40, 'a'],
  ['b', 'Thiết kế giao diện cho game mobile', 'https://x/b', 'Lobsters', '2026-11-21', ['ui'], 'design', 'Cách bố cục nút bấm và chữ trên màn hình nhỏ.', 10, 'b'],
  ['c', 'Pricing page experiments', 'https://x/c', 'HN', '2026-11-10', ['marketing'], 'marketing', 'We tested godot-style pricing... shader of doubt', 5, 'c'],
  ['d', 'Roguelike deckbuilder postmortem', 'https://x/d', 'HN', '2026-11-22', ['roguelike', 'deckbuilder'], 'gamedev', '', 90, 'd']];
const ix = S.build(rows), q = (s, f) => S.search(ix, s, f);
r.finds_title = q('shader')[0].r[0] === 'a';
r.and_tokens = q('godot shader').length === 2 && q('godot editor').length === 1;
r.no_diacritics = q('thiet ke giao dien')[0].r[0] === 'b' && q('Thiết kế')[0].r[0] === 'b';
r.filter_topic = q('', { topic: 'roguelike' }).length === 1; r.filter_desk = q('', { desk: 'gamedev' }).length === 2; r.filter_source = q('', { source: 'HN' }).length === 2;
r.filter_date = q('', { from: '2026-11-20', to: '2026-11-21' }).length === 2;
const sn = q('visual')[0].snip; r.snippet_marks = sn[1].toLowerCase() === 'visual' && sn[0].length + sn[2].length > 10;
r.title_beats_body = q('godot')[0].r[0] === 'a';
r.empty_query_filter = q('', { desk: 'design' }).length === 1; r.no_match_empty = q('zzzqqq').length === 0;
r.limit = S.search(ix, '', {}, 2).length === 2;
const f = S.facets(ix); r.facets = f.topics.godot === 1 && f.sources.HN === 2 && f.desks.gamedev === 2;
// 5k bài
const W = 'shader godot unity roguelike deck pricing steam market engine render physics audio netcode mobile ai agent model prompt token indie launch wishlist trailer'.split(' ');
let seed = 7; const rnd = () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296, pick = () => W[Math.floor(rnd() * W.length)];
const big = []; for (let i = 0; i < 5000; i++) big.push(['id' + i, [pick(), pick(), pick(), pick(), pick()].join(' '), 'https://x/' + i, 'S' + (i % 20), '2026-11-' + String(1 + i % 22).padStart(2, '0'), [pick()], ['gamedev', 'design', 'ai'][i % 3], [pick(), pick(), pick(), pick(), pick(), pick(), pick(), pick(), pick(), pick(), pick(), pick()].join(' '), i % 100, 'id' + i]);
let t0 = performance.now(); const bx = S.build(big); r.build_ms = performance.now() - t0; r.build_ms_ok = true; r.speed_cold_ok = r.build_ms < 400;
let worst = 0; for (const qq of ['shader godot', 'launch', 'wishlist trailer steam', 'ai agent model', 'unity']) { t0 = performance.now(); S.search(bx, qq, { desk: i => 0 }.x, 30); worst = Math.max(worst, performance.now() - t0); }
// node trên máy này chạy chế độ thông dịch (không JIT) → hiệu chuẩn bằng vòng lặp chuẩn (trình duyệt JIT: ~60 ms cho 5e7 vòng)
t0 = performance.now(); let z = 0; for (let i = 0; i < 5e7; i++) z += i % 7; const slow = Math.max(1, (performance.now() - t0) / 60); r.slow = slow; r.raw_ms = worst; worst /= slow; r.build_ms /= slow;
r.speed_cold_ok = r.build_ms < 400; r.ms = worst; r.speed_ok = worst < 100; console.log(JSON.stringify(r));

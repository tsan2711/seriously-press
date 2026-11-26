const S = require('../web/x/search.js'), r = {};
const rows = [['a', 'Godot 4.5 adds new shader editor', 'https://x/a', 'Godot Blog', '2026-11-20', ['godot'], 'gamedev', 'Visual shaders improved.', 40, 'a'],
  ['b', 'Thiết kế giao diện cho game mobile', 'https://x/b', 'Lobsters', '2026-11-21', ['ui-design'], 'design', 'Cách bố cục nút bấm.', 10, 'b'],
  ['c', 'Đầu tư dài hạn cho người mới', 'https://x/c', 'VnExpress', '2026-11-19', ['investing'], 'finance', 'Quỹ chỉ số.', 5, 'c']];
const ix = S.build(rows), meta = { topics: { godot: 'Godot', 'ui-design': 'UI & giao diện', investing: 'Đầu tư' }, desks: { design: 'Thiết kế', finance: 'Tài chính cá nhân' } };
// chuẩn hoá
r.fold_vn = S.fold('Đầu tư Thiết kế Ưu đãi') === 'dau tu thiet ke uu dai';
r.fold_case = S.fold('GODOT') === 'godot' && S.fold(null) === '';
r.toks = JSON.stringify(S.toks('  Thiết-kế  UI/UX ')) === JSON.stringify(['thiet', 'ke', 'ui', 'ux']) && S.toks('a b c d e f g h').length === 6;
// tô sáng giữ nguyên chữ gốc (có dấu), khớp theo không dấu
const sg = S.segments('Thiết kế giao diện', S.toks('thiet ke'));
r.seg_orig = sg.map(x => x[0]).join('') === 'Thiết kế giao diện' && sg[0][0] === 'Thiết' && sg[0][1] === true && sg[1][1] === false && sg[2][0] === 'kế' && sg[2][1] === true;
r.seg_none = JSON.stringify(S.segments('abc', [])) === '[["abc",false]]';
r.seg_html_inert = S.segments('<b>x</b>', ['b']).map(x => x[0]).join('') === '<b>x</b>';
// gần đúng
r.near = S.near('shader', 'shadre') && S.near('shader', 'shader') && S.near('godot', 'godto') && S.near('unity', 'unty') && !S.near('shader', 'sheder2') && !S.near('abc', 'xyz');
r.fuzzy_typo = S.groups(ix, 'shadre', {}, meta).articles.length === 1 && S.groups(ix, 'shadre', {}, meta).fuzzy === true;
r.strict_first = S.groups(ix, 'shader', {}, meta).fuzzy === false;
r.fuzzy_short_no = S.groups(ix, 'gx', {}, meta).articles.length === 0;
// nhóm
const g = S.groups(ix, 'thiet ke', {}, meta);
r.group_desk = g.desks.length === 1 && g.desks[0].id === 'design' && g.articles[0].r[0] === 'b';
r.group_topic_prefix = S.groups(ix, 'dau tu', {}, meta).topics[0].id === 'investing';
r.group_topic_id = S.groups(ix, 'ui', {}, meta).topics[0].id === 'ui-design';
r.group_empty_q = (() => { const x = S.groups(ix, '', {}, meta); return x.topics.length === 0 && x.desks.length === 0; })();
r.group_filter = S.groups(ix, '', { desk: 'finance' }, meta).articles.length === 1;
// xếp hạng: khớp tiêu đề > khớp nội dung; mới/engagement cao hơn khi hoà
r.rank_title = S.search(ix, 'shader')[0].r[0] === 'a';
// gần đây
let rc = []; ['unity', 'godot', 'Unity', 'a', '  ', 'ui ux', 'đầu tư', 'seo', 'llm'].forEach(q => { rc = S.pushRecent(rc, q); });
r.recent_max5 = rc.length === 5; r.recent_order = rc[0] === 'llm' && rc[1] === 'seo';
r.recent_dedupe = S.pushRecent(['godot', 'unity'], 'UNITY')[0] === 'UNITY' && S.pushRecent(['godot', 'unity'], 'UNITY').length === 2;
r.recent_fold = S.pushRecent(['đầu tư'], 'dau tu').length === 1;
r.recent_bad = JSON.stringify(S.pushRecent(null, 'ab')) === '["ab"]' && S.pushRecent([1, 'x2'], 'zz').length === 2;
// theo dõi
const fw = S.followedTopics({ godot: { v: 2 }, investing: { v: 5 }, gone: { v: 9 } }, meta.topics, 5);
r.follow = fw.length === 2 && fw[0].id === 'investing' && S.followedTopics(null, meta.topics).length === 0;
// phím tắt
const ev = (o) => Object.assign({ key: '', ctrlKey: false, metaKey: false, altKey: false }, o);
r.key_slash = S.wantsOpen(ev({ key: '/' }), {}) === 'open';
r.key_slash_typing = S.wantsOpen(ev({ key: '/' }), { typing: true }) === '';
r.key_slash_dialog = S.wantsOpen(ev({ key: '/' }), { dialog: true }) === '';
r.key_slash_mod = S.wantsOpen(ev({ key: '/', ctrlKey: true }), {}) === '' && S.wantsOpen(ev({ key: '/', altKey: true }), {}) === '';
r.key_slash_ime = S.wantsOpen(ev({ key: '/', isComposing: true }), {}) === '';
r.key_ctrl_k = S.wantsOpen(ev({ key: 'k', ctrlKey: true }), {}) === 'toggle' && S.wantsOpen(ev({ key: 'K', metaKey: true }), { typing: true }) === 'toggle';
r.key_plain_k = S.wantsOpen(ev({ key: 'k' }), {}) === '' && S.wantsOpen(ev({ key: 'k', ctrlKey: true, altKey: true }), {}) === '';
// mũi tên vòng
r.step = S.step(-1, 3, 1) === 0 && S.step(-1, 3, -1) === 2 && S.step(2, 3, 1) === 0 && S.step(0, 3, -1) === 2 && S.step(-1, 0, 1) === -1;
console.log(JSON.stringify(r));

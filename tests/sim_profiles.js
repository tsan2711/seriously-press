// Mô phỏng hồ sơ: 2 hồ sơ không lẫn sở thích, xoá sạch, di trú, đề xuất. In JSON.
const R = require('../web/rank.js'), C = require('../web/x/profilectl.js'), P = require('../web/profiles.js'), fs = require('fs');
const day = JSON.parse(fs.readFileSync(__dirname + '/../public/today.json', 'utf8'));
const s = P.memStore(), r = {};
let db = P.open(s);
r.default_is_me = db.list().length === 1 && db.list()[0].id === 'me' && db.active() === null;
const has = t => day.articles.some(x => x.topics.includes(t)), tl = Object.keys(day.topics).filter(has);
const tA = tl[0], tB = tl.filter(t => t !== tA).pop();
db.select('me'); db.save('me', R.newProfile(null, [tA]));
const idB = db.create('Bạn A', R.newProfile(null, [tB]));
r.created = !!idB && db.list().length === 2;
// không lẫn: mở lại từ cùng storage
db = P.open(s);
const pm = db.load('me'), pb = db.load(idB);
r.no_mixing = !!pm.w[tA] && !pm.w[tB] && !!pb.w[tB] && !pb.w[tA];
// phản hồi ở B không đụng 'Tôi'
const art = day.articles.find(a => a.topics.includes(tB));
for (let i = 0; i < 5; i++) R.feedback(pb, art, 'like', null);
db.save(idB, pb);
db = P.open(s);
r.feedback_isolated = JSON.stringify(db.load('me')) === JSON.stringify(pm) && db.load(idB).w[tB].v > 1;
// xếp hạng khác nhau theo hồ sơ
const top = p => R.rank(day.articles, p, day.topics, () => 0.5, Date.now(), {}).slice(0, 10).map(i => i.a.id).join();
r.rank_differs = top(db.load('me')) !== top(db.load(idB));
// chọn / rời
r.select = db.select(idB) && P.open(s).active() === idB && (db.leave(), P.open(s).active() === null);
// xoá B = sạch khoá riêng và dòng danh mục; 'Tôi' còn
db.remove(idB); db = P.open(s);
r.remove_clean = !s.keys().some(k => k.includes(idB)) && db.list().length === 1 && db.load(idB) === null;
// xoá 'Tôi' = xoá dữ liệu nhưng giữ thẻ
db.remove('me'); db = P.open(s);
r.me_wiped_keeps_card = db.load('me') === null && db.list().length === 1 && !s.keys().includes('press.p.me');
// giới hạn + tên rỗng
r.empty_name_rejected = db.create('  ') === null;
for (let i = 0; i < 20; i++) db.create('x' + i);
r.max_enforced = db.list().length === P.MAX && !db.canCreate();
db.wipe(); r.wipe_all = s.keys().length === 0;
// di trú hồ sơ M3 cũ
const s2 = P.memStore(); s2.setItem('press.profile', JSON.stringify(R.newProfile('ai', [tA])));
const d2 = P.open(s2);
r.migrated = d2.load('me') && d2.load('me').desk === 'ai' && s2.getItem('press.profile') === null;
// đề xuất
const sg = P.suggest(day);
r.suggest = sg.length === Object.keys(day.desks).length && sg.every(x => x.topics.length > 0 && x.topics.every(t => day.topics[t].desks.includes(x.desk)));
// người mới: chưa chọn → không có chủ đề (banner/trạng thái trống hiện); chọn rồi thì hết
const s3 = P.memStore(), d3 = P.open(s3), firstRun = d => { const p = d.active() && d.load(d.active()); return !p || !Object.keys(p.w || {}).length; };
r.first_run_new = firstRun(d3);
d3.select('me'); r.first_run_selected_empty = firstRun(d3);
d3.save('me', R.newProfile(null, [tA])); r.first_run_done = !firstRun(d3);
// HTML build: banner, trạng thái trống, nút Vào đọc dính đáy, nút Xem ở trang chủ
const pub = f => fs.readFileSync(__dirname + '/../public/' + f, 'utf8'), home = pub('index.html');
r.html_banner = home.includes('data-firstrun') && home.includes('Chọn chủ đề để có bảng tin riêng') && home.includes('data-fr-x');
r.html_empty = home.includes('data-fy-empty');
r.html_enter = pub('picker.html').includes('data-enter');
r.html_viewhome = pub('me.html').includes('data-run-view');
// onboarding 3 bước: đi hết → hồ sơ đúng; bỏ qua bước vẫn hợp lệ; lưu giữa chừng; điều hướng không vượt biên
r.nav = P.nav(1, 1) === 2 && P.nav(2, 1) === 3 && P.nav(3, 1) === 0 && P.nav(1, -1) === 1 && P.nav(3, -1) === 2 && P.STEPS === 3;
{
  const so = P.memStore(), d = P.open(so), id = d.create('Hà');
  d.select(id); let st = d.setStep(id, 1);                              // 1/3: chọn vai trò → chủ đề + mật độ sẵn
  d.save(id, R.newProfile(null, [tA], undefined, { role: 'x', density: 'compact' }));
  st = P.nav(st, 1); d.setStep(id, st);                                 // 2/3
  r.step_persist = P.open(so).step(id) === 2 && P.open(so).pending() === id;   // "đóng tab" rồi mở lại vẫn ở bước 2
  d.save(id, R.newProfile(null, [tA, tB], undefined, { role: 'x', density: 'compact' }));
  st = P.nav(st, 1); d.setStep(id, st);                                 // 3/3
  st = P.nav(st, 1); if (!st) d.doneStep(id);                           // Xong
  const p = P.open(so).load(id);
  r.steps_full = st === 0 && P.open(so).pending() === null && !!p.w[tA] && !!p.w[tB] && p.density === 'compact';
  // bỏ qua cả 3 bước: hồ sơ chưa có dữ liệu nhưng người đọc vẫn hợp lệ, vào đọc được
  const id2 = d.create('Bỏ qua'); let s2 = 1;
  while (s2) { d.setStep(id2, s2); s2 = P.nav(s2, 1); } d.doneStep(id2);
  const d2 = P.open(so);
  r.steps_skip = d2.load(id2) === null && d2.select(id2) && d2.list().some(x => x.id === id2) && d2.step(id2) === 0 && R.ensure(d2.load(id2) || R.newProfile(null, [])) != null;
  // bỏ qua chỉ bước 2 (chọn vai trò + mật độ, không chọn chủ đề) vẫn lưu được
  const id3 = d.create('Một phần'); d.save(id3, R.newProfile(null, [], undefined, { role: 'x', density: 'rich' }));
  r.steps_partial = !!P.open(so).load(id3) && P.open(so).load(id3).density === 'rich';
  // xoá người đọc dọn luôn bước dở
  d.setStep(id3, 2); d.remove(id3); r.step_cleanup = !so.keys().some(k => k.includes(id3));
  d.setStep('khong-co', 2); r.step_unknown = d.step('khong-co') === 0;
}
// HTML build: 3 fieldset 1/3 2/3 3/3, nút Tiếp/Quay lại/Bỏ qua, đếm đã chọn, form tạo ẩn tới khi bấm nút
{
  const pk = fs.readFileSync(__dirname + '/../public/picker.html', 'utf8');
  r.html_steps = ['1/3', '2/3', '3/3'].every(t => pk.includes(t)) && (pk.match(/<fieldset data-step=/g) || []).length === 3;
  r.html_nav = pk.includes('data-next') && pk.includes('data-prev') && pk.includes('data-count') && pk.includes('data-open-create') && /data-create hidden/.test(pk);
}

// ----- điều khiển hồ sơ đọc -----
{
  const now = Date.now(), A = day.articles, mk = () => { const p = R.newProfile('ai', [tA, tB], now); p.src['Nguồn X'] = 2; p.saved.push('s1'); p.hidden.push('h1'); p.density = 'rich'; p.role = 'dev'; C.setLevel(p, 'high'); C.setSource(p, 'Nguồn Y', 'less'); C.setTopic(p, tB, false, now); R.feedback(p, A[0], 'like', null, now); return p; };
  // xuất/nhập khứ hồi (qua JSON, qua cả localStorage giả)
  const p0 = mk(), txt = C.exportProfile(p0), im = C.importProfile(txt);
  const pick = p => JSON.stringify([p.desk, p.role, p.density, p.pz, p.w, p.src, p.sm, p.saved, p.hidden, p.bandit, p.stats]);
  r.ctl_roundtrip = !!im.profile && pick(im.profile) === pick(R.ensure(JSON.parse(JSON.stringify(p0)))) && C.importProfile(C.exportProfile(im.profile)).profile.pz === 'high';
  // từ chối rác / sai định dạng
  r.ctl_import_rejects = ['', 'khong json', '[]', '{}', '{"format":"press-profile","v":1}', '{"format":"press-profile","v":1,"profile":{"w":[]}}', '{"format":"x","v":1,"profile":{"w":{}}}', JSON.stringify({ format: 'press-profile', v: 2, profile: { w: {} } }), null, 5].every(t => !!C.importProfile(t).error);
  // làm sạch: ép kiểu, bỏ trường lạ, mức lạ → vừa
  const evil = C.importProfile(JSON.stringify({ format: 'press-profile', v: 1, profile: { w: { a: { v: 'x', l: null, t: 1, off: 1 }, b: 7 }, pz: 'hack', sm: { s1: 'hide', s2: '<img>' }, saved: ['a', 3, {}], extra: 1, density: 'zzz' } })).profile;
  r.ctl_import_sanitized = !!evil && evil.pz === 'mid' && evil.w.a.v === 0 && evil.w.a.off === true && !evil.w.b && evil.sm.s1 === 'hide' && !evil.sm.s2 && evil.saved.length === 1 && !('extra' in evil) && evil.density === 'normal';
  // đặt lại
  const pr = mk(); C.resetTaste(pr);
  r.ctl_reset = Object.keys(pr.w).length === 0 && Object.keys(pr.src).length === 0 && Object.keys(pr.sm).length === 0 && pr.pz === 'mid' && pr.stats.like === 0;
  r.ctl_reset_keeps_saved = pr.saved.includes('s1') && pr.role === 'dev' && pr.desk === 'ai';
  // bật/tắt chủ đề: tắt thì điểm về 0, bật lại khôi phục đúng; chủ đề lạ tắt = không làm gì
  const pt = R.newProfile(null, [tA], now); const w0 = R.weight(pt, tA, now);
  C.setTopic(pt, tA, false, now); const wOff = R.weight(pt, tA, now); C.setTopic(pt, tA, true, now);
  r.ctl_topic_toggle = w0 > 0.9 && wOff === 0 && Math.abs(R.weight(pt, tA, now) - w0) < 1e-9 && C.setTopic(pt, 'khong-co', false) === false && C.setTopic(pt, 'moi', true) === true && !!pt.w.moi;
  // nguồn: ẩn loại khỏi danh sách; giảm xuống thấp hơn nhưng còn; trở lại bình thường
  const src = A.map(a => a.source).filter(Boolean)[0], ps = R.newProfile(null, [tA], now), ids = () => R.rank(A, ps, day.topics, () => 0.5, now, { page: 200 }).map(i => i.a.id);
  const base = ids(), had = A.some(a => a.source === src);
  C.setSource(ps, src, 'hide'); const hid = ids().length === 0 || !R.rank(A, ps, day.topics, () => 0.5, now, { page: 200 }).some(i => i.a.source === src);
  C.setSource(ps, src, 'less'); const less = ids(), first = base.findIndex(id => A.find(a => a.id === id).source === src), nowIdx = less.findIndex(id => A.find(a => a.id === id).source === src);
  C.setSource(ps, src, null);
  r.ctl_source_modes = had && hid && less.length === base.length && nowIdx >= first && ids().join() === base.join() && !('sm' in ps && src in ps.sm);
  // thanh trượt đổi xếp hạng + tỉ lệ khám phá; Vừa = như chưa có mức
  const pl = R.newProfile(null, [tA, tB], now); R.feedback(pl, A.find(a => a.topics.includes(tA)), 'like', null, now);
  const top = lv => { const q = JSON.parse(JSON.stringify(pl)); C.setLevel(q, lv); return R.rank(A, q, day.topics, () => 0.5, now, { page: 24 }); };
  const ord = lv => top(lv).map(i => i.a.id).join(), exp = lv => top(lv).filter(i => i.explore).length;
  r.ctl_level_changes_rank = ord('low') !== ord('high') && C.setLevel(pl, 'bad') === false && C.setLevel(pl, 'low') === true;
  r.ctl_level_explore_share = R.LEVELS.low.explore > R.LEVELS.mid.explore && R.LEVELS.mid.explore > R.LEVELS.high.explore && exp('low') >= exp('mid') && exp('mid') >= exp('high');
  const legacy = JSON.parse(JSON.stringify(pl)); delete legacy.pz; delete legacy.sm;
  const mid = JSON.parse(JSON.stringify(pl)); C.setLevel(mid, 'mid');
  r.ctl_default_mid_same = R.rank(A, legacy, day.topics, () => 0.5, now, {}).map(i => i.a.id).join() === R.rank(A, mid, day.topics, () => 0.5, now, {}).map(i => i.a.id).join() && R.ensure(legacy).pz === 'mid';
}
console.log(JSON.stringify(r));

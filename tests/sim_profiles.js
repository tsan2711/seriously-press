// Mô phỏng hồ sơ: 2 hồ sơ không lẫn sở thích, xoá sạch, di trú, đề xuất. In JSON.
const R = require('../web/rank.js'), P = require('../web/profiles.js'), fs = require('fs');
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
console.log(JSON.stringify(r));

// Mô phỏng M3/M4 chạy bằng node; in JSON kết quả. Gọi từ sim_personalize.py
const R = require('../web/rank.js'), fs = require('fs');
const day = JSON.parse(fs.readFileSync(__dirname + '/../public/today.json', 'utf8'));
// Dữ liệu mô phỏng: today.json chỉ còn tin mới sau dedup (ít, lệch chủ đề) → bài lấy từ kho thô 3 ngày gần nhất, topics từ today.json
const sd = fs.readdirSync(__dirname + '/../store').filter(f => /^\d{4}-\d\d-\d\d\.json$/.test(f)).sort().slice(-3), seenId = new Set();
const topics = day.topics, arts = [].concat(...sd.map(f => JSON.parse(fs.readFileSync(__dirname + '/../store/' + f, 'utf8')).articles)).filter(a => !seenId.has(a.id) && seenId.add(a.id));
function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const res = {};
// chọn chủ đề A có >=3 bài và nằm ngoài ban mặc định để thấy rõ tác dụng
const cnt = {}; arts.forEach(a => a.topics.forEach(t => cnt[t] = (cnt[t] || 0) + 1));
const A = Object.keys(cnt).filter(t => cnt[t] >= 3).sort((x, y) => cnt[x] - cnt[y])[0];
const inA = a => a.topics.includes(A);
const now = Date.now();
// 1) mặc định: không hồ sơ → xếp theo độ nổi
let p = R.newProfile(null, [], now);
const base = R.rank(arts, p, topics, mulberry(1), now).slice(0, 5).map(x => x.a.id);
// 2) 20 lần thích A
const likeTarget = arts.filter(inA)[0];
for (let i = 0; i < 20; i++) R.feedback(p, likeTarget, 'like', null, now);
const after = R.rank(arts, p, topics, mulberry(2), now);
res.A = A; res.topA_after_like = inA(after[0].a);
// 3) xoá → mặc định
p = R.reset() || R.newProfile(null, [], now);
const back = R.rank(arts, p, topics, mulberry(1), now).slice(0, 5).map(x => x.a.id);
res.reset_equals_default = JSON.stringify(back) === JSON.stringify(base);
// 4) tỉ lệ khám phá: người dùng quan tâm vài chủ đề, 200 lượt xếp hạng ngẫu nhiên
const interests = Object.keys(topics).filter(t => topics[t].desks.includes('gamedev')).slice(0, 3);
let ex = 0, tot = 0, nonzero = 0;
for (let s = 0; s < 200; s++) {
  const pr = R.newProfile('gamedev', interests, now);
  const r = R.rank(arts, pr, topics, mulberry(100 + s), now);
  const e = r.filter(x => x.explore).length; ex += e; tot += r.length; if (e) nonzero++;
}
res.explore_rate = ex / tot; res.explore_runs_nonzero = nonzero;
// 5) thăng hạng sau 3 lần thích chủ đề được khám phá
const pr = R.newProfile('gamedev', interests, now);
const r0 = R.rank(arts, pr, topics, mulberry(7), now);
const e0 = r0.find(x => x.explore);
res.explore_label = e0 ? e0.why : null;
if (e0) {
  const T = e0.topic;
  const wasMain = R.isMain(pr, T, now);
  for (let i = 0; i < 3; i++) R.feedback(pr, e0.a, 'like', T, now);
  res.promoted = !wasMain && R.isMain(pr, T, now);
  const r1 = R.rank(arts, pr, topics, mulberry(8), now);
  res.promoted_not_labelled_new = !r1.some(x => x.explore && x.topic === T);
}
// 6) ẩn bài
p = R.newProfile(null, [], now); R.feedback(p, arts[0], 'hide', null, now);
res.hide_works = !R.rank(arts, p, topics, mulberry(3), now).some(x => x.a.id === arts[0].id);
console.log(JSON.stringify(res));

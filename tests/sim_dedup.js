// Mô phỏng người đọc 14 ngày: mỗi ngày mở trang, lọc theo seen-store, "thấy" mọi bài hiện, mở vài bài. In JSON kết quả.
const D = require('../web/dedup.js'); const days = JSON.parse(process.argv[2]);
const store = D.open(D.memStore(), 'me'); const out = { days: [], relapse: 0, update_shown: false, mirror_hidden: true, same_day_once: true };
const shownBefore = new Map();   // sid → rev đã hiện
days.forEach(([date, arts], di) => {
  const now = Date.parse(date + 'T10:00:00Z'); const seen = store.load();
  const f = D.filter(seen, arts, now); const ids = new Set();
  f.show.forEach(a => { const s = a.sid; if (ids.has(s)) out.same_day_once = false; ids.add(s);
    if (shownBefore.has(s) && shownBefore.get(s) >= a.rev && a._lab !== 'Cập nhật' && Date.parse(date) > 0) { const prevDay = shownBefore.get(s + '@d'); if (prevDay !== date) out.relapse++; }
    if (a.url === 'https://g.example.com/451' && a._lab === 'Cập nhật') out.update_shown = true; });
  if (arts.some(a => a.url === 'https://mirror.example.net/g451') && f.show.some(a => a.url === 'https://mirror.example.net/g451')) out.mirror_hidden = false;
  f.show.forEach((a, i) => { store.mark(a, i % 3 === 0, now); shownBefore.set(a.sid, a.rev); shownBefore.set(a.sid + '@d', date); });
  out.days.push({ date, shown: f.show.length, hidden: f.hidden.length });
});
out.store_size = Object.keys(store.load().st).length;
console.log(JSON.stringify(out));

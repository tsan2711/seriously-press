// Công cụ đọc (web-reader-tools) — lõi không phụ thuộc trình duyệt: phím j/k/o/s/?, "Đã đọc tất cả" + Hoàn tác có hạn 8 giây.
// Mọi thứ cần từ ngoài (thẻ, kho, hẹn giờ) được truyền vào để test mô phỏng bằng DOM tối giản.
(function (root) {
  const UNDO_MS = 8000, WPM = 200;
  // Số phút đọc ước tính từ số từ (≥1). Build ghi cùng công thức ở theme.read_min().
  const minutes = words => Math.max(1, Math.ceil((+words || 0) / WPM));
  const typing = t => !!t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName || '') || !!t.isContentEditable);
  const KEYS = [['j', 'Bài kế tiếp'], ['k', 'Bài trước'], ['o', 'Mở bài (đọc nhanh)'], ['s', 'Lưu đọc sau'], ['/', 'Tìm kiếm'], ['?', 'Bảng phím này']];
  // ctx: {cards(), cur(), mark(card), open(card), save(card), help(), blocked()}. Trả true nếu đã xử lý phím.
  function handle(e, ctx) {
    if (e.ctrlKey || e.metaKey || e.altKey || typing(e.target) || (ctx.blocked && ctx.blocked())) return false;
    const k = e.key, cs = ctx.cards();
    if (k === '?') { e.preventDefault(); ctx.help(); return true; }
    if (!cs.length || !'jkos'.includes(k) || k.length !== 1) return false;
    const c = ctx.cur(), i = c ? cs.indexOf(c) : -1;
    if (k === 'j' || k === 'k') { const n = Math.max(0, Math.min(cs.length - 1, i < 0 ? 0 : i + (k === 'j' ? 1 : -1))); e.preventDefault(); ctx.mark(cs[n]); return true; }
    const t = c || cs[0]; e.preventDefault(); if (k === 'o') ctx.open(t); else if (k === 's') ctx.save(t); return true;
  }
  // "Đã đọc tất cả": ghi vào kho đã-đọc một lần, nhớ ảnh chụp để Hoàn tác trong 8 giây. env: {store, key, cards, art(card), markRead(arts), timer(fn, ms), clear(h)}
  function markAll(env) {
    const cs = env.cards().filter(c => !c.hidden), snap = env.store.getItem(env.key), had = cs.filter(c => c.classList.contains('read'));
    env.markRead(cs.map(env.art)); cs.forEach(c => c.classList.add('read'));
    let live = true, h = null;
    const done = () => { live = false; if (h != null) env.clear(h); };
    h = env.timer(() => { live = false; }, UNDO_MS);
    return {
      n: cs.length, ms: UNDO_MS, active: () => live,
      undo() { if (!live) return false; done(); if (snap == null) env.store.removeItem(env.key); else env.store.setItem(env.key, snap); cs.forEach(c => { if (!had.includes(c)) c.classList.remove('read'); }); return true; },
    };
  }
  // "Tiếp tục đọc": nhớ bài đang đọc + vị trí cuộn theo số báo (ngày). Kho lỗi/đầy → trả false, không ném.
  const flow = {
    key: pid => 'press.flow.' + (pid || 'me'),
    save(store, key, s) { try { store.setItem(key, JSON.stringify({ d: s.d, id: s.id || '', t: String(s.t || '').slice(0, 90), y: Math.max(0, Math.round(+s.y || 0)) })); return true; } catch (e) { return false; } },
    // chỉ khôi phục đúng số báo và khi thật sự đã đọc đi đâu đó (có bài hoặc đã cuộn > 400px)
    load(store, key, day) { try { const o = JSON.parse(store.getItem(key)); return o && o.d === day && (o.id || o.y > 400) ? o : null; } catch (e) { return null; } },
    // thẻ đầu tiên còn nằm (một phần) trong khung nhìn: bottom > top
    firstVisible(rects, top) { for (let i = 0; i < rects.length; i++) if (rects[i].bottom > top) return i; return -1; },
  };
  const api = { minutes, typing, handle, markAll, flow, KEYS, UNDO_MS, WPM };
  if (typeof module !== 'undefined') module.exports = api; else root.PressReadTools = api;
})(typeof self !== 'undefined' ? self : this);

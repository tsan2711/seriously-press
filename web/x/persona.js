// Cá nhân hoá dài hạn (U6) — lõi thuần. Đầu vào là nhật ký cục bộ (journal.days: {ngày:{n:{open,seen,skip…},h:{giờ:số}}}).
(function (root) {
  const lastDays = (j, today, k) => { const out = []; for (let i = 0; i < k; i++) { const key = new Date(Date.parse(today) - i * 864e5).toISOString().slice(0, 10); if (j && j.days && j.days[key]) out.push([key, j.days[key]]); } return out; };
  // giờ đọc quen → 'sang' (<12) | 'chieu' (12–17) | 'toi' (≥17); cần ≥ 3 ngày và ≥ 6 sự kiện, ngược lại null (không đoán)
  function slot(j, today) {
    const ds = lastDays(j, today, 14), h = new Array(24).fill(0); if (ds.length < 3) return null;
    ds.forEach(([, d]) => Object.keys(d.h || {}).forEach(k => { h[+k] += d.h[k]; })); const tot = h.reduce((a, b) => a + b, 0); if (tot < 6) return null;
    const m = h.slice(0, 12).reduce((a, b) => a + b, 0), e = h.slice(17).reduce((a, b) => a + b, 0), a = tot - m - e;
    return m >= a && m >= e ? 'sang' : e >= a ? 'toi' : 'chieu';
  }
  const SLOT = { sang: 'Số báo sáng', chieu: 'Số báo chiều', toi: 'Số báo tối' };
  // gợi ý mật độ từ hành vi (không tự đổi): mở/ngày ≤1,5 → gọn; ≥8 → nhiều; cần ≥ 3 ngày
  function suggestDensity(j, today, cur) {
    const ds = lastDays(j, today, 14); if (ds.length < 3) return null;
    const per = ds.reduce((s, [, d]) => s + (d.n && d.n.open || 0), 0) / ds.length, to = per >= 8 ? 'rich' : per <= 1.5 ? 'compact' : 'normal';
    return to === cur ? null : { to, per: Math.round(per * 10) / 10 };
  }
  // cảnh báo quá tải: limit = giới hạn bài/ngày người dùng tự đặt (0 = tắt). Gợi ý đặt khi 3 ngày liền > 25 bài/ngày
  function overload(j, today, limit) {
    const d = j && j.days && j.days[today], read = d && d.n ? (d.n.open || 0) : 0;
    const heavy = lastDays(j, today, 3).length === 3 && lastDays(j, today, 3).every(([, x]) => (x.n && x.n.open || 0) > 25);
    return { read, over: !!limit && read >= limit, suggest: !limit && heavy, left: limit ? Math.max(0, limit - read) : null };
  }
  // chống bong bóng lọc: bảo đảm ≥ share (mặc định 15%) bài hiển thị nằm ngoài chủ đề chính; thiếu thì thay các bài cuối bằng bài ngoài-chủ-đề tốt nhất còn lại
  function ensureExplore(shown, pool, mainTopics, share) {
    share = share == null ? 0.15 : share; const main = new Set(mainTopics), isOut = a => !(a.topics || []).some(t => main.has(t)), ids = new Set(shown.map(a => a.id));
    const need = Math.ceil(shown.length * share) - shown.filter(isOut).length; if (need <= 0) return { list: shown.slice(), added: 0 };
    const extra = pool.filter(a => !ids.has(a.id) && isOut(a)).slice(0, need), list = shown.slice(); let k = list.length - 1, add = 0;
    for (const x of extra) { while (k >= 0 && isOut(list[k])) k--; if (k < 0) break; list[k--] = Object.assign({}, x, { explore: true }); add++; }
    return { list, added: add };
  }
  const api = { slot, SLOT, suggestDensity, overload, ensureExplore, lastDays };
  if (typeof module !== 'undefined') module.exports = api; else root.PressPersona = api;
})(typeof self !== 'undefined' ? self : this);

// Nhật ký duyệt theo ngày — CỤC BỘ (localStorage 'press.journal.<người đọc>'), không gửi đi đâu, không lên repo.
// Mỗi ngày: đếm sự kiện (n), giờ hoạt động (h), từng bài đã thấy/mở/... (items, ≤120/ngày). Giữ 365 ngày.
(function (root) {
  const PFX = 'press.journal.', KEEP_DAYS = 365, MAX_ITEMS = 120, EVENTS = ['seen', 'open', 'skip', 'like', 'save', 'less', 'hide', 'dwell', 'rate'];
  const dkey = ms => new Date(ms).toISOString().slice(0, 10);
  const empty = () => ({ v: 1, days: {} });
  const newDay = () => ({ n: { seen: 0, open: 0, skip: 0, like: 0, save: 0, less: 0, hide: 0 }, dwell_s: 0, h: {}, items: {} });

  function record(j, ev, a, now, amount) {
    if (!EVENTS.includes(ev) || !a || !a.id) return j;
    now = now || Date.now();
    const k = dkey(now), d = (j.days[k] = j.days[k] || newDay());
    if (ev in d.n) d.n[ev]++;
    if (ev === 'dwell') d.dwell_s += Math.min(Math.max(+amount || 0, 0), 600);
    const hr = new Date(now).getHours(); d.h[hr] = (d.h[hr] || 0) + 1;
    let it = d.items[a.id];
    if (!it) {
      if (Object.keys(d.items).length >= MAX_ITEMS) return j;      // đủ chi tiết, chỉ còn đếm
      it = d.items[a.id] = { t: String(a.title || '').slice(0, 140), s: String(a.source || '').slice(0, 40), topics: (a.topics || []).slice(0, 4), desk: (a.desks || [])[0] || null, ev: {} };
    }
    it.ev[ev] = ev === 'dwell' ? Math.min((it.ev.dwell || 0) + (+amount || 0), 600) : ev === 'rate' ? Math.min(Math.max(+amount || 3, 1), 5) : (it.ev[ev] || 0) + 1;
    return j;
  }
  function prune(j, now) {
    const cut = dkey((now || Date.now()) - KEEP_DAYS * 86400000);
    Object.keys(j.days).forEach(k => { if (k < cut) delete j.days[k]; });
    return j;
  }
  // Gộp ngoài vào (nhập file): cộng đếm, gộp bài; không vượt giới hạn.
  function merge(j, o, now) {
    if (!o || typeof o.days !== 'object') return { added: 0, error: 'Tệp nhật ký không hợp lệ.' };
    let added = 0;
    Object.keys(o.days).forEach(k => {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(k)) return; const s = o.days[k]; if (!s || typeof s.n !== 'object') return;
      if (!j.days[k]) { j.days[k] = Object.assign(newDay(), { n: Object.assign(newDay().n, s.n), dwell_s: +s.dwell_s || 0, h: s.h || {}, items: {} }); added++; }
      Object.keys(s.items || {}).forEach(id => { if (!j.days[k].items[id] && Object.keys(j.days[k].items).length < MAX_ITEMS) j.days[k].items[id] = s.items[id]; });
    });
    prune(j, now); return { added };
  }
  // Tổng hợp một khoảng ngày [fromKey..toKey]: đếm theo chủ đề {seen, open, skip}, nguồn, ban, giờ.
  function span(j, fromKey, toKey) {
    const out = { days: 0, n: { seen: 0, open: 0, skip: 0, like: 0, save: 0, less: 0, hide: 0 }, dwell_s: 0, topics: {}, desks: {}, sources: {}, hours: {} };
    Object.keys(j.days).sort().forEach(k => {
      if (k < fromKey || k > toKey) return; const d = j.days[k]; out.days++; out.dwell_s += d.dwell_s || 0;
      Object.keys(d.n).forEach(e => { out.n[e] = (out.n[e] || 0) + d.n[e]; });
      Object.keys(d.h || {}).forEach(h => { out.hours[h] = (out.hours[h] || 0) + d.h[h]; });
      Object.values(d.items).forEach(it => {
        const o = it.ev.open || 0, sk = it.ev.skip || 0, sn = (it.ev.seen || 0) + o + sk;
        (it.topics || []).forEach(t => { const x = (out.topics[t] = out.topics[t] || { seen: 0, open: 0, skip: 0 }); x.seen += sn; x.open += o; x.skip += sk; });
        if (it.desk) { const x = (out.desks[it.desk] = out.desks[it.desk] || { seen: 0, open: 0, skip: 0 }); x.seen += sn; x.open += o; x.skip += sk; }
        if (it.s) { const x = (out.sources[it.s] = out.sources[it.s] || { seen: 0, open: 0, skip: 0 }); x.seen += sn; x.open += o; x.skip += sk; }
      });
    });
    return out;
  }
  const memStore = () => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: k => { delete m[k]; } }; };
  // Kho theo người đọc.
  function open(store, id) {
    store = store || (typeof localStorage !== 'undefined' ? localStorage : memStore()); const key = PFX + id;
    const load = () => { try { const j = JSON.parse(store.getItem(key)); return j && typeof j.days === 'object' ? j : empty(); } catch (e) { return empty(); } };
    const save = j => { try { store.setItem(key, JSON.stringify(j)); return true; } catch (e) { return false; } };
    return {
      load, save,
      record(ev, a, now, amount) { const j = load(); record(j, ev, a, now, amount); prune(j, now); return save(j); },
      exportJSON() { return JSON.stringify(load()); },
      importJSON(txt) { let o; try { if (String(txt).length > 5e6) throw 0; o = JSON.parse(txt); } catch (e) { return { added: 0, error: 'Tệp nhật ký không hợp lệ.' }; } const j = load(), r = merge(j, o); if (!r.error) save(j); return r; },
      clear() { store.removeItem(key); },
    };
  }
  const api = { open, record, prune, merge, span, empty, newDay, dkey, memStore, PFX, KEEP_DAYS, MAX_ITEMS };
  if (typeof module !== 'undefined') module.exports = api; else root.PressJournal = api;
})(typeof self !== 'undefined' ? self : this);

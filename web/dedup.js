// Dedup qua ngày phía trình duyệt (K2): kho "đã thấy/đã đọc" THEO NGƯỜI ĐỌC, cục bộ (localStorage 'press.seen.<người đọc>').
// Cùng thuật toán chữ ký với kb.py (test parity). Một câu chuyện đã thấy ở ngày trước bị ẩn, TRỪ khi có update thật (rev tăng hoặc fact mới).
(function (root) {
  const STOP = new Set('the a an of to in on for and or with is are was be at by from as it this that how why what new show ask now you your we our vs via into over after about not no more than using use can will just get'.split(' '));
  const CAP_STOP = new Set(['The', 'How', 'Why', 'What', 'New', 'Show', 'Ask', 'When', 'Who', 'This', 'That', 'Your', 'You', 'Our', 'Introducing', 'Announcing', 'Now', 'After', 'Before']);
  const TOK = /[\p{L}\p{N}]+(?:[.\-][\p{L}\p{N}]+)*/gu, YEAR = /^(19|20)\d\d$/;
  const PFX = 'press.seen.', TTL_DAYS = 60, CAP = 1500;
  const DEF = { match: { jaccard_strong: 0.6, hamming_max: 3, jaccard_min_hamming: 0.3, jaccard_weak: 0.35, shared_entities: 2 } };
  const nfc = s => String(s == null ? '' : s).normalize('NFC');
  const toks = s => nfc(s).toLowerCase().match(TOK) || [];
  const keytoks = s => { const t = toks(s).filter(x => !STOP.has(x) && [...x].length > 1), k = t.filter(x => !/\d/.test(x)); return k.length >= 2 ? k : t; };   // số/phiên bản = fact, không phải danh tính
  const fnv = t => { let h = 0x811c9dc5; for (const b of new TextEncoder().encode(t)) h = Math.imul(h ^ b, 0x01000193) >>> 0; return h >>> 0; };
  function simhash(ts) { const v = new Array(32).fill(0); new Set(ts).forEach(t => { const h = fnv(t); for (let i = 0; i < 32; i++) v[i] += (h >>> i) & 1 ? 1 : -1; }); let r = 0; for (let i = 0; i < 32; i++) if (v[i] > 0) r = (r | (1 << i)) >>> 0; return r >>> 0; }
  const ham = (a, b) => { let x = (a ^ b) >>> 0, n = 0; while (x) { n += x & 1; x >>>= 1; } return n; };
  const facts = text => [...new Set(toks(text).filter(t => /\d/.test(t) && !YEAR.test(t) && [...t].length > 1))].sort();
  const entities = text => [...new Set((nfc(text).match(TOK) || []).filter(t => t.length >= 3 && t[0] >= 'A' && t[0] <= 'Z' && !CAP_STOP.has(t)).map(t => t.toLowerCase()))].sort();
  const canon = u => { try { const x = new URL(u); x.hash = ''; [...x.searchParams.keys()].forEach(k => { if (k.startsWith('utm_')) x.searchParams.delete(k); }); return x.protocol + '//' + x.hostname.toLowerCase().replace(/^www\./, '') + x.pathname.replace(/\/+$/, '') + x.search; } catch (e) { return String(u); } };
  const sig = a => { const kt = keytoks(a.title); return { kt, h: simhash(kt), f: facts(a.title + ' ' + (a.summary || '')), e: entities(a.title) }; };
  function jac(a, b) { a = new Set(a); b = new Set(b); if (!a.size || !b.size) return 0; let n = 0; a.forEach(x => { if (b.has(x)) n++; }); return n / (a.size + b.size - n); }
  function sameStory(s1, s2, c) {
    const m = (c || DEF).match, j = jac(s1.kt, s2.kt);
    if (j >= m.jaccard_strong) return true;
    if (ham(s1.h, s2.h) <= m.hamming_max && j >= m.jaccard_min_hamming) return true;
    return j >= m.jaccard_weak && s1.e.filter(x => s2.e.includes(x)).length >= m.shared_entities;
  }
  const dayKey = now => new Date(now || Date.now()).toISOString().slice(0, 10);
  const memStore = () => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: k => { delete m[k]; } }; };
  const empty = () => ({ v: 1, st: {} });   // st: khoá câu chuyện → {r:rev, d:ngày thấy đầu, o:đã mở, t:tiêu đề, f:fact[], h:simhash, k:canon id}

  // Một bài so với kho: 'new' | 'update' | 'repeat' (+ mục đã khớp). Khớp theo sid → URL chuẩn hoá → chữ ký tiêu đề.
  function judge(seen, a, cfg) {
    const st = seen.st, sg = a._sig || (a._sig = sig(a));
    let key = a.sid && st[a.sid] ? a.sid : st['u:' + canon(a.url)] ? 'u:' + canon(a.url) : null, e = key ? st[key] : null;
    if (!e) for (const k of Object.keys(st)) { const x = st[k]; if (x.h != null && sameStory(sg, { kt: keytoks(x.t), h: x.h, e: entities(x.t) }, cfg)) { e = x; key = k; break; } }
    if (!e) return { status: 'new', key: null, entry: null };
    const newf = sg.f.filter(f => !(e.f || []).includes(f));
    if ((a.rev || 0) > (e.r || 0) || newf.length) return { status: 'update', key, entry: e, note: newf.length ? 'Mới: ' + newf.slice(0, 3).join(', ') : (a.update_note || 'Có cập nhật') };
    return { status: 'repeat', key, entry: e };
  }
  // Ghi nhận "đã thấy" (read = đã mở). Giữ gọn: TTL + trần số mục.
  function mark(seen, a, read, now) {
    const k = a.sid || a.id || ('u:' + canon(a.url)), sg = a._sig || (a._sig = sig(a)), d = dayKey(now), j = judge(seen, a);
    const e = seen.st[j.key || k] || (seen.st[k] = { r: a.rev || 0, d, o: 0, t: String(a.title || '').slice(0, 90), f: sg.f.slice(0, 8), h: sg.h });
    if (j.status === 'update') { e.r = Math.max(e.r || 0, a.rev || 0); e.f = [...new Set([...(e.f || []), ...sg.f])].slice(0, 12); e.t = String(a.title || '').slice(0, 90); e.h = sg.h; e.u = d; }
    if (read) e.o = 1; e.l = d; return seen;
  }
  function prune(seen, now) {
    const cut = dayKey((now || Date.now()) - TTL_DAYS * 86400000), ks = Object.keys(seen.st);
    ks.forEach(k => { if ((seen.st[k].l || seen.st[k].d) < cut) delete seen.st[k]; });
    const left = Object.keys(seen.st); if (left.length > CAP) left.sort((a, b) => (seen.st[a].l || '').localeCompare(seen.st[b].l || '')).slice(0, left.length - CAP).forEach(k => delete seen.st[k]);
    return seen;
  }
  // Lọc danh sách hôm nay theo người đọc: {show:[bài + _lab], hidden:[bài đã thấy hôm trước]}. Cùng sid trong 1 ngày chỉ giữ bài đầu.
  function filter(seen, arts, now, cfg) {
    const today = dayKey(now), show = [], hidden = [], got = new Set();
    arts.forEach(a => {
      const j = judge(seen, a, cfg), sid = a.sid || a.id || canon(a.url);
      if (got.has(sid)) { hidden.push(Object.assign({}, a, { _lab: 'trùng' })); return; }
      if (j.status === 'repeat' && j.entry.d < today) { hidden.push(Object.assign({}, a, { _lab: j.entry.o ? 'Đã đọc' : 'Đã thấy' })); return; }
      got.add(sid);
      show.push(Object.assign({}, a, { _lab: j.status === 'update' ? 'Cập nhật' : (j.entry && j.entry.o ? 'Đã đọc' : j.entry ? '' : 'Mới'), _note: j.note || a.update_note || '' }));
    });
    return { show, hidden };
  }
  function open(store, id) {
    store = store || (typeof localStorage !== 'undefined' ? localStorage : memStore()); const key = PFX + id;
    const load = () => { try { const j = JSON.parse(store.getItem(key)); return j && typeof j.st === 'object' ? j : empty(); } catch (e) { return empty(); } };
    const save = j => { try { store.setItem(key, JSON.stringify(prune(j))); return true; } catch (e) { return false; } };
    return { load, save, mark(a, read, now) { const j = load(); mark(j, a, read, now); return save(j); }, clear() { store.removeItem(key); }, key };
  }
  const api = { sig, toks, keytoks, facts, entities, simhash, ham, jac, canon, sameStory, judge, mark, prune, filter, open, empty, dayKey, memStore, fnv, DEF, PFX, TTL_DAYS, CAP };
  if (typeof module !== 'undefined') module.exports = api; else root.PressDedup = api;
})(typeof self !== 'undefined' ? self : this);

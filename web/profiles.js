// Hồ sơ người đọc — cục bộ (localStorage), không tài khoản, không gửi đi đâu (spec §1, §4).
// Mỗi hồ sơ có khoá riêng 'press.p.<id>' chứa hồ sơ xếp hạng (rank.js newProfile: sở thích, đã lưu, ẩn, khám phá).
// Danh mục 'press.profiles' chỉ giữ {id, name, kind}. Xoá hồ sơ = xoá khoá riêng + dòng danh mục → sạch.
(function (root) {
  const CAT = 'press.profiles', PFX = 'press.p.', JPFX = 'press.journal.', OPFX = 'press.ob.', STEPS = 3, LEGACY = 'press.profile', ME = 'me', MAX = 8;
  const memStore = () => { const m = {}; return { getItem: k => (k in m ? m[k] : null), setItem: (k, v) => { m[k] = String(v); }, removeItem: k => { delete m[k]; }, keys: () => Object.keys(m) }; };

  const b64 = j => (typeof btoa === 'function' ? btoa : x => Buffer.from(x, 'binary').toString('base64'))(unescape(encodeURIComponent(j)));
  const unb64 = t => decodeURIComponent(escape((typeof atob === 'function' ? atob : x => Buffer.from(x, 'base64').toString('binary'))(t)));

  function open(store) {
    store = store || (typeof localStorage !== 'undefined' ? localStorage : memStore());
    const rd = k => { try { return JSON.parse(store.getItem(k)); } catch (e) { return null; } };
    const wr = (k, v) => store.setItem(k, JSON.stringify(v));
    let cat = rd(CAT);
    if (!cat || !Array.isArray(cat.list)) {
      cat = { v: 2, active: null, list: [{ id: ME, name: 'Tôi', kind: 'me' }] };
      const old = store.getItem(LEGACY);                       // chuyển hồ sơ M3 cũ sang 'Tôi'
      if (old) { store.setItem(PFX + ME, old); store.removeItem(LEGACY); }
      wr(CAT, cat);
    }
    if (!cat.list.some(x => x.id === ME)) cat.list.unshift({ id: ME, name: 'Tôi', kind: 'me' });
    const flush = () => wr(CAT, cat);
    const uid = () => 'p' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    const find = id => cat.list.find(x => x.id === id);

    return {
      list: () => cat.list.map(x => ({ id: x.id, name: x.name, kind: x.kind, hasData: !!store.getItem(PFX + x.id) })),
      active: () => cat.active,                                // null = chưa chọn → hiện màn chọn
      canCreate: () => cat.list.length < MAX,
      // Tạo hồ sơ mới (người đọc khác). Trả id, hoặc null nếu hết chỗ / tên rỗng.
      create(name, profile) {
        name = String(name || '').trim().slice(0, 24);
        if (!name || cat.list.length >= MAX) return null;
        const id = uid(); cat.list.push({ id, name, kind: 'other' });
        if (profile) wr(PFX + id, profile);
        flush(); return id;
      },
      // Bước onboarding đang dở (1..STEPS) của một người đọc; 0 = không có. Lưu ngay → đóng tab rồi mở lại vẫn tiếp được.
      step(id) { if (!find(id)) return 0; const n = parseInt(store.getItem(OPFX + id), 10); return n >= 1 && n <= STEPS ? n : 0; },
      setStep(id, n) { if (!find(id)) return 0; n = Math.max(1, Math.min(STEPS, n | 0)); store.setItem(OPFX + id, String(n)); return n; },
      doneStep(id) { store.removeItem(OPFX + id); },
      pending: () => { const x = cat.list.find(y => { const n = parseInt(store.getItem(OPFX + y.id), 10); return n >= 1 && n <= STEPS; }); return x ? x.id : null; },
      select(id) { if (!find(id)) return false; cat.active = id; flush(); return true; },
      leave() { cat.active = null; flush(); },                 // quay về màn chọn
      load: id => (find(id) ? rd(PFX + id) : null),            // null = chưa onboarding
      save(id, p) { if (find(id)) wr(PFX + id, p); },
      rename(id, name) { const x = find(id); name = String(name || '').trim().slice(0, 24); if (!x || !name) return false; x.name = name; flush(); return true; },
      clear(id) { if (!find(id)) return false; store.removeItem(PFX + id); store.removeItem(JPFX + id); store.removeItem(OPFX + id); return true; },   // xoá sở thích, giữ thẻ
      // 'Tôi' không xoá được khỏi danh mục, chỉ xoá sạch dữ liệu (về chưa onboarding). Người khác: xoá hẳn.
      remove(id) {
        const x = find(id); if (!x) return false;
        store.removeItem(PFX + id); store.removeItem(JPFX + id); store.removeItem(OPFX + id);   // xoá cả nhật ký
        if (x.kind !== 'me') cat.list = cat.list.filter(y => y.id !== id);
        if (cat.active === id) cat.active = null;
        flush(); return true;
      },
      // Đồng bộ giữa máy: mã văn bản 'press1.<base64>' (không qua mạng). Dán sang máy kia → nhập.
      exportAll() {
        const profiles = {}; cat.list.forEach(x => { const p = rd(PFX + x.id); if (p) profiles[x.id] = p; });
        const j = JSON.stringify({ v: 1, list: cat.list.map(x => ({ id: x.id, name: x.name, kind: x.kind })), profiles });
        return 'press1.' + b64(j);
      },
      // Trả {added, merged, error}. 'Tôi' chỉ bị ghi đè khi máy này chưa có dữ liệu; người khác nhập thành hồ sơ mới (không trùng id).
      importAll(code) {
        let o; try { code = String(code || '').trim(); if (!code.startsWith('press1.') || code.length > 400000) throw 0; o = JSON.parse(unb64(code.slice(7))); } catch (e) { return { added: 0, merged: 0, error: 'Mã không hợp lệ.' }; }
        if (!o || !Array.isArray(o.list) || typeof o.profiles !== 'object') return { added: 0, merged: 0, error: 'Mã không hợp lệ.' };
        let added = 0, merged = 0;
        o.list.forEach(x => {
          const p = o.profiles[x.id]; if (!p || typeof p !== 'object' || typeof p.w !== 'object') return;
          if (x.id === ME || x.kind === 'me') { if (!store.getItem(PFX + ME)) { wr(PFX + ME, p); merged++; } return; }
          const name = String(x.name || '').trim().slice(0, 24); if (!name || cat.list.length >= MAX) return;
          const id = uid(); cat.list.push({ id, name, kind: 'other' }); wr(PFX + id, p); added++;
        });
        flush(); return { added, merged };
      },
      // Xoá mọi dấu vết hồ sơ trên thiết bị này
      wipe() { cat.list.forEach(x => { store.removeItem(PFX + x.id); store.removeItem(JPFX + x.id); store.removeItem(OPFX + x.id); }); store.removeItem(CAT); store.removeItem(LEGACY); },
    };
  }

  // Đề xuất khi tạo hồ sơ mới: mỗi ban → bộ chủ đề gợi ý (chủ đề thuộc ban, nhiều bài nhất). Thuần dữ liệu, không hồ sơ nào lộ.
  function suggest(data, perDesk) {
    perDesk = perDesk || 4;
    const cnt = {}; (data.articles || []).forEach(a => (a.topics || []).forEach(t => { cnt[t] = (cnt[t] || 0) + 1; }));
    return Object.entries(data.desks || {}).map(([id, d]) => {
      const ts = Object.keys(data.topics || {}).filter(t => (data.topics[t].desks || []).includes(id))
        .sort((a, b) => (cnt[b] || 0) - (cnt[a] || 0)).slice(0, perDesk);
      return { desk: id, name: d.name, topics: ts };
    }).filter(s => s.topics.length);
  }

  // Điều hướng bước: dir +1 (Tiếp / Bỏ qua) hoặc -1 (Quay lại). Trả bước mới, hoặc 0 = xong (Vào đọc). Không vượt biên.
  const nav = (cur, dir) => { const n = (cur | 0) + dir; return n > STEPS ? 0 : Math.max(1, n); };
  const api = { open, suggest, memStore, nav, ME, MAX, STEPS };
  if (typeof module !== 'undefined') module.exports = api; else root.PressProfiles = api;
})(typeof self !== 'undefined' ? self : this);

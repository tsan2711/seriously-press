// Chia sẻ mở, KHÔNG tài khoản, KHÔNG link, KHÔNG quyền riêng (Bi 11-22). Logic thuần, kho KV trừu tượng → chạy trong Worker, test bằng node.
// kv = { get(k)→string|null, put(k,string), del(k), list(prefix)→[key] }.
// "Chủ" của một ghi chú = id ngẫu nhiên do trình duyệt tự sinh (cid, ở localStorage) — chỉ lưu SHA-256 của nó, nên chỉ máy đó xoá được bài mình.
// Chống spam khi ai cũng vào được: trần theo cid/ngày, trần theo IP-băm/ngày, trần toàn cục/ngày, trần lưu trữ.
// Nội dung người dùng = không tin: cắt độ dài, bỏ ký tự điều khiển, URL chỉ http(s); FE phải escape khi hiển thị.
(function (root) {
  const L = { name: 24, note: 140, title: 200, url: 500, perDay: 10, perIpDay: 30, globalDay: 300, keep: 400, feed: 30, cid: [16, 64] };
  const BAD = ['ignore previous', 'ignore all previous', 'disregard the above', 'system prompt'];
  const cryptoObj = () => (typeof crypto !== 'undefined' && crypto.subtle ? crypto : require('node:crypto').webcrypto);
  async function sha(s) { const b = await cryptoObj().subtle.digest('SHA-256', new TextEncoder().encode(s)); return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join(''); }
  function rand(n) { const a = new Uint8Array(n || 18); cryptoObj().getRandomValues(a); return [...a].map(x => x.toString(16).padStart(2, '0')).join(''); }
  const txt = (s, n) => String(s == null ? '' : s).replace(/[\u0000-\u001f\u007f<>]/g, ' ').replace(/\s+/g, ' ').trim().slice(0, n);
  const bad = s => BAD.some(m => s.toLowerCase().includes(m));
  const okCid = c => typeof c === 'string' && /^[0-9a-f]+$/.test(c) && c.length >= L.cid[0] && c.length <= L.cid[1];
  function cleanUrl(u) {
    try { const x = new URL(String(u)); if (!/^https?:$/.test(x.protocol) || x.username || x.password || !x.hostname.includes('.') || /^\d+\.\d+\.\d+\.\d+$/.test(x.hostname) || x.hostname.endsWith('.local')) return null;
      x.hash = ''; const s = x.toString(); return s.length <= L.url ? s : null; } catch (e) { return null; }
  }
  const err = (code, msg) => ({ ok: false, code, error: msg });

  function create(kv, opts) {
    opts = opts || {}; const now = opts.now || (() => Date.now());
    const jget = async k => { const v = await kv.get(k); try { return v ? JSON.parse(v) : null; } catch (e) { return null; } };
    const jput = (k, v) => kv.put(k, JSON.stringify(v));
    const day = () => new Date(now()).toISOString().slice(0, 10);
    const bump = async (k, cap) => { const n = +(await kv.get(k) || 0); if (n >= cap) return false; await kv.put(k, String(n + 1)); return true; };

    return {
      L,
      // Ghi chú/giới thiệu bài: ẩn danh hoặc tên tự đặt. cid = chủ (chỉ lưu băm). ipHash do Worker truyền (đã băm), có thể rỗng.
      async share(cid, p, ipHash) {
        if (!okCid(cid)) return err(400, 'Thiếu mã máy (cid).');
        p = p || {}; const url = cleanUrl(p.url), title = txt(p.title, L.title), note = txt(p.note, L.note), by = txt(p.name, L.name) || 'Ẩn danh';
        if (!url || !title) return err(400, 'Cần url http(s) và tiêu đề.');
        if (bad(title) || bad(note) || bad(by)) return err(400, 'Nội dung bị chặn.');
        const owner = await sha(cid), d = day();
        if (!await bump('rl:g:' + d, L.globalDay)) return err(429, 'Hôm nay chia sẻ đã đầy, thử lại ngày mai.');
        if (ipHash && !await bump('rl:i:' + ipHash + ':' + d, L.perIpDay)) return err(429, 'Mạng này chia sẻ quá nhiều hôm nay.');
        if (!await bump('rl:c:' + owner + ':' + d, L.perDay)) return err(429, `Tối đa ${L.perDay} lượt chia sẻ mỗi ngày.`);
        for (const k of await kv.list('sh:')) { const s = await jget(k); if (s && s.own === owner && s.url === url) return err(409, 'Bạn đã chia sẻ bài này.'); }
        const ts = now(), sid = rand(5), key = 'sh:' + String(9e15 - ts).padStart(16, '0') + ':' + sid;   // khoá tăng dần = mới nhất trước
        await jput(key, { id: sid, own: owner, by, url, title, note, ts });
        const all = await kv.list('sh:'); for (const k of all.slice(L.keep)) await kv.del(k);        // giữ tối đa L.keep, bỏ cũ nhất
        return { ok: true, id: sid };
      },
      // Xoá được CHỈ bài của mình (cùng cid).
      async remove(cid, sid) {
        if (!okCid(cid)) return err(400, 'Thiếu mã máy (cid).');
        const owner = await sha(cid);
        for (const k of await kv.list('sh:')) { const s = await jget(k); if (s && s.id === sid) { if (s.own !== owner) return err(403, 'Không phải bài của bạn.'); await kv.del(k); return { ok: true }; } }
        return err(404, 'Không có.');
      },
      // Feed công khai: gộp theo url, KHÔNG lộ id/chủ; chỉ tên hiển thị + ghi chú.
      async feed(limit) {
        const by = new Map();
        for (const k of await kv.list('sh:')) {
          const s = await jget(k); if (!s) continue; const g = by.get(s.url) || { url: s.url, title: s.title, ts: s.ts, people: [], notes: [] };
          g.people.push(s.by); if (s.note) g.notes.push({ by: s.by, note: s.note }); g.ts = Math.max(g.ts, s.ts); by.set(s.url, g);
        }
        const rows = [...by.values()].sort((a, b) => b.people.length - a.people.length || b.ts - a.ts).slice(0, Math.min(limit || L.feed, L.feed));
        return { ok: true, items: rows.map(g => ({ url: g.url, title: g.title, count: g.people.length, people: [...new Set(g.people)].slice(0, 5), notes: g.notes.slice(0, 3), ts: g.ts })) };
      },
      // Mục của riêng máy gọi (để hiện nút Xoá).
      async mine(cid) {
        if (!okCid(cid)) return err(400, 'Thiếu mã máy (cid).');
        const owner = await sha(cid), out = []; for (const k of await kv.list('sh:')) { const s = await jget(k); if (s && s.own === owner) out.push({ id: s.id, url: s.url, title: s.title, note: s.note, ts: s.ts }); }
        return { ok: true, items: out };
      },
    };
  }
  function memKV() { const m = new Map(); return { get: async k => (m.has(k) ? m.get(k) : null), put: async (k, v) => { m.set(k, String(v)); }, del: async k => { m.delete(k); }, list: async p => [...m.keys()].filter(k => k.startsWith(p)).sort(), _m: m }; }
  const api = { create, memKV, sha, rand, cleanUrl, okCid, L };
  if (typeof module !== 'undefined') module.exports = api; else root.PressShare = api;
})(typeof self !== 'undefined' ? self : this);

// Cloudflare Worker (free) — HTTP bọc quanh web/share-core.js (chia sẻ mở, không tài khoản) + /fetch proxy CORS cho nút "Chạy báo hôm nay".
// KHÔNG có bí mật nào. Biến: ALLOW_ORIGIN (vd https://<user>.github.io), PROXY_HOSTS (danh sách host nguồn, phẩy; xuất bằng `python3 press.py hosts`).
// /fetch KHÔNG bao giờ nhận API key; chỉ GET text từ host trong PROXY_HOSTS. Key AI đi thẳng trình duyệt → nhà cung cấp.
import { create, sha } from '../web/share-core.js';

const kvOf = ns => ({
  get: k => ns.get(k), put: (k, v) => ns.put(k, v), del: k => ns.delete(k),
  list: async p => { const out = []; let cursor; do { const r = await ns.list({ prefix: p, cursor }); out.push(...r.keys.map(x => x.name)); cursor = r.list_complete ? null : r.cursor; } while (cursor); return out.sort(); },
});
const MAXFETCH = 1_500_000;

export default {
  async fetch(req, env) {
    const origin = env.ALLOW_ORIGIN || '', ok = origin && req.headers.get('Origin') === origin;
    const cors = { 'Access-Control-Allow-Origin': ok ? origin : 'null', 'Access-Control-Allow-Headers': 'authorization,content-type', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Vary': 'Origin' };
    const send = (o, st) => new Response(JSON.stringify(o), { status: st || (o.ok === false ? o.code || 400 : 200), headers: { 'content-type': 'application/json', ...cors } });
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (!ok) return send({ ok: false, error: 'Origin không được phép.' }, 403);
    const u = new URL(req.url), path = u.pathname;
    if (req.method === 'GET' && path === '/fetch') {          // proxy đọc nguồn công khai (RSS/Atom/JSON) — chỉ host trong danh sách cho phép
      let t; try { t = new URL(u.searchParams.get('url') || ''); } catch (e) { return send({ ok: false, error: 'URL sai.' }, 400); }
      const hosts = (env.PROXY_HOSTS || '').split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
      if (!/^https:$/.test(t.protocol) || t.username || t.password || t.port || !hosts.includes(t.hostname.toLowerCase())) return send({ ok: false, error: 'Host không nằm trong danh sách nguồn.' }, 403);
      const r = await fetch(t.toString(), { headers: { 'user-agent': 'press-room/0.2 (RSS reader proxy)' }, redirect: 'manual', cf: { cacheTtl: 600 } });
      if (!r.ok) return send({ ok: false, error: 'Nguồn trả ' + r.status }, 502);
      const body = (await r.text()).slice(0, MAXFETCH);
      return new Response(body, { status: 200, headers: { 'content-type': 'text/plain; charset=utf-8', ...cors } });
    }
    const ip = req.headers.get('CF-Connecting-IP'), ipHash = ip ? (await sha('ip:' + ip)).slice(0, 24) : '';
    const core = create(kvOf(env.PRESS));
    const cid = (req.headers.get('authorization') || '').replace(/^Bearer\s+/i, '');
    let body = {};
    if (req.method === 'POST') { const t = await req.text(); if (t.length > 4096) return send({ ok: false, error: 'Quá lớn.' }, 413); try { body = JSON.parse(t || '{}'); } catch (e) { return send({ ok: false, error: 'JSON sai.' }, 400); } }
    if (req.method === 'GET' && path === '/feed') return send(await core.feed());
    if (req.method === 'GET' && path === '/mine') return send(await core.mine(cid));
    if (req.method !== 'POST') return send({ ok: false, error: 'Không có.' }, 404);
    if (path === '/share') return send(await core.share(cid, body, ipHash));
    if (path === '/delete') return send(await core.remove(cid, body.id));
    return send({ ok: false, error: 'Không có.' }, 404);
  },
};

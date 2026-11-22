/* Chia sẻ mở (không tài khoản): giới thiệu bài kèm ghi chú; feed "Mọi người thấy hay". Chỉ chạy khi config/share.toml có endpoint (meta press-share).
   Máy tự sinh mã ngẫu nhiên 'press.cid' (localStorage) để chỉ máy đó xoá được bài của mình; tên hiển thị tuỳ chọn 'press.name'. Mọi chữ từ máy chủ hiển thị bằng textContent. */
(() => {
  const D = document, ep = (D.querySelector('meta[name=press-share]') || {}).content; if (!ep) return;
  const base = ep.replace(/\/$/, '');
  const cid = (() => { try { let c = localStorage.getItem('press.cid'); if (!/^[0-9a-f]{32}$/.test(c || '')) { const a = new Uint8Array(16); crypto.getRandomValues(a); c = [...a].map(x => x.toString(16).padStart(2, '0')).join(''); localStorage.setItem('press.cid', c); } return c; } catch (e) { return null; } })();
  if (!cid) return;
  const api = (path, body) => fetch(base + path, { method: body ? 'POST' : 'GET', headers: { 'content-type': 'application/json', authorization: 'Bearer ' + cid }, body: body ? JSON.stringify(body) : undefined })
    .then(r => r.json()).catch(() => ({ ok: false, error: 'Không kết nối được máy chủ chia sẻ.' }));
  const myName = () => { try { return localStorage.getItem('press.name') || ''; } catch (e) { return ''; } };

  // ----- bài: nút Giới thiệu -----
  const sb = D.querySelector('[data-share]');
  if (sb) {
    sb.hidden = false;
    sb.addEventListener('click', () => { const msg = D.querySelector('[data-share-msg]'), note = prompt('Ghi chú cho mọi người (tối đa 140 ký tự, có thể để trống):', ''); if (note === null) return;
      (window.PressData || Promise.resolve(null)).then(d => { const a = d && d.articles.find(x => x.id === sb.dataset.id); if (!a) return;
        api('/share', { url: a.url, title: a.title, note, name: myName() }).then(r => { msg.textContent = r.ok ? 'Đã giới thiệu cho mọi người.' : (r.error || 'Lỗi.'); }); }); });
  }

  // ----- trang chủ: feed chung -----
  const fs = D.querySelector('[data-sharefeed]');
  if (fs) {
    const ul = fs.querySelector('[data-sf-list]'), msg = fs.querySelector('[data-sf-msg]');
    Promise.all([api('/feed'), api('/mine')]).then(([f, mine]) => {
      if (!f.ok || !f.items.length) return; fs.hidden = false; ul.textContent = '';
      const own = {}; if (mine.ok) mine.items.forEach(x => { own[x.url] = x.id; });
      f.items.forEach(x => { const li = D.createElement('li'), a = D.createElement('a'), s = D.createElement('small');
        a.href = /^https?:\/\//.test(x.url) ? x.url : '#'; a.rel = 'noopener'; a.textContent = x.title;
        s.textContent = ' — ' + x.count + ' người thấy hay: ' + x.people.join(', ') + (x.notes.length ? ' · “' + x.notes[0].note + '” (' + x.notes[0].by + ')' : '');
        li.append(a, s);
        if (own[x.url]) { const b = D.createElement('button'); b.type = 'button'; b.className = 'chip'; b.textContent = 'Xoá của tôi';
          b.addEventListener('click', () => api('/delete', { id: own[x.url] }).then(r => { if (r.ok) li.remove(); else msg.textContent = r.error || 'Lỗi.'; })); li.append(' ', b); }
        ul.append(li); });
    });
  }
})();

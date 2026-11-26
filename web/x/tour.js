/* Gợi ý lần đầu (nhẹ, không chặn): 3 chấm nhỏ cạnh điều khiển (Lưu / Xem ít hơn / Ctrl+K) + một khay ngắn có nút "Đã hiểu".
   Cờ đã xem lưu theo hồ sơ ở localStorage 'press.tour.<id>' → bấm "Đã hiểu" (hoặc Esc) là hết, không hiện lại. Không mạng. Mọi chữ bằng textContent. */
(function (root) {
  const KEY = 'press.tour.';
  const HINTS = [
    { id: 'save', sel: '[data-save]', label: 'Lưu', text: 'Lưu: giữ bài để đọc sau — nút “Lưu bài” ở trang bài, hoặc phím s.' },
    { id: 'less', sel: '[data-less]', label: 'Xem ít hơn', text: 'Xem ít hơn: bấm ở thẻ bài nếu không muốn thấy chủ đề/nguồn này nữa — trang sẽ ưu tiên tin khác.' },
    { id: 'search', sel: '[data-search]', label: 'Ctrl+K', text: 'Ctrl+K (hoặc /): tìm nhanh chủ đề, ban, bài.' },
  ];
  const seen = (store, id) => { try { return store.getItem(KEY + id) === '1'; } catch (e) { return false; } };
  const mark = (store, id) => { try { store.setItem(KEY + id, '1'); return true; } catch (e) { return false; } };
  // Chỉ hiện khi: đã có hồ sơ (đã chọn chủ đề), chưa xem, và không ở màn chọn người đọc.
  const shouldShow = (store, id, hasProfile, page) => !!id && !!hasProfile && page !== 'picker' && !seen(store, id);

  function mount(D, store, id, onDone) {
    if (D.querySelector('[data-tour]')) return null;
    const mk = (t, c, x) => { const n = D.createElement(t); if (c) n.className = c; if (x != null) n.textContent = x; return n; };
    const box = mk('aside', 'tour'); box.setAttribute('data-tour', ''); box.setAttribute('role', 'region'); box.setAttribute('aria-label', 'Gợi ý lần đầu');
    const ul = mk('ul', 'tour-l'), dots = [];
    HINTS.forEach(h => {  // 'Xem ít hơn' do addLess ghim sau khi thẻ vẽ xong
      const li = mk('li'); li.append(mk('span', 'tour-dot'), mk('span', '', h.text)); ul.append(li);
      const a = D.querySelector(h.sel);
      if (a && a.parentNode) { const d = mk('span', 'tour-dot tour-pin'); d.setAttribute('aria-hidden', 'true'); d.title = h.label; a.parentNode.insertBefore(d, a.nextSibling); dots.push(d); }
    });
    const ok = mk('button', 'btn', 'Đã hiểu'); ok.type = 'button'; ok.setAttribute('data-tour-ok', '');
    const close = () => { mark(store, id); dots.forEach(d => d.remove()); box.remove(); D.removeEventListener('keydown', key, true); if (onDone) onDone(); };
    const key = e => { if (e.key === 'Escape') { close(); } };
    ok.addEventListener('click', close);
    box.addEventListener('keydown', key);   // bỏ qua bằng bàn phím khi tiêu điểm trong khay
    D.addEventListener('keydown', key, true);
    box.append(mk('p', 'tour-t', 'Ba mẹo nhỏ — bỏ qua cũng được (Esc).'), ul, ok);
    (D.querySelector('main') || D.body).prepend(box);
    return box;
  }

  // Nút "Xem ít hơn" ở thẻ bài (app.js nghe [data-less] → tín hiệu 'less'). Thẻ 'Dành cho bạn' vẽ muộn nên quét lại khi DOM đổi.
  function addLess(D) {
    D.querySelectorAll('.card[data-id]').forEach(c => {
      const cb = c.querySelector('.cb'); if (!cb || c.querySelector('[data-less]') || c.classList.contains('hub')) return;
      const b = D.createElement('button'); b.type = 'button'; b.className = 'btn less'; b.setAttribute('data-less', ''); b.dataset.id = c.dataset.id; b.textContent = 'Xem ít hơn'; b.title = 'Không hứng thú: bớt hiện tin cùng chủ đề/nguồn này';
      b.addEventListener('click', () => { b.textContent = 'Đã bớt ✓'; b.disabled = true; }); cb.append(b);
      const t = D.querySelector('[data-tour]'); if (t && !D.querySelector('.tour-pin[data-for="less"]')) { const d = D.createElement('span'); d.className = 'tour-dot tour-pin'; d.dataset.for = 'less'; d.setAttribute('aria-hidden', 'true'); b.after(d); }
    });
  }
  function init(D, PP) {
    const page = D.documentElement.dataset.page; let db; try { db = PP.open(); } catch (e) { return; }
    const id = db.active(); if (!id) return;
    if (D.querySelector('[data-foryou]') && typeof MutationObserver === 'function') { let q = 0; new MutationObserver(() => { if (!q) q = setTimeout(() => { q = 0; addLess(D); }, 200); }).observe(D.querySelector('[data-foryou]'), { childList: true, subtree: true }); addLess(D); }
    const p = db.load(id), has = !!(p && p.w && Object.keys(p.w).length);
    if (shouldShow(localStorage, id, has, page)) mount(D, localStorage, id);
  }
  const api = { KEY, HINTS, seen, mark, shouldShow, mount, init, addLess };
  if (typeof module !== 'undefined') module.exports = api; else { root.PressTour = api; if (root.document && root.PressProfiles) root.PressTour.init(root.document, root.PressProfiles); }
})(typeof self !== 'undefined' ? self : this);

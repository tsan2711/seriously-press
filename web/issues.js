/* Bộ chọn số báo ở trang chủ: ◀ ngày ▶ + danh sách 14 ngày; đổi ngày KHÔNG tải lại trang.
   Nguồn: issues.json (bản cron, công khai) + localStorage 'press.issues' (bản bạn tự chạy, chỉ ở máy này). Mọi chữ hiển thị bằng textContent. */
(() => {
  const D = document, bar = D.querySelector('[data-issues]'), grid = D.querySelector('main .grid'); if (!bar || !grid) return;
  const ctl = bar.querySelector('.isu-c'), sel = bar.querySelector('[data-isu-sel]'), line = bar.querySelector('[data-isu-line]');
  const pad = n => String(n).padStart(2, '0'), dm = d => pad(d.getDate()) + '.' + pad(d.getMonth() + 1), hm = d => pad(d.getHours()) + ':' + pad(d.getMinutes());
  const no = date => { const n = Math.round((Date.parse(date) - Date.parse('2026-11-20')) / 864e5) + 1; return 'Số ' + String(Math.max(n, 1)).padStart(4, '0'); };
  const hue = s => { let h = 0; for (const c of String(s || '')) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
  const el = (t, cls, txt) => { const x = D.createElement(t); if (cls) x.className = cls; if (txt != null) x.textContent = txt; return x; };
  const origNodes = [...grid.childNodes], TODAY = bar.dataset.today, origLine = line.textContent, cache = {};
  const ok = u => /^https?:\/\//i.test(u || '');

  function card(a, i) {
    const c = el('article', 'card' + (i === 0 ? ' lead' : '')); c.dataset.id = a.id || ''; c.dataset.st = a.st || 'new'; c.style.setProperty('--i', i);
    const th = el('div', 'thumb'); th.style.setProperty('--h', a.h != null ? a.h : hue(a.s)); th.setAttribute('aria-hidden', 'true');
    if (ok(a.i)) { const im = D.createElement('img'); im.src = a.i; im.alt = 'Ảnh bài: ' + String(a.t).slice(0, 90); im.width = 640; im.height = 360; im.loading = i === 0 ? 'eager' : 'lazy'; im.decoding = 'async'; im.referrerPolicy = 'no-referrer'; im.addEventListener('error', () => im.remove()); th.append(im); th.setAttribute('aria-hidden', 'false'); }
    const cb = el('div', 'cb'); if (a.st === 'update') cb.append(el('span', 'lab lab-up', 'Cập nhật'));
    const h = el('h3'), l = el('a', '', a.t); l.href = ok(a.u) ? a.u : '#'; l.rel = 'noopener'; h.append(l); cb.append(h, el('p', 'meta', a.m || a.s || ''));
    c.append(th, cb); return c;
  }
  const localList = () => { try { const l = JSON.parse(localStorage.getItem('press.issues')); return Array.isArray(l) ? l : []; } catch (e) { return []; } };
  let list = [], cur = 0;
  const label = (e, i) => e.src === 'local' ? dm(new Date(e.ts)) + ' ' + hm(new Date(e.ts)) + ' · ' + e.by + ' (máy này)' : (e.date === TODAY ? 'Hôm nay' : dm(new Date(e.date + 'T00:00')) + ' · ' + e.by) + (e.date === TODAY ? ' · ' + e.by : '');
  const info = e => { const t = new Date(e.ts); return (e.no || no(e.date)) + ' · ' + dm(t) + ' ' + hm(t) + ' · chạy bởi ' + e.by + (e.src === 'local' ? ' (máy này)' : '') + ' · ' + e.new + ' mới, ' + (e.up || 0) + ' cập nhật' + (e.srcs ? ' · ' + e.srcs + ' nguồn' : ''); };
  const note = D.querySelector('[data-dd-note]');
  async function show(i) {
    const e = list[i]; if (!e) return; cur = i; sel.value = String(i);
    const isToday = e.src !== 'local' && e.date === TODAY;
    if (isToday) { grid.replaceChildren(...origNodes); line.textContent = origLine; if (note) note.style.display = ''; return; }
    let arts = e.articles;
    if (!arts) { grid.classList.add('sk-load'); line.textContent = 'Đang tải số báo…'; try { arts = cache[e.file] = cache[e.file] || (await (await fetch(e.file)).json()).articles; } catch (x) { grid.classList.remove('sk-load'); line.textContent = 'Không tải được số báo này. Kiểm tra mạng rồi chọn lại ngày.'; return; } }
    grid.classList.remove('sk-load');
    if (cur !== i) return;   // người dùng đã chuyển tiếp
    grid.replaceChildren(...arts.slice(0, 24).map(card)); line.textContent = info(e); if (note) note.style.display = 'none';
  }
  const idle = f => ('requestIdleCallback' in window ? requestIdleCallback(f, { timeout: 2000 }) : setTimeout(f, 300));
  addEventListener('load', () => idle(async () => {
    let pub = []; try { pub = (await (await fetch('issues.json')).json()).issues || []; } catch (e) {}
    const loc = localList().map(x => Object.assign({}, x, { src: 'local', articles: (x.articles || []).map(a => ({ id: a.id, t: a.title, u: a.url, s: a.source, m: a.source, st: a.isNew === false ? 'repeat' : 'new', h: hue((a.topics || [])[0]) })) }));
    list = pub.concat(loc).filter(e => e.ts).sort((a, b) => Date.parse(b.ts) - Date.parse(a.ts)).slice(0, 14 + loc.length);
    if (list.length < 2) return;
    list.forEach((e, i) => { const o = el('option', '', label(e, i)); o.value = i; sel.append(o); }); sel.querySelector('option:not([value])') && sel.querySelector('option:not([value])').remove();
    cur = Math.max(0, list.findIndex(e => e.src !== 'local' && e.date === TODAY)); sel.value = String(cur); ctl.hidden = false;
    sel.addEventListener('change', () => show(+sel.value));
    bar.querySelector('[data-isu-prev]').addEventListener('click', () => show(Math.min(cur + 1, list.length - 1)));
    bar.querySelector('[data-isu-next]').addEventListener('click', () => show(Math.max(cur - 1, 0)));
  }));
})();

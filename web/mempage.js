/* Trang "Bộ nhớ của tôi": xem / ghim / tắt / xoá mục nhớ, thêm tay, xuất-nhập, quên đã thấy. Chỉ localStorage. */
(function () {
  const D = document, root = D.querySelector('[data-mem]'); if (!root) return;
  const PM = window.PressMemory, PD = window.PressDedup, PP = window.PressProfiles; if (!PM || !PP) return;
  const db = PP.open(), id = db.active() || 'me', mo = PM.open(null, id), $ = s => root.querySelector(s);
  const who = db.list().find(x => x.id === id); { const w = D.querySelector('[data-mm-who]'); if (w) w.textContent = who ? who.name : 'Tôi'; }
  const msg = t => { $('[data-mm-msg]').textContent = t; };
  const KIND = { topic: 'chủ đề', source: 'nguồn', fact: 'thói quen' };
  function paint() {
    const m = mo.load(), v = PM.view(m, Date.now());
    ['long', 'mid', 'short'].forEach(t => {
      const ul = $('[data-mm-' + t + ']'); ul.textContent = '';
      const li = v.filter(x => x.tier === t);
      if (!li.length) { const e = D.createElement('li'); e.textContent = 'Chưa có mục nào.'; ul.append(e); return; }
      li.forEach(x => {
        const l = D.createElement('li'); if (x.off) l.dataset.off = '1';
        const n = D.createElement('span'); n.className = 'grow'; n.textContent = x.label + ' · ' + (KIND[x.kind] || x.kind) + (x.n > 1 ? ' · ' + x.n + ' lần' : '');
        const b = D.createElement('span'); b.className = 'bar'; b.setAttribute('role', 'img'); b.setAttribute('aria-label', 'Độ mạnh ' + Math.round(Math.abs(x.strength) * 100) + '%'); const i = D.createElement('i'); i.style.width = Math.min(100, Math.abs(x.strength) * 50) + '%'; b.append(i);
        const bt = (txt, act, pressed) => { const k = D.createElement('button'); k.type = 'button'; k.textContent = txt; if (pressed !== undefined) k.setAttribute('aria-pressed', pressed ? 'true' : 'false'); k.setAttribute('aria-label', txt + ': ' + x.label); k.addEventListener('click', () => { const mm = mo.load(); act(mm); mo.save(mm); paint(); }); return k; };
        l.append(n, b, bt('Ghim', mm => PM.pin(mm, x.id, !x.pin), !!x.pin), bt('Tắt', mm => PM.off(mm, x.id, !x.off), !!x.off), bt('Xoá', mm => PM.forget(mm, x.id)));
        ul.append(l);
      });
    });
    const sd = PD ? PD.open(null, id).load() : null; $('[data-mm-seen]').textContent = sd && Object.keys(sd.st).length ? 'đã thấy ' + Object.keys(sd.st).length + ' tin (giữ 60 ngày để không lặp)' : 'chưa thấy bài nào';
  }
  const sel = $('[data-mm-topic]');
  (window.PressData || Promise.resolve(null)).then(d => { const t = (d && d.topics) || {}; Object.keys(t).forEach(k => { const o = D.createElement('option'); o.value = k; o.textContent = t[k].label || k; sel.append(o); }); });
  $('[data-mm-add]').addEventListener('click', () => { if (!sel.value) return; const m = mo.load(); PM.add(m, 'topic', sel.value, sel.options[sel.selectedIndex].textContent, Date.now()); mo.save(m); msg('Đã ghim “' + sel.options[sel.selectedIndex].textContent + '”.'); paint(); });
  $('[data-mm-out]').addEventListener('click', () => { const a = D.createElement('a'); a.href = URL.createObjectURL(new Blob([mo.exportJSON()], { type: 'application/json' })); a.download = 'ban-tin-bo-nho.json'; a.click(); msg('Đã tải bộ nhớ.'); });
  $('[data-mm-in]').addEventListener('change', e => { const f = e.target.files[0]; if (!f) return; f.text().then(t => { const r = mo.importJSON(t); msg(r.error || 'Đã nhập ' + r.added + ' mục.'); paint(); }); });
  $('[data-mm-seenclr]').addEventListener('click', () => { if (PD && confirm('Quên các bài đã thấy? Tin cũ có thể hiện lại.')) { PD.open(null, id).clear(); msg('Đã quên các bài đã thấy.'); paint(); } });
  $('[data-mm-clear]').addEventListener('click', () => { if (confirm('Xoá toàn bộ bộ nhớ của người đọc này trên thiết bị?')) { const m = mo.load(); PM.clear(m); mo.save(m); msg('Đã xoá bộ nhớ.'); paint(); } });
  // Gu của tôi: chủ đề top theo hồ sơ (cùng số liệu với trang chọn người đọc)
  const PR = window.PressRank, tb = $('[data-mm-taste]');
  if (PR && tb) (window.PressData || Promise.resolve(null)).then(data => {
    const p = db.load(id); if (!p || !data) return; const rp = PR.report(PR.ensure(p), data.topics, Date.now(), 8);
    if (!rp.top.length && !rp.stats.open) return;
    const T = { rising: '↑ đang lên', fading: '↓ nhạt dần', steady: '→ ổn định' }, mx = Math.max(...rp.top.map(x => x.score), 1), ul = D.createElement('ul'); ul.className = 'taste';
    rp.top.forEach(x => { const li = D.createElement('li'), b = D.createElement('i'); b.style.width = Math.round(100 * x.score / mx) + '%'; b.setAttribute('aria-hidden', 'true'); li.append(b, D.createTextNode(x.label + ' · ' + T[x.trend])); ul.append(li); });
    const st = D.createElement('p'); st.className = 'm'; st.textContent = rp.days + ' ngày có hoạt động · mở ' + rp.stats.open + ', bỏ qua ' + rp.stats.skip + (rp.open_rate != null ? ' (tỉ lệ mở ' + Math.round(rp.open_rate * 100) + '%)' : '');
    tb.textContent = ''; tb.append(ul, st);
  });
  paint();
})();

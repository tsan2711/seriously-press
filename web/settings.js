/* Trang Cài đặt + bản chạy tại máy. Không tài khoản, ai vào cũng toàn quyền trên máy của mình.
   API key CHỈ ở localStorage 'press.ai' của máy này: file này không có lệnh mạng nào — việc gọi AI nằm trong run-core.js, đích duy nhất là nhà cung cấp.
   Bản chạy: 'press.run' = {date, articles}; nhật ký: 'press.runlog'. Mọi chữ hiển thị bằng textContent. */
(() => {
  const D = document, KEY = 'press.ai', RUN = 'press.run', LOG = 'press.runlog', NAME = 'press.name';
  const rd = k => { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } };
  const wr = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } };
  const today = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
  const el = (t, props, ...kids) => { const x = D.createElement(t); Object.assign(x, props || {}); x.append(...kids); return x; };
  const list = (ul, arts, n) => { ul.textContent = ''; arts.slice(0, n).forEach(a => { const li = el('li'), l = el('a', { href: /^https?:\/\//.test(a.url) ? a.url : '#', rel: 'noopener', textContent: a.title });
    li.append(l, el('small', { textContent: ' — ' + a.source + (a.summary ? ' · ' + a.summary : '') })); ul.append(li); }); };

  // ----- trang chủ: dải "Bản chạy tại máy" nếu hôm nay đã chạy -----
  const strip = D.querySelector('[data-localrun]');
  if (strip) { const r = rd(RUN); if (r && r.date === today() && r.articles && r.articles.length) { strip.hidden = false; strip.querySelector('[data-lr-n]').textContent = r.articles.length; list(strip.querySelector('[data-lr-list]'), r.articles, 10); } }

  const box = D.querySelector('[data-settings]'); if (!box) return;
  const $ = s => box.querySelector(s), msg = $('[data-set-msg]'), say = t => { msg.textContent = t; };

  // ----- tên hiển thị khi chia sẻ -----
  const nm = $('[data-name]'); try { nm.value = localStorage.getItem(NAME) || ''; } catch (e) {}
  $('[data-name-save]').addEventListener('click', () => { try { localStorage.setItem(NAME, nm.value.trim().slice(0, 24)); say('Đã lưu tên hiển thị (để trống = Ẩn danh).'); } catch (e) { say('Không lưu được.'); } });

  // ----- API key -----
  const prov = $('[data-ai-provider]'), key = $('[data-ai-key]'), model = $('[data-ai-model]'), st = $('[data-ai-state]');
  const maxA = $('[data-run-max]'), maxS = $('[data-run-sum]');
  const mask = k => k.length > 10 ? k.slice(0, 4) + '…' + k.slice(-3) : '•••';
  const drawKey = () => { const c = rd(KEY); st.textContent = c && c.key ? 'Đã lưu key ' + (c.provider === 'openai' ? 'OpenAI' : 'Anthropic') + ' (' + mask(c.key) + ') trên máy này.' : 'Chưa có key — nút Chạy vẫn hoạt động, tóm tắt chỉ là bản trích.'; if (c) { prov.value = c.provider || 'anthropic'; model.value = c.model || ''; } key.value = ''; };
  $('[data-ai-save]').addEventListener('click', () => { const old = rd(KEY) || {}, k = key.value.trim() || old.key; if (!k) { say('Dán key trước.'); return; }
    wr(KEY, { provider: prov.value, key: k, model: model.value.trim().slice(0, 60) }); drawKey(); say('Đã lưu key trên máy này.'); });
  $('[data-ai-clear]').addEventListener('click', () => { try { localStorage.removeItem(KEY); } catch (e) {} drawKey(); say('Đã xoá key khỏi máy này.'); });
  drawKey();
  const lim = rd('press.runcfg') || {}; maxA.value = lim.max || 30; maxS.value = lim.sum || 10;

  // ----- nhật ký -----
  const drawLog = () => { const ul = $('[data-run-log]'), L = rd(LOG) || []; ul.textContent = ''; if (!L.length) { ul.append(el('li', { textContent: 'Chưa chạy lần nào.' })); return; }
    L.forEach(e => ul.append(el('li', { textContent: e.date + ' ' + (e.ts || '').slice(11, 16) + ' — ' + e.articles + ' bài (' + e.fresh + ' mới), ' + e.sourceErrors + '/' + e.sources + ' nguồn lỗi, ' + (e.provider ? 'tóm tắt AI ' + e.summarized + ' bài (' + e.provider + ', ' + e.aiCalls + ' lượt gọi)' : 'bản trích, không AI') + (e.aiError ? ' · lỗi AI: ' + e.aiError : '') }))); };
  drawLog();
  const out = $('[data-run-out]'), draw = () => { const r = rd(RUN); if (r && r.date === today()) { out.hidden = false; list(out.querySelector('ul'), r.articles, 60); } };
  draw();

  // ----- nút Chạy báo hôm nay -----
  const go = $('[data-run-go]'), bar = $('[data-run-prog]'), cancel = $('[data-run-cancel]'); let ctl = null;
  if (cancel) cancel.addEventListener('click', () => { if (ctl) ctl.abort(); say('Đang huỷ…'); });
  go.addEventListener('click', async () => {
    const PR = window.PressRun; if (!PR) { say('Thiếu run-core.js.'); return; }
    const c = rd(KEY), max = Math.max(1, Math.min(+maxA.value || 30, PR.LIM.maxHard)), sum = Math.max(0, Math.min(+maxS.value || 0, PR.LIM.sumHard));
    wr('press.runcfg', { max, sum });
    if (c && c.key && !confirm('Sẽ gọi ' + (c.provider === 'openai' ? 'OpenAI' : 'Anthropic') + ' bằng key của bạn để tóm tắt tối đa ' + sum + ' bài (khoảng ' + Math.ceil(sum / PR.LIM.batch) + ' lượt gọi). Chi phí do bạn chịu. Tiếp tục?')) return;
    go.disabled = true; go.setAttribute('aria-busy', 'true'); go.dataset.l = go.textContent; go.textContent = 'Đang chạy…'; ctl = typeof AbortController !== 'undefined' ? new AbortController() : null; if (cancel) cancel.hidden = false; bar.hidden = false; say('Đang lấy nguồn…');
    try {
      const [src, today_] = await Promise.all([PR.loadSources(), (window.PressData || Promise.resolve(null))]);
      const ep = (D.querySelector('meta[name=press-share]') || {}).content || '';
      const r = await PR.run({ sources: src.feeds, hn: src.hn, topics: (today_ && today_.topics) || {}, known: ((today_ && today_.articles) || []).map(a => a.url), max, maxSummarize: sum, signal: ctl && ctl.signal, endpoint: ep, ai: c && c.key ? c : null,
        onProgress: p => { bar.hidden = false; if (p.step === 'fetch') { bar.max = p.total; bar.value = p.done; say('Lấy nguồn ' + p.done + '/' + p.total + '…'); } else say('Đang tóm tắt bằng AI…'); } });
      let who = ''; try { who = (localStorage.getItem(NAME) || '').trim().slice(0, 24); } catch (e) {} who = who || 'bạn';
      r.log.by = who; wr(RUN, { date: r.date, articles: r.articles }); wr(LOG, PR.pushLog(rd(LOG), r.log));
      // số báo bản tự chạy: chỉ ở máy này (≤14), hiện trong bộ chọn ngày ở trang chủ
      wr('press.issues', [{ ts: r.log.ts, date: r.date, by: who, src: 'local', n: r.articles.length, new: r.log.fresh, up: 0, srcs: r.log.sources, articles: r.articles.slice(0, 24).map(a => ({ id: a.id, title: a.title, url: a.url, source: a.source, topics: a.topics, isNew: a.isNew })) }].concat(rd('press.issues') || []).slice(0, 14)); drawLog(); draw(); const vw = $('[data-run-view]'); if (vw) vw.hidden = false;
      say('Xong: ' + r.articles.length + ' bài (' + r.log.fresh + ' mới), ' + (r.log.provider ? r.log.summarized + ' tóm tắt AI' : 'bản trích') + (r.log.aiError ? ' — lỗi AI: ' + r.log.aiError + ' (đã dùng bản trích)' : '') + (r.log.sourceErrors ? ' · ' + r.log.sourceErrors + ' nguồn lỗi' : '') + '. Về Trang chủ để xem — số báo vừa chạy tự hiện ở đầu (chỉ trên máy này).');
    } catch (e) { say(e && e.message === 'Đã huỷ' ? 'Đã huỷ — chưa ghi gì.' : 'Lỗi: ' + (e && e.message || e) + '. Thử lại, hoặc kiểm tra mạng.'); }
    go.disabled = false; go.removeAttribute('aria-busy'); go.textContent = go.dataset.l; bar.hidden = true; if (cancel) cancel.hidden = true; ctl = null;
  });
  $('[data-run-clear]').addEventListener('click', () => { try { localStorage.removeItem(RUN); localStorage.removeItem(LOG); localStorage.removeItem('press.issues'); } catch (e) {} out.hidden = true; drawLog(); say('Đã xoá bản chạy và nhật ký trên máy này.'); });
})();

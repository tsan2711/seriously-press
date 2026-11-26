// Mô phỏng DOM tối giản cho web/x/feedback.js: toast aria-live + Hoàn tác 6 giây (hẹn giờ giả), khoá bấm đúp, cập nhật lạc quan.
const FB = require(process.argv[2] + '/feedback.js'), r = {};
const mk = tag => { const n = { tagName: tag, children: [], attrs: {}, dataset: {}, cls: new Set(), hidden: false, textContent: '', listeners: {}, id: '', className: '',
  setAttribute(k, v) { n.attrs[k] = String(v); }, removeAttribute(k) { delete n.attrs[k]; }, getAttribute(k) { return k in n.attrs ? n.attrs[k] : null; },
  append(...c) { n.children.push(...c); }, addEventListener(e, f) { n.listeners[e] = f; }, click() { n.listeners.click && n.listeners.click(); },
  querySelector(s) { return n.children.find(c => '.' + c.className === s) || null; },
  classList: { add: x => n.cls.add(x), remove: x => n.cls.delete(x), contains: x => n.cls.has(x) } }; return n; };
const body = mk('body'), doc = { createElement: mk, getElementById: id => body.children.find(c => c.id === id) || null, body };
let now = 0, timers = []; const st = (f, ms) => { const t = { f, at: now + ms, on: true }; timers.push(t); return t; }, ct = t => { if (t) t.on = false; };
const tick = ms => { now += ms; timers.filter(t => t.on && t.at <= now).forEach(t => { t.on = false; t.f(); }); };
const T = FB.toaster({ doc, setTimeout: st, clearTimeout: ct }), box = body.children[0], msg = box.children[0], ub = box.children[1];
r.live_region = box.id === 'toast' && box.attrs.role === 'status' && box.attrs['aria-live'] === 'polite' && box.attrs['aria-atomic'] === 'true';
r.one_region = (() => { FB.toaster({ doc, setTimeout: st, clearTimeout: ct }); return body.children.length === 1; })();
// toast thường: chỉ đổi chữ, không có nút, tự tắt
T.show('Đã lưu bài.'); r.shows = msg.textContent === 'Đã lưu bài.' && box.cls.has('on') && ub.hidden === true; tick(3300); r.autohide = !box.cls.has('on');
// hoàn tác: có nút, đúng 6 giây, một lần
let undone = 0; T.show('Đã bỏ.', { undo: () => undone++ }); r.undo_btn = ub.hidden === false && ub.textContent === 'Hoàn tác';
tick(5900); r.undo_still = box.cls.has('on') && T.active(); tick(200); r.undo_expired = !box.cls.has('on') && !T.active() && T.undo() === false && undone === 0;
T.show('Đã theo dõi.', { undo: () => undone++ }); ub.click(); ub.click(); r.undo_once = undone === 1 && msg.textContent === 'Đã hoàn tác.' && ub.hidden === true;
r.undo_ms = FB.UNDO_MS === 6000;
// toast mới thay toast cũ: hoàn tác cũ không còn hiệu lực
let u1 = 0, u2 = 0; T.show('A', { undo: () => u1++ }); T.show('B', { undo: () => u2++ }); T.undo(); r.latest_wins = u1 === 0 && u2 === 1;
// chặn bấm đúp
(async () => {
  const b = mk('button'); b.textContent = 'Chạy báo'; let runs = 0, release; const gate = new Promise(res => (release = res));
  const p1 = FB.busy(b, async () => { runs++; await gate; return 'ok'; }, 'Đang chạy…');
  r.busy_state = b.disabled === true && b.textContent === 'Đang chạy…' && b.attrs['aria-busy'] === 'true';
  const p2 = FB.busy(b, async () => { runs++; }, 'Đang chạy…'); const s2 = await p2;
  r.double_click_blocked = s2.skipped === true && runs === 1;
  release(); const s1 = await p1; r.busy_restored = s1.value === 'ok' && !b.disabled && b.textContent === 'Chạy báo' && !('aria-busy' in b.attrs) && b.dataset.busy === undefined;
  const bf = mk('button'); bf.textContent = 'X'; let thrown = false; try { await FB.busy(bf, async () => { throw new Error('x'); }, 'Chờ…'); } catch (e) { thrown = true; }
  r.busy_restored_on_error = thrown && !bf.disabled && bf.textContent === 'X' && bf.dataset.busy === undefined;
  const s3 = await FB.busy(b, async () => { runs++; }); r.busy_reusable = s3.skipped === false && runs === 2;
  // lạc quan: apply ngay; commit hỏng (ném / false) → revert + onError; commit tốt → giữ
  const st_ = { v: 0, err: 0 }; let okRes = await FB.optimistic({ apply: () => { st_.v = 1; }, commit: () => true, revert: () => { st_.v = 0; }, onError: () => st_.err++ });
  r.opt_ok = okRes === true && st_.v === 1 && st_.err === 0;
  let seen; const p = FB.optimistic({ apply: () => { st_.v = 2; seen = st_.v; }, commit: async () => { throw new Error('quota'); }, revert: () => { st_.v = 1; }, onError: () => st_.err++ });
  r.opt_applies_first = seen === 2; okRes = await p; r.opt_throw_reverts = okRes === false && st_.v === 1 && st_.err === 1;
  okRes = await FB.optimistic({ apply: () => { st_.v = 3; }, commit: () => false, revert: () => { st_.v = 1; }, onError: () => st_.err++ }); r.opt_false_reverts = okRes === false && st_.v === 1 && st_.err === 2;
  console.log(JSON.stringify(r));
})();

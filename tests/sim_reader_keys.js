// Mô phỏng DOM tối giản cho web/x/readtools.js: chuyển thẻ j/k, không bắt phím khi gõ, o/s/?, Đã đọc tất cả + Hoàn tác (8 giây, hẹn giờ giả).
const RT = require(process.argv[2] + '/readtools.js'), r = {};
const mkCard = id => { const cl = new Set(); return { id, hidden: false, classList: { add: x => cl.add(x), remove: x => cl.delete(x), contains: x => cl.has(x) } }; };
const cs = ['a', 'b', 'c'].map(mkCard), log = [];
let curCard = null, dialog = false;
const ctx = { cards: () => cs, cur: () => curCard, blocked: () => dialog, mark: c => { curCard = c; log.push('mark:' + c.id); }, open: c => log.push('open:' + c.id), save: c => log.push('save:' + c.id), help: () => log.push('help') };
const key = (k, o) => { let pd = false; const e = Object.assign({ key: k, target: { tagName: 'BODY' }, preventDefault: () => { pd = true; } }, o || {}); const h = RT.handle(e, ctx); return { h, pd }; };
// chuyển thẻ
key('j'); key('j'); key('j'); key('j'); r.next_clamped = curCard.id === 'c';
key('k'); r.prev = curCard.id === 'b'; key('k'); key('k'); r.prev_clamped = curCard.id === 'a';
curCard = null; key('k'); r.first_when_none = curCard.id === 'a';
const n = log.length; r.prevent_default = key('j').pd === true;
// o / s / ? dùng thẻ hiện tại
curCard = cs[1]; key('o'); key('s'); key('?'); r.o_s_help = log.slice(-3).join() === 'open:b,save:b,help';
// không bắt phím khi gõ / có phím bổ trợ / hộp thoại / phím lạ
const before = log.length;
const typed = ['INPUT', 'TEXTAREA', 'SELECT'].map(t => key('j', { target: { tagName: t } })); typed.push(key('s', { target: { tagName: 'DIV', isContentEditable: true } }), key('?', { target: { tagName: 'INPUT' } }));
r.no_capture_typing = typed.every(x => !x.h && !x.pd) && log.length === before;
r.no_capture_mod = !key('j', { ctrlKey: true }).h && !key('s', { metaKey: true }).h && !key('o', { altKey: true }).h;
dialog = true; r.no_capture_dialog = !key('j').h; dialog = false;
r.other_keys_ignored = !key('x').h && !key('Shift').h && !key('os').h && log.length === before;
const empty = RT.handle({ key: 'j', target: {}, preventDefault() {} }, Object.assign({}, ctx, { cards: () => [] })); r.no_cards_ok = empty === false;
// thời gian đọc
r.min_floor = RT.minutes(0) === 1 && RT.minutes(5) === 1; r.min_ceil = RT.minutes(201) === 2 && RT.minutes(400) === 2 && RT.minutes(401) === 3;
// Đã đọc tất cả + Hoàn tác
const mem = {}, store = { getItem: k => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = v; }, removeItem: k => { delete mem[k]; } };
const timers = []; const env = (s) => ({ store, key: 'press.seen.me', cards: () => cs, art: c => ({ id: c.id }), markRead: arts => { store.setItem('press.seen.me', JSON.stringify(arts.map(a => a.id))); }, timer: (f, ms) => { timers.push({ f, ms }); return timers.length; }, clear: h => { timers[h - 1].f = null; } });
cs[2].hidden = true; cs[0].classList.add('read'); store.setItem('press.seen.me', 'OLD');
let h = RT.markAll(env());
r.readall_marks = h.n === 2 && mem['press.seen.me'] === '["a","b"]' && cs[1].classList.contains('read') && !cs[2].classList.contains('read');
r.undo_window = h.ms === 8000 && timers[0].ms === 8000 && h.active();
r.undo_restores = h.undo() === true && mem['press.seen.me'] === 'OLD' && !cs[1].classList.contains('read') && cs[0].classList.contains('read') && !h.active();
r.undo_once = h.undo() === false;
// hết 8 giây → không hoàn tác được nữa
delete mem['press.seen.me']; cs[0].classList.remove('read'); h = RT.markAll(env()); const t = timers[timers.length - 1]; t.f(); r.undo_expired = h.undo() === false && mem['press.seen.me'] === '["a","b"]';
// kho trống từ đầu → hoàn tác xoá khoá
delete mem['press.seen.me']; h = RT.markAll(env()); h.undo(); r.undo_to_empty = !('press.seen.me' in mem);
console.log(JSON.stringify(r));

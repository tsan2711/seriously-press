const T = require('../web/x/tour.js'), P = require('../web/profiles.js'), r = {};
const mem = () => P.memStore();
// cờ lưu theo hồ sơ, không lẫn nhau
let s = mem(); r.unseen = T.seen(s, 'me') === false;
T.mark(s, 'me'); r.flag_saved = T.seen(s, 'me') === true && s.getItem('press.tour.me') === '1' && T.seen(s, 'p2') === false;
// điều kiện hiện
s = mem();
r.show_first = T.shouldShow(s, 'me', true, 'home') === true;
r.hide_no_profile = T.shouldShow(s, 'me', false, 'home') === false && T.shouldShow(s, null, true, 'home') === false;
r.hide_picker = T.shouldShow(s, 'me', true, 'picker') === false;
T.mark(s, 'me'); r.not_twice = T.shouldShow(s, 'me', true, 'home') === false;
// DOM giả tối thiểu: mount → Esc đóng → cờ → mount lại không hiện (qua shouldShow)
const mk = tag => { const n = { tag, className: '', children: [], attrs: {}, ls: {}, textContent: '', parentNode: null,
  setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(e, f) { (this.ls[e] = this.ls[e] || []).push(f); },
  append(...c) { c.forEach(x => { x.parentNode = this; this.children.push(x); }); }, prepend(x) { x.parentNode = this; this.children.unshift(x); },
  remove() { const p = this.parentNode; if (p) p.children = p.children.filter(y => y !== this); this.parentNode = null; },
  insertBefore(x, ref) { x.parentNode = this; const i = this.children.indexOf(ref); this.children.splice(i < 0 ? this.children.length : i, 0, x); },
  get nextSibling() { const p = this.parentNode; return p ? p.children[p.children.indexOf(this) + 1] || null : null; },
  querySelector(sel) { const w = n => { for (const c of n.children) { if (c.match(sel) || w(c)) return c.match(sel) ? c : w(c); } return null; }; return w(this); },
  match(sel) { if (sel === 'main') return this.tag === 'main'; const m = sel.match(/^\[(data-[a-z-]+)\]$/); return !!m && (m[1] in this.attrs); } }; return n; };
const body = mk('body'), main = mk('main'); body.append(main);
const save = mk('button'); save.setAttribute('data-save', ''); main.append(save);
const kl = []; const D = { body, createElement: mk, querySelector: sel => body.querySelector(sel) || null,
  addEventListener(e, f) { if (e === 'keydown') kl.push(f); }, removeEventListener(e, f) { const i = kl.indexOf(f); if (i >= 0) kl.splice(i, 1); } };
s = mem(); let done = 0;
const box = T.mount(D, s, 'me', () => { done++; });
r.mounted = !!box && main.children[0] === box && box.attrs['data-tour'] === '' && box.attrs.role === 'region';
r.three_hints = T.HINTS.length === 3 && box.children[1].children.length === 3;
r.dot_beside_control = main.children.some(c => c.className.includes('tour-pin'));
r.has_ok_button = box.children[2].textContent === 'Đã hiểu' && box.children[2].type === 'button';
r.no_second_mount = T.mount(D, s, 'me') === null;
kl.forEach(f => f({ key: 'a' })); r.other_key_ignored = s.getItem('press.tour.me') === null && done === 0;
kl.slice().forEach(f => f({ key: 'Escape' }));
r.esc_dismiss = s.getItem('press.tour.me') === '1' && done === 1 && !main.children.some(c => c === box || c.className.includes('tour-pin')) && kl.length === 0;
r.after_esc_not_shown = T.shouldShow(s, 'me', true, 'home') === false;
// nút Đã hiểu
s = mem(); const b2 = T.mount(D, s, 'me'); b2.children[2].ls.click[0]();
r.ok_dismiss = s.getItem('press.tour.me') === '1' && !main.children.includes(b2);
// kho lỗi không làm hỏng
r.broken_store = (() => { const bad = { getItem() { throw 1; }, setItem() { throw 1; } }; return T.seen(bad, 'me') === false && T.mark(bad, 'me') === false; })();
console.log(JSON.stringify(r));

// Phản hồi tức thì (ux-feedback-states) — lõi không phụ thuộc trình duyệt: toast aria-live + Hoàn tác 6 giây,
// nút đang xử lý (disabled + nhãn chờ, chặn bấm đúp), cập nhật lạc quan (lỗi thì trả lại và báo). Chữ chỉ gán bằng textContent.
(function (root) {
  const UNDO_MS = 6000;
  // env: {doc, setTimeout, clearTimeout}. Toast là MỘT vùng role=status aria-live=polite tạo sẵn; mỗi lần show chỉ đổi chữ.
  function toaster(env) {
    const D = env.doc, st = env.setTimeout || setTimeout, ct = env.clearTimeout || clearTimeout;
    let box = D.getElementById('toast'), msg, ub, timer = null, undo = null;
    if (box && box._pf) return box._pf;   // một vùng toast = một bộ trạng thái (không nhân bản trình nghe)
    if (!box) {
      box = D.createElement('div'); box.id = 'toast'; box.setAttribute('role', 'status'); box.setAttribute('aria-live', 'polite'); box.setAttribute('aria-atomic', 'true');
      msg = D.createElement('span'); msg.className = 'tmsg'; ub = D.createElement('button'); ub.type = 'button'; ub.className = 'tundo'; ub.hidden = true;
      box.append(msg, ub); D.body.append(box);
    } else { msg = box.querySelector('.tmsg'); ub = box.querySelector('.tundo'); }
    const hide = () => { box.classList.remove('on'); ub.hidden = true; undo = null; timer = null; };
    const show = (text, o) => {
      o = o || {}; ct(timer); undo = typeof o.undo === 'function' ? o.undo : null;
      msg.textContent = text; ub.textContent = o.undoLabel || 'Hoàn tác'; ub.hidden = !undo; box.classList.add('on');
      timer = st(hide, undo ? (o.ms || UNDO_MS) : (o.ms || 3200));
    };
    // Hoàn tác chỉ một lần, chỉ trong cửa sổ; xong báo "Đã hoàn tác."
    const doUndo = () => { const f = undo; if (!f) return false; undo = null; ct(timer); f(); show('Đã hoàn tác.'); return true; };
    ub.addEventListener('click', doUndo);
    return (box._pf = { show, undo: doUndo, hide, active: () => !!undo, el: box });
  }
  // Nút đang xử lý: khoá ngay (đồng bộ) nên bấm đúp lần hai bị bỏ qua. fn có thể trả Promise; xong (hay lỗi) thì trả nút về như cũ.
  async function busy(btn, fn, label) {
    if (btn.dataset.busy === '1') return { skipped: true };
    const old = btn.textContent; btn.dataset.busy = '1'; btn.disabled = true; btn.setAttribute('aria-busy', 'true'); if (label) btn.textContent = label;
    try { return { skipped: false, value: await fn() }; }
    finally { delete btn.dataset.busy; btn.disabled = false; btn.removeAttribute('aria-busy'); if (label) btn.textContent = old; }
  }
  // Lạc quan: apply() đổi giao diện ngay; commit() ghi thật (ném lỗi hoặc trả false = hỏng) → revert() rồi onError().
  async function optimistic(o) {
    o.apply();
    try { if ((await o.commit()) === false) throw new Error('commit'); return true; }
    catch (e) { o.revert(); if (o.onError) o.onError(e); return false; }
  }
  root.PressFeedback = { toaster, busy, optimistic, UNDO_MS };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.PressFeedback;
})(typeof window !== 'undefined' ? window : globalThis);

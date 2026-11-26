#!/usr/bin/env python3
"""ux-feedback-states: toast aria-live + Hoàn tác 6 giây, nút đang xử lý (chặn bấm đúp), cập nhật lạc quan. Lõi chạy trên DOM mô phỏng (node), phần nối dây đọc web/ và public/ — offline."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
R = f'{d}/../public'; W = f'{d}/../web'; bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
def rd(p): return open(p, encoding='utf8').read()
r = json.loads(node(f'{d}/sim_feedback.js', os.path.abspath(f'{W}/x')))
for k, n in {'live_region': 'toast là vùng role=status aria-live=polite aria-atomic', 'one_region': 'chỉ một vùng toast (tái dùng, không nhân bản)', 'shows': 'toast đổi chữ + hiện, không nút khi không có hoàn tác',
             'autohide': 'toast thường tự tắt', 'undo_btn': 'toast có nút Hoàn tác khi có hành động hoàn tác', 'undo_still': 'còn hoàn tác ở giây 5,9', 'undo_expired': 'quá 6 giây không hoàn tác được',
             'undo_once': 'Hoàn tác chỉ một lần, rồi báo Đã hoàn tác.', 'undo_ms': 'cửa sổ hoàn tác đúng 6 giây', 'latest_wins': 'toast mới thay toast cũ (hoàn tác cũ hết hiệu lực)',
             'busy_state': 'nút chạy: disabled + aria-busy + nhãn Đang chạy…', 'double_click_blocked': 'bấm đúp bị chặn (chỉ chạy một lần)', 'busy_restored': 'xong thì nút trả về như cũ',
             'busy_restored_on_error': 'lỗi giữa chừng vẫn trả nút về như cũ', 'busy_reusable': 'sau khi xong bấm lại được', 'opt_ok': 'lạc quan: commit tốt thì giữ trạng thái mới',
             'opt_applies_first': 'lạc quan: giao diện đổi trước khi commit xong', 'opt_throw_reverts': 'lạc quan: commit ném lỗi → trả lại + báo', 'opt_false_reverts': 'lạc quan: commit trả false → trả lại + báo'}.items(): ck(r.get(k) is True, n)
# nối dây (nguồn)
ui, app, st, css = rd(f'{W}/x/ui.js'), rd(f'{W}/app.js'), rd(f'{W}/settings.js'), rd(f'{W}/style.css')
ck("'feedback'" in rd(f'{d}/../extras.py'), 'extras.py gói feedback.js vào x/ui.js')
ck('PressFeedback' in rd(f'{R}/x/ui.js') and 'PressToast' in rd(f'{R}/x/ui.js'), 'public/x/ui.js có PressFeedback + PressToast')
ck(re.search(r"data-save[^>]*aria-pressed=\"false\"", rd(f'{d}/../theme.py')) is not None, 'nút Lưu bài ở trang bài có aria-pressed')
ck(any(re.search(r'<button[^>]*data-save[^>]*aria-pressed="(true|false)"', rd(f'{R}/{f}')) for f in os.listdir(R) if f.endswith('.html')), 'public: nút Lưu bài có aria-pressed')
ck("'aria-pressed': !!inLib(a.id)" in ui and 'data-later-id' in ui, 'ui.js: nút Đọc sau có aria-pressed + đồng bộ khi hoàn tác')
ck('function saveBtn' in ui and "setAttribute('aria-pressed', String(on))" in ui and "}, true)" in ui and '[data-save]' in rd(f'{W}/boot.js'), 'ui.js: Lưu bài đổi aria-pressed ngay (capture) + toast Hoàn tác; boot.js nạp ui khi bấm'); ck('PressToast' not in app, 'app.js (eager) không phình thêm')
ck('undo:' in ui and 'saveLib(before)' in ui and 'if (!saveLib(l))' in ui, 'ui.js: lưu/bỏ có Hoàn tác và trả lại khi ghi lỗi')
ck("FBK.optimistic" in ui and "'Đã theo dõi chủ đề.'" in ui, 'ui.js: Theo dõi chủ đề lạc quan + toast Hoàn tác')
ck("go.disabled = true" in st and "'Đang chạy…'" in st and "aria-busy" in st and "go.disabled = false" in st, 'settings.js: Chạy báo có trạng thái chờ (disabled + aria-busy + nhãn Đang chạy…)')
ck('#toast .tundo' in css and '.btn[aria-busy=true]' in css, 'style.css: kiểu nút Hoàn tác + nút đang chờ')
# toast không có innerHTML (chữ chỉ bằng textContent)
fb = rd(f'{W}/x/feedback.js'); ck('innerHTML' not in fb and 'insertAdjacentHTML' not in fb, 'feedback.js: không innerHTML')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_feedback'); sys.exit(1 if bad else 0)

#!/usr/bin/env python3
"""Gợi ý lần đầu: cờ đã xem lưu theo hồ sơ, không hiện lần hai, Esc/‘Đã hiểu’ đóng được, trạng thái trống có hướng dẫn, chữ bằng textContent (offline)."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nodewrap import node
d = os.path.dirname(os.path.abspath(__file__)); S = f'{d}/..'; bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
rd = lambda f: open(f'{S}/{f}', encoding='utf8').read()
tour, css, app, th, ex = rd('web/x/tour.js'), rd('web/style.css'), rd('web/app.js'), rd('theme.py'), rd('extras.py')
ck('press.tour.' in tour and 'Đã hiểu' in tour and "'Escape'" in tour, 'tour.js: cờ press.tour.<id>, nút Đã hiểu, Esc')
ck('innerHTML' not in tour and 'insertAdjacentHTML' not in tour and 'textContent' in tour, 'tour.js: chỉ textContent')
ck(all(k in tour for k in ('Lưu:', 'Xem ít hơn:', 'Ctrl+K')), 'đủ 3 gợi ý Lưu / Xem ít hơn / Ctrl+K')
ck("'tour', 'ui'" in ex, 'tour.js nằm trong gói x/ui.js')
ck('addLess' in tour and "setAttribute('data-less'" in tour and 'MutationObserver' in tour, 'thẻ bài có nút Xem ít hơn (gợi ý không nói suông)')
ck('data-less' in app, 'app.js nghe [data-less]')
ck(re.search(r'\.tour \.btn\{min-height:44px', css) is not None, 'nút Đã hiểu ≥44px')
ck(re.search(r'Chưa có bài nào được lưu\. Làm tiếp:.*index\.html', th) is not None, 'trống: chưa lưu → hướng dẫn + liên kết trang chủ')
ck(re.search(r'Chưa có bài nào đã đọc\. Làm tiếp:.*index\.html', th) is not None, 'trống: chưa đọc → hướng dẫn + liên kết trang chủ')
pub = f'{S}/public/x/ui.js'
if os.path.exists(pub): ck('press.tour.' in open(pub, encoding='utf8').read(), 'bản build có tour')
try:
    r = json.loads(node(f'{d}/sim_tour.js').strip().splitlines()[-1])
    for k, v in r.items(): ck(v is True, 'sim: ' + k)
    ck(len(r) >= 14, 'sim chạy đủ ca')
except Exception as ex_: ck(False, f'sim_tour.js chạy được ({ex_})')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_tour'); sys.exit(1 if bad else 0)

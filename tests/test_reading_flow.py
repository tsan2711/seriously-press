#!/usr/bin/env python3
"""ux-reading-flow: nhớ bài + vị trí cuộn theo số báo, thanh "Tiếp tục đọc", bấm thân thẻ → xem nhanh + đánh dấu đã đọc. Lõi chạy node; phần build đọc public/."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
r = json.loads(node(f'{d}/sim_reading_flow.js', os.path.abspath(f'{d}/../web/x'))); bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
for k, n in {'key': 'khoá theo hồ sơ', 'save_ok': 'lưu được', 'load': 'đọc lại đúng bài/vị trí/tiêu đề', 'other_day': 'sang số báo khác thì không khôi phục', 'too_little': 'chưa đọc gì (không bài, cuộn <400px) thì không hiện',
             'scrolled_only': 'chỉ cuộn xa vẫn khôi phục', 'corrupt': 'dữ liệu hỏng → null, không ném', 'full_store': 'kho đầy → false, không ném', 'no_item': 'chưa có → null', 'title_cut': 'tiêu đề cắt 90 ký tự', 'first_visible': 'thẻ đầu còn trong khung nhìn'}.items(): ck(r.get(k) is True, n)
ui = open(f'{d}/../public/x/ui.js', encoding='utf8').read(); css = open(f'{d}/../public/style.css', encoding='utf8').read()
ck('RT.flow.load' in ui and 'class="resume"' in ui.replace("el('p', 'resume')", 'class="resume"') and 'markRead' in ui, 'ui.js: thanh Tiếp tục đọc + markRead')
ck('.resume{' in css and '.card.read .meta::before' in css, 'style.css: thanh resume + dấu ✓ thẻ đã đọc')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_reading_flow'); sys.exit(1 if bad else 0)

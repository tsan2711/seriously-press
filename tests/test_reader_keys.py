#!/usr/bin/env python3
"""web-reader-tools: phím j/k/o/s/? (không bắt phím khi gõ), thời gian đọc ≈ N phút ghi ở build, 'Đã đọc tất cả' + Hoàn tác 8 giây. Lõi chạy trên DOM mô phỏng (node), phần build đọc public/ — offline."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d); sys.path.insert(0, f'{d}/..')
from nodewrap import node
r = json.loads(node(f'{d}/sim_reader_keys.js', os.path.abspath(f'{d}/../web/x'))); bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
for k, n in {'next_clamped': 'j: sang thẻ kế, dừng ở thẻ cuối', 'prev': 'k: về thẻ trước', 'prev_clamped': 'k: dừng ở thẻ đầu', 'first_when_none': 'chưa chọn thẻ: phím đầu vào thẻ đầu', 'prevent_default': 'phím đã xử lý thì chặn mặc định',
             'o_s_help': 'o mở, s lưu, ? bảng phím — trên thẻ đang chọn', 'no_capture_typing': 'không bắt phím khi gõ trong input/textarea/select/contenteditable', 'no_capture_mod': 'không bắt Ctrl/Cmd/Alt + phím',
             'no_capture_dialog': 'không bắt phím khi đang mở hộp thoại', 'other_keys_ignored': 'phím khác bị bỏ qua', 'no_cards_ok': 'không có thẻ: không lỗi',
             'min_floor': 'thời gian đọc tối thiểu 1 phút', 'min_ceil': 'thời gian đọc làm tròn lên theo 200 từ/phút',
             'readall_marks': 'Đã đọc tất cả: ghi kho + đánh dấu thẻ đang hiện', 'undo_window': 'Hoàn tác có hạn đúng 8 giây', 'undo_restores': 'Hoàn tác khôi phục kho và thẻ như cũ',
             'undo_once': 'Hoàn tác chỉ một lần', 'undo_expired': 'quá 8 giây không hoàn tác được', 'undo_to_empty': 'Hoàn tác về kho trống thì xoá khoá'}.items(): ck(r.get(k) is True, n)
# build: thẻ có ≈ N phút khớp công thức, nút ở Tin chung, ui.js gói readtools
import theme
ck(theme.read_min({'title': 'a', 'summary': ''}) == 1 and theme.read_min({'title': 'x', 'summary': ' '.join(['w'] * 450)}) == 3 and theme.read_min({'words': 1000}) == 5, 'build: read_min theo số từ (200 từ/phút, ≥1, ưu tiên words)')
R = f'{d}/../public'; idx = open(f'{R}/index.html', encoding='utf8').read()
cards = re.findall(r'<article class="card[^"]*"[^>]*>.*?</article>', idx, flags=re.S)
ck(cards and all(re.search(r'<span class="rt" data-min="(\d+)">≈ \1 phút</span>', c) for c in cards), f'index.html: {len(cards)} thẻ đều có "≈ N phút" khớp data-min')
gen = re.search(r'<section class="gen-sec" data-general.*?</h2>(.*?)<div class="grid"', idx, flags=re.S)
ck(bool(gen) and 'data-readall>' in gen.group(1) and 'data-readall-undo' in gen.group(1) and 'Hoàn tác' in gen.group(1), 'index.html: nút "Đã đọc tất cả" + Hoàn tác ở đầu Tin chung')
ui = open(f'{R}/x/ui.js', encoding='utf8').read()
ck('PressReadTools' in ui and 'RT.handle' in ui and ui.index('PressReadTools = ') < ui.index('RT.handle') if 'PressReadTools = ' in ui else 'root.PressReadTools' in ui, 'public/x/ui.js gói readtools + dùng RT.handle')
ck("'jkos?'" in open(f'{R}/boot.js', encoding='utf8').read(), 'boot.js nạp ui khi bấm ? / j k o s')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_reader_keys'); sys.exit(1 if bad else 0)

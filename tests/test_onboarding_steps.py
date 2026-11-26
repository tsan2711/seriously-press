#!/usr/bin/env python3
"""Onboarding 3 bước ở picker: cấu trúc HTML (fieldset/nút/đếm), CSS (chip ≥44px, nút ≥48px, đã chọn đổi nền, Vào đọc dính đáy mobile),
JS (lưu giữa chừng, mọi chữ bằng textContent, không innerHTML mới) + mô phỏng sim_profiles.js (chạy offline, dữ liệu mẫu)."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nodewrap import node
d = os.path.dirname(os.path.abspath(__file__)); S = f'{d}/..'; bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
rd = lambda f: open(f'{S}/{f}', encoding='utf8').read()
pk, css, app, prof = rd('public/picker.html'), rd('web/style.css'), rd('web/app.js'), rd('web/profiles.js')
ck(len(re.findall(r'<fieldset data-step="[123]"', pk)) == 3, 'đúng 3 fieldset bước')
ck(all(f'<span class="stp">{n}/3</span>' in pk for n in (1, 2, 3)), 'nhãn 1/3 2/3 3/3')
ck(pk.count('data-next') == 1 and pk.count('data-prev') == 1 and 'bấm Tiếp để bỏ qua' in pk, 'một thanh Tiếp/Quay lại dùng chung; Tiếp = bỏ qua bước')
ck("n === 1" in app and "'Xong ✓'" in app and 'textContent' in app, 'Quay lại ẩn ở bước 1, bước 3 đổi nhãn Xong')
ck('data-count' in pk and 'Đã chọn 0 chủ đề' in pk and 'data-topic-filter' in pk, 'đếm đã chọn + ô tìm còn')
ck(re.search(r'data-create hidden', pk) and 'data-open-create' in pk, 'form tạo ẩn, mở bằng nút Tạo người đọc')
ck(re.search(r'data-step="2" hidden', pk) and re.search(r'data-step="3" hidden', pk), 'chỉ bước 1 hiện lúc đầu')
ck('required' not in pk[pk.find('data-picker'):], 'không ô bắt buộc')
cn = css.replace(' ', '')
ck(re.search(r'\.chip\{min-height:44px', cn) is not None, 'chip cao ≥44px (mọi thiết bị)')
ck('.stepnav.btn{min-height:48px}' in cn and '.enter.btn{min-height:48px' in cn, 'nút bước và Vào đọc ≥48px')
ck('.chip[aria-pressed=true]{background:var(--ink)' in cn, 'chip đã chọn đổi nền')
ck(re.search(r'@media\(max-width:640px\)\{\.enter\{position:sticky;bottom:0', cn) is not None, 'Vào đọc dính đáy trên mobile')
ck('PP.nav(' in app and 'db.setStep(' in app and 'db.pending()' in app and 'db.doneStep(' in app, 'app.js lưu bước + tiếp bước dở')
ck('step(id)' in prof and 'setStep' in prof and 'press.ob.' in prof, 'profiles.js lưu bước ở localStorage')
ck(not re.search(r'innerHTML[^;\n]*(step|Đang chọn|Đã chọn \$)', app), 'chữ mới dùng textContent')
try:
    r = json.loads(node(f'{d}/sim_profiles.js').strip().splitlines()[-1])
    want = ['nav', 'step_persist', 'steps_full', 'steps_skip', 'steps_partial', 'step_cleanup', 'step_unknown', 'html_steps', 'html_nav']
    for k in want: ck(r.get(k) is True, 'sim: ' + k)
except Exception as ex: ck(False, f'sim_profiles.js chạy được ({ex})')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_onboarding_steps'); sys.exit(1 if bad else 0)

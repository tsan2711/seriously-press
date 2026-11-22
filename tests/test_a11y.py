#!/usr/bin/env python3
"""U7: a11y + i18n VN/EN + mobile — mọi nút/ô nhập có tên, html lang, focus-visible, reduced-motion, tap ≥44px trên cảm ứng, bàn phím, en.json phủ chữ giao diện."""
import glob, json, os, re, sys
from html.parser import HTMLParser
d = os.path.dirname(os.path.abspath(__file__)); R = f'{d}/../public'; bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
class P(HTMLParser):
    def __init__(s): super().__init__(); s.stack = []; s.issues = []; s.ids = set(); s.labels = set(); s.inputs = []; s.imgs = []; s.h = []
    def handle_starttag(s, t, a):
        a = dict(a)
        if t in ('button', 'a'): s.stack.append([t, a, '']) 
        if t == 'label' and a.get('for'): s.labels.add(a['for'])
        if t in ('input', 'select', 'textarea') and a.get('type') not in ('hidden',): s.inputs.append(a)
        if t == 'img': s.imgs.append(a)
        if t in ('h1', 'h2', 'h3'): s.h.append(int(t[1]))
    def handle_data(s, x):
        if s.stack: s.stack[-1][2] += x
    def handle_endtag(s, t):
        if t in ('button', 'a') and s.stack and s.stack[-1][0] == t:
            _, a, txt = s.stack.pop()
            if t == 'button' or 'href' in a:
                if not (txt.strip() or a.get('aria-label') or a.get('title')): s.issues.append((t, a))
pages = sorted(glob.glob(f'{R}/*.html')); noname = []; nolab = []; noalt = []; nolang = []; skip = []; h1 = []
for f in pages:
    h = open(f, encoding='utf8').read(); p = P(); p.feed(h); n = os.path.basename(f)
    if 'http-equiv="refresh"' in h and len(h) < 400: continue   # trang chuyển hướng
    if not re.search(r'<html[^>]*lang="(vi|en)"', h): nolang.append(n)
    if p.issues: noname.append((n, p.issues[:2]))
    for a in p.inputs:
        if not (a.get('aria-label') or a.get('id') in p.labels or a.get('title') or a.get('type') in ('submit', 'button')): nolab.append((n, a))
    if any('alt' not in a for a in p.imgs): noalt.append(n)
    if 'offline' not in n and 'data-skip' not in h and 'class="skip' not in h and 'Bỏ qua' not in h: skip.append(n)
    if 'offline' not in n and p.h and p.h.count(1) != 1: h1.append(n)
ck(not nolang, f'{len(pages)} trang có <html lang>' + (f' thiếu {nolang}' if nolang else ''))
ck(not noname, 'mọi nút/liên kết có tên đọc được' + (f' — {noname[:2]}' if noname else ''))
ck(not nolab, 'mọi ô nhập có nhãn' + (f' — {nolab[:2]}' if nolab else ''))
ck(not noalt, 'mọi ảnh có alt' + (f' — {noalt}' if noalt else ''))
ck(not h1, 'mỗi trang đúng 1 h1' + (f' — {h1}' if h1 else ''))
css = open(f'{R}/style.css', encoding='utf8').read()
ck(':focus-visible' in css, 'có :focus-visible')
ck('prefers-reduced-motion:reduce' in css.replace(' ', ''), 'tôn trọng reduced-motion')
m = re.search(r'pointer:coarse\)\{([^}]*)\}', css.replace(' ', '')) or re.search(r'pointer:\s*coarse\)\s*\{(.*?)\}\s*\}', css, re.S)
tap = css[css.find('pointer:coarse'):css.find('pointer:coarse') + 1500]
ck('min-height:44px' in tap.replace(' ', '') and all(s in tap for s in ('.chip', '[role=tab]', '.btn')), 'cảm ứng: nút/tab/chip cao ≥44px')
ck('.srch' in tap and '.pp' in tap, 'cảm ứng: ô tìm + reader cũng ≥44px')
ui = open(f'{R}/x/ui.js', encoding='utf8').read()
ck("'Escape'" in ui and ("'j'" in ui and "'k'" in ui) and 'aria-modal' in ui and 'role' in ui, 'bàn phím: Esc/j/k, hộp thoại aria-modal')
ck('aria-live' in ui or 'role="status"' in ui or "'status'" in ui, 'thông báo động có aria-live/role=status')
idx = open(f'{R}/index.html', encoding='utf8').read()
ck('aria-pressed' in idx and 'data-lang="en"' in idx, 'chọn ngôn ngữ VI/EN bằng nút aria-pressed')
# i18n: chữ giao diện cố định trên trang chủ + me phải có bản EN
en = json.load(open(f'{R}/x/en.json', encoding='utf8'))
ck(len(en) >= 100, f'en.json {len(en)} chuỗi')
need = ['Tóm 60 giây', 'Đã lưu', 'Lịch sử', 'Bộ nhớ', 'Cài đặt', 'Huỷ', 'Số báo cũ hơn', 'Số báo mới hơn']
miss = [k for k in need if k not in en]; ck(not miss, 'en.json phủ nhãn chính' + (f' thiếu {miss}' if miss else ''))
vals_bad = [k for k, v in en.items() if not isinstance(v, str) or not v.strip() or v == k and k not in ('Menu', 'Game dev', 'English', 'VI', 'EN', 'API key', 'Model')]; ck(not vals_bad, 'en.json: mọi bản dịch khác gốc, không rỗng' + (f' {vals_bad[:3]}' if vals_bad else ''))
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_a11y'); sys.exit(1 if bad else 0)

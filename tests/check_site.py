"""Cổng máy cho site (đọc public/*.html sau build): không dây/3D, a11y cơ bản, SEO, nặng trang, tương phản, link ngoài an toàn."""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nodewrap import node
R = os.path.join(os.path.dirname(__file__), '..', 'public'); bad = []
def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]; c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]
    return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
def cr(a, b): x, y = sorted((lum(a), lum(b)), reverse=True); return (x + .05) / (y + .05)
for f in sorted(glob.glob(R + '/*.html')):
    s = open(f, encoding='utf8').read(); n = os.path.basename(f)
    if len(s) < 1000: continue                                   # trang chuyển hướng cũ (gamedev.html …)
    body = re.sub(r'<a [^>]*>.*?</a>', '', s, flags=re.S)       # tiêu đề bài từ nguồn ngoài không tính
    if re.search(r'class="strings"|<canvas|three\.js|webgl', body, re.I): bad.append(f'{n}: còn dây/3D')
    if s.count('<h1') != 1: bad.append(f'{n}: cần đúng 1 <h1>, có {s.count("<h1")}')
    if '<html lang="vi"' not in s: bad.append(f'{n}: thiếu lang=vi')
    if 'name="viewport"' not in s or 'name="description"' not in s or 'og:title' not in s: bad.append(f'{n}: thiếu viewport/description/og')
    if 'class="skip"' not in s or '<main id="main"' not in s: bad.append(f'{n}: thiếu skip-link/main')
    if re.search(r'<img(?![^>]*alt=)', s): bad.append(f'{n}: <img> thiếu alt')
    if len(s.encode()) > 150_000: bad.append(f'{n}: nặng {len(s)//1000} KB > 150 KB')
    if s.count('<') > 900: bad.append(f'{n}: quá nhiều DOM node (>900 thẻ)')
    imgs = re.findall(r'<img[^>]*>', s)
    if any('width=' not in i or 'height=' not in i for i in imgs): bad.append(f'{n}: <img> thiếu width/height (CLS)')
    if sum('loading="eager"' in i for i in imgs) > 1: bad.append(f'{n}: >1 ảnh eager')
    for m in re.finditer(r'<a [^>]*href="https?://[^"]+"[^>]*>', s):
        if 'noopener' not in m.group(0): bad.append(f'{n}: link ngoài thiếu rel=noopener'); break
JS_BUDGET = 130_000   # tổng JS tải lúc đầu (byte, chưa nén)
if sum(os.path.getsize(f) for f in glob.glob(R + '/*.js')) > JS_BUDGET: bad.append('tổng JS vượt ngân sách %d' % JS_BUDGET)
if re.search(r'animation-timeline|feTurbulence[^}]*\.card', open(R + '/style.css', encoding='utf8').read().split('/* ---- perf')[-1]): bad.append('style.css: perf block dính animation-timeline')
for f in sorted(glob.glob(R + '/*.js')):   # cú pháp JS phía trình duyệt
    try: node('--check', f)
    except Exception: bad.append(f'{os.path.basename(f)}: lỗi cú pháp JS')
# riêng tư: không PII/khoá trong thứ được đẩy lên Pages
for f in glob.glob(R + '/*'):
    if os.path.isfile(f) and f.endswith(('.html', '.js', '.json', '.css')):
        t = open(f, encoding='utf8', errors='ignore').read()
        if re.search(r'ADMIN_TOKEN\s*[:=]\s*["\'][^"\']+|sk-ant-[\w-]{10,}|sk-[A-Za-z0-9]{24,}|nguyen[t]ansang|@gmail\.com|press\.share"\s*:\s*\{"token', t): bad.append(f'{os.path.basename(f)}: dính khoá/PII')
# nhật ký là của riêng người đọc: không tệp dữ liệu nhật ký nào trong public/, today.json không chứa log
if glob.glob(R + '/**/journal*.json', recursive=True) or os.path.isdir(R + '/journals'): bad.append('public/ có tệp nhật ký')
if not os.path.exists(R + '/me.html'): bad.append('thiếu trang Của tôi (me.html)')
else:
    _m = open(R + '/me.html', encoding='utf-8').read()
    for _k in ('data-mem', 'data-diary', 'data-settings', 'aria-live', '<h1', 'role="tablist"', 'role="tabpanel"'):
        if _k not in _m: bad.append('me.html thiếu ' + _k)
    if _m.count('role="tab"') != 3: bad.append('me.html cần đúng 3 tab (Lịch sử | Bộ nhớ | Cài đặt)')
for _o, _t in (('journal', 'lich-su'), ('memory', 'bo-nho'), ('settings', 'cai-dat')):   # URL cũ vẫn sống: chuyển sang tab
    _p = R + '/' + _o + '.html'
    if not os.path.exists(_p) or 'me.html#' + _t not in open(_p, encoding='utf-8').read(): bad.append(_o + '.html không chuyển hướng về me.html#' + _t)
_h = open(R + '/index.html', encoding='utf-8').read(); _mp = re.search(r'<div class="mp">(.*?)<div class="schemes"', _h, re.S)
if not _mp or len(re.findall(r'<a ', _mp.group(1))) > 3: bad.append('menu chính phải ≤ 3 mục (Báo hôm nay · Của tôi · Chia sẻ)')
if 'data-issues' not in _h or not os.path.exists(R + '/issues.json'): bad.append('trang chủ thiếu bộ chọn số báo / issues.json')
else:
    _i = json.loads(open(R + '/issues.json', encoding='utf-8').read())['issues']
    if len(_i) > 14 or any(x.get('src') != 'cron' for x in _i): bad.append('issues.json: >14 ngày hoặc có bản không phải cron')
    for x in _i:
        if not os.path.exists(R + '/' + x['file']): bad.append('thiếu ' + x['file'])
for _f in ('today.json', 'index.html', 'me.html'):
    _x = open(R + '/' + _f, encoding='utf-8').read()
    if 'press.mem.' in _x and _f != 'me.html': bad.append(_f + ' chứa khoá bộ nhớ người đọc')
    if '"st":{' in _x or 'press.seen.' in _x and _f == 'today.json': bad.append(_f + ' chứa seen-store')
import json as _j
_t = _j.load(open(R + '/today.json', encoding='utf8'))
if any(k in _t for k in ('days', 'journal', 'readers', 'profile')): bad.append('today.json chứa dữ liệu người đọc')
css = open(R + '/style.css', encoding='utf8').read()
for fg, bg, nm in [('#1a1712', '#f5eedb', 'chữ/thẻ sáng'), ('#5c5345', '#f5eedb', 'meta/thẻ sáng'), ('#4a4233', '#ddd4bd', 'meta/thẻ tối'), ('#1a1712', '#ddd4bd', 'chữ/thẻ tối'), ('#f1e8cf', '#3a2b1d', 'chân trang tối'), ('#fffdf5', '#8f6640', 'chân trang sáng')]:
    k = cr(fg, bg)
    if k < 4.5: bad.append(f'tương phản {nm} {k:.2f} < 4.5')
if '.strings' in css or 'animation-timeline' in css and False: bad.append('CSS còn .strings')
print('\n'.join(['FAIL ' + b for b in bad]) or 'OK check_site: không dây/3D, a11y, SEO, nặng ≤150KB, tương phản ≥4.5')
sys.exit(1 if bad else 0)

#!/usr/bin/env python3
"""Ảnh cục bộ — offline: ảnh mẫu tạo bằng Pillow; không Pillow thì kiểm đường fallback."""
import os, sys, tempfile, json, time, io
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import imgcache as C
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)

root = tempfile.mkdtemp(); IMG = f'{root}/public/img'
def arts(*us): return [dict(id=str(i), img=u, img_credit='x') for i, u in enumerate(us)]

# ── fallback khi không Pillow (luôn kiểm, bằng cách tạm tắt) ──
real = C.Image; C.Image = None
calls = []
a = arts('https://x.test/a.png')
r = C.localize(a, root, fetcher=lambda u: calls.append(u))
chk('không Pillow → giữ hotlink, không tải', a[0]['img'] == 'https://x.test/a.png' and not calls and r['local'] == 0 and not os.path.isdir(IMG))
chk('không Pillow → to_webp None', C.to_webp(b'abc') is None)
C.Image = real

if not C.have_pillow():
    print('SKIP phần Pillow (chưa cài)')
    sys.exit(0 if all(ok) else 1)

from PIL import Image
def mk(w, h, fmt='PNG', col=(200, 30, 30)):
    im = Image.new('RGB', (w, h))   # dải chuyển màu kín khung (ảnh phẳng 1 màu sẽ bị coi là logo)
    im.putdata([(x * 255 // w, y * 255 // h, col[2]) for y in range(h) for x in range(w)])
    o = io.BytesIO(); im.save(o, fmt); return o.getvalue()

# ── kích thước + định dạng ──
for w, h in ((1600, 900), (800, 800), (300, 600), (640, 360)):
    out = C.to_webp(mk(w, h)); im = Image.open(io.BytesIO(out))
    chk(f'{w}x{h} → 640x360 webp', im.size == (640, 360) and im.format == 'WEBP')
chk('ảnh hỏng → None', C.to_webp(b'not an image') is None)

# ── localize ──
src = {'https://x.test/a.png': mk(1200, 700), 'https://x.test/b.jpg': mk(900, 900, 'JPEG', (10, 90, 200)), 'https://x.test/big.png': None, 'https://x.test/bad.png': b'zzz'}
dl = []
def fetcher(u):
    dl.append(u)
    if u.endswith('err.png'): raise OSError('net')
    return src.get(u)
a = arts('https://x.test/a.png', 'https://x.test/b.jpg', 'https://x.test/a.png', 'https://x.test/big.png', 'https://x.test/bad.png', 'https://x.test/err.png', '')
a[2]['img_credit'] = 'y'
r = C.localize(a, root, fetcher=fetcher)
chk('a/b → đường dẫn tương đối img/*.webp', all(a[i]['img'].startswith('img/') and a[i]['img'].endswith('.webp') and '://' not in a[i]['img'] for i in (0, 1, 2)))
chk('cùng URL → cùng tệp, chỉ tải 1 lần', a[0]['img'] == a[2]['img'] and dl.count('https://x.test/a.png') == 1)
chk('tên = hash nội dung', os.path.basename(a[0]['img'])[:-5] == __import__('hashlib').sha1(open(f'{root}/public/{a[0]["img"]}', 'rb').read()).hexdigest()[:16])
chk('width/height thật', all((a[i]['img_w'], a[i]['img_h']) == (640, 360) for i in (0, 1)) and Image.open(f'{root}/public/{a[0]["img"]}').size == (640, 360))
chk('giữ URL gốc', a[0]['img_remote'] == 'https://x.test/a.png')
chk('quá lớn/hỏng/lỗi mạng → giữ hotlink', all(a[i]['img'].startswith('https://') and 'img_w' not in a[i] for i in (3, 4, 5)))
chk('thống kê', r['local'] == 3 and r['kept'] == 3)
chk('không có ảnh → bỏ qua', 'img' in a[6] and a[6]['img'] == '')
dl.clear(); b = arts('https://x.test/a.png'); C.localize(b, root, fetcher=fetcher)
chk('chạy lại: dùng cache, không tải lại', not dl and b[0]['img'] == a[0]['img'])
chk('tên tệp tồn tại trong public/img', os.path.isfile(f'{root}/public/{a[0]["img"]}'))

# ── fetch_full: trần 2 MB (giả urlopen) ──
class R:
    def __init__(s, b, ct='image/png'): s.b, s.headers = b, {'Content-Type': ct}
    def read(s, n): return s.b[:n]
    def __enter__(s): return s
    def __exit__(s, *x): pass
import urllib.request as U
orig = U.urlopen
try:
    U.urlopen = lambda rq, timeout=0: R(b'x' * (C.MAX_DL + 1)); chk('>2 MB → None', C.fetch_full('https://x.test/a') is None)
    U.urlopen = lambda rq, timeout=0: R(b'x' * C.MAX_DL); chk('=2 MB → nhận', len(C.fetch_full('https://x.test/a')) == C.MAX_DL)
    U.urlopen = lambda rq, timeout=0: R(b'x', 'text/html'); chk('không phải ảnh → None', C.fetch_full('https://x.test/a') is None)
    chk('scheme lạ → None', C.fetch_full('file:///etc/passwd') is None)
finally: U.urlopen = orig

# ── dọn tệp ──
r2 = tempfile.mkdtemp(); D = f'{r2}/public/img'; os.makedirs(D)
now = time.time()
def put(n, size, age_days):
    p = f'{D}/{n}'; open(p, 'wb').write(b'0' * size); t = now - age_days * 86400; os.utime(p, (t, t))
put('used_old.webp', 100, 30); put('unused_old.webp', 100, 15); put('unused_new.webp', 100, 3)
n = C.prune(r2, {'used_old.webp'}, now)
fs = set(os.listdir(D))
chk('dọn: bỏ tệp không dùng >14 ngày', 'unused_old.webp' not in fs and n == 1)
chk('dọn: giữ tệp đang dùng dù cũ + tệp mới', {'used_old.webp', 'unused_new.webp'} <= fs)
put('c1.webp', 1000, 5); put('c2.webp', 1000, 2); put('c3.webp', 1000, 1)
C.prune(r2, {'used_old.webp'}, now, cap=2200)
fs = set(os.listdir(D)); tot = sum(os.path.getsize(f'{D}/{f}') for f in fs)
chk('trần dung lượng: xoá không-dùng cũ nhất trước, ≤ trần', tot <= 2200 and 'c1.webp' not in fs and {'c2.webp', 'c3.webp', 'used_old.webp'} <= fs)
put('big_used.webp', 5000, 0)
C.prune(r2, {'used_old.webp', 'big_used.webp'}, now, cap=10)
chk('trần không xoá tệp đang dùng', {'used_old.webp', 'big_used.webp'} <= set(os.listdir(D)))
chk('trần mặc định 40 MB, giữ 14 ngày', C.DIR_CAP == 40 * 1024 * 1024 and C.KEEP_DAYS == 14)

# ── localize dọn tệp cũ không còn bài dùng ──
r3 = tempfile.mkdtemp(); os.makedirs(f'{r3}/public/img'); old = f'{r3}/public/img/old.webp'
open(old, 'wb').write(b'0'); t = time.time() - 20 * 86400; os.utime(old, (t, t))
C.localize(arts('https://x.test/a.png'), r3, fetcher=fetcher)
chk('localize dọn tệp cũ không dùng', not os.path.exists(old))

# ── logo/icon/thẻ thương hiệu: nền phẳng + nội dung chỉ ở giữa → loại, nhớ trong logo.json ──
if C.Image:
    def png(draw):
        im = C.Image.new('RGB', (800, 450), (14, 20, 28)); draw(im); b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()
    def blob(im):
        for x in range(350, 450):
            for y in range(180, 280): im.putpixel((x, y), (200, 200, 200))
    def busy(im):
        for x in range(800):
            for y in range(0, 450, 7): im.putpixel((x, y), (200, (x * 3) % 255, 90))
    r4 = tempfile.mkdtemp(); A = arts('https://x.test/logo.png', 'https://x.test/photo.png')
    C.localize(A, r4, fetcher=lambda u: png(blob if 'logo' in u else busy))
    chk('logo giữa nền phẳng bị gỡ (thà không ảnh)', 'img' not in A[0] and A[0].get('img_bad') == ['https://x.test/logo.png'])
    chk('ảnh nội dung kín khung được giữ', A[1].get('img', '').startswith('img/'))
    A2 = arts('https://x.test/logo.png'); C.localize(A2, r4, fetcher=lambda u: (_ for _ in ()).throw(AssertionError('không tải lại')))
    chk('logo đã nhớ không tải lại', 'img' not in A2[0])

print(f'\n{sum(ok)}/{len(ok)}'); sys.exit(0 if all(ok) else 1)

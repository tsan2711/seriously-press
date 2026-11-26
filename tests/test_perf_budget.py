#!/usr/bin/env python3
"""Ngân sách hiệu năng (đo trên public/ sau build, offline): JS trang chủ, số thẻ dựng ban đầu ≤12, không script đồng bộ chặn,
mỗi trang chỉ nạp script cần, ảnh giữ chỗ + fetchpriority ≤2, không scroll listener không passive. Ngưỡng chỉ được hạ, không nới."""
import glob, os, re, sys, types
D = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(D, '..', 'public'); sys.path.insert(0, os.path.join(D, '..'))
HOME_JS_MAX = 90_000      # đo 11-23 sau tách: 84 189 B (trước: 117 782 B)
PAGE_JS_MAX = 105_000     # trang nặng nhất (me.html) đo 100 110 B
FIRST_CARDS = 12
bad = []
def rd(n): return open(f'{R}/{n}', encoding='utf8').read()
def live(s): return re.sub(r'<template\b.*?</template>', '', s, flags=re.S)
for f in sorted(glob.glob(R + '/*.html')):
    n = os.path.basename(f); s = rd(n)
    if len(s) < 1000: continue
    tags = re.findall(r'<script\b[^>]*>', s); srcs = [re.search(r'src="([^"]+)"', t).group(1) for t in tags if 'src=' in t]
    for t in tags:
        if 'src=' in t and 'defer' not in t and 'async' not in t: bad.append(f'{n}: script đồng bộ chặn {t}')
    sz = sum(os.path.getsize(f'{R}/{j}') for j in srcs)
    if sz > PAGE_JS_MAX: bad.append(f'{n}: JS {sz} > {PAGE_JS_MAX}')
    if n == 'index.html':
        if sz > HOME_JS_MAX: bad.append(f'index.html: JS {sz} B > ngưỡng {HOME_JS_MAX}')
        for j in ('settings.js', 'mempage.js', 'diary.js', 'run-core.js', 'share-core.js'):
            if j in srcs: bad.append(f'index.html nạp {j} (chỉ trang khác dùng)')
        if len(re.findall(r'<article class="card', live(s))) > FIRST_CARDS: bad.append(f'index.html: dựng >{FIRST_CARDS} thẻ ban đầu')
    if n == 'picker.html' and any(j in srcs for j in ('issues.js', 'fx.js', 'settings.js', 'community.js')): bad.append('picker.html nạp script trang khác')
    if n == 'me.html' and any(j in srcs for j in ('issues.js', 'fx.js')): bad.append('me.html nạp script trang chủ')
    imgs = re.findall(r'<img[^>]*>', s)
    if sum('fetchpriority' in i for i in imgs) > 2: bad.append(f'{n}: >2 ảnh có fetchpriority')
    for i in imgs:
        if not all(k in i for k in ('width=', 'height=', 'decoding="async"')): bad.append(f'{n}: ảnh thiếu width/height/decoding')
        if 'loading="eager"' not in i and 'loading="lazy"' not in i: bad.append(f'{n}: ảnh không lazy/eager rõ ràng')
for f in glob.glob(R + '/*.js') + glob.glob(R + '/x/*.js'):
    c = open(f, encoding='utf8').read()
    for m in re.finditer(r"addEventListener\(\s*'(scroll|wheel|touchmove|touchstart)'(.*)", c):
        if 'passive' not in m.group(2).split('addEventListener')[0]: bad.append(f'{os.path.basename(f)}: sự kiện {m.group(1)} không passive')
if 'IntersectionObserver' not in rd('app.js') or 'data-more-btn' not in rd('app.js'): bad.append('app.js thiếu Xem thêm/IntersectionObserver')
if 'requestIdleCallback' not in rd('app.js'): bad.append('app.js: cá nhân hoá không chạy trong requestIdleCallback')
if not re.search(r'performance\.now\(\) - t < 8\b', rd('app.js')): bad.append('app.js: lô cá nhân hoá phải ≤8ms')
if not re.search(r'setTimeout\(\(\) => \{ const q =', rd('app.js')): bad.append('app.js: ô lọc chủ đề chưa debounce')
# board(): >12 thẻ → 12 đầu dựng ngay, phần còn lại trong <template> + nút Xem thêm (dữ liệu mẫu, offline)
import theme
class B:
    DN = {'ai': 'AI'}; DESKS = {'ai': {'accent': '#123456'}}
    topic = staticmethod(lambda a: 'ai'); meta = staticmethod(lambda a: a['source'])
theme.B = B
arts = [dict(id=f'{i:08x}', sid='', title=f'T{i}', url='https://x.test/%d' % i, source='S', desks=['ai'], img='https://x.test/i%d.jpg' % i, status='new') for i in range(30)]
h = theme.board(arts, lead=arts[0])
if len(re.findall(r'<article class="card', live(h))) != FIRST_CARDS: bad.append('board(): thẻ dựng ban đầu != 12')
if h.count('<template data-more>') != 1 or 'data-more-btn' not in h: bad.append('board(): thiếu template/nút Xem thêm')
if len(re.findall(r'<article class="card', h)) != 24: bad.append('board(): tổng thẻ != 24')
if sum('fetchpriority' in i for i in re.findall(r'<img[^>]*>', h)) > 2: bad.append('board(): >2 ảnh fetchpriority')
if sum('loading="eager"' in i for i in re.findall(r'<img[^>]*>', h)) > 1: bad.append('board(): >1 ảnh eager')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_perf_budget'); sys.exit(1 if bad else 0)

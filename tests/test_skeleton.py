#!/usr/bin/env python3
"""Khung chờ: có aria-busy, bỏ khi dữ liệu về, CSS tôn trọng reduced-motion, không innerHTML. Offline (đọc nguồn web/ và bản build public/)."""
import os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); W = f'{d}/../web'
rd = lambda p: open(f'{W}/{p}', encoding='utf8').read()
app, ui, css = rd('app.js'), rd('x/ui.js'), rd('style.css'); bad = []
def need(ok, n):
    print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
need("busy(fyList, 1)" in app and "setAttribute('aria-busy', 'true')" in app, 'Dành cho tôi: khung chờ đặt aria-busy')
need("busy(gen0, 1)" in app, 'Tin chung: aria-busy khi chờ cá nhân hoá')
need(re.search(r"skOff = \(\) => \{[^}]*busy\(fyList\); busy\(gen0\);[^}]*\.sk-card'\)\.forEach\(x => x\.remove\(\)\)", app) is not None and "removeAttribute('aria-busy')" in app, 'bỏ aria-busy và thẻ giả khi dữ liệu về')
need('}).then(skOff, skOff)' in app, 'skOff chạy cả khi lỗi/rỗng (không kẹt khung chờ)')
idx = open(f'{d}/../public/index.html', encoding='utf8').read(); tm = re.search(r'<template data-fy-sk>(.*?)</template>', idx, re.S)
need(bool(tm) and tm.group(1).count('class="card sk-card" aria-hidden="true"') >= 3 and 'skT.content.cloneNode' in app, 'thẻ giả (template) dùng lớp .card cùng chiều cao, ẩn với đọc màn hình')
need("list.setAttribute('aria-busy', 'true')" in ui and "list.removeAttribute('aria-busy')" in ui, 'kết quả tìm: aria-busy bật khi chờ, tắt trong run()')
need("sk-row" in ui and 'failed' in ui, 'kết quả tìm: dòng chờ + trạng thái lỗi (không kẹt)')
blk = app[app.index('khung chờ (template'):app.index('dataP.then(async data')]
need(not re.search(r'innerHTML|insertAdjacentHTML|outerHTML', blk + ui), 'khung chờ không innerHTML (chữ qua textContent)')
# CSS: mọi animation/transition của khung chờ nằm trong no-preference; có khối reduce tắt hoàn toàn
blocks = re.findall(r'@media \(prefers-reduced-motion:no-preference\)\{(.*?)\n\}', css[css.index('khung chờ (ux-skeleton'):], re.S)
need(any('sk-bar' in b and 'animation' in b for b in blocks), 'CSS: hoạt ảnh khung chờ chỉ trong no-preference')
tail = css[css.index('khung chờ (ux-skeleton'):]
def strip_media(t):   # bỏ mọi khối @media (đếm ngoặc)
    out, i = '', 0
    while i < len(t):
        j = t.find('@media', i)
        if j < 0: out += t[i:]; break
        out += t[i:j]; k = t.index('{', j); depth = 1; k += 1
        while depth: depth += {'{': 1, '}': -1}.get(t[k], 0); k += 1
        i = k
    return out
outside = strip_media(tail)
need('animation' not in outside and 'transition' not in outside, 'CSS: không hoạt ảnh/chuyển cảnh ngoài khối media')
need(re.search(r'prefers-reduced-motion:reduce\)\{[^}]*animation:none!important;transition:none!important', tail) is not None, 'CSS: reduce → tắt hoàn toàn animation + transition')
pub = f'{d}/../public/style.css'
if os.path.exists(pub): need('sk-bar' in open(pub, encoding='utf8').read(), 'bản build public/style.css có khung chờ')
sys.exit(1 if bad else 0)

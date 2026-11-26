#!/usr/bin/env python3
"""Tách 'Dành cho tôi' / 'Tin chung': HTML dựng có hai section id/aria riêng, đúng thứ tự; CSS thứ bậc chữ; node --check mọi JS."""
import os, re, subprocess, sys, glob
d = os.path.dirname(os.path.abspath(__file__)); site = os.path.dirname(d); bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
sys.path.insert(0, site)
import theme
src = open(f'{site}/theme.py', encoding='utf-8').read(); css = open(f'{site}/web/style.css', encoding='utf-8').read()
fy = theme.FORYOU
ck('data-foryou' in fy and 'id="fy"' in fy and 'aria-labelledby="fy"' in fy, "section 'Dành cho tôi': data-foryou, id=fy, aria-labelledby")
ck('data-general' in src and 'id="gn"' in src and 'aria-labelledby="gn"' in src, "section 'Tin chung': data-general, id=gn, aria-labelledby")
ck(src.index('{FORYOU}') < src.index('data-general') < src.index('data-gen)') if 'data-gen)' in src else src.index('{FORYOU}') < src.index('data-general') < src.index("'class=\"grid\" data-gen'"), "thứ tự: Dành cho tôi → Tin chung → lưới")
ck('Dành cho' in fy and 'tôi' in fy, "tiêu đề 'Dành cho tôi'")
ck(src.count('<section class="gen-sec"') == src.count('</section></main>') == 1, 'section Tin chung đóng đúng trước </main>')
ck(re.search(r'\.fyg \.card\{[^}]*flex-direction:row[^}]*border-left:4px', css) is not None, 'thẻ ngang + viền trái 4px')
ck(re.search(r'\.fyg \.card \.thumb\{[^}]*width:96px', css) is not None, 'cột ảnh 96px')
ck('.chip-why' in css and 'vì bạn theo: ' in open(f'{site}/web/app.js', encoding='utf-8').read(), "chip 'vì bạn theo: <chủ đề>'")
ck(re.search(r'\.card h3\{margin:0;font:700 1\.25rem/1\.25 ', css) is not None, 'h3 1.25rem/1.25')
ck(re.search(r'\.ex\{[^}]*max-width:60ch[^}]*-webkit-line-clamp:3', css) is not None, 'đoạn trích ≤60ch, 3 dòng')
ck(re.search(r'\.kicker\{[^}]*font:700 \.75rem', css) is not None, 'kicker .75rem')
ck(re.search(r'\.gen-h\{font:700 \.75rem var\(--mono\)', css) is not None, "h2 'Tin chung' nhỏ mono")
js = sorted(glob.glob(f'{site}/web/*.js'))
for f in js: ck(subprocess.run(['node', '--check', f], capture_output=True).returncode == 0, 'node --check ' + os.path.basename(f))
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_sections'); sys.exit(1 if bad else 0)

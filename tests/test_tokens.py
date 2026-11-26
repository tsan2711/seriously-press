#!/usr/bin/env python3
"""Token CSS (eye-review 11-22): xoay chỉ .lead/sticky (≤ .4deg), grain alpha ≤ .15, speck ≤ .06, .thumb không gradient khi không ảnh,
bóng thẻ ≤ trần, hover không scale, ghim ≤ 12px. Quét web/style.css (nguồn) + public/style.css nếu có; chỉ stdlib, offline."""
import os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); bad = []
def ck(ok, n, more=''):
    print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else f' — {more}')); ok or bad.append(n)

def rules(css):
    """[(selector, body)] phẳng, đi vào @media/@supports."""
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S); out = []
    def walk(t):
        i = 0
        while True:
            j = t.find('{', i)
            if j < 0: return
            sel = t[i:j].strip(); dep = 1; k = j + 1
            while dep and k < len(t): dep += (t[k] == '{') - (t[k] == '}'); k += 1
            body = t[j + 1:k - 1]
            if sel.startswith('@keyframes'): pass
            elif sel.startswith('@'): walk(body)
            else: out.append((sel, body))
            i = k
    walk(css); return out

SHADOW_MAX_A, SHADOW_MAX_Y = .35, 6
srcs = [f'{d}/../web/style.css'] + ([f'{d}/../public/style.css'] if os.path.exists(f'{d}/../public/style.css') else [])
for f in srcs:
    css = open(f, encoding='utf8').read(); R = rules(css); tag = os.path.relpath(f, d + '/..')
    # 1) --r
    bad_r = []
    for sel, body in R:
        for v in re.findall(r'--r\s*:\s*(-?[\d.]+)deg', body):
            ok_sel = all(re.search(r'\.lead\b|\.hub\b|\.sticky\b|\.note\b', x) for x in sel.split(','))
            if abs(float(v)) > 0 and (not ok_sel or abs(float(v)) > .4): bad_r.append(f'{sel}:{v}deg')
    ck(not bad_r, f'{tag}: --r ≠ 0 chỉ ở .lead/sticky và ≤ .4deg', bad_r)
    # 1b) rotate() cứng trong transform thường trú (ngoài keyframes/animation vào) ≤ .4deg
    hard = [f'{sel}:{v}' for sel, body in R for v in re.findall(r'(?<![\w-])rotate\((-?[\d.]+)deg\)', body)
            if abs(float(v)) > .4 and 'fx' not in sel and 'hover' not in sel]
    ck(not hard, f'{tag}: không xoay cứng > .4deg', hard)
    # 2) grain / speck alpha
    ga = re.search(r'--grain:url\("[^"]*0 0 0 ([\d.]+) 0', css); sa = re.findall(r'--speck:url\("[^"]*0 0 0 ([\d.]+) (-?[\d.]+)', css)
    ck(bool(ga) and float(ga.group(1)) <= .15, f'{tag}: grain alpha ≤ .15', ga and ga.group(1))
    ck(bool(sa) and all(float(a) <= .06 and float(b) >= 0 for a, b in sa), f'{tag}: speck alpha ≤ .06', sa)
    # 3) .thumb không ảnh: không gradient nền
    gr = [sel for sel, body in R if '.thumb' in sel and ':has(img)' not in sel and 'img' not in sel and re.search(r'background[^;]*gradient', body)]
    ck(not gr, f'{tag}: .thumb không ảnh không gradient', gr)
    flat = any(sel.strip() == '.thumb' and re.search(r'background:\s*var\(--card2\)', body) for sel, body in R)
    ck(flat, f'{tag}: .thumb nền phẳng --card2')
    # 4) bóng thẻ
    over = []
    for sel, body in R:
        if not re.search(r'\.card|\.zhead|\.clipping|\.hub', sel): continue
        for m in re.finditer(r'(?:box-shadow|filter)\s*:\s*([^;}]+)', body):
            for lay in re.finditer(r'(?:drop-shadow\()?\s*(-?[\d.]+)(?:px)?\s+(-?[\d.]+)px\s+(?:-?[\d.]+px\s+){0,2}rgba\(\s*0,\s*0,\s*0,\s*([\d.]+)\)', m[1]):
                if float(lay[3]) > SHADOW_MAX_A or float(lay[2]) > SHADOW_MAX_Y: over.append(f'{sel}: {lay[0].strip()}')
    ck(not over, f'{tag}: bóng thẻ alpha ≤ {SHADOW_MAX_A}, y ≤ {SHADOW_MAX_Y}px', over)
    # 5) hover không scale
    sc = [sel for sel, body in R if re.search(r':hover|:focus-within', sel) and re.search(r'scale\(', body)]
    ck(not sc, f'{tag}: hover/focus không scale', sc)
    # 6) ghim ≤ 12px
    pins = [(sel, int(w)) for sel, body in R if re.search(r'\.pin\b|::before', sel) and '.card' in sel + '.pin' for w in re.findall(r'(?<![\w-])width:(\d+)px', body) if '.pin' in sel or 'lead::before' in sel or 'pinned::before' in sel]
    ck(bool(pins) and all(w <= 12 for _, w in pins), f'{tag}: ghim ≤ 12px', pins)
    # 7) dây đỏ ≤ 1.5px, opacity .7, ẩn < 700px
    ck('--string-w:1.5px' in css and '--string-o:.7' in css and re.search(r'max-width:699px\)\{\.string\{display:none', css), f'{tag}: dây đỏ 1.5px/.7, ẩn <700px')
    # 8) --desk-accent có token
    ck('--desk-accent' in css, f'{tag}: có token --desk-accent')

# theme.py: --r inline của sticky ≤ .4, dải/chữ cái đầu ban, lead không ảnh dùng trích dẫn
t = open(f'{d}/../theme.py', encoding='utf8').read()
rr = [float(x) for x in re.findall(r'--r:(-?[\d.]+)deg', t)] + [float(x) for x in re.findall(r'\((-?[\d.]+(?:, -?[\d.]+)+)\)\[k % 3\]', t) for x in x.split(',')]
ck(rr and all(abs(x) <= .4 for x in rr), 'theme.py: --r inline ≤ .4deg', rr)
ck('--desk-accent' in t and 'data-ini' in t and 'class="lq"' in t, 'theme.py: --desk-accent, chữ cái đầu ban, trích dẫn lead')
ck(not [x for x in re.findall(r'style="--h:', t)], 'theme.py: không còn --h gradient')
print('\n' + ('PASS' if not bad else f'FAIL {len(bad)}')); sys.exit(1 if bad else 0)

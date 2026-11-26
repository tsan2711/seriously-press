#!/usr/bin/env python3
"""Mobile 390px (tĩnh): không phần tử rộng quá viewport, vùng bấm ≥44px, chữ ô nhập ≥16px. Quét public/*.html + public/style.css."""
import glob, os, re, sys
from html.parser import HTMLParser
d = os.path.dirname(os.path.abspath(__file__)); R = f'{d}/../public'; VW = 390; bad = []
def ck(ok, n, more=''):
    print(('OK   ' if ok else 'FAIL ') + n + ('' if ok else f' — {more}')); ok or bad.append(n)

def px(v, base=16):
    m = re.fullmatch(r'max\((.+),(.+)\)', v.strip())
    if m: return max([x for x in (px(m[1]), px(m[2])) if x is not None] or [None])
    m = re.fullmatch(r'(-?[\d.]+)(px|rem|em)', v.strip())
    return None if not m else float(m[1]) * (1 if m[2] == 'px' else base)

def active(cond):
    """@media điều kiện có hiệu lực ở 390px, cảm ứng, không hover, sáng/tối đều tính, motion bất kỳ."""
    c = cond.replace(' ', '')
    for k, v in re.findall(r'\((min|max)-width:([\d.]+)px\)', c):
        if (k == 'min' and float(v) > VW) or (k == 'max' and float(v) < VW): return False
    if '(hover:hover)' in c or '(pointer:fine)' in c or 'print' in c: return False
    return True

def parse(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S); out = []; i = 0
    def block(i):  # trả (nội dung, vị trí sau })
        dep = 1; j = i
        while dep:
            j += 1 if j < len(css) else 0
            if j >= len(css): break
            dep += (css[j] == '{') - (css[j] == '}')
        return css[i:j], j + 1
    def walk(s, on):
        k = 0
        while k < len(s):
            o = s.find('{', k)
            if o < 0: break
            head = s[k:o].strip(); dep = 1; j = o + 1
            while dep and j < len(s):
                dep += (s[j] == '{') - (s[j] == '}'); j += 1
            body = s[o + 1:j - 1]; k = j
            if head.startswith('@media'): walk(body, on and active(head[6:]))
            elif head.startswith('@'): continue
            elif on: out.append((head, dict((a.strip(), b.strip().replace('!important', '').strip()) for a, b in re.findall(r'([\w-]+)\s*:\s*((?:[^;{}"\']|"[^"]*"|\'[^\']*\')+)', body))))
    walk(css, True); return out

css = parse(open(f'{R}/style.css', encoding='utf8').read())

class H(HTMLParser):
    def __init__(s): super().__init__(); s.els = []; s.vp = False; s.inline = []
    def handle_starttag(s, t, a):
        a = dict(a); s.els.append((t, a))
        if t == 'meta' and a.get('name') == 'viewport': s.vp = 'width=device-width' in a.get('content', '')
        if 'style' in a: s.inline.append((t, a['style']))
pages = sorted(glob.glob(f'{R}/*.html')); els = []; novp = []; inl = []
for f in pages:
    h = open(f, encoding='utf8').read()
    if 'http-equiv="refresh"' in h and len(h) < 400: continue
    p = H(); p.feed(h); els += [(os.path.basename(f), t, a) for t, a in p.els]
    if not p.vp: novp.append(os.path.basename(f))
    for t, st in p.inline:
        for k, v in re.findall(r'(?:^|;)\s*((?:min-)?width)\s*:\s*([^;]+)', st):
            w = px(v)
            if w and w > VW: inl.append((os.path.basename(f), t, st))
ck(len(pages) > 5, f'{len(pages)} trang public/')
ck(not novp, 'mọi trang có viewport width=device-width', novp)
ck(not inl, 'không style inline rộng hơn 390px', inl[:3])

def match(sel, t, a):
    comp = re.split(r'[\s>+~]+', sel.strip())[-1]
    comp = re.sub(r'::?[\w-]+(\([^)]*\))?', '', comp)
    if not comp or comp == '*': return False
    mt = re.match(r'^[a-zA-Z][\w-]*', comp)
    if mt and mt[0] != t: return False
    cls = (a.get('class') or '').split()
    for c in re.findall(r'\.([\w-]+)', comp):
        if c not in cls: return False
    for i in re.findall(r'#([\w-]+)', comp):
        if a.get('id') != i: return False
    for k, v in re.findall(r'\[([\w-]+)=?([^\]]*)\]', comp):
        if k not in a or (v and a[k] != v.strip('"\'')): return False
    return bool(mt or '.' in comp or '#' in comp or '[' in comp)

def eff(t, a, prop):
    """Giá trị cuối theo thứ tự nguồn (xấp xỉ cascade), ưu tiên thuộc tính riêng rồi shorthand font."""
    val = None
    for sel, decl in css:
        if any(match(s, t, a) for s in sel.split(',')):
            if prop in decl: val = decl[prop]
            elif prop == 'font-size' and 'font' in decl:
                m = re.search(r'(?:^|\s)(-?[\d.]+(?:px|rem|em))(?:/[^\s]+)?\s', decl['font'] + ' ')
                if m: val = m[1]
    return val

# 1) Không rộng hơn viewport: width/min-width cố định > 390px ở 390px
wide = []
for sel, decl in css:
    for p in ('width', 'min-width', 'flex-basis'):
        w = px(decl.get(p, ''))
        if w and w > VW: wide.append((sel[:50], p, decl[p]))
    m = re.match(r'(?:[\d.]+\s+[\d.]+\s+)?([\d.]+(?:px|rem))$', decl.get('flex', '').strip())
    if m and px(m[1]) > VW: wide.append((sel[:50], 'flex', decl['flex']))
ck(not wide, 'không width/min-width cố định > 390px', wide[:5])
base = ' '.join(f'{s}{{{";".join(f"{k}:{v}" for k, v in dd.items())}}}' for s, dd in css)
for tag in ('img', 'svg', 'video', 'table', 'pre', 'iframe'):
    used = any(t == tag for _, t, _ in els)
    if used:
        ok = any(re.search(rf'(^|[\s,]){tag}\b', s) and (dd.get('max-width') == '100%' or dd.get('width') == '100%' or dd.get('overflow-x') in ('auto', 'scroll') or dd.get('overflow') in ('auto', 'scroll', 'hidden')) for s, dd in css)
        ck(ok, f'<{tag}> bị giới hạn theo viewport (max-width:100% / cuộn riêng)', 'thiếu rule')

# 2) Chữ ô nhập ≥16px (tránh iOS tự zoom)
small = set()
for n, t, a in els:
    if t in ('input', 'select', 'textarea') and a.get('type') not in ('hidden', 'checkbox', 'radio', 'submit', 'button', 'range'):
        fs = eff(t, a, 'font-size'); v = px(fs) if fs else 16
        if v is None or v < 16: small.add((t, a.get('class') or a.get('id') or '', fs))
ck(not small, 'ô nhập/select/textarea có font-size ≥16px', sorted(small))
# ô nhập chèn bằng JS (createElement) — luật phải có trong CSS theo class
for f in glob.glob(f'{R}/*.js') + glob.glob(f'{R}/x/*.js'):
    pass
fsel = [(s, px(dd['font-size']) if 'font-size' in dd else None, dd) for s, dd in css if re.search(r'\b(input|select|textarea)\b', s)]
tiny = [(s[:50], dd.get('font-size') or dd.get('font')) for s, _, dd in fsel
        for v in [px(dd['font-size']) if 'font-size' in dd else None] if v is not None and v < 16]
tiny += [(s[:50], dd['font']) for s, _, dd in fsel if 'font' in dd and (lambda m: m and px(m[1]) is not None and px(m[1]) < 16)(re.search(r'(?:^|\s)(-?[\d.]+(?:px|rem|em))(?:/[^\s]+)?\s', dd['font'] + ' '))]
ck(not tiny, 'rule CSS cho input/select/textarea không đặt chữ <16px', tiny[:5])

# 3) Vùng bấm ≥44px (cảm ứng, 390px) cho nút/liên kết/tab/ô nhập
inter = ('button', 'a', 'select', 'input', 'summary')
smallt = {}
for n, t, a in els:
    if t not in inter and a.get('role') not in ('tab', 'button'): continue
    if t == 'a' and 'href' not in a: continue
    if t == 'input' and a.get('type') in ('hidden', 'checkbox', 'radio'): continue
    key = (t, a.get('class') or a.get('id') or a.get('role') or '')
    h = eff(t, a, 'min-height'); h2 = eff(t, a, 'height')
    hv = max([x for x in (px(h or ''), px(h2 or '')) if x] or [0])
    if t == 'a' and not a.get('class') and not a.get('id'): continue   # liên kết chữ thường trong đoạn văn
    if hv < 44 and key not in smallt: smallt[key] = hv
ck(not smallt, 'nút/tab/ô nhập/liên kết có class cao ≥44px', sorted(smallt.items())[:8])
wsm = []
for n, t, a in els:
    if t in ('button',) or a.get('role') in ('tab',):
        for p in ('width',):
            w = px(eff(t, a, p) or '')
            if w and w < 44: wsm.append((a.get('class') or a.get('id') or t, w))
ck(not wsm, 'nút không rộng cố định <44px', sorted(set(wsm))[:5])
# class chỉ do JS tạo: những selector tap chính phải ≥44 ở 390px
js_tap = []; last = {}
for sel, decl in css:
    for one in sel.split(','):
        one = one.strip()
        if re.search(r'\.(chip|btn|scheme|srch|lg)\b|\.tags a|\.mp>a|\.pp-i a|\.pp-ol a|\[role=tab\]|\.mem button|^(button|select)\b|input\b', one):
            for p in ('min-height', 'height'):
                if p in decl: last.setdefault(one, {})[p] = decl[p]
for one, dd in last.items():
    v = max([px(x) or 0 for x in dd.values()])
    if v < 44 and not re.search(r'\.lg|progress', one): js_tap.append((one[:45], dd))
ck(not js_tap, 'selector nút (kể cả JS tạo) ≥44px ở 390px', js_tap[:6])

# 4) Mục 20: scrollWidth ≤ 390 (tĩnh) + mọi điều khiển ≥44×44 + chi tiết mobile 16–19
def last(sel_re, prop):
    v = None
    for sel, decl in css:
        if any(re.fullmatch(sel_re, x.strip()) for x in sel.split(',')) and prop in decl: v = decl[prop]
    return v
# 4a) mọi khối chứa kích thước cố định ngang (width/min-width/max-width px, margin âm lớn) không vượt 390
over = []
for sel, decl in css:
    for p in ('width', 'min-width', 'max-width', 'flex-basis'):
        w = px(decl.get(p, ''))
        if w and w > VW and p != 'max-width': over.append((sel[:40], p, decl[p]))
    m = re.match(r'(-?[\d.]+)(px|rem)', decl.get('margin-left', '').strip())
    if m and (px(m[0]) or 0) < -16: over.append((sel[:40], 'margin-left', decl['margin-left']))
ck(not over, 'scrollWidth ≤ 390: không phần tử cố định rộng/lệch quá viewport', over[:5])
# 4b) điều khiển ≥44 cả hai chiều (kể cả liên kết có class, nút trong menu)
dim = {}
for n, t, a in els:
    if not (t in ('button', 'select', 'summary') or a.get('role') in ('tab', 'button') or (t == 'a' and 'href' in a and (a.get('class') or a.get('id'))) or (t == 'input' and a.get('type') not in ('hidden', 'checkbox', 'radio'))): continue
    if 'vh' in (a.get('class') or '').split(): continue   # ẩn thị giác (nhãn đọc màn hình)
    key = (t, a.get('class') or a.get('id') or a.get('role') or '')
    h = max([x for x in (px(eff(t, a, 'min-height') or ''), px(eff(t, a, 'height') or '')) if x] or [0])
    w = px(eff(t, a, 'width') or '') or px(eff(t, a, 'min-width') or '')
    if h < 44 or (w is not None and w < 44): dim[key] = (h, w)
ck(not dim, 'mọi nút/liên kết điều khiển ≥44×44', sorted(dim.items())[:8])
# 4c) nút đổi sáng/tối trong menu đúng 44px
sch = [dd for s, dd in css if re.fullmatch(r'\.mp \.scheme', s.split(',')[0].strip())]
ck(any(px(d_.get('min-height', '')) == 44 and px(d_.get('min-width', '')) == 44 for d_ in sch), 'nút sáng/tối trong menu ≥44×44 ở 390px', sch[:1])
# 4d) tiêu đề trang co theo clamp(2.4rem,13vw,3.4rem)
ck(last(r'\.title', 'font-size') == 'clamp(2.4rem,13vw,3.4rem)', 'tiêu đề .title = clamp(2.4rem,13vw,3.4rem) ở mobile', last(r'\.title', 'font-size'))
# 4e) dải ban cuộn ngang + mép mờ
tg = {}
for s, dd in css:
    if s.strip() == '.tags': tg.update(dd)
ck(tg.get('overflow-x') == 'auto' and 'mask-image' in tg and 'gradient' in tg['mask-image'], 'dải ban cuộn ngang có mép mờ (mask-image)', tg.get('mask-image'))
# 4f) padding thẻ mobile 1rem
pl = [dd for s, dd in css if s.strip() in ('.tray .card,.board>.card,.art-board>.card',)]
ck(pl and all(any(px(d_.get(k, '')) == 16 for k in ('padding', 'padding-left')) or d_.get('padding', '').startswith('1rem') for d_ in pl), 'padding thẻ mobile 1rem', pl)
print('\n' + ('FAIL ' + str(len(bad)) if bad else 'PASS test_mobile'))
sys.exit(1 if bad else 0)

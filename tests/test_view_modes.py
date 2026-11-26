#!/usr/bin/env python3
"""Chế độ đọc: giá trị lưu theo hồ sơ (qua node), thuộc tính đặt sớm trong <head> (không nháy), mọi chế độ không làm tràn ngang (quét tĩnh)."""
import json, os, re, subprocess, sys
d = os.path.dirname(os.path.abspath(__file__)); S = f'{d}/..'; bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
pub = lambda f: open(f'{S}/public/{f}', encoding='utf8').read()

# 1) giá trị lưu: chạy lõi thật bằng node
js = r"""
const R = require(process.argv[1] + '/web/rank.js'), C = require(process.argv[1] + '/web/x/profilectl.js'), o = {};
const p = R.ensure(R.newProfile(null, []));
o.default = C.getView(p).fs === 'md' && !C.getView(p).titles;
o.set = C.setView(p, { fs: 'lg', titles: true }) && p.view.fs === 'lg' && p.view.titles === true;
o.bad_ignored = (C.setView(p, { fs: 'huge', titles: 'yes' }), p.view.fs === 'lg' && p.view.titles === true);
const q = C.importProfile(C.exportProfile(p)).profile; o.roundtrip = q.view.fs === 'lg' && q.view.titles === true;
const old = C.getView(R.ensure({ v: 2, w: {} })); o.old_profile = old.fs === 'md' && old.titles === false;
const z = C.getView(R.ensure({ v: 2, w: {}, view: { fs: 'x', titles: 1 } })); o.sanitized = z.fs === 'md' && z.titles === false;
o.reset_keeps = (C.resetTaste(p), C.getView(p).fs === 'lg');
console.log(JSON.stringify(o));
"""
r = json.loads(subprocess.run(['node', '-e', js, S], capture_output=True, text=True, check=True).stdout)
for k, v in r.items(): ck(v is True, 'giá trị lưu: ' + k)

# 2) thuộc tính đặt sớm: script trong <head>, trước style.css? ít nhất trước </head> và trước <body>, không phụ thuộc file JS
for page in ('index.html', 'me.html'):
    h = pub(page); head = h.split('</head>')[0]
    sc = [m for m in re.findall(r'<script>(.*?)</script>', head, re.S)]
    early = next((s for s in sc if 'press.scheme' in s), '')
    ck(bool(early), f'{page}: script nội tuyến trong <head>')
    ck(all(k in early for k in ('dataset.fs', 'dataset.titles', "press.p.", 'press.profiles')), f'{page}: đặt data-fs/data-titles từ hồ sơ trước khi vẽ')
    ck(bool(early) and '<body' not in head, f'{page}: chạy đồng bộ trong <head>, trước <body>')

# 3) menu hiển thị
me = pub('me.html')
for a in ('data-pc-view', 'data-fs="sm"', 'data-fs="md"', 'data-fs="lg"', 'data-pc-titles', 'data-mode="light"', 'data-mode="dark"', 'data-mode="auto"'):
    ck(a in me, f'me.html có {a}')
src = open(f'{S}/web/x/profilectl.js', encoding='utf8').read()
ck('innerHTML' not in src, 'profilectl.js không innerHTML')

# 4) tràn ngang (tĩnh): mọi chế độ chỉ đổi font-size gốc / display:none, không đặt width/min-width/white-space:nowrap
css = pub('style.css'); rules = re.findall(r'html\[data-(?:fs|titles)[^{]*\{([^}]*)\}', css)
ck(len(rules) >= 3, 'style.css có quy tắc cho data-fs / data-titles')
ck(all(not re.search(r'(^|;)\s*(min-)?width|nowrap|overflow-x|position\s*:\s*(fixed|absolute)', r) for r in rules), 'quy tắc chế độ không đặt width/nowrap/absolute → không gây scrollWidth > viewport')
ck(all(re.fullmatch(r'\s*(font-size:[\d.]+%|display:none)\s*;?\s*', r) for r in rules), 'quy tắc chế độ chỉ đổi font-size (%) hoặc display:none')
big = max(float(x) for x in re.findall(r'data-fs=lg\]\{font-size:([\d.]+)%', css) or ['0'])
ck(0 < big <= 125, f'A+ ≤125% ({big}%)')
ck(re.search(r'overflow-wrap\s*:\s*(anywhere|break-word)|word-break', css) is not None, 'có overflow-wrap để chữ lớn không đẩy tràn')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_view_modes'); sys.exit(1 if bad else 0)

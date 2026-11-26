#!/usr/bin/env python3
"""Điều khiển hồ sơ đọc: logic (rank.js) qua node, khung HTML build, chip bấm được, mọi chữ bằng textContent."""
import json, os, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
S = f'{d}/..'; bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
r = json.loads(node(f'{d}/sim_profiles.js'))
for k in ('ctl_roundtrip', 'ctl_import_rejects', 'ctl_import_sanitized', 'ctl_reset', 'ctl_reset_keeps_saved', 'ctl_topic_toggle', 'ctl_source_modes', 'ctl_level_changes_rank', 'ctl_level_explore_share', 'ctl_default_mid_same'):
    ck(r.get(k) is True, k)
pub = lambda f: open(f'{S}/public/{f}', encoding='utf8').read()
me = pub('me.html')
for a in ('data-pc ', 'data-pc-level', 'data-pc-topics', 'data-pc-sources', 'data-pc-reset', 'data-pc-export', 'data-pc-import', 'Hồ sơ đọc của tôi'):
    ck(a in me, f'me.html có {a.strip()}')
ui = pub('x/ui.js'); ck('PressProfileCtl' in ui and 'data-pc-level' in ui, 'x/ui.js (lazy) có module điều khiển hồ sơ')
ck(me.count('role="tab"') == 4 and 'data-pc' in me.split('id="pn-cai-dat"')[0], 'panel hồ sơ đọc nằm trong tab Bộ nhớ (vẫn 4 tab)')
ck('Ít' in me and 'Vừa' in me, 'nhãn mức Ít/Vừa/Nhiều')
js = open(f'{S}/web/x/profilectl.js', encoding='utf8').read()
ck('innerHTML' not in js and 'insertAdjacentHTML' not in js and 'document.write' not in js, 'controls.js không innerHTML')
app = open(f'{S}/web/app.js', encoding='utf8').read()
ck("'me.html?topic='" in app and "#bo-nho" in app and 'vì bạn theo: ' in app, "chip 'vì bạn theo' bấm được → me.html?topic=…#bo-nho")
ck('URLSearchParams' in js and 'data-focus' in js, 'trang hồ sơ mở đúng chủ đề từ chip')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_profile_controls'); sys.exit(1 if bad else 0)

#!/usr/bin/env python3
"""Nút 'Chạy báo hôm nay' + ô API key: logic (run-core.js, fetch giả) và các ràng buộc riêng tư của FE/Worker (key chỉ ở localStorage)."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
ok = {k: bool(v) for k, v in json.loads(node(f'{d}/sim_run.js')).items()}
W = f'{d}/../web/'; rd = lambda f: open(W + f, encoding='utf8').read()
st, rc, cm, wk = rd('settings.js'), rd('run-core.js'), rd('community.js'), open(f'{d}/../worker/share-worker.js', encoding='utf8').read()
ok['settings: key lưu localStorage, không gửi đi đâu ngoài nhà cung cấp'] = "'press.ai'" in st and 'fetch(' not in st and 'XMLHttpRequest' not in st and 'sendBeacon' not in st
ok['settings: có nút Xoá key'] = 'data-ai-clear' in st and "removeItem(KEY)" in st
ok['settings: cảnh báo key ở máy + chi phí'] = bool(re.search(r'chi phí', open(f'{d}/../theme.py', encoding='utf8').read(), re.I)) and 'chỉ nằm trên máy này' in open(f'{d}/../theme.py', encoding='utf8').read()
ok['community/share-core: không còn invite/admin/token thành viên'] = not re.search(r'invite|admin|redeem|member', cm + rd('share-core.js') + wk, re.I)
ok['community: key AI không bị đọc'] = 'press.ai' not in cm
ok['worker: không secret, không key AI'] = 'ADMIN_TOKEN' not in wk and 'x-api-key' not in wk.lower() and 'anthropic' not in wk.lower()
ok['worker: /fetch chỉ https + allowlist host'] = 'PROXY_HOSTS' in wk and "'https:'" in wk.replace('/^https:$/.test(t.protocol)', "'https:'")
ok['worker: /fetch không nhận Authorization của người dùng'] = "headers: { 'user-agent'" in wk
ok['run-core: không dùng localStorage/DOM'] = 'localStorage' not in rc and 'document' not in rc
for k, v in ok.items(): print(('OK   ' if v else 'FAIL ') + k.replace('_', ' '))
sys.exit(0 if all(ok.values()) else 1)

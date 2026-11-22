#!/usr/bin/env python3
"""Chia sẻ mở, KHÔNG tài khoản/mời/admin: logic (share-core.js) bằng node, kho KV bộ nhớ; kiểm Worker không chứa bí mật; FE không gọi BE khi tắt."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
r = json.loads(node(f'{d}/sim_share.js'))
r.pop('share_bad_url', None)
ok = {k: bool(v) for k, v in r.items()}
w = open(f'{d}/../worker/share-worker.js', encoding='utf8').read()
ok['worker: không bí mật/admin'] = 'ADMIN_TOKEN' not in w and not re.search(r'/admin/|invite|redeem', w)
ok['worker: chặn Origin lạ'] = 'ALLOW_ORIGIN' in w and "'Origin không được phép.'" in w
ok['worker: giới hạn body'] = '4096' in w
import tomllib
cfg = tomllib.load(open(f'{d}/../config/share.toml', 'rb'))
ok['config/share.toml: endpoint chỉ là URL https hoặc rỗng'] = cfg.get('endpoint', '') == '' or cfg['endpoint'].startswith('https://')
ok['config/share.toml: không chứa khoá'] = not re.search(r'(token|secret|key)\s*=', open(f'{d}/../config/share.toml').read(), re.I)
for k, v in ok.items(): print(('OK   ' if v else 'FAIL ') + k.replace('_', ' '))
sys.exit(0 if all(ok.values()) else 1)

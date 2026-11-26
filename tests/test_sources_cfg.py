#!/usr/bin/env python3
"""Cấu hình nguồn: offline, chỉ đọc toml."""
import os, sys, urllib.parse
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import press as P
_, desks = P.load_cfg()
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)
feeds = [(k, f) for k, c in desks.items() for f in c.get('feed', [])]
chk('mọi feed có id/name/url', all(f.get('id') and f.get('name') and f.get('url') for _, f in feeds))
chk('url là https', all(urllib.parse.urlparse(f['url']).scheme == 'https' and urllib.parse.urlparse(f['url']).hostname for _, f in feeds))
ids = [f['id'] for _, f in feeds]
chk('id không trùng', len(ids) == len(set(ids)))
for k, c in desks.items(): chk(f'ban {k} ≥ 8 nguồn ({len(c.get("feed", []))})', len(c.get('feed', [])) >= 8)
chk('PER_FEED ≤ 4', P.PER_FEED <= 4)
hosts = set(P.proxy_hosts())
chk('host mọi feed nằm trong `press.py hosts`', all(urllib.parse.urlparse(f['url']).hostname in hosts for _, f in feeds))
sys.exit(0 if all(ok) else 1)

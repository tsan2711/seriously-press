#!/usr/bin/env python3
"""U3: tìm kiếm cục bộ — đúng/lọc/đoạn trích/bỏ dấu, <100 ms trên 5k bài (node), search.json build đúng định dạng và không PII."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
r = json.loads(node(f'{d}/sim_search.js')); bad = []
names = {'finds_title': 'tìm theo tiêu đề', 'and_tokens': 'nhiều từ = AND', 'no_diacritics': 'gõ không dấu vẫn khớp chữ có dấu', 'filter_topic': 'lọc theo chủ đề', 'filter_desk': 'lọc theo ban', 'filter_source': 'lọc theo nguồn',
         'filter_date': 'lọc theo ngày', 'snippet_marks': 'đoạn trích có khớp tô sáng', 'title_beats_body': 'khớp tiêu đề xếp trên khớp nội dung', 'empty_query_filter': 'chỉ lọc, không từ khoá', 'no_match_empty': 'không khớp → rỗng',
         'limit': 'giới hạn số kết quả', 'facets': 'đếm facet', 'speed_ok': f"5k bài: {r['ms']:.1f} ms hiệu chuẩn JIT (thô {r['raw_ms']:.0f} ms ÷ {r['slow']:.0f}) <100", 'speed_cold_ok': f"dựng chỉ mục 5k: {r['build_ms']:.0f} ms (<400)"}
for k, n in names.items():
    print(('OK   ' if r.get(k) else 'FAIL ') + n)
    if not r.get(k): bad.append(n)
p = os.path.join(d, '..', 'public', 'search.json')
if not os.path.exists(p): bad.append('thiếu public/search.json (chạy build)')
else:
    j = json.load(open(p, encoding='utf8')); rows = j['rows']
    ok = rows and all(len(x) == 10 and isinstance(x[5], list) and re.match(r'\d{4}-\d\d-\d\d$', x[4]) for x in rows)
    print(('OK   ' if ok else 'FAIL ') + f'search.json: {len(rows)} hàng, đúng 10 cột'); ok or bad.append('search.json sai định dạng')
    t = open(p, encoding='utf8').read()
    pii = re.search(r'sk-ant-|@gmail\.com|nguyen[t]ansang|press\.(journal|mem|seen)', t)
    print(('FAIL ' if pii else 'OK   ') + 'search.json: không PII/khoá'); pii and bad.append('search.json dính PII')
    sz = len(t.encode()); print(('OK   ' if sz < 3_000_000 else 'FAIL ') + f'search.json {sz//1000} KB (<3 MB)'); sz < 3_000_000 or bad.append('search.json quá lớn')
sys.exit(1 if bad else 0)

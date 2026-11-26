#!/usr/bin/env python3
"""Cổng tỉ lệ bài có ảnh: bộ số báo mẫu (tests/fixtures/img_coverage_issue.json) phải ≥ 90% có ảnh; offline."""
import os, sys, json
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import metrics
GATE = 90.0
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)
fx = json.load(open(f'{d}/fixtures/img_coverage_issue.json', encoding='utf8'))['articles']
ic = metrics.img_coverage(fx)
print(metrics.img_line(ic))
chk(f'số báo mẫu: ảnh {ic["pct"]}% ≥ {GATE}%', ic['pct'] >= GATE)
chk('các kênh cộng lại = tổng bài', ic['og'] + ic['body'] + ic['feed'] + ic['host'] + ic['commons'] + ic['none'] == ic['total'])
chk('đủ cả 5 kênh trong mẫu (og·thân·feed·host·commons)', all(ic[k] > 0 for k in ('og', 'body', 'feed', 'host', 'commons')))
# cổng phải thật sự đỏ khi tụt: bỏ ảnh 15% bài thì dưới ngưỡng
low = [dict(a) for a in fx]
for a in low[:max(1, len(low) * 15 // 100)]: a.pop('img', None)
chk('mẫu bị tụt ảnh → dưới ngưỡng (cổng bắt được)', metrics.img_coverage(low)['pct'] < GATE)
chk('chuỗi báo đúng khuôn', metrics.img_line(ic).startswith('ảnh: ') and ' — og ' in metrics.img_line(ic) and 'không có' in metrics.img_line(ic))
chk('danh sách rỗng không sập', metrics.img_coverage([])['pct'] == 0.0)
txt = metrics.render(metrics.compute([dict(date='2026-11-23', generated='2026-11-23T10:00:00', articles=fx, errors=[])], []), ['x'], '2026-11-23')
chk('daily-metrics có dòng ảnh', 'ảnh: ' in txt)
sys.exit(0 if all(ok) else 1)

#!/usr/bin/env python3
"""Test metrics.py bằng dữ liệu giả (không mạng, không ghi vào knowledge/)."""
import os, sys, json, tempfile
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import metrics
def art(i, src, topic, h=2): return dict(id=f'a{i}', title=f't{i}', source=src, topics=[topic], published=f'2026-11-2{1}T0{h}:00:00Z')
def day(date, arts, errs): return dict(date=date, generated=f'{date}T10:00:00', articles=arts, errors=errs)
A = [art(i, 'HN', 'llm') for i in range(8)] + [art(10, 'Blog', 'godot')]
days = [day(f'2026-11-{15 + k}', A, ['ai/reddit:LocalLLaMA: HTTPError: 403']) for k in range(7)]
jr = [{'days': {'2026-11-20': {'n': {'seen': 20, 'open': 5, 'skip': 15}, 'items': {f'i{k}': {'t': 'x', 's': 'Old', 'topics': ['finance'], 'ev': {'skip': 1}} for k in range(12)} | {f'o{k}': {'t': 'y', 's': 'Blog', 'topics': ['godot'], 'ev': {'open': 1}} for k in range(6)}}}}]
m = metrics.compute(days, jr); P = metrics.proposals(m); txt = metrics.render(m, P, '2026-11-21')
ok = [
    ('đa dạng chủ đề thấp khi dồn 1 chủ đề', m['topic_entropy_norm'] < 0.55),
    ('nguồn lớn nhất = HN, >40%', m['top_source'] == 'HN' and m['top_source_share'] > 0.4),
    ('nguồn lỗi 7/7 ngày được đề xuất tắt', any('reddit:LocalLLaMA' in x and 'lỗi 7/7' in x for x in P)),
    ('đề xuất giảm chủ đề bị bỏ qua 12 lần, 0 mở', any('`finance`' in x for x in P)),
    ('đề xuất tăng trọng số nguồn mở nhiều', any('`Blog`' in x and 'tăng' in x for x in P)),
    ('tỉ lệ mở từ nhật ký = 5/40', m['open_rate'] == 0.125),
    ('báo cáo có frontmatter + mục Đề xuất, nói rõ không tự sửa', txt.startswith('---') and '## Đề xuất cho Bi duyệt' in txt and 'không sửa config' in txt),
    ('dữ liệu trống không sập', 'chưa có dữ liệu' in metrics.render(metrics.compute([], []), metrics.proposals({}), '2026-11-21')),
]
with tempfile.TemporaryDirectory() as t:
    metrics.main(['--out', f'{t}/m.md']); ok.append(('chạy thật trên store/ → ghi tệp', os.path.getsize(f'{t}/m.md') > 100))
for k, v in ok: print(('OK   ' if v else 'FAIL ') + k)
sys.exit(0 if all(v for _, v in ok) else 1)

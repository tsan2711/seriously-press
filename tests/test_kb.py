#!/usr/bin/env python3
"""K3: knowledge base — gom câu chuyện nhiều ngày + timeline, thực thể, nguồn, tra cứu 'liên quan trước đó', hết hạn/nén, không PII, tăng có kiểm soát."""
import os, sys, json, datetime, re, hashlib, tempfile
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import kb as K
c = K.cfg(); ok = []
def chk(n, v): ok.append((n, bool(v)))
def A(t, u, s='HN', summ=''): return dict(title=t, url=u, source=s, summary=summ, topics=['gamedev'])
kb = dict(stories={}, sources={}); D = lambda n: (datetime.date(2026, 1, 1) + datetime.timedelta(days=n)).isoformat()
K.ingest(kb, [A('Godot 4.5 released with typed dictionaries', 'https://g.io/45'), A('Ubisoft studio closure in Montreal', 'https://u.io/1')], D(0), c)
r1 = K.ingest(kb, [A('Godot 4.5.1 released fixing typed dictionaries crash', 'https://g.io/451', 'Blog'), A('Ubisoft studio closure in Montreal', 'https://copy.io/u1', 'Other')], D(3), c)
sid = next(s for s in kb['stories'].values() if 'Godot' in s['title'])
chk('câu chuyện gom qua ngày: 2 mục trong timeline, rev tăng', len(sid['entries']) == 2 and sid['rev'] == 1 and sid['first'] == D(0) and sid['last'] == D(3))
chk('timeline ghi trạng thái từng mục (new → update)', [e['st'] for e in sid['entries']] == ['new', 'update'])
chk('tin cùng nội dung outlet khác không tạo story mới', len(kb['stories']) == 2 and r1['repeat'] == 1 and r1['update'] == 1)
art = [A('Godot Foundation announces funding round for Godot Engine', 'https://g.io/fund2', 'Blog')]; K.ingest(kb, art, D(6), c)
chk('bài mới có related trỏ tới story cũ (ngày + tiêu đề)', art[0].get('related') and art[0]['related'][0]['title'].startswith('Godot'))
q = K.query(kb, 'godot 4.5.1')
chk('query() tìm đúng câu chuyện', q and q[0]['title'].startswith('Godot') and q[0]['days'] >= 2)
with tempfile.TemporaryDirectory() as tmp:
    K.save(kb, tmp); e = json.load(open(f'{tmp}/entities.json')); sr = json.load(open(f'{tmp}/sources.json'))
    chk('thực thể: godot có ≥2 câu chuyện', e.get('godot', {}).get('n', 0) >= 2)
    chk('nguồn: đếm new/update/repeat theo ngày', sr['HN']['days'][D(0)]['new'] == 2 and sr['Other']['days'][D(3)]['repeat'] == 1)
    kb2 = K.load(tmp); chk('lưu/đọc vòng tròn giữ nguyên', json.dumps(kb2['stories'], sort_keys=True) == json.dumps(kb['stories'], sort_keys=True))
    raw = open(f'{tmp}/stories.jsonl', encoding='utf8').read() + open(f'{tmp}/sources.json', encoding='utf8').read()
    chk('không PII: không email/token/khoá', not re.search(r'@[a-z0-9-]+\.[a-z]{2,}|sk-[A-Za-z0-9]{10,}|ADMIN_TOKEN', raw))
# hết hạn + nén + tăng có kiểm soát: 200 ngày × 12 tin, mỗi ngày đều có vài tin lặp
kb3 = dict(stories={}, sources={}); sizes = []
def w(n): return ''.join(chr(97 + b % 26) for b in hashlib.sha1(str(n).encode()).digest()[:8])
for day in range(200):
    arts = [A(f'{w(day * 20 + i).title()} {w(day * 20 + i + 9000)} {w(day * 20 + i + 18000)} update', f'https://x.io/{day}/{i}') for i in range(12)]
    if day: arts.append(A(f'{w((day - 1) * 20).title()} {w((day - 1) * 20 + 9000)} {w((day - 1) * 20 + 18000)} update', f'https://x.io/{day - 1}/0'))
    K.ingest(kb3, arts, D(day), c); sizes.append(len(kb3['stories']))
chk('hết hạn: kho dừng tăng sau ttl (không vô hạn)', max(sizes[100:]) <= 13 * c['kb']['ttl_days'] and sizes[-1] <= sizes[120] + 12)
old = [e for s in kb3['stories'].values() for e in s['entries'] if e['d'] < D(200 - c['kb']['slim_after_days'] - 1)]
chk('nén: mục cũ bỏ tiêu đề/fact, giữ ngày+url+rev', old and all('title' not in e and 'f' not in e and 'url' in e and 'rev' in e for e in old))
chk('timeline mỗi story có trần', all(len(s['entries']) <= c['kb']['max_entries'] for s in kb3['stories'].values()))
# KB thật trong repo: hợp lệ + gọn
real = K.load(); n = len(real['stories']); sz = sum(os.path.getsize(f'{K.KBDIR}/{f}') for f in os.listdir(K.KBDIR)) if os.path.isdir(K.KBDIR) else 0
chk(f'KB thật: có dữ liệu, gọn ({n} story, {sz // 1024} KB ≤ 2048 KB)', n > 0 and sz <= 2048 * 1024)
for n_, v in ok: print(('OK   ' if v else 'FAIL ') + n_)
sys.exit(0 if all(v for _, v in ok) else 1)

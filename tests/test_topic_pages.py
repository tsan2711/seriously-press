#!/usr/bin/env python3
"""Trang chủ đề: topic-<id>.html cho mọi chủ đề có bài (≤24, mới nhất trước), topics.html, liên kết từ thẻ + chip, không trang mồ côi, sitemap/precache.
Dữ liệu mẫu dựng trong bộ nhớ → chạy offline; phần cuối kiểm bản build thật trong public/ nếu có."""
import glob, os, re, sys, tempfile, json
from html.parser import HTMLParser
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{D}/..')
import theme, extras
bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
class P(HTMLParser):
    def __init__(s): super().__init__(); s.href = []; s.cards = 0; s.chipl = 0; s.follow = 0
    def handle_starttag(s, t, a):
        a = dict(a)
        if t == 'a' and a.get('href'): s.href.append(a['href'])
        if t == 'article' and 'card' in (a.get('class') or ''): s.cards += 1
        if t == 'a' and 'chip-l' in (a.get('class') or ''): s.chipl += 1
        if 'data-follow-topic' in a: s.follow += 1
def parse(h): p = P(); p.feed(h); return p
TOP = {'ai': dict(label='AI', desks=['ai']), 'ui': dict(label='UI & <b>', desks=['design']), 'vacant': dict(label='Trống', desks=['ai'])}
DESKS = {'ai': dict(name='AI', tagline='t', accent='#111'), 'design': dict(name='Design', tagline='t', accent='#222')}
def art(i, topics, d='2026-11-23', pub=None):
    return dict(id=f'{i:08x}' + '0' * 8, sid=f's{i}', title=f'Bài số {i} đủ dài để làm tiêu đề thử', url=f'https://e.com/{i}', summary='x' * 150, published=pub or f'{d}T{i % 24:02d}:00:00Z', source='S', points=0, topics=topics, desks=['ai'], img='', status='new')
today = [art(i, ['ai'] if i % 2 else ['ui', 'ai']) for i in range(1, 40)] + [art(100, ['ghost'])]   # 'ghost' không có trong cấu hình
hist = [dict(date='2026-11-22', articles=[art(200 + i, ['ui'], '2026-11-22') for i in range(5)] + [dict(art(1, ['ai']), id='dup')])]   # sid trùng s1 → bỏ
ctx = theme.Ctx(dict(date='2026-11-23', generated='2026-11-23T12:00:00', articles=today), TOP, DESKS, history=hist)
pages = theme.render_all(ctx)
tp = {k for k in pages if k.startswith('topic-')}
ck(tp == {'topic-ai.html', 'topic-ui.html'}, f'số trang = số chủ đề có bài ({sorted(tp)}; "vacant" và "ghost" không có trang)')
ck('topics.html' in pages, 'có topics.html')
for t in ('ai', 'ui'):
    p = parse(pages[f'topic-{t}.html']); ck(p.cards <= 24 and p.cards >= 1, f'topic-{t}: 1..24 thẻ ({p.cards})'); ck(p.follow == 1, f'topic-{t}: có nút Theo dõi chủ đề')
ids = [a['sid'] for a in ctx.TPAGES['ui']]; pubs = [a['published'] for a in ctx.TPAGES['ui']]
ck(pubs == sorted(pubs, reverse=True), 'mới nhất trước'); ck(len(ids) == len(set(ids)), 'không trùng bài'); ck(any(i.startswith('s2') or i.startswith('s2') for i in ids) and any(i.startswith('s2') for i in ids), 'có bài từ số báo trước (ui)')
ck(len(ctx.TPAGES['ai']) == 24, 'chủ đề nhiều bài bị cắt ở 24')
ck('&lt;b&gt;' in pages['topic-ui.html'] and '<b>' not in pages['topic-ui.html'].split('<h1>')[1].split('</h1>')[0], 'nhãn chủ đề được escape')
# liên kết nội bộ tồn tại + không mồ côi
names = set(pages) | {'repos.html'}   # repos.html do hotrepos.write_page ghi riêng ngoài render_all
inbound = {n: 0 for n in names}
for n, h in pages.items():
    if 'http-equiv="refresh"' in h and len(h) < 400: continue
    for hr in parse(h).href:
        if re.match(r'^(https?:|#|mailto:)', hr): continue
        f = hr.split('#')[0]
        if f.endswith('.html'):
            ck(f in names, f'{n} → {f} tồn tại') if f not in names else None
            if f in inbound and f != n: inbound[f] += 1
orph = [n for n in tp | {'topics.html'} if not inbound[n]]; ck(not orph, f'không trang mồ côi {orph}')
ck(parse(pages['index.html']).href.count('topic-ai.html') >= 1, 'thẻ ở trang chủ liên kết tới chủ đề')
ck(parse(pages['picker.html']).chipl == 2 and 'topic-vacant.html' not in pages['picker.html'], 'chip trong màn chọn có liên kết (chỉ chủ đề có bài)')
# sitemap + precache trên thư mục tạm
with tempfile.TemporaryDirectory() as root:
    os.makedirs(f'{root}/public'); os.makedirs(f'{root}/store')
    for n, h in pages.items(): open(f'{root}/public/{n}', 'w', encoding='utf8').write(h)
    json.dump(dict(date='2026-11-23', articles=today), open(f'{root}/store/2026-11-23.json', 'w'))
    extras.build_feed(root); sm = open(f'{root}/public/sitemap.xml', encoding='utf8').read()
    ck('topic-ai.html' in sm and 'topics.html' in sm, 'sitemap có trang chủ đề')
sh = [f for f in glob.glob(f'{D}/../web/sw.js')]; ck(bool(sh), 'sw.js nguồn có mặt (SHELL quét mọi *.html trong build)')
print('FAIL' if bad else 'test_topic_pages: OK'); sys.exit(1 if bad else 0)

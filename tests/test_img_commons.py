#!/usr/bin/env python3
"""Ảnh dự phòng Wikimedia Commons — offline, JSON API mẫu."""
import os, sys, tempfile, json
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import imgfind as F
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)
cfg = F.load_cfg()
def page(i, title, w=1200, lic='CC BY-SA 4.0', desc='', artist='<a href="x">Jane Doe</a>', thumb=True):
    return str(i), dict(index=i, title=title, imageinfo=[dict(width=w, height=800, thumburl=f'https://upload.wikimedia.org/t/{i}.jpg' if thumb else '',
        extmetadata=dict(LicenseShortName=dict(value=lic), Artist=dict(value=artist), ImageDescription=dict(value=desc)))])
def api(*ps): return dict(query=dict(pages=dict(ps)))
SAMPLE = api(
    page(1, 'File:Sunset over mountains.jpg', desc='unrelated landscape'),
    page(2, 'File:Roguelike deckbuilder game photo.jpg', desc='roguelike deckbuilder card game'),
    page(3, 'File:Roguelike deckbuilder logo.png', desc='roguelike deckbuilder'),
    page(4, 'File:Roguelike deckbuilder card.svg', desc='roguelike deckbuilder'),
    page(5, 'File:Roguelike deckbuilder small.jpg', w=300, desc='roguelike deckbuilder'),
    page(6, 'File:Roguelike deckbuilder nc.jpg', lic='CC BY-NC 4.0', desc='roguelike deckbuilder'),
    page(7, 'File:Roguelike deckbuilder copyrighted.jpg', lic='Copyrighted free use', desc='roguelike deckbuilder'))
want = F.tokens('New roguelike deckbuilder hits Steam', cfg)
chk('stopword bị bỏ', 'new' not in want and 'roguelike' in want)
cs = F.candidates(SAMPLE, cfg)
titles = {c['title'] for c in cs}
chk('loại svg/logo', not any('logo' in t or t.endswith('.svg') for t in titles))
chk('loại ảnh < 600px', 'File:Roguelike deckbuilder small.jpg' not in titles)
chk('loại giấy phép không mở (NC, copyrighted)', not any(k in t for t in titles for k in ('nc.jpg', 'copyrighted')))
chk('còn ảnh hợp lệ', len(cs) == 2)
b = F.best(cs, want, cfg)
chk('chọn đúng ảnh liên quan', b and b['title'].endswith('photo.jpg'))
chk('ghi công có tác giả+giấy phép', b and 'Jane Doe' in b['credit'] and 'CC BY-SA' in b['credit'] and '<' not in b['credit'])
chk('ảnh sai chủ đề bị loại (dưới ngưỡng)', F.best(cs, F.tokens('Quantum networking breakthrough', cfg), cfg) is None)
chk('một token chung chung không đủ', F.best(F.candidates(api(page(1, 'File:Steam locomotive.jpg')), cfg), F.tokens('Steam Deck review roguelike', cfg), cfg) is None)
chk('PD được nhận', F.candidates(api(page(1, 'File:A b c.jpg', lic='Public domain')), cfg) != [])
chk('CC0 được nhận', F.candidates(api(page(1, 'File:A b c.jpg', lic='CC0')), cfg) != [])
chk('JSON hỏng/None không ném', F.candidates(None, cfg) == [] and F.candidates({'x': 1}, cfg) == [])
# fill_commons
root = tempfile.mkdtemp(); calls = []
def fake(u): calls.append(u); return SAMPLE
arts = [dict(title='New roguelike deckbuilder hits Steam', topics=['roguelike'], img=''), dict(title='Has image', img='https://x.example/a.jpg'),
        dict(title='Quantum networking breakthrough', img='')]
n, q = F.fill_commons(arts, root, lambda a: 'Roguelike', fake, cfg)
chk('gắn ảnh + credit cho bài khớp', arts[0]['img'].startswith('https://upload.wikimedia.org') and 'Jane Doe' in arts[0]['img_credit'])
chk('bài có ảnh sẵn không bị đụng', arts[1]['img'] == 'https://x.example/a.jpg' and 'img_credit' not in arts[1])
chk('bài sai chủ đề: không ảnh', arts[2]['img'] == '' and 'img_credit' not in arts[2])
calls.clear(); arts[0].pop('img'); arts[0]['img'] = ''
F.fill_commons(arts, root, lambda a: 'Roguelike', fake, cfg)
chk('cache theo từ khoá: không truy vấn lại', calls == [] or all('Quantum' in c or 'quantum' in c for c in calls))
c2 = dict(cfg, max_queries=2); calls.clear()
F.fill_commons([dict(title=f'Alpha{i} beta{i} gamma{i} delta{i}', img='') for i in range(10)], tempfile.mkdtemp(), lambda a: '', fake, c2)
chk('giới hạn truy vấn/build', len(calls) == 2)
n, q = F.fill_commons([dict(title='Roguelike deckbuilder', img='')], tempfile.mkdtemp(), lambda a: '', lambda u: None, cfg)
chk('lỗi mạng → không ảnh, không ném', n == 0)
import press
pg = press.credit_caption({'article.html': '<article data-id="a1"><div class="thumb"><img></div><p>x</p>'}, [dict(id='a1', img='https://i/x.jpg', img_credit='A <b> · CC0')])
chk('chú thích hiển thị, đã escape', 'img-credit' in pg['article.html'] and '&lt;b&gt;' in pg['article.html'])
sys.exit(0 if all(ok) else 1)

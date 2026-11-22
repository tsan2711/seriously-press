#!/usr/bin/env python3
"""K2: dedup qua ngày. (1) parity chữ ký Python↔JS; (2) mô phỏng 14 ngày phía build (KB) — 0 trùng, update lọt, idempotent;
(3) mô phỏng 14 ngày phía người đọc (seen-store JS) — không bao giờ hiện lại bài đã thấy, trừ update thật. Không mạng."""
import os, sys, json, datetime, random, tempfile, shutil
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..'); sys.path.insert(0, d)
import kb as K
from nodewrap import node
ok = []
def chk(n, v): ok.append((n, bool(v)))
# ---- 1. parity ----
SAMPLES = [dict(title='Godot 4.5 released with new 2D features', summary='Version 4.5 ships 120 fixes, GDScript 2.1'), dict(title='Ubisoft lays off 166 staff in Montreal and Quebec studios', summary=''),
           dict(title='Tin Việt: Unity công bố bản 6.2 cho Android', summary='Tăng 30% hiệu năng'), dict(title='Why Figma raised $1.2B in 2026?', summary='')]
py = [dict(kt=s['kt'], h=s['h'], f=s['f'], e=s['e']) for s in map(K.sig, SAMPLES)]
js = json.loads(node('-e', f'const D=require("{d}/../web/dedup.js");console.log(JSON.stringify({json.dumps(SAMPLES)}.map(a=>D.sig(a))))'))
chk('parity chữ ký (token, simhash, fact, thực thể) Python = JS', py == js)
cu = ['https://www.Example.com/a/b/?utm_source=x&id=3#frag', 'https://example.com/a/b?id=3']
chk('parity URL chuẩn hoá', json.loads(node('-e', f'const D=require("{d}/../web/dedup.js");console.log(JSON.stringify({json.dumps(cu)}.map(D.canon)))')) == [K.canon(u) for u in cu])
# ---- 2. build: 14 ngày ----
rng = random.Random(7); base = datetime.date(2026, 12, 1); c = K.cfg()
def art(i, title, summ='', url=None): return dict(title=title, url=url or f'https://n{i % 5}.example.com/p/{i}', summary=summ, source=f'S{i % 5}', topics=['t'])
STORY = [('Godot', 'engine'), ('Unity', 'runtime'), ('Figma', 'plugin'), ('Claude', 'agent'), ('Blender', 'render')]
def day_items(n, day):
    """Mỗi ngày: 6 tin hoàn toàn mới + (từ ngày 1) lặp lại mọi tin cũ (feed cũ, outlet khác) + vài tin có update thật."""
    import hashlib
    def w(n):   # từ chỉ-chữ, duy nhất & khác hẳn nhau theo n (tránh tin giả tình cờ trùng)
        return ''.join(chr(97 + b % 26) for b in hashlib.sha1(str(n).encode()).digest()[:7])
    new = [art(day * 100 + i, f'{w(day * 31 + i).title()} {w(day * 37 + i + 500)} {rng.choice(["launches", "acquires", "delays", "open-sources"])} {w(day * 41 + i + 900)} {w(day * 43 + i + 1300)}', f'Details about {w(day + i)}') for i in range(6)]
    return new
kb = dict(stories={}, sources={}); allarts = []; stats = []
upd_days = {4: 'Godot', 9: 'Unity'}
hist = []          # (day, art) đã phát hành
for day in range(14):
    date = (base + datetime.timedelta(days=day)).isoformat(); arts = day_items(6, day)
    # lặp: toàn bộ tin 3 ngày gần nhất, nguyên văn, cùng URL; + một bản "outlet khác" (URL khác, cùng tiêu đề)
    for dd, a in hist[-18:]: arts.append(dict(a))
    for dd, a in hist[-6:]: b = dict(a); b['url'] = 'https://other.example.org/copy/' + a['url'].rsplit('/', 1)[-1]; arts.append(b)
    if day == 4: arts.append(art(900, 'Godot 4.5 released: typed dictionaries', 'Version 4.5 ships', 'https://g.example.com/45'))
    if day == 6: arts.append(art(901, 'Godot 4.5.1 released: typed dictionaries', 'Version 4.5.1 hotfix', 'https://g.example.com/451'))   # update của câu chuyện ngày 4
    if day == 7: arts.append(art(902, 'Godot 4.5.1 released: typed dictionaries', 'Version 4.5.1 hotfix', 'https://mirror.example.net/g451'))   # lặp, không update
    r = K.ingest(kb, arts, date, c); stats.append((date, r, arts)); hist += [(day, a) for a in arts if a['status'] == 'new']
tot = lambda k: sum(r[k] for _, r, _ in stats)
fresh_urls = {}; dup = 0
for date, r, arts in stats:
    for a in arts:
        if a['status'] in ('new', 'update'):
            key = (K.canon(a['url']), a['rev'])
            if key in fresh_urls: dup += 1
            fresh_urls[key] = 1
chk('14 ngày: không bài nào "new/update" bị phát hành hai lần (0 trùng)', dup == 0)
chk('14 ngày: mọi tin cũ lặp lại đều bị đánh repeat', all(r['repeat'] >= 12 for _, r, _ in stats[1:]))
chk('14 ngày: mỗi ngày đúng 6 tin mới thật (+update)', all(r['new'] - (1 if date.endswith('-05') else 0) >= 6 for date, r, _ in stats))
by = {a['url']: a for _, _, arts in stats for a in arts if a['url'].startswith('https://g.example.com/')}
chk('update thật lọt (Godot 4.5.1 sau 4.5, đúng ngày) kèm nhãn', by['https://g.example.com/451']['status'] == 'update' and 'Mới' in by['https://g.example.com/451'].get('update_note', ''))
m = [a for _, _, arts in stats for a in arts if a['url'] == 'https://mirror.example.net/g451']
chk('cùng tin outlet khác, không fact mới → repeat', m and m[0]['status'] == 'repeat')
# idempotent: chạy lại ngày cuối cho cùng trạng thái
last = stats[-1]; before = [(a['sid'], a['status'], a['rev']) for a in last[2]]
fresh = [dict(title=a['title'], url=a['url'], summary=a.get('summary', ''), source=a['source'], topics=a['topics']) for a in last[2]]
K.ingest(kb, fresh, last[0], c); chk('chạy lại cùng ngày → kết quả y hệt (idempotent)', [(a['sid'], a['status'], a['rev']) for a in fresh] == before)
# ---- 3. người đọc: seen-store JS 14 ngày trên cùng dữ liệu ----
def feed(strip):   # toàn bộ bài của từng ngày (kể cả bản lặp) như nguồn thô — người đọc phải tự lọc
    def one(a): return dict(title=a['title'], url=a['url'], summary=a.get('summary', '')) if strip else dict(title=a['title'], url=a['url'], summary=a.get('summary', ''), sid=a['sid'], rev=a['rev'])
    return json.dumps([[date, [one(a) for a in arts]] for date, _, arts in stats])
out = json.loads(node(f'{d}/sim_dedup.js', feed(False)))
out2 = json.loads(node(f'{d}/sim_dedup.js', feed(True)))
chk('người đọc: ngày nào cũng có tin để đọc', all(x['shown'] >= 6 for x in out['days']))
chk('người đọc: 0 bài đã thấy hôm trước hiện lại (trừ update)', out['relapse'] == 0)
chk('người đọc: update thật vẫn hiện, nhãn "Cập nhật"', out['update_shown'])
chk('người đọc (nguồn thô không sid/rev, như Chạy báo trong trình duyệt): 0 trùng + update vẫn lọt', out2['relapse'] == 0 and out2['update_shown'] and out2['mirror_hidden'])
chk('người đọc: bản sao outlet khác của tin đã thấy bị ẩn dù URL khác', out['mirror_hidden'])
chk('người đọc: cùng sid trong 1 ngày chỉ hiện 1 lần', out['same_day_once'])
chk('người đọc: TTL/trần giữ kho gọn', out['store_size'] <= 1500)
for n, v in ok: print(('OK   ' if v else 'FAIL ') + n)
sys.exit(0 if all(v for _, v in ok) else 1)

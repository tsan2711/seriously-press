#!/usr/bin/env python3
"""Phòng Báo M1 — fetch → dedupe → gắn chủ đề → kho bài JSON theo ngày → build tĩnh. Chỉ stdlib.
  python3 press.py fetch [--date YYYY-MM-DD]   # ghi store/<date>.json (CHỈ ghi vào store/)
  python3 press.py build                       # đọc store/ + config/ → public/ (index + mỗi ban)
  python3 press.py check                       # >=20 bài hôm nay, mỗi bài có nguồn + chủ đề
  python3 press.py all
Nội dung web = không tin: chỉ là dữ liệu; qua security.injection_hits (nếu tìm thấy), không đưa vào phiên agent nào ở đây.
Tóm tắt M1 = trích tối đa 200 ký tự từ mô tả của nguồn (summary_by="excerpt"); bước viết lại bằng Haiku/Sonnet là mốc sau."""
import sys, os, re, json, html, datetime, hashlib, urllib.request, urllib.parse, concurrent.futures as cf
import tomllib
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = 'press-room/0.1 (+public RSS reader; respects robots)'
MAX_SUM = 200
PER_FEED = 15
HN_PER_Q = 8
MIN_POINTS = 15

try:
    sys.path.insert(0, os.path.expanduser('~/Documents/GitHub/Unity/Seriously/tools/company'))
    from security import injection_hits
except Exception:
    def injection_hits(t):
        return [m for m in ('ignore previous', 'ignore all previous', 'disregard the above', 'system prompt') if m in t.lower()]

IMG_MAX = 90

def load_cfg():
    topics = tomllib.load(open(f'{ROOT}/config/topics.toml', 'rb'))['topic']
    desks = {}
    d = f'{ROOT}/config/desks'
    for f in sorted(os.listdir(d)):
        if f.endswith('.toml'):
            c = tomllib.load(open(f'{d}/{f}', 'rb')); desks[c['id']] = c
    # nguồn thả thêm: config/sources.d/*.toml ([[feed]] desk=…) — không sửa mã (M4)
    sd = f'{ROOT}/config/sources.d'
    if os.path.isdir(sd):
        have = {x['id'] for c in desks.values() for x in c.get('feed', [])}
        for f in sorted(os.listdir(sd)):
            if not f.endswith('.toml'): continue
            for x in tomllib.load(open(f'{sd}/{f}', 'rb')).get('feed', []):
                if x.get('desk') in desks and x.get('id') and x.get('url', '').startswith('http') and x['id'] not in have:
                    desks[x['desk']].setdefault('feed', []).append(x); have.add(x['id'])
    return topics, desks

def load_roles():
    return tomllib.load(open(f'{ROOT}/config/roles.toml', 'rb'))

def http(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()

def clean(s, n=None):
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))
    s = re.sub(r'\s+', ' ', s).strip()
    if n and len(s) > n:
        s = s[:n].rsplit(' ', 1)[0].rstrip(',;:.') + '…'
    return s

def tag(e):
    return e.tag.rsplit('}', 1)[-1]

IMG_BAD = re.compile(r'(pixel|spacer|1x1|blank|tracking|badge|avatar|gravatar|emoji|logo|favicon|\.svg|\.gif)(\b|[?.])', re.I)
def good_img(u, base=''):
    u = html.unescape((u or '').strip())
    if u.startswith('//'): u = 'https:' + u
    elif u.startswith('/') and base: u = urllib.parse.urljoin(base, u)
    return u if u.startswith('https://') and len(u) < 400 and not IMG_BAD.search(u) else ''

def feed_img(it, desc, link):
    """Ảnh đại diện từ chính feed (media:thumbnail/content, enclosure ảnh, <img> đầu trong mô tả) — không tốn request thêm."""
    for c in it.iter():
        k = tag(c)
        if k in ('thumbnail', 'content') and c.get('url') and (k == 'thumbnail' or 'image' in (c.get('type') or c.get('medium') or 'image')):
            if (u := good_img(c.get('url'), link)): return u
        if k == 'enclosure' and 'image' in (c.get('type') or '') and (u := good_img(c.get('url'), link)): return u
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', html.unescape(desc or '') if '&lt;img' in (desc or '') else (desc or ''))
    return good_img(m.group(1), link) if m else ''

OG = re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\'][^>]*>', re.I)
def og_image(url):
    """og:image từ <head> của bài gốc (đọc ≤ 200KB, 8 s). Lỗi → rỗng, không sập."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=8) as r:
            if 'html' not in (r.headers.get('Content-Type') or 'html'): return ''
            h = r.read(200_000).decode('utf-8', 'ignore')
        for m in OG.finditer(h):
            c = re.search(r'content=["\']([^"\']+)', m.group(0))
            if c and (u := good_img(c.group(1), url)): return u
    except Exception: pass
    return ''

def parse_feed(raw, feed):
    out = []
    root = ET.fromstring(raw)
    items = [e for e in root.iter() if tag(e) in ('item', 'entry')]
    for it in items[:PER_FEED]:
        f = {tag(c): c for c in it}
        title = clean(f['title'].text) if 'title' in f else ''
        link = ''
        if 'link' in f:
            link = f['link'].get('href') or (f['link'].text or '')
        desc = ''
        for k in ('description', 'summary', 'content', 'encoded'):
            if k in f and f[k].text:
                desc = f[k].text; break
        date = ''
        for k in ('pubDate', 'published', 'updated', 'date'):
            if k in f and f[k].text:
                date = f[k].text.strip(); break
        if desc and clean(desc).lower() in ('comments', 'comment'): desc = ''
        if title and link.startswith('http'):
            out.append(dict(title=title, url=link.strip(), summary=clean(desc, MAX_SUM), published=date,
                            source=feed['name'], source_id=feed['id'], img=feed_img(it, desc, link)))
    return out

def hn(query):
    q = urllib.parse.urlencode({'query': query, 'tags': 'story', 'numericFilters': f'points>{MIN_POINTS},created_at_i>{int(datetime.datetime.now().timestamp()) - 4 * 86400}', 'hitsPerPage': HN_PER_Q})
    data = json.loads(http(f'https://hn.algolia.com/api/v1/search?{q}'))
    out = []
    for h in data.get('hits', []):
        t = clean(h.get('title'))
        url = h.get('url') or f"https://news.ycombinator.com/item?id={h['objectID']}"
        if t:
            out.append(dict(title=t, url=url, summary='', published=h.get('created_at', ''),
                            source='Hacker News', source_id='hn', points=h.get('points', 0), comments=h.get('num_comments', 0)))
    return out

def load_eng():
    return tomllib.load(open(f'{ROOT}/config/engagement.toml', 'rb'))

def eng_norm(score, comments, kind, cfg):
    """Điểm thô → engagement 0..1 (thang log, trần = cfg.norm[kind])."""
    import math
    raw = max(score, 0) + cfg['weights']['comment_factor'] * max(comments, 0)
    return round(min(1.0, math.log1p(raw) / math.log1p(cfg['norm'][kind])), 3)

def reddit_items(sub, cfg):
    q = urllib.parse.urlencode({'t': 'month', 'limit': 15})
    d = json.loads(http(f'https://www.reddit.com/r/{sub}/top.json?{q}'))
    out = []
    for c in d['data']['children']:
        x = c['data']
        out.append(dict(title=clean(x.get('title')), url='https://www.reddit.com' + x['permalink'], source=f'r/{sub}', source_id='reddit',
                        points=x.get('score', 0), comments=x.get('num_comments', 0), published=str(x.get('created_utc', ''))))
    return out

def github_items(query, cfg):
    since = (datetime.date.today() - datetime.timedelta(days=cfg['trending']['window_days'])).isoformat()
    q = urllib.parse.urlencode({'q': f'created:>{since} {query}', 'sort': 'stars', 'per_page': cfg['trending']['github_per_query']})
    d = json.loads(http(f'https://api.github.com/search/repositories?{q}'))
    return [dict(title=clean(f"{r['full_name']}: {r.get('description') or ''}", 140), url=r['html_url'], source='GitHub', source_id='github',
                 points=r.get('stargazers_count', 0), comments=0, published=r.get('created_at', '')) for r in d.get('items', [])]

def hn_month(query, cfg):
    since = int(datetime.datetime.now().timestamp()) - cfg['trending']['window_days'] * 86400
    q = urllib.parse.urlencode({'query': query, 'tags': 'story', 'numericFilters': f'created_at_i>{since},points>30', 'hitsPerPage': 10})
    return [dict(title=clean(h.get('title')), url=f"https://news.ycombinator.com/item?id={h['objectID']}", source='Hacker News', source_id='hn',
                 points=h.get('points', 0), comments=h.get('num_comments', 0), published=h.get('created_at', ''))
            for h in json.loads(http(f'https://hn.algolia.com/api/v1/search?{q}')).get('hits', []) if h.get('title')]

def last30_items(query, cfg):
    """Adapter TUỲ CHỌN cho mvanhorn/last30days-skill (knowledge/last30days.md). Tắt mặc định: cần Bi tự cài CLI + bật [last30days] trong engagement.toml.
    Đọc JSON phòng thủ (schema có thể đổi): lấy mọi dict có title+url http(s); lỗi/timeout → ném, trending() ghi vào errors."""
    c = cfg.get('last30days') or {}
    if not c.get('enabled') or not c.get('cmd'): return []
    import shlex, subprocess
    r = subprocess.run(shlex.split(c['cmd']) + ['--emit', 'json', '--search', c.get('search', 'reddit,hn,github'), '--quick', query],
                       capture_output=True, text=True, timeout=int(c.get('timeout', 120)), stdin=subprocess.DEVNULL)
    if r.returncode: raise RuntimeError(f'last30days exit {r.returncode}')
    found = []
    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('title'), str) and str(o.get('url', '')).startswith(('http://', 'https://')): found.append(o)
            else: [walk(v) for v in o.values()]
        elif isinstance(o, list): [walk(v) for v in o]
    walk(json.loads(r.stdout))
    out = []
    for o in found[:int(c.get('max_items', 20))]:
        num = lambda k: int(o.get(k) or 0) if str(o.get(k) or 0).lstrip('-').isdigit() else 0
        out.append(dict(title=clean(o['title'], 140), url=o['url'], source='last30days', source_id='hn', points=num('score') or num('points') or num('upvotes'),
                        comments=num('comments') or num('num_comments'), published=str(o.get('date') or o.get('published') or '')))
    return out

def trending(desks, topics, cfg):
    """Mục 'Đang bàn tán': mỗi ban 3–5 chủ đề nóng trong 30 ngày. Link thảo luận gốc + câu do mình sinh bằng mẫu (không chép bình luận)."""
    jobs = []
    for did, d in desks.items():
        for q in d.get('hn_queries', []): jobs.append((did, 'hn', q, lambda q=q: hn_month(q, cfg)))
        for s in cfg['reddit'].get(did, []): jobs.append((did, 'reddit', s, lambda s=s: reddit_items(s, cfg)))
        for g in cfg['github'].get(did, []): jobs.append((did, 'github', g, lambda g=g: github_items(g, cfg)))
        if (cfg.get('last30days') or {}).get('enabled'):
            for q in d.get('hn_queries', [])[:2]: jobs.append((did, 'hn', 'l30:' + q, lambda q=q: last30_items(q, cfg)))
    def run(j):
        try: return j, j[3](), None
        except Exception as e: return j, [], f'{j[0]}/{j[1]}:{j[2]}: {type(e).__name__}: {e}'
    with cf.ThreadPoolExecutor(4) as ex: res = list(ex.map(run, jobs))
    errs = [r[2] for r in res if r[2]]
    per = {}
    for (did, kind, _, _), items, _e in res:
        for it in items:
            if injection_hits(it['title']): continue
            it['engagement'] = eng_norm(it['points'], it.get('comments', 0), kind, cfg)
            tl, _d = classify(it, topics, did); it['topics'] = tl
            per.setdefault(did, []).append(it)
    out = {}
    for did, items in per.items():
        by = {}
        for it in items:
            for t in it['topics'][:1]: by.setdefault(t, []).append(it)
        rows = []
        for t, its in by.items():
            if len(its) < cfg['trending']['min_items']: continue
            its.sort(key=lambda x: -x['engagement']); top = its[0]
            rows.append(dict(topic=t, heat=round(sum(x['engagement'] for x in its), 2), count=len(its), url=top['url'], title=top['title'], source=top['source'],
                             blurb=f"{len(its)} cuộc thảo luận về {topics.get(t, {}).get('label', t)} trong {cfg['trending']['window_days']} ngày; sôi nhất trên {top['source']} ({top['points']} điểm, {top.get('comments', 0)} bình luận)."))
        rows.sort(key=lambda r: -r['heat'])
        out[did] = rows[:cfg['trending']['per_desk']]
    return out, errs

def classify(a, topics, desk_id):
    text = f"{a['title']} {a.get('summary', '')}".lower()
    hits = []
    for tid, t in topics.items():
        n = sum(1 for k in t['kw'] if re.search(r'(?<![a-z0-9])' + re.escape(k.lower()), text))
        if n:
            hits.append((n, tid))
    hits.sort(reverse=True)
    tl = [t for _, t in hits[:3]]
    if not tl:   # không khớp từ khoá → chủ đề đầu của ban (đánh dấu để Haiku gắn lại sau)
        tl = [next((k for k, t in topics.items() if desk_id in t['desks']), 'misc')]
        a['topic_by'] = 'desk-default'
    else:
        a['topic_by'] = 'keyword'
    desks = sorted({d for t in tl if t in topics for d in topics[t]['desks']} | {desk_id})
    return tl, desks

def canon(url):
    u = urllib.parse.urlsplit(url)
    q = [p for p in urllib.parse.parse_qsl(u.query) if not p[0].startswith('utm_')]
    return urllib.parse.urlunsplit((u.scheme, u.netloc.lower().removeprefix('www.'), u.path.rstrip('/'), urllib.parse.urlencode(q), ''))

def fetch(date):
    topics, desks = load_cfg(); cfg = load_eng()
    jobs = []
    for did, d in desks.items():
        for f in d.get('feed', []):
            jobs.append((did, 'feed', f))
        for q in d.get('hn_queries', []):
            jobs.append((did, 'hn', q))
    def run(j):
        did, k, x = j
        try:
            return j, (parse_feed(http(x['url']), x) if k == 'feed' else hn(x)), None
        except Exception as e:
            return j, [], f'{type(e).__name__}: {e}'
    seen, arts, errs, blocked = {}, [], [], 0
    with cf.ThreadPoolExecutor(8) as ex:
        results = list(ex.map(run, jobs))
    for (did, k, x), items, err in results:
        if err:
            errs.append(f"{did}/{x['id'] if k == 'feed' else x}: {err}")
        for a in items:
            if injection_hits(a['title'] + ' ' + a['summary']):
                blocked += 1; continue
            key = canon(a['url'])
            if key in seen:
                prev = seen[key]
                prev['desks'] = sorted(set(prev['desks']) | {did})
                continue
            a['engagement'] = eng_norm(a.get('points', 0), a.get('comments', 0), 'hn', cfg) if a['source_id'] == 'hn' else 0.0
            tl, dl = classify(a, topics, did)
            a.update(id=hashlib.sha1(key.encode()).hexdigest()[:10], topics=tl, desks=sorted(set(dl) | {did}), summary_by='excerpt' if a['summary'] else 'none')
            seen[key] = a; arts.append(a)
    arts.sort(key=lambda a: -a.get('engagement', 0))
    need = [a for a in arts if not a.get('img')][:IMG_MAX]   # bù ảnh thiếu bằng og:image (song song, giới hạn số bài)
    with cf.ThreadPoolExecutor(8) as ex:
        for a, u in zip(need, ex.map(lambda a: og_image(a['url']), need)): a['img'] = u
    print(f"ảnh: {sum(bool(a.get('img')) for a in arts)}/{len(arts)} bài có ảnh")
    import kb as KB   # K2/K3: gắn new/update/repeat theo các ngày TRƯỚC + ghi KB (idempotent theo ngày)
    kbs = KB.load(); dstat = KB.ingest(kbs, arts, date); KB.save(kbs)
    trend, terrs = trending(desks, topics, cfg); errs += terrs
    os.makedirs(f'{ROOT}/store', exist_ok=True)
    json.dump(dict(date=date, generated=datetime.datetime.now().isoformat(timespec='seconds'), articles=arts, trending=trend, errors=errs, blocked_injection=blocked, dedup=dstat),
              open(f'{ROOT}/store/{date}.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(f'fetch {date}: {len(arts)} bài ({dstat["new"]} mới, {dstat["update"]} cập nhật, {dstat["repeat"]} lặp), {len(errs)} nguồn lỗi, {blocked} bị chặn injection')
    for e in errs: print('  !', e)

def e(s): return html.escape(s or '')

PAGE = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{--bg:#f6f1e7;--fg:#1d1b18;--mut:#6d665b;--rule:#cfc7b7;--acc:{acc}}}
@media(prefers-color-scheme:dark){{:root{{--bg:#161514;--fg:#ece7dc;--mut:#9b9487;--rule:#38352f}}}}
body{{margin:0 auto;max-width:44rem;padding:1rem;background:var(--bg);color:var(--fg);font:1.05rem/1.5 system-ui,sans-serif}}
h1{{font:700 2.2rem/1.1 Georgia,serif;border-bottom:3px double var(--fg);padding-bottom:.4rem}}
h2{{font:700 1.2rem Georgia,serif;color:var(--acc);border-bottom:1px solid var(--rule);margin-top:2rem}}
nav a{{margin-right:1rem;color:var(--acc)}}a{{color:inherit}}article{{border-bottom:1px solid var(--rule);padding:.6rem 0}}
article a{{font:600 1.1rem Georgia,serif}}p{{margin:.2rem 0}}small{{color:var(--mut)}}</style>
<h1>{title}</h1><nav>{nav}</nav><small>{sub}</small>{body}</html>'''

MIN_FRESH = 8
def fresh_only(arts):
    """Ngày mới LOẠI tin lặp (status=repeat, K2); chỉ giữ new + update. Quá ít tin mới → bù vài tin lặp nổi nhất, gắn 'repeat' để UI ghi 'Đã thấy'."""
    fresh = [a for a in arts if a.get('status', 'new') != 'repeat']
    if len(fresh) < MIN_FRESH:
        fresh += sorted([a for a in arts if a.get('status') == 'repeat'], key=lambda a: -a.get('engagement', 0))[:MIN_FRESH - len(fresh)]
    return fresh

def build():
    topics, desks = load_cfg()
    files = sorted(f for f in os.listdir(f'{ROOT}/store') if f.endswith('.json'))
    if not files: sys.exit('store/ rỗng — chạy fetch trước')
    day = json.load(open(f'{ROOT}/store/{files[-1]}', encoding='utf8'))
    arts = fresh_only(day['articles'])
    day = dict(day, articles=arts)
    os.makedirs(f'{ROOT}/public', exist_ok=True)
    import shutil, theme   # theme Xưởng đồng hồ 2D tĩnh: web/style.css + web/app.js, HTML từ theme.py
    pages = theme.render_all(theme.Ctx(day, topics, desks, roles=load_roles(), share=tomllib.load(open(f'{ROOT}/config/share.toml', 'rb')).get('endpoint', '')))
    for name, h in pages.items(): open(f'{ROOT}/public/{name}.tmp', 'w', encoding='utf8').write(h); os.replace(f'{ROOT}/public/{name}.tmp', f'{ROOT}/public/{name}')
    for f in ('rank.js', 'dedup.js', 'memory.js', 'journal.js', 'profiles.js', 'share-core.js', 'run-core.js', 'app.js', 'diary.js', 'community.js', 'settings.js', 'mempage.js', 'issues.js', 'style.css'): shutil.copy(f'{ROOT}/web/{f}', f'{ROOT}/public/{f}')
    if os.path.isdir(f'{ROOT}/web/tex'): shutil.copytree(f'{ROOT}/web/tex', f'{ROOT}/public/tex', dirs_exist_ok=True)
    build_issues(files, topics, desks)
    import extras; n_s = extras.build_search(ROOT, topics, desks)
    for d in desks:   # tên cũ <ban>.html → desk-<ban>.html (liên kết đã chia sẻ không gãy)
        open(f'{ROOT}/public/{d}.html', 'w', encoding='utf8').write(f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=desk-{d}.html"><a href="desk-{d}.html">Mở ban</a>')
    # danh sách nguồn cho nút "Chạy báo hôm nay" trong trình duyệt (công khai, không bí mật)
    json.dump(dict(feeds=[dict(id=x['id'], name=x['name'], url=x['url'], desk=d) for d, c in desks.items() for x in c.get('feed', [])], hn=[dict(desk=d, q=q) for d, c in desks.items() for q in c.get('hn_queries', [])]),
              open(f'{ROOT}/public/sources.json', 'w', encoding='utf8'), ensure_ascii=False)
    trend = day.get('trending', {})
    json.dump(dict(date=day['date'], desks={d: dict(name=c['name'], accent=c['accent']) for d, c in desks.items()}, topics=topics, trending=trend, hot=sorted({x['topic'] for v in trend.values() for x in v}), dedup=tomllib.load(open(f'{ROOT}/config/dedup.toml', 'rb')), repeat_hidden=day.get('dedup', {}).get('repeat', 0), engagement_weight=load_eng()['weights']['rank'], roles=load_roles(), articles=arts),
              open(f'{ROOT}/public/today.json', 'w', encoding='utf8'), ensure_ascii=False)
    extras.build_pwa(ROOT)
    print(f'build: {len(pages)} trang, {len(arts)} bài → public/')

ISSUE_DAYS = 14
def build_issues(files, topics, desks):
    """Số báo theo ngày cho bộ chọn ở trang chủ: public/issues.json + public/issues/<ngày>.json (14 ngày gần nhất).
    Chỉ có bản CRON (store/). Bản người dùng tự chạy ở trình duyệt nằm trong localStorage, không bao giờ vào đây."""
    import theme
    os.makedirs(f'{ROOT}/public/issues', exist_ok=True); rows, keep = [], set()
    for f in files[-ISSUE_DAYS:]:
        try:
            day = json.load(open(f'{ROOT}/store/{f}', encoding='utf8')); day['articles'] = fresh_only(day['articles'])
            theme.bind(theme.Ctx(day, topics, desks, roles=load_roles(), share=''))
            head, arts = theme.issue_json()
        except Exception as ex:
            print(f'  ! số báo {f}: {type(ex).__name__}: {ex}'); continue
        json.dump(dict(issue=head, articles=arts), open(f'{ROOT}/public/issues/{head["date"]}.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
        rows.append(head); keep.add(f'{head["date"]}.json')
    for old in os.listdir(f'{ROOT}/public/issues'):
        if old not in keep: os.remove(f'{ROOT}/public/issues/{old}')
    rows.sort(key=lambda r: r['ts'], reverse=True)
    json.dump(dict(issues=rows), open(f'{ROOT}/public/issues.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))

def check(date):
    p = f'{ROOT}/store/{date}.json'
    if not os.path.exists(p): print(f'FAIL không có {p}'); return 1
    arts = json.load(open(p, encoding='utf8'))['articles']
    bad = [a['id'] for a in arts if not (a.get('url') and a.get('source') and a.get('topics'))]
    if len(arts) < 20 or bad: print(f'FAIL {len(arts)} bài, {len(bad)} thiếu nguồn/chủ đề'); return 1
    print(f'OK {len(arts)} bài, mỗi bài có nguồn + chủ đề'); return 0

if __name__ == '__main__':
    a = sys.argv[1:]
    date = a[a.index('--date') + 1] if '--date' in a else datetime.date.today().isoformat()
    cmd = a[0] if a else 'all'
    if cmd in ('fetch', 'all'): fetch(date)
    if cmd in ('build', 'all'): build()
    if cmd == 'images':   # bù ảnh cho store của ngày đã fetch (không fetch lại nguồn)
        f = f'{ROOT}/store/{date}.json'; d = json.load(open(f, encoding='utf8')); need = [x for x in d['articles'] if not x.get('img')][:IMG_MAX]
        with cf.ThreadPoolExecutor(8) as ex:
            for x, u in zip(need, ex.map(lambda x: og_image(x['url']), need)): x['img'] = u
        json.dump(d, open(f, 'w', encoding='utf8'), ensure_ascii=False, indent=1); print(f"ảnh: {sum(bool(x.get('img')) for x in d['articles'])}/{len(d['articles'])}")
    if cmd == 'hosts':   # dán vào biến PROXY_HOSTS của Worker (allowlist cho /fetch)
        _, ds = load_cfg(); print(','.join(sorted({urllib.parse.urlparse(x['url']).hostname for c in ds.values() for x in c.get('feed', [])} | {'hn.algolia.com'})))
    if cmd in ('check', 'all'): sys.exit(check(date))

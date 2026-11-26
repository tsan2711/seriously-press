#!/usr/bin/env python3
"""Phòng Báo M1 — fetch → dedupe → gắn chủ đề → kho bài JSON theo ngày → build tĩnh. Chỉ stdlib.
  python3 press.py fetch [--date YYYY-MM-DD]   # ghi store/<date>.json (CHỈ ghi vào store/)
  python3 press.py build                       # đọc store/ + config/ → public/ (index + mỗi ban)
  python3 press.py check                       # >=20 bài hôm nay, mỗi bài có nguồn + ban
  python3 press.py all
Nội dung web = không tin: chỉ là dữ liệu; qua security.injection_hits (nếu tìm thấy), không đưa vào phiên agent nào ở đây.
Tóm tắt M1 = trích tối đa 200 ký tự từ mô tả của nguồn (summary_by="excerpt"); bước viết lại bằng Haiku/Sonnet là mốc sau."""
import sys, os, re, json, html, time, threading, datetime, hashlib, urllib.request, urllib.error, urllib.parse, concurrent.futures as cf
import tomllib
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = 'press-room/0.1 (+public RSS reader; respects robots)'
MAX_SUM = 200
PER_FEED = 4   # ≤4 bài/ngày/nguồn: không nguồn nào lấn át
HN_PER_Q = 8
MIN_POINTS = 15

try:
    sys.path.insert(0, os.path.expanduser('~/Documents/GitHub/Unity/Seriously/tools/company'))
    from security import injection_hits
except Exception:
    def injection_hits(t):
        return [m for m in ('ignore previous', 'ignore all previous', 'disregard the above', 'system prompt') if m in t.lower()]

IMG_MAX = 250   # trước 90: bài engagement thấp (sej, mobilegamer…) bị cắt khỏi og → thiếu ảnh

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

# ---- Trần thời gian giai đoạn mạng + đo giờ (task build-speed) ----
NET_BUDGET = 90     # tổng giây cho MỌI giai đoạn mạng của fetch; quá thì bỏ phần còn lại
CAP_FEEDS, CAP_TREND = 35, 20   # trần riêng: nguồn, "đang bàn tán" — phần còn lại của 90 s dành cho ảnh
HTTP_TIMEOUT = 20
PHASES, WARNS = {}, []
_NET = dict(deadline=None)

def net_start(budget=None):
    _NET['deadline'] = time.monotonic() + (NET_BUDGET if budget is None else budget)
def net_left(cap=None):
    """Giây còn lại của trần mạng (≤ cap nếu có). Chưa bắt đầu đếm → không giới hạn (chỉ cap)."""
    left = float('inf') if _NET['deadline'] is None else _NET['deadline'] - time.monotonic()
    return max(0.0, min(left, cap) if cap is not None else left)
def warn(msg):
    WARNS.append(msg); print('CẢNH BÁO:', msg)

class phase:
    """with phase('nguồn'): … — cộng dồn giây vào PHASES."""
    def __init__(self, name): self.name = name
    def __enter__(self): self.t0 = time.monotonic()
    def __exit__(self, *a): PHASES[self.name] = PHASES.get(self.name, 0.0) + time.monotonic() - self.t0

def time_line():
    net = sum(v for k, v in PHASES.items() if k != 'dựng trang')
    parts = ' · '.join(f'{k} {v:.1f}s' for k, v in PHASES.items())
    return f'thời gian: {parts} · mạng {net:.1f}/{NET_BUDGET}s · tổng {sum(PHASES.values()):.1f}s' + (f' · {len(WARNS)} cảnh báo' if WARNS else '')

def par_map(fn, jobs, workers, limit):
    """Chạy fn(job) song song, tối đa `limit` giây. Trả list cùng thứ tự: (kết quả|None, lỗi|None);
    job chưa xong khi hết giờ → (None, 'hết trần thời gian'). Luồng daemon: không giữ tiến trình sống sau khi quá hạn."""
    res = [(None, 'hết trần thời gian')] * len(jobs); q = list(enumerate(jobs)); lk = threading.Lock(); t_end = time.monotonic() + limit
    def worker():
        while time.monotonic() < t_end:
            with lk:
                if not q: return
                i, j = q.pop(0)
            try: r = (fn(j), None)
            except Exception as ex: r = (None, f'{type(ex).__name__}: {ex}')
            if time.monotonic() < t_end: res[i] = r
    ts = [threading.Thread(target=worker, daemon=True) for _ in range(max(1, min(workers, len(jobs))))]
    for t in ts: t.start()
    for t in ts: t.join(max(0.0, t_end - time.monotonic()))
    return res

def http(url, headers=None):
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=max(1.0, min(HTTP_TIMEOUT, net_left()))) as r:
        return r.read()

# Cache điều kiện cho feed: store/feeds.json {url: {etag, lm}} + thân bản cũ ở store/feeds/<sha1>.xml. 304 → dùng bản cũ.
def _fc_path(): return f'{ROOT}/store/feeds.json'
def feed_cache_load():
    try:
        c = json.load(open(_fc_path(), encoding='utf8')); return c if isinstance(c, dict) else {}
    except Exception: return {}
def feed_cache_save(c):
    try:
        os.makedirs(f'{ROOT}/store', exist_ok=True)
        json.dump(c, open(_fc_path() + '.tmp', 'w', encoding='utf8'), ensure_ascii=False, indent=0, sort_keys=True); os.replace(_fc_path() + '.tmp', _fc_path())
    except Exception: pass
def _body_path(url): return f'{ROOT}/store/feeds/{hashlib.sha1(url.encode()).hexdigest()[:16]}.xml'
def http_cond(url, cache, opener=None):
    """GET có If-None-Match/If-Modified-Since qua opener(url, headers) → (thân, {etag, lm}). 304 + có bản cũ → trả bản cũ."""
    opener = opener or http_meta; ent = cache.get(url) or {}; h = {}; old = None
    if ent and os.path.isfile(_body_path(url)):
        old = open(_body_path(url), 'rb').read()
        if ent.get('etag'): h['If-None-Match'] = ent['etag']
        if ent.get('lm'): h['If-Modified-Since'] = ent['lm']
    try:
        body, meta = opener(url, h)
    except urllib.error.HTTPError as ex:
        if ex.code == 304 and old is not None: return old
        raise
    if meta.get('etag') or meta.get('lm'):
        try:
            os.makedirs(os.path.dirname(_body_path(url)), exist_ok=True)
            open(_body_path(url) + '.tmp', 'wb').write(body); os.replace(_body_path(url) + '.tmp', _body_path(url))
            cache[url] = dict(etag=meta.get('etag', ''), lm=meta.get('lm', ''))
        except Exception: pass
    return body

def http_meta(url, headers=None):
    """Như http() nhưng trả (thân, {etag, lm}) để lưu cache điều kiện."""
    req = urllib.request.Request(url, headers={'User-Agent': UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=max(1.0, min(HTTP_TIMEOUT, net_left()))) as r:
        return r.read(), dict(etag=r.headers.get('ETag') or '', lm=r.headers.get('Last-Modified') or '')

def strip_quotes(t):
    """Tiêu đề bọc trọn trong ngoặc kép (tweet trích trên HN) → bỏ cặp ngoặc ngoài; ngoặc giữa câu giữ nguyên."""
    t = (t or '').strip()
    for o, c in (('"', '"'), ('\u201c', '\u201d'), ("'", "'"), ('\u2018', '\u2019')):
        if len(t) > 2 and t[0] == o and t[-1] == c and o not in t[1:-1] and c not in t[1:-1]: return t[1:-1].strip()
    return t

def clean(s, n=None):
    s = html.unescape(re.sub(r'<[^>]+>', ' ', s or ''))
    s = re.sub(r'\s+', ' ', s).strip()
    if n and len(s) > n:
        s = s[:n].rsplit(' ', 1)[0].rstrip(',;:.') + '…'
    return s

def tag(e):
    return e.tag.rsplit('}', 1)[-1]

IMG_BAD = re.compile(r'(pixel|spacer|1x1|blank|tracking|badge|avatar|gravatar|emoji|logo|favicon|\.svg|\.gif)(\b|[?.])|profile_images|/_si/', re.I)
def good_img(u, base=''):
    u = html.unescape((u or '').strip())
    if u.startswith('//'): u = 'https:' + u
    elif u.startswith('/') and base: u = urllib.parse.urljoin(base, u)
    return u if u.startswith('https://') and len(u) < 400 and not IMG_BAD.search(u) else ''

def feed_img(it, desc, link):
    """Ảnh đại diện từ chính feed (media:thumbnail/content, enclosure ảnh, <img> đầu trong content:encoded/summary) — không tốn request thêm."""
    for c in it.iter():
        k = tag(c); u0 = c.get('url')
        if not u0: continue
        kind = (c.get('type') or c.get('medium') or '').lower()
        if k == 'thumbnail' or (k in ('content', 'enclosure') and kind.startswith('image')):
            if (u := good_img(u0, link)): return u
    texts = [desc or ''] + [c.text or '' for c in it if tag(c) in ('description', 'summary', 'content', 'encoded')]
    for t in dict.fromkeys(texts):
        m = re.search(r'<img[^>]+src=["\']([^"\']+)', html.unescape(t) if '&lt;img' in t else t)
        if m and (u := good_img(m.group(1), link)): return u
    return ''

import ogimg

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
    def run(j, r):
        v, err = r
        return j, v or [], (f'{j[0]}/{j[1]}:{j[2]}: {err}' if err else None)
    res = [run(j, r) for j, r in zip(jobs, par_map(lambda j: j[3](), jobs, 4, net_left(CAP_TREND)))]
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
        tl = []   # không khớp → không gắn chủ đề (gắn bừa chủ đề đầu của ban = nhãn sai); chỉ tính ban
        a['topic_by'] = 'none'
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
    net_start(); PHASES.clear(); WARNS.clear(); fcache = feed_cache_load()
    def run(j):
        did, k, x = j
        return parse_feed(http_cond(x['url'], fcache), x) if k == 'feed' else hn(x)
    seen, arts, errs, blocked = {}, [], [], 0
    with phase('nguồn'):
        raw = par_map(run, jobs, 8, net_left(CAP_FEEDS))
        feed_cache_save(fcache)
    results = [(j, v or [], err) for j, (v, err) in zip(jobs, raw)]
    late = sum(1 for _, _, err in results if err == 'hết trần thời gian')
    if late: warn(f'nguồn: {late}/{len(jobs)} nguồn chưa xong trong {CAP_FEEDS}s → bỏ')
    for (did, k, x), items, err in results:
        if err:
            errs.append(f"{did}/{x['id'] if k == 'feed' else x}: {err}")
        for a in items:
            a['title'] = strip_quotes(a['title'])
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
    import imgcache
    # trending chạy TRƯỚC giai đoạn ảnh (trần riêng) để ảnh dùng phần còn lại của 90 s
    with phase('bàn tán'):
        trend, terrs = trending(desks, topics, cfg); errs += terrs
    if any('hết trần thời gian' in t for t in terrs): warn('bàn tán: một số truy vấn chưa xong trong trần → bỏ')
    t_img = time.monotonic()
    def img_budget(b):
        left = net_left()
        if left < b: warn(f'ảnh: còn {left:.0f}s < {b}s mặc định → rút ngắn/bỏ bước')
        return max(0, int(min(b, left)))
    def img_step(name, fn):
        if net_left() < 1: warn(f'ảnh/{name}: hết trần {NET_BUDGET}s → bỏ'); return None
        try: return fn()
        except Exception as ex: warn(f'ảnh/{name}: {type(ex).__name__}'); return None
    img_step('kiểm feed', lambda: imgcache.clean(arts, ROOT, budget=img_budget(imgcache.BUDGET)))   # ảnh từ feed: gỡ hỏng/lặp >2 thẻ
    img_step('og', lambda: ogimg.fill_images(arts, ROOT, IMG_MAX, budget=img_budget(ogimg.BUDGET), retry_empty=ogimg.RETRY_EMPTY))   # bù ảnh thiếu bằng og:image (cache theo url, giới hạn thời gian)
    img_step('kiểm og', lambda: imgcache.clean(arts, ROOT, budget=img_budget(imgcache.BUDGET)))
    img_step('tóm tắt', lambda: print('tóm tắt meta: +%d bài (%d request)' % ogimg.fill_summaries(arts, ROOT, budget=img_budget(ogimg.BUDGET), bad=injection_hits)))   # H7: bài HN chỉ có tiêu đề → meta description
    try:
        import imgfind   # dự phòng cuối: ảnh Wikimedia Commons liên quan (giấy phép mở, kèm ghi công)
        _to = imgfind.load_cfg()['timeout']; _ff = lambda u: None if net_left() < 1 else imgfind.fetch_json(u, _to)
        nc, qc = imgfind.fill_commons(arts, ROOT, fetcher=_ff, topic_label=lambda a: (topics.get(a['topics'][0], {}) if isinstance(topics, dict) else next((t for t in topics if t.get('id') == a['topics'][0]), {})).get('label', '') if a.get('topics') else '')
        print(f'commons: +{nc} ảnh ({qc} truy vấn)')
        print('kiểm ảnh:', img_step('kiểm commons', lambda: imgcache.clean(arts, ROOT, budget=img_budget(imgcache.BUDGET))))
    except Exception as ex: print('commons: bỏ qua:', type(ex).__name__)
    print('ảnh cục bộ:', img_step('cục bộ', lambda: imgcache.localize(arts, ROOT, budget=img_budget(imgcache.LOCAL_BUDGET))))   # tải về + thu 640×360 webp (cần Pillow; không có → giữ hotlink)
    import metrics; print(metrics.img_line(metrics.img_coverage(arts)))
    import kb as KB   # K2/K3: gắn new/update/repeat theo các ngày TRƯỚC + ghi KB (idempotent theo ngày)
    kbs = KB.load(); dstat = KB.ingest(kbs, arts, date); KB.save(kbs)
    PHASES['ảnh'] = time.monotonic() - t_img
    os.makedirs(f'{ROOT}/store', exist_ok=True)
    json.dump(dict(date=date, generated=datetime.datetime.now().isoformat(timespec='seconds'), articles=arts, trending=trend, errors=errs, blocked_injection=blocked, dedup=dstat),
              open(f'{ROOT}/store/{date}.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    print(f'fetch {date}: {len(arts)} bài ({dstat["new"]} mới, {dstat["update"]} cập nhật, {dstat["repeat"]} lặp), {len(errs)} nguồn lỗi, {blocked} bị chặn injection')
    for e in errs: print('  !', e)
    if net_left() <= 0: warn(f'trần mạng {NET_BUDGET}s đã hết — phần chưa xong đã bỏ')

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
    for a in arts: a['title'] = strip_quotes(a.get('title'))   # kể cả số báo cũ trong store
    fresh = [a for a in arts if a.get('status', 'new') != 'repeat']
    if len(fresh) < MIN_FRESH:
        fresh += sorted([a for a in arts if a.get('status') == 'repeat'], key=lambda a: -a.get('engagement', 0))[:MIN_FRESH - len(fresh)]
    return fresh

def credit_caption(pages, arts):
    """Chú thích ghi công ảnh Commons dưới ảnh bài nổi bật ở article.html (escape; theme.py không đổi)."""
    h = pages.get('article.html'); m = re.search(r'data-id="([^"]+)"', h or '')
    a = next((x for x in arts if m and x['id'] == html.unescape(m.group(1))), None)
    if a and a.get('img_credit') and a.get('img'):
        i = h.find('</div>', h.find('class="thumb"'))
        if i > 0: pages['article.html'] = h[:i + 6] + f'<p class="img-credit" style="font-size:.75rem;opacity:.8;margin:.25rem 0">Ảnh: {html.escape(a["img_credit"])}</p>' + h[i + 6:]
    return pages

def build():
    with phase('dựng trang'): _build()

def _build():
    topics, desks = load_cfg()
    files = sorted(f for f in os.listdir(f'{ROOT}/store') if re.fullmatch(r'\d{4}-\d\d-\d\d\.json', f))
    if not files: sys.exit('store/ rỗng — chạy fetch trước')
    day = json.load(open(f'{ROOT}/store/{files[-1]}', encoding='utf8'))
    arts = fresh_only(day['articles'])
    day = dict(day, articles=arts)
    os.makedirs(f'{ROOT}/public', exist_ok=True)
    import shutil, theme   # theme Xưởng đồng hồ 2D tĩnh: web/style.css + web/app.js, HTML từ theme.py
    hist = [json.load(open(f'{ROOT}/store/{f}', encoding='utf8')) for f in files[:-1][-theme.TOPIC_DAYS:]]
    hist = [dict(h, articles=fresh_only(h['articles'])) for h in hist]
    try:   # lấy repo TRƯỚC khi dựng trang: khối "Repo hay" ở trang chủ đọc store/repos/ (lỗi mạng → bản đã có trên đĩa)
        import hotrepos as repos; repos.build()
    except Exception as ex: print('repos: không lấy được —', ex)
    pages = theme.render_all(theme.Ctx(day, topics, desks, roles=load_roles(), history=hist, share=tomllib.load(open(f'{ROOT}/config/share.toml', 'rb')).get('endpoint', '')))
    pages = credit_caption(pages, day['articles'])
    for name, h in pages.items(): open(f'{ROOT}/public/{name}.tmp', 'w', encoding='utf8').write(h); os.replace(f'{ROOT}/public/{name}.tmp', f'{ROOT}/public/{name}')
    for f in ('rank.js', 'dedup.js', 'memory.js', 'journal.js', 'profiles.js', 'share-core.js', 'run-core.js', 'app.js', 'diary.js', 'community.js', 'settings.js', 'mempage.js', 'issues.js', 'fx.js', 'style.css'): shutil.copy(f'{ROOT}/web/{f}', f'{ROOT}/public/{f}')
    sk = theme.skin_name()   # skin: nối web/skins/_flat.css + <skin>.css sau style.css gốc (chỉ lớp trình bày)
    if sk:
        with open(f'{ROOT}/public/style.css', 'a', encoding='utf8') as o:
            for f in ('_flat.css', f'{sk}.css'): o.write('\n' + open(f'{ROOT}/web/skins/{f}', encoding='utf8').read())
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
    try:
        import hotrepos as repos; repos.write_page(f'{ROOT}/public')
    except Exception as ex: print('repos: bỏ qua —', ex)
    extras.build_feed(ROOT)
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
    bad = [a['id'] for a in arts if not (a.get('url') and a.get('source') and a.get('desks'))]
    if len(arts) < 20 or bad: print(f'FAIL {len(arts)} bài, {len(bad)} thiếu nguồn/ban'); return 1
    print(f'OK {len(arts)} bài, mỗi bài có nguồn + ban'); return 0

def proxy_hosts():
    _, ds = load_cfg()
    return sorted({urllib.parse.urlparse(x['url']).hostname for c in ds.values() for x in c.get('feed', [])} | {'hn.algolia.com'})

if __name__ == '__main__':
    a = sys.argv[1:]
    date = a[a.index('--date') + 1] if '--date' in a else datetime.date.today().isoformat()
    cmd = a[0] if a else 'all'
    if cmd in ('fetch', 'all'): fetch(date)
    if cmd in ('build', 'all'): build()
    if cmd == 'images':   # bù ảnh cho store của ngày đã fetch (không fetch lại nguồn)
        f = f'{ROOT}/store/{date}.json'; d = json.load(open(f, encoding='utf8')); ogimg.fill_images(d['articles'], ROOT, IMG_MAX)
        json.dump(d, open(f, 'w', encoding='utf8'), ensure_ascii=False, indent=1); print(f"ảnh: {sum(bool(x.get('img')) for x in d['articles'])}/{len(d['articles'])}")
    if cmd == 'hosts':   # dán vào biến PROXY_HOSTS của Worker (allowlist cho /fetch)
        print(','.join(proxy_hosts()))
    if cmd in ('fetch', 'build', 'all'): print(time_line())
    if cmd in ('check', 'all'): sys.exit(check(date))

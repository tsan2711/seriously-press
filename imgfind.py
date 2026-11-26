"""Ảnh dự phòng Wikimedia Commons cho bài vẫn thiếu ảnh. Chỉ stdlib. Mạng chỉ lúc build; cache theo từ khoá trong store/commons/cache.json.
Chấm liên quan theo token tiêu đề/chủ đề khớp tên file + mô tả; dưới ngưỡng (config/img_commons.toml) → bỏ. Lưu a['img_credit'] = 'Tác giả · Giấy phép'."""
import re, os, json, html, tomllib, unicodedata, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
CFG = f'{ROOT}/config/img_commons.toml'
UA = 'press-room/0.1 (+public RSS reader; respects robots)'
MAX_BYTES = 400_000
_TAG = re.compile(r'<[^>]+>')

def load_cfg(path=CFG):
    c = tomllib.load(open(path, 'rb'))
    c['_bad'] = re.compile(c['bad_title'], re.I)
    c['_stop'] = {_fold(w) for w in c.get('stop_en', []) + c.get('stop_vi', [])}
    return c

def _fold(s): return unicodedata.normalize('NFC', (s or '').lower())

def tokens(text, cfg):
    out = []
    for t in re.findall(r'[^\W_]{3,}', _fold(text)):
        if t not in cfg['_stop'] and not t.isdigit() and t not in out: out.append(t)
    return out

def phrases(title, topic_label, cfg):
    """2–3 cụm từ khoá: toàn bộ token chính của tiêu đề (≤4), rồi cặp đầu, rồi chủ đề + token đầu."""
    tk = tokens(title, cfg)
    ps = []
    if tk: ps.append(' '.join(tk[:4]))
    if len(tk) > 2: ps.append(' '.join(tk[:2]))
    tp = tokens(topic_label or '', cfg)
    if tp and tk: ps.append(' '.join(tp[:1] + tk[:1]))
    return list(dict.fromkeys(ps))[:cfg.get('max_phrases', 3)]

def fetch_json(u, timeout=4):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=timeout) as r:
            return json.loads(r.read(MAX_BYTES).decode('utf-8', 'ignore'))
    except Exception: return None

def query_url(q, cfg):
    p = dict(action='query', format='json', generator='search', gsrnamespace=6, gsrsearch=q, gsrlimit=10,
             prop='imageinfo', iiprop='url|size|extmetadata', iiurlwidth=640)
    return cfg['api'] + '?' + urllib.parse.urlencode(p)

def _meta(ii, k): return html.unescape(_TAG.sub('', (ii.get('extmetadata', {}).get(k) or {}).get('value', ''))).strip()

def license_ok(ii, cfg):
    short = _meta(ii, 'LicenseShortName').lower()
    if not short or re.search(r'non.?commercial|\bnc\b|\bnd\b|no.?deriv|fair use|all rights|copyright', short): return False
    return any(re.search(r'(?<![a-z])' + re.escape(l) + r'(?![a-z])', short) for l in cfg['licenses'])

def candidates(data, cfg):
    """JSON API → [{url, title, desc, credit}] đã lọc: rộng ≥ min_width, giấy phép mở, không svg/logo/biểu đồ."""
    out = []
    pages = ((data or {}).get('query') or {}).get('pages') or {}
    for p in pages.values():
        try:
            title = p.get('title', ''); ii = (p.get('imageinfo') or [{}])[0]
            if cfg['_bad'].search(title) or not re.search(r'\.(jpe?g|png|webp)$', title, re.I): continue
            if (ii.get('width') or 0) < cfg['min_width']: continue
            if not license_ok(ii, cfg): continue
            url = ii.get('thumburl') or ''
            if not url.startswith('https://') or len(url) > 400: continue
            auth = _meta(ii, 'Artist') or 'Không rõ tác giả'
            credit = f"{auth[:80]} · {_meta(ii, 'LicenseShortName')} · Wikimedia Commons"
            desc = _meta(ii, 'ImageDescription') + ' ' + _meta(ii, 'ObjectName') + ' ' + _meta(ii, 'Categories')
            out.append(dict(url=url, title=title, desc=desc, credit=credit, idx=p.get('index', 99)))
        except Exception: continue
    return out

def score(c, want, cfg):
    """(tỉ lệ, số khớp) của token khoá trong tên file + mô tả."""
    if not want: return 0.0, 0
    hay = set(tokens(c['title'].rsplit('.', 1)[0] + ' ' + c['desc'], cfg))
    n = sum(1 for t in want if t in hay)
    return n / len(want), n

def best(cands, want, cfg):
    scored = [(score(c, want, cfg), -c['idx'], c) for c in cands]
    scored = [s for s in scored if s[0][0] >= cfg['min_score'] and s[0][1] >= cfg['min_matches']]
    return max(scored, key=lambda s: (s[0], s[1]))[2] if scored else None

def _cache_path(root): return f'{root}/store/commons/cache.json'
def load_cache(root):
    try: return json.load(open(_cache_path(root), encoding='utf8'))
    except Exception: return {}
def save_cache(root, c):
    try:
        os.makedirs(os.path.dirname(_cache_path(root)), exist_ok=True)
        json.dump(c, open(_cache_path(root), 'w', encoding='utf8'), ensure_ascii=False, sort_keys=True)
    except Exception: pass

def fill_commons(arts, root, topic_label=lambda a: '', fetcher=None, cfg=None):
    """Gắn a['img'] + a['img_credit'] cho bài vẫn thiếu ảnh. Trả (số bài gắn, số truy vấn mạng). Không ném lỗi."""
    cfg = cfg or load_cfg(); fetcher = fetcher or (lambda u: fetch_json(u, cfg['timeout']))
    cache = load_cache(root); q_used = n = 0
    try:
        for a in arts:
            if a.get('img') or not a.get('title'): continue
            want = tokens(a['title'] + ' ' + (topic_label(a) or ''), cfg)
            for ph in phrases(a['title'], topic_label(a), cfg):
                if ph not in cache:
                    if q_used >= cfg['max_queries']: continue
                    q_used += 1
                    data = fetcher(query_url(ph, cfg))
                    if data is None: continue   # lỗi mạng: không cache, thử lại lần sau
                    cache[ph] = candidates(data, cfg)
                if (c := best(cache.get(ph, []), want, cfg)):
                    a['img'], a['img_credit'] = c['url'], c['credit']; n += 1; break
    finally:
        save_cache(root, cache)
    return n, q_used

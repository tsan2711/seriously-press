"""og:image lúc build cho bài thiếu ảnh. Chỉ stdlib. Nội dung trang = không tin: chỉ lấy URL ảnh https.
Giới hạn: chỉ http(s), timeout 4 s/bài, đọc ≤ 1 MB, song song ≤ 6, tổng ≤ 40 s; cache theo url trong store/og/cache.json
(cả kết quả rỗng, để không tải lại); mọi lỗi → bỏ qua, không sập build."""
import re, os, json, html, time, urllib.request, urllib.parse, concurrent.futures as cf
from html.parser import HTMLParser
import imgrules

TIMEOUT, MAX_BYTES, WORKERS, BUDGET, RETRY_EMPTY = 4, 1_000_000, 6, 40, 20
UA = 'press-room/0.1 (+public RSS reader; respects robots)'
IMG_BAD = re.compile(r'(pixel|spacer|1x1|blank|tracking|badge|avatar|gravatar|emoji|logo|favicon|\.svg|\.gif)(\b|[?.])|profile_images|/_si/', re.I)   # profile_images = avatar Twitter (mặt người lạ); wp.com/_si = thẻ icon site
META = re.compile(r'<meta\b[^>]*>', re.I)
ATTR = re.compile(r'([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'>]+))')
KEYS = ('og:image', 'og:image:url', 'og:image:secure_url', 'twitter:image', 'twitter:image:src')

def absolutize(u, base=''):
    u = html.unescape((u or '').strip())
    if not u: return ''
    if u.startswith('//'): u = 'https:' + u
    elif not re.match(r'[a-z][a-z0-9+.-]*:', u, re.I) and base: u = urllib.parse.urljoin(base, u)
    return u if u.startswith('https://') and len(u) < 400 and not IMG_BAD.search(u) else ''

def parse_og(page, base=''):
    """Trả URL ảnh tuyệt đối (https) từ og:image / twitter:image trong HTML; ưu tiên og:image. Không có → ''."""
    found = {}
    for m in META.finditer(page):
        at = {k.lower(): html.unescape(a or b or c) for k, a, b, c in ATTR.findall(m.group(0))}
        key = (at.get('property') or at.get('name') or '').strip().lower()
        if key in KEYS and at.get('content'):
            if (u := absolutize(at['content'], base)): found.setdefault(key, u)
    return next((found[k] for k in KEYS if k in found), '')

MIN_PX = 300
IMG_CLASS_BAD = re.compile(r'logo|avatar|sprite|banner-ad|\bads?\b|advert|emoji|icon', re.I)
SKIP_TAGS = ('header', 'nav', 'footer', 'aside', 'script', 'style', 'template')
VOID = ('img', 'br', 'hr', 'meta', 'link', 'input', 'source', 'wbr', 'area', 'base', 'col', 'embed', 'param', 'track')
LAZY = ('data-src', 'data-lazy-src', 'data-original', 'data-lazy', 'src')
SETS = ('srcset', 'data-srcset', 'data-lazy-srcset')

def _px(v):
    m = re.match(r'\s*(\d+)\s*(px)?\s*$', v or '')
    return int(m.group(1)) if m else None

def _best_srcset(v):
    """'a.jpg 400w, b.jpg 800w' → (url, w) lớn nhất có descriptor w; không có w → (url đầu, 0)."""
    best = ('', -1)
    for part in (v or '').split(','):
        bits = part.split()
        if not bits: continue
        w = int(bits[1][:-1]) if len(bits) > 1 and re.fullmatch(r'\d+w', bits[1]) else 0
        if w > best[1]: best = (bits[0], w)
    return best

class _Imgs(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.stack = []; self.found = []
    def _ctx(self):
        names = [t for t in self.stack]
        if any(t in SKIP_TAGS for t in names): return None
        return 0 if any(t in ('article', 'main') for t in names) else 1
    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            c = self._ctx()
            if c is not None: self.found.append((c, dict((k, v or '') for k, v in attrs)))
        elif tag not in VOID: self.stack.append(tag)
    def handle_startendtag(self, tag, attrs):
        if tag == 'img': self.handle_starttag(tag, attrs)
    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag: pass

def _img_candidate(at, base):
    if IMG_CLASS_BAD.search(' '.join((at.get('class', ''), at.get('alt', ''), at.get('id', '')))): return ''
    w, h = _px(at.get('width')), _px(at.get('height'))
    dims = [d for d in (w, h) if d is not None]
    url, sw = '', -1
    for k in SETS:
        if at.get(k):
            u, ww = _best_srcset(at[k])
            if ww > sw: url, sw = u, ww
    if sw >= MIN_PX: return absolutize(url, base)
    if dims and all(d >= MIN_PX for d in dims):
        for k in LAZY:
            if (u := absolutize(at.get(k, ''), base)): return u
    return ''   # không rõ kích thước / quá nhỏ → bỏ

def parse_body(page, base=''):
    """Ảnh lớn đầu tiên trong thân bài (article/main trước, rồi phần còn lại của body). Không có → ''."""
    p = _Imgs()
    try: p.feed(page); p.close()
    except Exception: pass
    for ctx in (0, 1):
        for c, at in p.found:
            if c == ctx and (u := _img_candidate(at, base)): return u
    return ''

def parse_page(page, base=''):
    """Bước 1: og/twitter; bước 2: ảnh lớn đầu tiên trong thân bài."""
    return parse_og(page, base) or parse_body(page, base)

VIA = {}   # url bài → 'host'|'og'|'body' (chỉ trong lần chạy này; cache cũ mặc định 'og')

def fetch_og(url, timeout=TIMEOUT):
    """Luật host (imgrules, kể cả API wiki) trước; không khớp mới tải trang (≤ 1 MB) → og:image hoặc ''. Không ném lỗi."""
    if (k := imgrules.resolve(url, remote=True)): VIA[url] = 'host'; return k
    try:
        if urllib.parse.urlsplit(url).scheme not in ('http', 'https'): return ''
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
            if 'html' not in (r.headers.get('Content-Type') or 'html').lower(): return ''
            page = r.read(MAX_BYTES).decode('utf-8', 'ignore'); base = r.geturl() or url
            if (u := parse_og(page, base)): VIA[url] = 'og'; return u
            if (u := parse_body(page, base)): VIA[url] = 'body'; return u
            return ''
    except Exception:
        return ''

def _cache_path(root): return f'{root}/store/og/cache.json'
def load_cache(root):
    try:
        c = json.load(open(_cache_path(root), encoding='utf8'))
        return c if isinstance(c, dict) else {}
    except Exception: return {}
def save_cache(root, c):
    try:
        os.makedirs(os.path.dirname(_cache_path(root)), exist_ok=True)
        json.dump(c, open(_cache_path(root), 'w', encoding='utf8'), ensure_ascii=False, indent=0, sort_keys=True)
    except Exception: pass

def fill_images(arts, root, limit=90, fetcher=fetch_og, budget=BUDGET, workers=WORKERS, retry_empty=0):
    """Gắn a['img'] cho bài thiếu ảnh. Trả (số bài được gắn, số request mạng). URL đã có trong cache thì không tải lại."""
    cache = load_cache(root); need = [a for a in arts if not a.get('img') and a.get('url')][:limit]
    pre = 0
    for a in need:   # luật host dạng URL: không mạng, không cần cache
        if (k := imgrules.resolve(a['url'])): a['img'] = k; a['img_via'] = 'host'; pre += 1
    need = [a for a in need if not a.get('img')]
    todo = list(dict.fromkeys(a['url'] for a in need if a['url'] not in cache))
    todo += list(dict.fromkeys(a['url'] for a in need if a['url'] in cache and not cache[a['url']]))[:retry_empty]   # rỗng có thể do timeout 4 s → thử lại vài bài/lần
    t0 = time.monotonic(); done = 0
    if todo:
        ex = cf.ThreadPoolExecutor(workers)
        futs = {ex.submit(fetcher, u): u for u in todo}
        try:
            for f in cf.as_completed(futs, timeout=budget):
                try: cache[futs[f]] = f.result() or ''
                except Exception: cache[futs[f]] = ''
                done += 1
        except cf.TimeoutError: pass   # hết ngân sách: phần chưa xong KHÔNG vào cache → thử lại lần sau
        ex.shutdown(wait=False, cancel_futures=True)
        save_cache(root, cache)
    n = pre
    for a in need:
        if cache.get(a['url']): a['img'] = cache[a['url']]; a['img_via'] = VIA.get(a['url'], 'og'); n += 1
    return n, done

# ---- H7: tóm tắt cho bài chưa có (HN chỉ có tiêu đề) — trích meta description/og:description, cache store/og/desc.json ----
DKEYS = ('og:description', 'twitter:description', 'description')
DESC_MAX = 200

def parse_desc(page, title=''):
    """Mô tả ngắn từ meta (chỉ văn bản, bỏ thẻ, ≤ 200 ký tự). Quá ngắn / trùng tiêu đề → ''."""
    found = {}
    for m in META.finditer(page):
        at = {k.lower(): html.unescape(a or b or c) for k, a, b, c in ATTR.findall(m.group(0))}
        key = (at.get('property') or at.get('name') or '').strip().lower()
        if key in DKEYS and at.get('content'): found.setdefault(key, at['content'])
    t = next((found[k] for k in DKEYS if k in found), '')
    t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip()
    if len(t) < 40 or t.lower().startswith(title.lower()[:40]) and len(t) < len(title) + 20: return ''
    return t if len(t) <= DESC_MAX else t[:DESC_MAX - 1].rsplit(' ', 1)[0] + '…'

def fetch_desc(url, title='', timeout=TIMEOUT):
    try:
        if urllib.parse.urlsplit(url).scheme not in ('http', 'https'): return ''
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
            if 'html' not in (r.headers.get('Content-Type') or 'html').lower(): return ''
            return parse_desc(r.read(MAX_BYTES).decode('utf-8', 'ignore'), title)
    except Exception:
        return ''

def fill_summaries(arts, root, limit=60, fetcher=fetch_desc, budget=BUDGET, workers=WORKERS, retry_empty=10, bad=lambda s: False):
    """Gắn a['summary'] (+summary_by='meta') cho bài thiếu tóm tắt. Trả (số bài được gắn, số request). Lỗi → bỏ qua."""
    path = f'{root}/store/og/desc.json'
    try: cache = json.load(open(path, encoding='utf8'))
    except Exception: cache = {}
    need = [a for a in arts if not a.get('summary') and a.get('url') and 'news.ycombinator.com/item' not in a['url']][:limit]
    todo = list(dict.fromkeys(a['url'] for a in need if a['url'] not in cache))
    todo += list(dict.fromkeys(a['url'] for a in need if a['url'] in cache and not cache[a['url']]))[:retry_empty]
    titles = {a['url']: a.get('title', '') for a in need}; done = 0
    if todo:
        ex = cf.ThreadPoolExecutor(workers)
        futs = {ex.submit(fetcher, u, titles[u]): u for u in todo}
        try:
            for f in cf.as_completed(futs, timeout=budget):
                try: cache[futs[f]] = f.result() or ''
                except Exception: cache[futs[f]] = ''
                done += 1
        except cf.TimeoutError: pass
        ex.shutdown(wait=False, cancel_futures=True)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(cache, open(path, 'w', encoding='utf8'), ensure_ascii=False, indent=0, sort_keys=True)
        except Exception: pass
    n = 0
    for a in need:
        s = cache.get(a['url'])
        if s and not bad(s): a['summary'] = s; a['summary_by'] = 'meta'; n += 1
    return n, done

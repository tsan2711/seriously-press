"""Kiểm ảnh chọn được: content-type image/*, kích thước từ ≤64 KB đầu (PNG/JPEG/WEBP/GIF, stdlib), tỉ lệ; dedup theo URL.
Mạng chỉ lúc build (fetcher tiêm được → test offline). Kết quả kiểm cache trong store/og/validate.json (lỗi mạng KHÔNG cache)."""
import os, json, struct, time, urllib.request, urllib.parse, concurrent.futures as cf

HEAD_BYTES, TIMEOUT, WORKERS, BUDGET = 65536, 4, 6, 30
MIN_PX, MAX_RATIO, MIN_RATIO = 300, 4.0, 0.5   # rộng/cao ≤ 4:1 và ≥ 1:2
MAX_USES = 2
UA = 'press-room/0.1 (+public RSS reader; respects robots)'
TRACK = ('utm_', 'fbclid', 'gclid', 'mc_', 'ref', 'source', 'igshid', 'yclid', 'msclkid')

def size_of(b):
    """Bytes đầu tệp → (w, h) hoặc None. PNG/GIF/WEBP/JPEG."""
    try:
        if b[:8] == b'\x89PNG\r\n\x1a\n' and b[12:16] == b'IHDR':
            return struct.unpack('>II', b[16:24])
        if b[:6] in (b'GIF87a', b'GIF89a'):
            return struct.unpack('<HH', b[6:10])
        if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
            k = b[12:16]
            if k == b'VP8X': return (int.from_bytes(b[24:27], 'little') + 1, int.from_bytes(b[27:30], 'little') + 1)
            if k == b'VP8L' and b[20] == 0x2f:
                v = int.from_bytes(b[21:25], 'little'); return ((v & 0x3fff) + 1, ((v >> 14) & 0x3fff) + 1)
            if k == b'VP8 ' and b[23:26] == b'\x9d\x01\x2a':
                return (struct.unpack('<H', b[26:28])[0] & 0x3fff, struct.unpack('<H', b[28:30])[0] & 0x3fff)
            return None
        if b[:2] == b'\xff\xd8':
            i, n = 2, len(b)
            while i + 4 <= n:
                if b[i] != 0xff: i += 1; continue
                m = b[i + 1]
                if m == 0xff: i += 1; continue
                if m in (0xd8, 0x01) or 0xd0 <= m <= 0xd7: i += 2; continue
                ln = struct.unpack('>H', b[i + 2:i + 4])[0]
                if m in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                    h, w = struct.unpack('>HH', b[i + 5:i + 9]); return (w, h)
                i += 2 + ln
    except Exception: pass
    return None

def judge(ctype, head):
    """(content-type, bytes đầu) → {ok, w, h, why}. Thuần."""
    ct = (ctype or '').split(';')[0].strip().lower()
    if not ct.startswith('image/'): return dict(ok=False, why='not-image')
    sz = size_of(head or b'')
    if not sz or not sz[0] or not sz[1]: return dict(ok=False, why='no-size')
    w, h = sz
    if w < MIN_PX or h < MIN_PX: return dict(ok=False, w=w, h=h, why='small')
    r = w / h
    if r > MAX_RATIO or r < MIN_RATIO: return dict(ok=False, w=w, h=h, why='ratio')
    return dict(ok=True, w=w, h=h)

def fetch_head(url, timeout=TIMEOUT):
    """(content-type, ≤64 KB đầu). Ném lỗi nếu mạng hỏng (→ không cache)."""
    if urllib.parse.urlsplit(url).scheme not in ('http', 'https'): return ('', b'')
    rq = urllib.request.Request(url, headers={'User-Agent': UA, 'Range': f'bytes=0-{HEAD_BYTES - 1}'})
    with urllib.request.urlopen(rq, timeout=timeout) as r:
        return r.headers.get('Content-Type') or '', r.read(HEAD_BYTES)

def norm_url(u):
    """Khoá dedup: bỏ fragment + query theo dõi, host thường, bỏ www."""
    s = urllib.parse.urlsplit((u or '').strip())
    q = [(k, v) for k, v in urllib.parse.parse_qsl(s.query, keep_blank_values=True) if not k.lower().startswith(TRACK)]
    host = s.netloc.lower()
    host = host[4:] if host.startswith('www.') else host
    return urllib.parse.urlunsplit((s.scheme.lower(), host, s.path, urllib.parse.urlencode(sorted(q)), ''))

def _path(root): return f'{root}/store/og/validate.json'
def load_cache(root):
    try:
        c = json.load(open(_path(root), encoding='utf8')); return c if isinstance(c, dict) else {}
    except Exception: return {}
def save_cache(root, c):
    try:
        os.makedirs(os.path.dirname(_path(root)), exist_ok=True)
        json.dump(c, open(_path(root), 'w', encoding='utf8'), ensure_ascii=False, indent=0, sort_keys=True)
    except Exception: pass

def validate_urls(urls, root, fetcher=fetch_head, budget=BUDGET, workers=WORKERS):
    """{url: verdict} cho URL đã biết (cache hoặc vừa kiểm). URL không kiểm được (lỗi mạng/hết giờ) vắng mặt."""
    cache = load_cache(root)
    todo = [u for u in dict.fromkeys(urls) if u and u not in cache]
    if todo:
        ex = cf.ThreadPoolExecutor(workers)
        futs = {ex.submit(fetcher, u): u for u in todo}
        try:
            for f in cf.as_completed(futs, timeout=budget):
                try: ct, head = f.result()
                except Exception: continue
                cache[futs[f]] = judge(ct, head)
        except cf.TimeoutError: pass
        ex.shutdown(wait=False, cancel_futures=True)
        save_cache(root, cache)
    return {u: cache[u] for u in urls if u in cache}

def clean(arts, root, fetcher=fetch_head, **kw):
    """Gỡ a['img'] hỏng (không phải ảnh / nhỏ / tỉ lệ lạ) và ảnh lặp >MAX_USES thẻ (giữ MAX_USES bài đầu theo thứ tự arts).
    Bài bị gỡ nhận tập a['img_bad'] để bước dự phòng kế tiếp biết. Trả {'bad': n, 'dup': n}."""
    withimg = [a for a in arts if a.get('img')]
    verdicts = validate_urls([a['img'] for a in withimg], root, fetcher, **kw)
    out = dict(bad=0, dup=0); uses = {}
    for a in withimg:
        v = verdicts.get(a['img'])
        why = 'bad' if v and not v.get('ok') else None
        if not why:
            k = norm_url(a['img']); uses[k] = uses.get(k, 0) + 1
            if uses[k] > MAX_USES: why = 'dup'
        if why:
            out[why] += 1; a.setdefault('img_bad', []).append(a['img'])
            a.pop('img'); a.pop('img_credit', None); a.pop('img_via', None)
    return out

# ── Bản sao cục bộ: tải về, thu 640×360 webp, lưu public/img/<hash>.webp (cần Pillow, tuỳ chọn) ──
import hashlib
try:
    from PIL import Image, ImageOps   # tuỳ chọn: không có thì giữ hotlink như cũ
    import io
except Exception:
    Image = None
LOCAL_W, LOCAL_H, LOCAL_Q = 640, 360, 78
MAX_DL, DL_TIMEOUT = 2 * 1024 * 1024, 5
DIR_CAP, KEEP_DAYS, LOCAL_BUDGET = 40 * 1024 * 1024, 14, 60

def have_pillow(): return Image is not None

def fetch_full(url, timeout=DL_TIMEOUT):
    """Tải cả ảnh (≤2 MB). Quá lớn / không phải ảnh / không http(s) → None. Lỗi mạng ném ra."""
    if urllib.parse.urlsplit(url).scheme not in ('http', 'https'): return None
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
        if not (r.headers.get('Content-Type') or '').lower().startswith('image/'): return None
        b = r.read(MAX_DL + 1)
    return None if len(b) > MAX_DL else b

LOGO_MIN_SHARE, LOGO_MAX_EDGE = 0.75, 0.03

def logo_card(im):
    """Ảnh logo/icon/thẻ thương hiệu: một màu nền chiếm ≥75% khung VÀ viền ngoài (10 cột/6 hàng của lưới 64×36) gần như trơn
    (<3% khác nền) → nội dung chỉ ở giữa. Biểu đồ/ảnh chụp màn hình có nội dung sát mép nên không dính."""
    try:
        s = im.convert('RGB').resize((64, 36)); px = s.load()
        q = [(px[x, y][0] >> 4, px[x, y][1] >> 4, px[x, y][2] >> 4) for y in range(36) for x in range(64)]
        bg, n = max(((c, q.count(c)) for c in set(q)), key=lambda t: t[1])
        ring = [q[y * 64 + x] for y in range(36) for x in range(64) if x < 10 or x >= 54 or y < 6 or y >= 30]
        return n / len(q) >= LOGO_MIN_SHARE and sum(1 for c in ring if c != bg) / len(ring) < LOGO_MAX_EDGE
    except Exception: return False

class LogoCard(Exception): pass

def to_webp(data):
    """Bytes ảnh → bytes webp 640×360 (cắt kiểu cover) hoặc None (không Pillow / ảnh hỏng). Ném LogoCard nếu là logo/icon."""
    if Image is None: return None
    try:
        im = Image.open(io.BytesIO(data)); im.load()
        if logo_card(im): raise LogoCard()
        im = ImageOps.fit(im.convert('RGB'), (LOCAL_W, LOCAL_H), Image.LANCZOS)
        o = io.BytesIO(); im.save(o, 'WEBP', quality=LOCAL_Q); return o.getvalue()
    except LogoCard: raise
    except Exception: return None

def _lpath(root): return f'{root}/store/og/local.json'
def _imgdir(root): return f'{root}/public/img'

def prune(root, used, now=None, cap=DIR_CAP, keep_days=KEEP_DAYS):
    """Xoá tệp không bài nào dùng và cũ hơn keep_days; nếu vẫn >cap thì xoá tiếp tệp không dùng cũ nhất. Tệp đang dùng giữ nguyên. Trả số tệp xoá."""
    d, now, n = _imgdir(root), now or time.time(), 0
    if not os.path.isdir(d): return 0
    fs = []
    for f in os.listdir(d):
        p = f'{d}/{f}'
        if os.path.isfile(p): s = os.stat(p); fs.append((s.st_mtime, s.st_size, f, p))
    fs.sort()
    total = sum(x[1] for x in fs); keep = []
    for m, sz, f, p in fs:
        if f not in used and now - m > keep_days * 86400:
            os.remove(p); total -= sz; n += 1
        else: keep.append((m, sz, f, p))
    for m, sz, f, p in keep:
        if total <= cap: break
        if f not in used: os.remove(p); total -= sz; n += 1
    return n

def localize(arts, root, fetcher=fetch_full, now=None, budget=LOCAL_BUDGET, workers=WORKERS):
    """Thay a['img'] http(s) bằng 'img/<hash>.webp' (+ a['img_w'], a['img_h'], a['img_remote'] giữ URL gốc). Không Pillow/lỗi → giữ nguyên.
    Cache url→tên trong store/og/local.json. Trả {'local': n, 'kept': n, 'pruned': n}."""
    out = dict(local=0, kept=0, pruned=0)
    if Image is None: return out
    now = now or time.time(); d = _imgdir(root)
    try: cache = json.load(open(_lpath(root), encoding='utf8'))
    except Exception: cache = {}
    if not isinstance(cache, dict): cache = {}
    urls = list(dict.fromkeys(a['img'] for a in arts if a.get('img', '').startswith(('http://', 'https://'))))
    try: rej = set(json.load(open(f'{root}/store/og/logo.json', encoding='utf8')))
    except Exception: rej = set()
    todo = [u for u in urls if u not in rej and not (u in cache and os.path.isfile(f'{d}/{cache[u]}'))]
    def work(u):
        b = fetcher(u); w = to_webp(b) if b else None
        if not w: return None
        name = hashlib.sha1(w).hexdigest()[:16] + '.webp'
        os.makedirs(d, exist_ok=True)
        if not os.path.isfile(f'{d}/{name}'):
            open(f'{d}/{name}.tmp', 'wb').write(w); os.replace(f'{d}/{name}.tmp', f'{d}/{name}')
        return name
    if todo:
        ex = cf.ThreadPoolExecutor(workers); futs = {ex.submit(work, u): u for u in todo}
        try:
            for f in cf.as_completed(futs, timeout=budget):
                try: nm = f.result()
                except LogoCard: rej.add(futs[f]); continue
                except Exception: continue
                if nm: cache[futs[f]] = nm
        except cf.TimeoutError: pass
        ex.shutdown(wait=False, cancel_futures=True)
    used = set()
    for a in arts:
        u = a.get('img', ''); nm = cache.get(u)
        if u in rej:   # logo/icon/thẻ thương hiệu: thà không ảnh hơn ảnh sai
            a.setdefault('img_bad', []).append(u); a.pop('img'); a.pop('img_credit', None); a.pop('img_via', None); out['logo'] = out.get('logo', 0) + 1
        elif u in urls and nm and os.path.isfile(f'{d}/{nm}'):
            a['img_remote'] = u; a['img'] = f'img/{nm}'; a['img_w'], a['img_h'] = LOCAL_W, LOCAL_H
            used.add(nm); out['local'] += 1
            try: os.utime(f'{d}/{nm}', (now, now))
            except OSError: pass
        elif u: out['kept'] += 1
    cache = {u: n for u, n in cache.items() if os.path.isfile(f'{d}/{n}')}
    try: os.makedirs(f'{root}/store/og', exist_ok=True); json.dump(sorted(rej), open(f'{root}/store/og/logo.json', 'w', encoding='utf8'))
    except Exception: pass
    try:
        os.makedirs(os.path.dirname(_lpath(root)), exist_ok=True)
        json.dump(cache, open(_lpath(root), 'w', encoding='utf8'), indent=0, sort_keys=True)
    except Exception: pass
    out['pruned'] = prune(root, used, now)
    return out

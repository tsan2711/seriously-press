"""Luật ảnh theo host (config/img_rules.toml). Chỉ stdlib. resolve() thuần: không mạng.
kind=url → trả URL ảnh luôn; kind=api → cần mạng, chỉ chạy khi remote=True (lúc build) với fetcher tiêm được."""
import re, os, json, tomllib, urllib.request, urllib.parse

CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'img_rules.toml')
TIMEOUT, MAX_BYTES = 4, 200_000
UA = 'press-room/0.1 (+public RSS reader; respects robots)'
_cache = {}

def load_rules(path=CFG):
    if path in _cache: return _cache[path]
    try:
        raw = tomllib.load(open(path, 'rb')).get('rule', [])
        rules = [dict(r, _re=re.compile(r['match'], re.I)) for r in raw if r.get('match')]
    except Exception: rules = []
    _cache[path] = rules
    return rules

def _match(url, rules):
    u = urllib.parse.urlsplit((url or '').strip())
    if u.scheme not in ('http', 'https'): return None, None
    for r in rules:
        # youtube watch cần query; các host khác khớp trên URL bỏ query/fragment
        cand = url.split('#')[0] if 'youtube' in r.get('name', '') and '?' in r['match'] else url.split('#')[0].split('?')[0]
        m = r['_re'].fullmatch(cand.rstrip('/'))
        if m: return r, m
    return None, None

def _fill(tpl, groups):
    return tpl.format(**{k: urllib.parse.quote(v, safe='%') for k, v in groups.items() if v is not None})

def _dig(obj, parts):
    if not parts: return obj if isinstance(obj, str) else ''
    if isinstance(obj, dict):
        keys = list(obj.values()) if parts[0] == '*' else ([obj[parts[0]]] if parts[0] in obj else [])
        for v in keys:
            if (r := _dig(v, parts[1:])): return r
    return ''

def fetch_json(u, timeout=TIMEOUT):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=timeout) as r:
            return json.loads(r.read(MAX_BYTES).decode('utf-8', 'ignore'))
    except Exception: return None

def resolve(url, remote=False, fetcher=fetch_json, rules=None):
    """URL bài → URL ảnh https, hoặc ''. Luật api chỉ chạy khi remote=True. Không ném lỗi."""
    try:
        r, m = _match(url, load_rules() if rules is None else rules)
        if not r: return ''
        g = m.groupdict()
        if r.get('kind', 'url') == 'url':
            out = _fill(r['image'], g)
        elif remote:
            out = _dig(fetcher(_fill(r['api'], g)), r['json_path'].split('.'))
        else: return ''
        return out if out.startswith('https://') and len(out) < 400 else ''
    except Exception: return ''

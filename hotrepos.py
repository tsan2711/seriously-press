#!/usr/bin/env python3
"""Mục "Repo hay": ~10 repo GitHub — 6 đang trending (sao tăng nhanh) + 4 repo hay (đã được tin dùng, còn sống), mỗi repo ghi "giải quyết vấn đề gì".
Nguồn (mỗi nguồn hỏng thì bỏ qua, không làm hỏng build): github.com/trending (HTML) · Search API (repo mới tăng sao / repo lâu năm còn cập nhật) · HN Show HN trỏ vào github.
Lọc: bỏ fork/archived/danh sách awesome/không mô tả; chấm theo độ liên quan tới các ban (config/desks/*.toml: hn_queries + topics.toml). Chỉ stdlib.
  python3 hotrepos.py [--offline]    # ghi store/repos/<ngày>.json; theme dựng repos.html từ file này"""
import sys, os, re, json, html, datetime, urllib.parse, tomllib, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
N_TREND, N_GOOD = 6, 4
BAD_NAME = re.compile(r'awesome|^free-|-list$|interview|roadmap|cheat-?sheet|tutorial|leetcode|public-apis', re.I)
SLUG = re.compile(r'^/([\w.-]+)/([\w.-]+)$')
TREND_PAGES = [('', 'daily'), ('', 'weekly'), ('c%23', 'weekly'), ('python', 'weekly'), ('typescript', 'weekly')]

def _http():
    import press
    return press.http

def keywords():
    """Từ khoá liên quan: hn_queries của từng ban → {ban: [từ…]}. Ban không có thì bỏ."""
    out = {}
    for f in sorted(glob.glob(f'{ROOT}/config/desks/*.toml')):
        d = tomllib.load(open(f, 'rb')); out[d['id']] = [q.lower() for q in d.get('hn_queries', [])]
    return out

def relevance(r, kw):
    """→ (điểm, [ban]). Mỗi từ khoá (cả cụm hoặc ≥2 từ lẻ) trúng tên/mô tả/chủ đề repo = 1 điểm."""
    text = ' '.join([r['name'], r.get('desc') or '', ' '.join(r.get('topics', []))]).lower(); sc, ds = 0, []
    for d, qs in kw.items():
        n = sum(1 for q in qs if q in text or (len(q.split()) > 1 and all(w in text for w in q.split())) or (len(q.split()) == 1 and re.search(r'\b' + re.escape(q) + r'\b', text)))
        if n: sc += n; ds.append(d)
    return sc, ds

def parse_trending(page, period):
    """HTML github.com/trending → [{name, desc, lang, stars, gain, period}]. Chịu được đổi nhẹ markup: lỗi một khối → bỏ khối đó."""
    out = []
    for blk in re.split(r'<article[^>]*class="[^"]*Box-row', page)[1:]:
        try:
            m = re.search(r'<h2[^>]*>.*?href="(/[^"]+)"', blk, re.S); s = SLUG.match(m.group(1).strip()) if m else None
            if not s: continue
            desc = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', blk, re.S)
            lang = re.search(r'itemprop="programmingLanguage"[^>]*>\s*([^<]+?)\s*<', blk)
            gain = re.search(r'([\d,]+)\s+stars?\s+(?:today|this week|this month)', blk)
            tot = re.search(r'href="/[^"]+/stargazers"[^>]*>(?:\s|<[^>]+>)*([\d,]+)', blk)
            out.append(dict(name=f'{s.group(1)}/{s.group(2)}'.replace('//', '/').lstrip('/') if False else f'{s.group(1)}/{s.group(2)}',
                            desc=html.unescape(re.sub(r'<[^>]+>', '', desc.group(1))).strip() if desc else '', lang=lang.group(1) if lang else '',
                            stars=int(tot.group(1).replace(',', '')) if tot else 0, gain=int(gain.group(1).replace(',', '')) if gain else 0, period=period, via='trending'))
        except Exception:
            continue
    for r in out: r['name'] = r['name'].strip('/')
    return out

def api_items(items, via):
    return [dict(name=i['full_name'], desc=i.get('description') or '', lang=i.get('language') or '', stars=i.get('stargazers_count', 0), gain=0, period='',
                 topics=i.get('topics', []), license=(i.get('license') or {}).get('spdx_id') or '', archived=i.get('archived', False), fork=i.get('fork', False),
                 pushed=i.get('pushed_at', ''), created=i.get('created_at', ''), via=via) for i in items]

def collect(http, kw):
    got, log = [], {}
    def run(tag, fn):
        try: r = fn(); got.extend(r); log[tag] = len(r)
        except Exception as ex: log[tag] = f'lỗi: {str(ex)[:50]}'
    for lang, per in TREND_PAGES:
        run(f'trending/{lang or "all"}/{per}', lambda lang=lang, per=per: parse_trending(http(f'https://github.com/trending{"/" + lang if lang else ""}?since={per}').decode('utf8', 'replace'), per))
    since = (datetime.date.today() - datetime.timedelta(days=14)).isoformat(); old = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    for d, qs in kw.items():
        for q in qs[:2]:
            run(f'rising/{q}', lambda q=q: api_items(json.loads(http('https://api.github.com/search/repositories?' + urllib.parse.urlencode({'q': f'{q} created:>{since} stars:>30', 'sort': 'stars', 'per_page': 8}))).get('items', []), 'rising'))
            run(f'good/{q}', lambda q=q: api_items(json.loads(http('https://api.github.com/search/repositories?' + urllib.parse.urlencode({'q': f'{q} stars:>1500 pushed:>{old}', 'sort': 'stars', 'per_page': 8}))).get('items', []), 'good'))
    def hn():
        u = 'https://hn.algolia.com/api/v1/search_by_date?' + urllib.parse.urlencode({'tags': 'show_hn', 'query': 'github.com', 'numericFilters': 'points>40', 'hitsPerPage': 30})
        o = []
        for h in json.loads(http(u)).get('hits', []):
            m = re.match(r'https?://github\.com/([\w.-]+/[\w.-]+?)/?$', h.get('url') or '')
            if m: o.append(dict(name=m.group(1), desc=re.sub(r'^Show HN:\s*', '', h.get('title') or ''), lang='', stars=h.get('points', 0), gain=0, period='', via='hn'))
        return o
    run('hn-show', hn)
    return got, log

def readme_lead(http, name):
    """Đoạn đầu README có chữ thật (bỏ huy hiệu/ảnh/tiêu đề) ≤220 ký tự, hoặc ''."""
    try: t = http(f'https://raw.githubusercontent.com/{name}/HEAD/README.md').decode('utf8', 'replace')
    except Exception: return ''
    for para in re.split(r'\n\s*\n', re.sub(r'<!--.*?-->|<[^>]+>', ' ', t, flags=re.S)):
        p = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', para); p = re.sub(r'[#>*_`|-]+', ' ', p); p = re.sub(r'\s+', ' ', p).strip()
        if len(p) >= 50 and len(re.findall(r'[A-Za-z]{3,}', p)) >= 8: return p[:220].rsplit(' ', 1)[0] + ('…' if len(p) > 220 else '')
    return ''

def pick(cands, kw):
    """Gộp trùng theo tên, lọc, chấm điểm → {'trend': 6, 'good': 4}. Trending: sao tăng × (1 + liên quan); Hay: sao × liên quan, phải liên quan ≥1."""
    by = {}
    for r in cands:
        k = r['name'].lower()
        if k in by:   # giữ bản có nhiều thông tin: trending (có gain) + API (có chủ đề/giấy phép)
            o = by[k]; o.update({x: v for x, v in r.items() if v and not o.get(x)}); o['via'] = o['via'] if o['via'] == 'trending' else r['via']
        else: by[k] = dict(r)
    ok = []
    for r in by.values():
        if r.get('archived') or r.get('fork') or BAD_NAME.search(r['name'].split('/')[-1]) or not (r.get('desc') or '').strip(): continue
        r['rel'], r['desks'] = relevance(r, kw); ok.append(r)
    trend = sorted([r for r in ok if r['via'] in ('trending', 'rising', 'hn') and (r['gain'] or r['via'] != 'trending')], key=lambda r: -((r['gain'] or r['stars'] / 20) * (1 + r['rel'])))
    chosen = []
    for d in kw:   # mỗi ban ≥1 repo nếu có
        x = next((r for r in trend if d in r['desks'] and r not in chosen), None)
        if x and len(chosen) < N_TREND: chosen.append(x)
    for r in trend:
        if len(chosen) >= N_TREND: break
        if r not in chosen: chosen.append(r)
    for r in chosen: r['kind'] = 'trend'
    good = sorted([r for r in ok if r not in chosen and r['rel'] >= 1 and r['stars'] >= 1500 and r['via'] in ('good', 'trending')], key=lambda r: -(r['stars'] * (1 + r['rel'])))[:N_GOOD]
    for r in good: r['kind'] = 'good'
    return chosen + good

def why(r):
    bits = []
    if r.get('gain'): bits.append(f"+{r['gain']:,} sao {'hôm nay' if r['period'] == 'daily' else 'tuần này'}")
    if r.get('stars'): bits.append(f"★ {r['stars']:,}")
    if r.get('lang'): bits.append(r['lang'])
    if r.get('license'): bits.append(r['license'])
    if r.get('pushed'): bits.append('cập nhật ' + r['pushed'][:10])
    return ' · '.join(bits)

def build(offline=False, http=None):
    kw = keywords(); date = datetime.date.today().isoformat(); out = f'{ROOT}/store/repos'; os.makedirs(out, exist_ok=True)
    http = http or _http(); got, log = ([], {'offline': True}) if offline else collect(http, kw)
    chosen = pick(got, kw) if got else []
    for r in chosen:
        r['solves'] = (readme_lead(http, r['name']) if not offline else '') or r['desc']; r['why'] = why(r); r['url'] = 'https://github.com/' + r['name']
    if len(chosen) < 3:   # mạng/nguồn hỏng: dùng lại bản gần nhất, đánh dấu cũ
        prev = sorted(glob.glob(f'{out}/????-??-??.json'))
        if prev and not os.path.basename(prev[-1]).startswith(date):
            d = json.load(open(prev[-1], encoding='utf8')); d['stale'] = True; d['log'] = log; return d
    d = dict(date=date, repos=chosen, log=log, stale=False)
    if chosen: json.dump(d, open(f'{out}/{date}.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    return d

def latest():
    f = sorted(glob.glob(f'{ROOT}/store/repos/????-??-??.json'))
    return json.load(open(f[-1], encoding='utf8')) if f else None

def render(d=None):
    """→ HTML trang repos.html (dùng theme.page, class thẻ có sẵn). Không có dữ liệu → trang báo chưa có."""
    import theme; e = html.escape; d = d or latest()
    if not d or not d.get('repos'): return theme.page('repos', 'Repo hay', '<main id="main" class="wrap"><h1>Repo hay</h1><p>Chưa lấy được danh sách repo; lần build sau sẽ thử lại.</p></main>', 'repos')
    def sec(title, sub, rs):
        if not rs: return ''
        cs = ''.join(f'<article class="card"><div class="cb"><h3><a href="{e(r["url"])}" rel="noopener" target="_blank">{e(r["name"])}</a></h3><p class="sum">{e(r["solves"])}</p><p class="meta">{e(r["why"])}</p></div></article>' for r in rs)
        return f'<section><h2>{e(title)}</h2><p class="sub">{e(sub)}</p><div class="grid">{cs}</div></section>'
    rs = d['repos']; stale = f'<p class="sub">Dữ liệu cũ ({e(d["date"])}) — lần lấy mới chưa được.</p>' if d.get('stale') else ''
    body = ('<main id="main" class="wrap"><h1>Repo hay</h1>' + stale
            + sec('Đang trending', 'Sao tăng nhanh nhất trong tuần, ưu tiên repo liên quan các ban.', [r for r in rs if r['kind'] == 'trend'])
            + sec('Repo hay đáng biết', 'Đã được nhiều người tin dùng và vẫn còn cập nhật.', [r for r in rs if r['kind'] == 'good']) + '</main>')
    return theme.page('repos', 'Repo hay', body, 'repos')

def write_page(public):
    open(f'{public}/repos.html', 'w', encoding='utf8').write(render())

if __name__ == '__main__':
    d = build('--offline' in sys.argv); print(json.dumps(d['log'], ensure_ascii=False)); print(len(d['repos']), 'repo')
    for r in d['repos']: print(r['kind'], r['name'], '|', r['why'], '|', r['solves'][:70])

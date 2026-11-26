"""Phần build cho U2–U7: search.json (tìm kiếm cục bộ), stories.json (theo dõi/timeline từ KB), PWA (manifest, sw.js, icon), module lazy public/x/.
Chỉ dữ liệu CÔNG KHAI (tin + KB). Không PII."""
import glob, hashlib, json, os, re, shutil

SNIP = 150
_ISO = re.compile(r'\d{4}-\d\d-\d\d')


def _day(pub, fallback):
    m = _ISO.match(pub or '')
    return m.group(0) if m else fallback


def _rows(root, topics, desks):
    """Mỗi hàng: [id, tiêu đề, url, nguồn, ngày, [chủ đề], ban, đoạn trích, engagement 0-100]; trùng sid → giữ bản mới nhất."""
    by = {}
    for f in sorted(glob.glob(f'{root}/store/????-??-??.json')):
        d = json.load(open(f, encoding='utf8'))
        for a in d['articles']:
            key = a.get('sid') or a['id']
            by[key] = [a['id'], a['title'], a['url'], a['source'], _day(a.get('published'), d['date']), a.get('topics', [])[:3],
                       (a.get('desks') or [''])[0], (a.get('summary') or '')[:SNIP], int(round((a.get('engagement') or 0) * 100)), a.get('sid') or a['id']]
    kb = f'{root}/../knowledge/kb/stories.jsonl'
    if os.path.exists(kb):   # KB giữ cả tin đã rơi khỏi store → vẫn tìm được
        for line in open(kb, encoding='utf8'):
            s = json.loads(line)
            if s['sid'] in by: continue
            e = s['entries'][-1]
            by[s['sid']] = [s['sid'], e['title'], e['url'], e['src'], e['d'], s.get('topics', [])[:3], '', '', 0, s['sid']]
    return sorted(by.values(), key=lambda r: r[4], reverse=True)


def build_search(root, topics, desks):
    rows = _rows(root, topics, desks)
    pub = f'{root}/public'
    json.dump(dict(v=1, topics={k: v.get('label', k) for k, v in topics.items()}, desks={k: v['name'] for k, v in desks.items()}, rows=rows),
              open(f'{pub}/search.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    st = {}
    kb = f'{root}/../knowledge/kb/stories.jsonl'
    if os.path.exists(kb):
        for line in open(kb, encoding='utf8'):
            s = json.loads(line)
            if len({e['d'] + e['title'] for e in s['entries']}) > 1:
                st[s['sid']] = [[e['d'], e['title'][:120], e['src'], e['url']] for e in s['entries']][-12:]
    json.dump(st, open(f'{pub}/stories.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    return len(rows)


ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="#a77c4e"/>'
        '<rect x="96" y="104" width="320" height="304" fill="#f5eedb" transform="rotate(-3 256 256)"/><rect x="136" y="160" width="240" height="28" fill="#1a1712"/>'
        '<rect x="136" y="216" width="240" height="16" fill="#5c5345"/><rect x="136" y="252" width="190" height="16" fill="#5c5345"/><circle cx="256" cy="120" r="26" fill="#d33a2c"/></svg>')


def build_pwa(root):
    pub = f'{root}/public'
    os.makedirs(f'{pub}/x', exist_ok=True)
    # gói lazy: lõi thuần + giao diện thành một tệp (test chạy trên từng lõi riêng)
    open(f'{pub}/x/ui.js', 'w', encoding='utf8').write('\n'.join(open(f'{root}/web/x/{n}.js', encoding='utf8').read() for n in ('search', 'features', 'persona', 'profilectl', 'readtools', 'feedback', 'tour', 'ui')))
    shutil.copy(f'{root}/web/x/en.json', f'{pub}/x/en.json')
    shutil.copy(f'{root}/web/boot.js', f'{pub}/boot.js')
    open(f'{pub}/icon.svg', 'w').write(ICON)
    json.dump(dict(name='Bản Tin', short_name='Bản Tin', description='Bản tin công nghệ hằng ngày: game dev, thiết kế, AI.', start_url='./index.html', scope='./', display='standalone',
                   background_color='#3a2b1d', theme_color='#a77c4e', lang='vi', icons=[dict(src='icon.svg', sizes='any', type='image/svg+xml', purpose='any maskable')]),
              open(f'{pub}/manifest.webmanifest', 'w', encoding='utf8'), ensure_ascii=False)
    open(f'{pub}/offline.html', 'w', encoding='utf8').write(
        '<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Offline · Bản Tin</title></head>'
        '<body style="font:1rem/1.5 system-ui;margin:2rem;max-width:32rem"><h1>Bạn đang offline</h1><p>Chưa có bản lưu của trang này. Kết nối lại rồi thử lần nữa — các số báo bạn đã mở sẽ đọc được khi offline.</p><p><a href="index.html">Về báo hôm nay</a></p></body></html>\n')
    shell = sorted(os.path.relpath(p, pub) for p in glob.glob(f'{pub}/*') if os.path.isfile(p) and not p.endswith(('.tmp', 'sw.js')) and
                   (p.endswith(('.html', '.js', '.css', '.webmanifest', '.svg')) or os.path.basename(p) in ('today.json', 'issues.json')))
    shell += ['x/ui.js', 'x/en.json', 'search.json', 'stories.json']
    ver = hashlib.sha1(b''.join(open(f'{pub}/{p}', 'rb').read() for p in shell)).hexdigest()[:10]
    sw = open(f'{root}/web/sw.js', encoding='utf8').read().replace('__VER__', ver).replace('__SHELL__', json.dumps(shell))
    open(f'{pub}/sw.js', 'w', encoding='utf8').write(sw)
    return ver


# ---- feed.xml (Atom) + sitemap.xml: chỉ dữ liệu công khai, stdlib ----
SITE_URL = os.environ.get('PRESS_SITE_URL', 'https://tsan2711.github.io/seriously-press/').rstrip('/') + '/'
FEED_N = 20


def _iso(pub, fallback):
    """Chuẩn hoá về RFC 3339 (UTC); thiếu/sai giờ → 00:00:00Z của ngày fallback."""
    m = re.match(r'(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d:\d\d)', pub or '')
    return f'{m.group(1)}T{m.group(2)}Z' if m else f'{_day(pub, fallback)}T00:00:00Z'


def feed_items(root, n=FEED_N):
    """n bài mới nhất qua mọi số báo trong store/ (trùng sid → bản mới nhất), mỗi mục là dict."""
    by = {}
    for f in sorted(glob.glob(f'{root}/store/????-??-??.json')):
        d = json.load(open(f, encoding='utf8'))
        for a in d['articles']:
            if not a.get('url') or not a.get('title'): continue
            by[a.get('sid') or a['id']] = dict(id=a.get('sid') or a['id'], title=a['title'], url=a['url'], updated=_iso(a.get('published'), d['date']),
                                               summary=(a.get('summary') or '')[:300], source=a.get('source', ''))
    return sorted(by.values(), key=lambda x: (x['updated'], x['id']), reverse=True)[:n]


def build_feed_xml(items, base=SITE_URL, now=None):
    from xml.sax.saxutils import escape as x
    upd = items[0]['updated'] if items else (now or '1970-01-01T00:00:00Z')
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="vi">',
           '<title>Bản Tin</title>', '<subtitle>Bản tin công nghệ hằng ngày: game dev, thiết kế, AI.</subtitle>',
           f'<id>{x(base)}</id>', f'<link rel="self" type="application/atom+xml" href="{x(base)}feed.xml"/>',
           f'<link rel="alternate" type="text/html" href="{x(base)}"/>', f'<updated>{upd}</updated>']
    for it in items:
        out.append(f'<entry><id>urn:press:{x(it["id"])}</id><title>{x(it["title"])}</title><link rel="alternate" href="{x(it["url"], {chr(34): "&quot;"})}"/>'
                   f'<updated>{it["updated"]}</updated><summary>{x(it["summary"] or it["title"])}</summary>'
                   + (f'<source><title>{x(it["source"])}</title></source>' if it['source'] else '') + '</entry>')
    out.append('</feed>')
    return '\n'.join(out) + '\n'


def build_sitemap_xml(pages, base=SITE_URL, lastmod=None):
    from xml.sax.saxutils import escape as x
    out = ['<?xml version="1.0" encoding="utf-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in pages:
        out.append(f'<url><loc>{x(base + p)}</loc>' + (f'<lastmod>{lastmod}</lastmod>' if lastmod else '') + '</url>')
    out.append('</urlset>')
    return '\n'.join(out) + '\n'


def build_feed(root):
    """Ghi public/feed.xml + public/sitemap.xml (gọi sau khi các trang HTML đã ra). Trả về số mục feed."""
    pub = f'{root}/public'
    items = feed_items(root)
    open(f'{pub}/feed.xml', 'w', encoding='utf8').write(build_feed_xml(items))
    pages = [''] + sorted(os.path.basename(p) for p in glob.glob(f'{pub}/*.html')
                          if os.path.getsize(p) > 1000 and os.path.basename(p) not in ('index.html', 'offline.html'))
    last = items[0]['updated'][:10] if items else None
    open(f'{pub}/sitemap.xml', 'w', encoding='utf8').write(build_sitemap_xml(pages, lastmod=last))
    return len(items)

"""feed.xml (Atom) + sitemap.xml: parse bằng xml.etree, trường bắt buộc, escape. Offline, dữ liệu mẫu."""
import json, os, sys, tempfile
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import extras
A = '{http://www.w3.org/2005/Atom}'; S = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
NASTY = 'Tom & Jerry <script>"x"</script> \'y\''
with tempfile.TemporaryDirectory() as root:
    os.makedirs(f'{root}/store'); os.makedirs(f'{root}/public')
    def day(d, arts): json.dump(dict(date=d, articles=arts), open(f'{root}/store/{d}.json', 'w', encoding='utf8'))
    day('2026-11-21', [dict(id=f'o{i}', sid=f'o{i}', title=f'Old {i}', url=f'https://e.com/o?i={i}&x=1', published=f'2026-11-{10 + i % 10}T08:00:00Z', summary='s', source='S') for i in range(30)])
    day('2026-11-22', [dict(id='n1', sid='n1', title=NASTY, url='https://e.com/a?b=1&c="2"', published='2026-11-22T09:00:00Z', summary='<b>&</b>', source='A&B'),
                       dict(id='n2', sid='n2', title='No date', url='https://e.com/n2', summary='', source='')])
    open(f'{root}/public/desk-ai.html', 'w').write('x' * 2000)
    assert extras.build_feed(root) == 20
    t = ET.parse(f'{root}/public/feed.xml').getroot()
    assert t.tag == A + 'feed' and t.find(A + 'id') is not None and t.find(A + 'title') is not None and t.find(A + 'updated') is not None
    es = t.findall(A + 'entry'); assert len(es) == 20
    for e in es:
        for k in ('id', 'title', 'updated', 'summary'): assert (e.find(A + k).text or '').strip(), k
        assert e.find(A + 'link').get('href').startswith('https://')
    assert len({e.find(A + 'id').text for e in es}) == 20
    ups = [e.find(A + 'updated').text for e in es]; assert ups == sorted(ups, reverse=True)
    top = es[0]
    assert top.find(A + 'title').text == NASTY and top.find(A + 'link').get('href') == 'https://e.com/a?b=1&c="2"'
    assert top.find(A + 'summary').text == '<b>&</b>' and top.find(A + 'source/' + A + 'title').text == 'A&B'
    assert '<script>' not in open(f'{root}/public/feed.xml', encoding='utf8').read()
    sm = ET.parse(f'{root}/public/sitemap.xml').getroot()
    locs = [u.find(S + 'loc').text for u in sm.findall(S + 'url')]
    assert extras.SITE_URL in locs and extras.SITE_URL + 'desk-ai.html' in locs and not any('offline' in l for l in locs), locs
print('test_feed_xml: OK')

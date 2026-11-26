#!/usr/bin/env python3
"""Knowledge base của Bản Tin (K2+K3): gom bài thành *câu chuyện* qua nhiều ngày, đánh dấu new/update/repeat, nhớ thực thể + nguồn.
Chỉ tin công khai, KHÔNG PII → lưu ở knowledge/kb/ (jsonl/json, diff được). Thuật toán chữ ký trùng khít web/dedup.js (test parity).
  python3 kb.py backfill      # chạy lại toàn bộ store/ theo thứ tự ngày, ghi status vào store/*.json + KB
  python3 kb.py query "godot 4.6"   # câu chuyện liên quan
  python3 kb.py stats"""
import os, re, sys, json, hashlib, datetime, tomllib, unicodedata

ROOT = os.path.dirname(os.path.abspath(__file__))
KBDIR = os.path.normpath(os.path.join(ROOT, '..', 'knowledge', 'kb'))
STOP = set('the a an of to in on for and or with is are was be at by from as it this that how why what new show ask now you your we our vs via into over after about not no more than using use can will just get'.split())
CAP_STOP = {'The', 'How', 'Why', 'What', 'New', 'Show', 'Ask', 'When', 'Who', 'This', 'That', 'Your', 'You', 'Our', 'Introducing', 'Announcing', 'Now', 'After', 'Before'}
TOK = re.compile(r'[^\W_]+(?:[.\-][^\W_]+)*')
YEAR = re.compile(r'^(19|20)\d\d$')

def cfg():
    return tomllib.load(open(f'{ROOT}/config/dedup.toml', 'rb'))

def nfc(s): return unicodedata.normalize('NFC', s or '')
def toks(s): return [t for t in TOK.findall(nfc(s).lower())]
def keytoks(s):
    """Token định danh câu chuyện: bỏ từ dừng và token có chữ số (số/phiên bản là *fact* đổi theo diễn biến, không phải danh tính). Quá ngắn → dùng cả số."""
    t = [x for x in toks(s) if x not in STOP and len(x) > 1]; k = [x for x in t if not re.search(r'\d', x)]
    return k if len(k) >= 2 else t

def fnv(t):
    h = 0x811c9dc5
    for b in t.encode('utf8'): h = ((h ^ b) * 0x01000193) & 0xffffffff
    return h

def simhash(ts):
    v = [0] * 32
    for t in set(ts):
        h = fnv(t)
        for i in range(32): v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(32) if v[i] > 0)

def ham(a, b): return bin(a ^ b).count('1')

def facts(text):
    """Con số/phiên bản/mã có chữ số, trừ năm và số 1 chữ số — thứ đổi khi một tin *có diễn biến mới*."""
    return sorted({t for t in toks(text) if re.search(r'\d', t) and not YEAR.match(t) and not (len(t) == 1)})

def entities(text):
    out = set()
    for t in TOK.findall(nfc(text)):
        if len(t) >= 3 and 'A' <= t[0] <= 'Z' and t not in CAP_STOP: out.add(t.lower())
    return sorted(out)

def canon(url):
    import urllib.parse as up
    u = up.urlsplit(url)
    q = [p for p in up.parse_qsl(u.query) if not p[0].startswith('utm_')]
    return up.urlunsplit((u.scheme, u.netloc.lower().removeprefix('www.'), u.path.rstrip('/'), up.urlencode(q), ''))

def sig(a):
    kt = keytoks(a['title'])
    return dict(kt=kt, h=simhash(kt), f=facts(a['title'] + ' ' + (a.get('summary') or '')), e=entities(a['title']))

def jac(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a and b else 0.0

def same_story(s1, s2, c):
    j = jac(s1['kt'], s2['kt']); m = c['match']
    if j >= m['jaccard_strong']: return True
    if ham(s1['h'], s2['h']) <= m['hamming_max'] and j >= m['jaccard_min_hamming']: return True
    return j >= m['jaccard_weak'] and len(set(s1['e']) & set(s2['e'])) >= m['shared_entities']

# ---------- kho ----------
def load(d=KBDIR):
    p = f'{d}/stories.jsonl'
    stories = [json.loads(l) for l in open(p, encoding='utf8') if l.strip()] if os.path.exists(p) else []
    return dict(stories={s['sid']: s for s in stories}, sources=json.load(open(f'{d}/sources.json', encoding='utf8')) if os.path.exists(f'{d}/sources.json') else {})

def save(kb, d=KBDIR):
    os.makedirs(d, exist_ok=True)
    ss = sorted(kb['stories'].values(), key=lambda s: (s['first'], s['sid']))
    open(f'{d}/stories.jsonl', 'w', encoding='utf8').write(''.join(json.dumps(s, ensure_ascii=False, separators=(',', ':')) + '\n' for s in ss))
    ents = {}
    for s in ss:
        for e in s.get('ents', []):
            x = ents.setdefault(e, dict(n=0, last='', sids=[])); x['n'] += 1; x['last'] = max(x['last'], s['last']); x['sids'].append(s['sid'])
    for x in ents.values(): x['sids'] = x['sids'][-10:]
    json.dump(dict(sorted(ents.items())), open(f'{d}/entities.json', 'w', encoding='utf8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(dict(sorted(kb['sources'].items())), open(f'{d}/sources.json', 'w', encoding='utf8'), ensure_ascii=False, indent=1)

def sdate(s, k): return min(e['d'] for e in s['entries']) if k == 'first' else max(e['d'] for e in s['entries'])

def prune(kb, today, c):
    """Hết hạn + nén: bỏ story quá ttl; mục cũ chỉ giữ ngày/url/rev; trần số mục."""
    k = c['kb']; cut = (datetime.date.fromisoformat(today) - datetime.timedelta(days=k['ttl_days'])).isoformat()
    slim = (datetime.date.fromisoformat(today) - datetime.timedelta(days=k['slim_after_days'])).isoformat()
    for sid in list(kb['stories']):
        s = kb['stories'][sid]
        if s['last'] < cut: del kb['stories'][sid]; continue
        for e in s['entries']:
            if e['d'] < slim: e.pop('title', None); e.pop('f', None); e.pop('h', None); e.pop('kt', None)
        if len(s['entries']) > k['max_entries']: s['entries'] = s['entries'][:1] + s['entries'][-(k['max_entries'] - 1):]
    kb['sources'] = {n: dict(v, days={d: x for d, x in v['days'].items() if d >= slim}) for n, v in kb['sources'].items()}

def rollback(kb, date):
    """Bỏ mọi mục từ ngày `date` trở đi → chạy lại cùng ngày cho kết quả y hệt (idempotent)."""
    for sid in list(kb['stories']):
        s = kb['stories'][sid]; s['entries'] = [e for e in s['entries'] if e['d'] < date]
        if not s['entries']: del kb['stories'][sid]
        else: s['first'], s['last'], s['rev'] = sdate(s, 'first'), sdate(s, 'last'), max(e['rev'] for e in s['entries'])
    for v in kb['sources'].values(): v['days'].pop(date, None)

def _story_view(s):
    """Chữ ký gộp của story để so khớp: dùng mục mới nhất còn tiêu đề."""
    last = [e for e in s['entries'] if 'kt' in e][-1:] or s['entries'][-1:]
    e = last[0]
    return dict(kt=e.get('kt') or keytoks(e.get('title', '')), h=e.get('h', 0), e=s.get('ents', []))

def ingest(kb, arts, date, c=None):
    """Gắn sid/status/rev/related cho từng bài (sửa tại chỗ). status: new | update | repeat."""
    c = c or cfg(); rollback(kb, date)
    prior = dict(kb['stories'])                       # chỉ ngày < date
    cache = {sid: _story_view(s) for sid, s in prior.items()}
    by_url = {}
    for sid, s in prior.items():
        for e in s['entries']: by_url[canon(e['url'])] = sid
    idx = {}                                          # token → sid (lọc ứng viên)
    for sid, v in cache.items():
        for t in v['kt']: idx.setdefault(t, set()).add(sid)
    today_new = {}                                    # story tạo trong ngày này: sid → view
    for a in arts:
        sg = sig(a); cu = canon(a['url']); sid = by_url.get(cu)
        if not sid:
            cand = {}
            for t in sg['kt']:
                for x in idx.get(t, ()): cand[x] = cand.get(x, 0) + 1
            for x in sorted(cand, key=lambda y: -cand[y]):
                if cand[x] >= 2 and same_story(sg, cache[x], c): sid = x; break
        if not sid:
            for x, v in today_new.items():   # cùng ngày: hai bài có fact khác hẳn nhau (Jan 19 vs Feb 22) là hai việc, không gộp
                if same_story(sg, v, c) and not (sg['f'] and v['f'] and not set(sg['f']) & set(v['f'])): sid = x; break
        status, note = 'new', ''
        if sid and sid in prior:
            s = prior[sid]; known = {f for e in s['entries'] for f in e.get('f', [])}
            newf = [f for f in sg['f'] if f not in known]
            same_url = any(canon(e['url']) == cu for e in s['entries'])
            ptitle = [e for e in s['entries'] if 'kt' in e and canon(e['url']) == cu][-1:]
            dist = 1 - jac(sg['kt'], ptitle[0]['kt']) if (same_url and ptitle) else 0.0
            if newf or (same_url and dist >= c['update']['text_distance']):
                status = 'update'; note = ('Mới: ' + ', '.join(newf[:3])) if newf else 'Nội dung đổi đáng kể'
            else: status = 'repeat'
            rev = s['rev'] + (1 if status == 'update' else 0)
        else:
            rev = 0
            if not sid:
                sid = hashlib.sha1(cu.encode()).hexdigest()[:10]
                today_new[sid] = sg
                s = kb['stories'][sid] = dict(sid=sid, first=date, last=date, rev=0, title=a['title'][:140], topics=a.get('topics', []), ents=sg['e'], entries=[])
            else: s = kb['stories'][sid]
        s = kb['stories'][sid]
        s['rev'] = max(s['rev'], rev) if sid in prior else s['rev']
        s['last'] = date; s['ents'] = sorted(set(s.get('ents', [])) | set(sg['e']))[:12]
        s['entries'].append(dict(d=date, url=a['url'], src=a.get('source', ''), title=a['title'][:140], kt=sg['kt'], h=sg['h'], f=sg['f'], rev=s['rev'], st=status))
        a.update(sid=sid, status=status, rev=s['rev'])
        if note: a['update_note'] = note
        else: a.pop('update_note', None)
    # liên quan trước đó: story cũ (ngày < date) chung ≥2 thực thể, hoặc ≥1 thực thể + chủ đề
    for a in arts:
        if a['status'] == 'repeat': continue
        ents = set(entities(a['title'])); rel = []
        for sid, s in prior.items():
            if sid == a['sid']: continue
            n = len(ents & set(s.get('ents', [])))
            if n >= 2 or (n >= 1 and set(a.get('topics', [])) & set(s.get('topics', []))): rel.append((n, s['last'], sid, s['title'], s['first']))
        rel.sort(reverse=True); a['related'] = [dict(sid=r[2], title=r[3], d=r[4]) for r in rel[:c['kb']['related_max']]]
        if not a['related']: a.pop('related')
    for a in arts:
        v = kb['sources'].setdefault(a.get('source', '?'), dict(days={})); d = v['days'].setdefault(date, dict(n=0, new=0, update=0, repeat=0))
        d['n'] += 1; d[a['status']] += 1
    for s in kb['stories'].values(): s['first'], s['last'] = sdate(s, 'first'), sdate(s, 'last')
    prune(kb, date, c)
    return dict(n=len(arts), **{k: sum(a['status'] == k for a in arts) for k in ('new', 'update', 'repeat')})

def query(kb, text, n=5):
    sg = dict(kt=keytoks(text), e=entities(text)); out = []
    for s in kb['stories'].values():
        v = _story_view(s); sc = jac(sg['kt'], v['kt']) + 0.3 * len(set(sg['e']) & set(s.get('ents', [])))
        if sc > 0.1: out.append((sc, s))
    out.sort(key=lambda x: (-x[0], x[1]['last'])); return [dict(sid=s['sid'], title=s['title'], first=s['first'], last=s['last'], rev=s['rev'], days=len({e['d'] for e in s['entries']})) for _, s in out[:n]]

def backfill():
    kb = dict(stories={}, sources={}); fs = sorted(f for f in os.listdir(f'{ROOT}/store') if re.fullmatch(r'\d{4}-\d\d-\d\d\.json', f))
    for f in fs:
        p = f'{ROOT}/store/{f}'; day = json.load(open(p, encoding='utf8')); r = ingest(kb, day['articles'], day['date'])
        json.dump(day, open(p, 'w', encoding='utf8'), ensure_ascii=False, indent=1); print(f, r)
    save(kb)

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'stats'
    if cmd == 'backfill': backfill()
    elif cmd == 'query': print(json.dumps(query(load(), ' '.join(sys.argv[2:])), ensure_ascii=False, indent=1))
    else:
        kb = load(); print(f"{len(kb['stories'])} câu chuyện, {sum(len(s['entries']) for s in kb['stories'].values())} mục, {len(kb['sources'])} nguồn")

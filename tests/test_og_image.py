#!/usr/bin/env python3
"""og:image lúc build — test offline bằng HTML mẫu: parser, URL tương đối → tuyệt đối, cache, giới hạn, lỗi không sập. Không mạng."""
import os, sys, json, time, tempfile, shutil, threading
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import ogimg as O
ok = []
def chk(n, v): ok.append((n, bool(v))); print(('PASS ' if v else 'FAIL ') + n)
P = O.parse_og
B = 'https://news.example.com/2026/post/a'
chk('og:image tuyệt đối', P('<head><meta property="og:image" content="https://cdn.example.com/a.jpg"></head>', B) == 'https://cdn.example.com/a.jpg')
chk('đảo thứ tự thuộc tính (content trước property)', P('<meta content="https://c.example.com/x.png" property="og:image"/>', B) == 'https://c.example.com/x.png')
chk('dấu nháy đơn + name=', P("<meta name='twitter:image' content='https://c.example.com/t.jpg'>", B) == 'https://c.example.com/t.jpg')
chk('twitter:image:src', P('<meta name="twitter:image:src" content="https://c.example.com/s.jpg">', B) == 'https://c.example.com/s.jpg')
chk('og:image ưu tiên hơn twitter:image', P('<meta name="twitter:image" content="https://c.example.com/t.jpg"><meta property="og:image" content="https://c.example.com/o.jpg">', B) == 'https://c.example.com/o.jpg')
chk('og:image:secure_url', P('<meta property="og:image:secure_url" content="https://c.example.com/sec.jpg">', B) == 'https://c.example.com/sec.jpg')
chk('URL gốc-tuyệt-đối-đường-dẫn → tuyệt đối', P('<meta property="og:image" content="/img/a.jpg">', B) == 'https://news.example.com/img/a.jpg')
chk('URL tương đối → tuyệt đối', P('<meta property="og:image" content="../img/b.jpg">', B) == 'https://news.example.com/2026/img/b.jpg')
chk('URL // → https', P('<meta property="og:image" content="//cdn.example.com/c.jpg">', B) == 'https://cdn.example.com/c.jpg')
chk('&amp; được giải mã', P('<meta property="og:image" content="https://c.example.com/i?a=1&amp;b=2">', B) == 'https://c.example.com/i?a=1&b=2')
chk('trang nền http: ảnh tương đối không thành https giả', P('<meta property="og:image" content="/a.jpg">', 'http://old.example.com/p') == '')
chk('không có thẻ → rỗng', P('<html><head><title>x</title></head></html>', B) == '')
chk('og:image rỗng → rỗng', P('<meta property="og:image" content="">', B) == '')
chk('bỏ ảnh rác (logo/svg)', P('<meta property="og:image" content="https://c.example.com/logo.png">', B) == '' and P('<meta property="og:image" content="https://c.example.com/a.svg">', B) == '')
chk('scheme lạ (javascript:/data:) bị bỏ', P('<meta property="og:image" content="javascript:alert(1)">', B) == '' and P('<meta property="og:image" content="data:image/png;base64,AAAA">', B) == '')
chk('og lỗi nhưng twitter hợp lệ → dùng twitter', P('<meta property="og:image" content="data:x"><meta name="twitter:image" content="https://c.example.com/t.jpg">', B) == 'https://c.example.com/t.jpg')
chk('fetch_og: scheme không phải http(s) → rỗng, không ném', O.fetch_og('file:///etc/passwd') == '' and O.fetch_og('ftp://x/y') == '' and O.fetch_og('') == '')
chk('fetch_og: lỗi mạng → rỗng, không ném', O.fetch_og('http://127.0.0.1:1/x', timeout=1) == '')

tmp = tempfile.mkdtemp()
try:
    calls = []; lock = threading.Lock()
    def fake(u):
        with lock: calls.append(u)
        if 'boom' in u: raise RuntimeError('x')
        return '' if 'none' in u else f'https://img.example.com/{abs(hash(u)) % 999}.jpg'
    def mk(): return [dict(url='https://a.example.com/1'), dict(url='https://a.example.com/none'), dict(url='https://a.example.com/boom'),
                      dict(url='https://a.example.com/has', img='https://k.example.com/keep.jpg'), dict(url='https://a.example.com/1')]
    A = mk(); n, net = O.fill_images(A, tmp, 90, fetcher=fake)
    chk('gắn ảnh cho bài thiếu; giữ ảnh có sẵn', A[0]['img'].startswith('https://img.example.com/') and A[3]['img'] == 'https://k.example.com/keep.jpg')
    chk('lỗi/không có ảnh → img vẫn rỗng, không sập', not A[1].get('img') and not A[2].get('img'))
    chk('url trùng chỉ tải 1 lần; bài có ảnh không tải', sorted(calls) == sorted(set(calls)) and 'https://a.example.com/has' not in calls and net == 3)
    cp = f'{tmp}/store/og/cache.json'
    chk('cache nằm trong store/og/ (không lẫn store/*.json của ngày)', os.path.exists(cp) and not [f for f in os.listdir(f'{tmp}/store') if f.endswith('.json')])
    calls.clear(); B2 = mk(); n2, net2 = O.fill_images(B2, tmp, 90, fetcher=fake)
    chk('lần 2: 0 request (kể cả kết quả rỗng/lỗi đã cache), ảnh vẫn được gắn', not calls and net2 == 0 and B2[0]['img'] == A[0]['img'])
    open(cp, 'w').write('{hỏng'); calls.clear()
    chk('cache hỏng → bỏ qua, tải lại, không sập', O.fill_images(mk(), tmp, 90, fetcher=fake)[1] == 3)
    # giới hạn số bài
    shutil.rmtree(f'{tmp}/store'); calls.clear()
    O.fill_images([dict(url=f'https://z.example.com/{i}') for i in range(50)], tmp, 10, fetcher=fake)
    chk('limit số bài', len(calls) == 10)
    # song song ≤ 6
    shutil.rmtree(f'{tmp}/store'); cur = [0]; peak = [0]
    def slow(u):
        with lock: cur[0] += 1; peak[0] = max(peak[0], cur[0])
        time.sleep(0.05)
        with lock: cur[0] -= 1
        return ''
    O.fill_images([dict(url=f'https://p.example.com/{i}') for i in range(30)], tmp, 90, fetcher=slow)
    chk('song song ≤ 6 (đỉnh %d)' % peak[0], 1 < peak[0] <= 6)
    # tổng ngân sách
    shutil.rmtree(f'{tmp}/store'); t0 = time.monotonic()
    def hang(u): time.sleep(3); return 'https://img.example.com/h.jpg'
    C = [dict(url=f'https://h.example.com/{i}') for i in range(12)]
    O.fill_images(C, tmp, 90, fetcher=hang, budget=0.5)
    chk('hết ngân sách → trả về đúng hạn, bài chưa xong không gắn ảnh và không vào cache', time.monotonic() - t0 < 2 and not any(a.get('img') for a in C) and not O.load_cache(tmp))
    chk('hằng số đúng yêu cầu', (O.TIMEOUT, O.MAX_BYTES, O.WORKERS, O.BUDGET) == (4, 1_000_000, 6, 40))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
bad = [n for n, v in ok if not v]
print(f'{len(ok) - len(bad)}/{len(ok)} đạt'); sys.exit(1 if bad else 0)

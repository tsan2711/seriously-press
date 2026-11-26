#!/usr/bin/env python3
"""Trần thời gian build + cache điều kiện feed. OFFLINE: mọi urlopen bị thay bằng bản giả (chậm hoặc dữ liệu mẫu); ghi vào thư mục tạm."""
import os, sys, time, json, shutil, tempfile, io, urllib.error, contextlib
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import press, kb as KB
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)

tmp = tempfile.mkdtemp()
try:
    shutil.copytree(f'{d}/../config', f'{tmp}/config'); os.makedirs(f'{tmp}/store')
    press.ROOT = tmp; KB.KBDIR = f'{tmp}/kb'
    RSS = b'<rss><channel><item><title>Bai thu nghiem</title><link>https://example.com/a</link><description>mo ta</description></item></channel></rss>'

    # 1) Nguồn chậm: mọi request treo SLOW giây → fetch phải xong trong trần, ghi cảnh báo, không treo
    SLOW = 12
    class Slow:
        def __init__(s, *a, **k): time.sleep(SLOW); raise urllib.error.URLError('slow')
    real = urllib.request.urlopen; urllib.request.urlopen = lambda *a, **k: Slow()
    press.NET_BUDGET, press.CAP_FEEDS, press.CAP_TREND = 6, 2, 1
    t0 = time.monotonic(); buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf): press.fetch('2026-11-23')
    finally: urllib.request.urlopen = real
    dt = time.monotonic() - t0; out = buf.getvalue()
    chk(f'nguồn chậm {SLOW}s/request: fetch xong trong trần ({dt:.1f}s ≤ {press.NET_BUDGET + 3}s, không đợi {SLOW}s)', dt <= press.NET_BUDGET + 3)
    chk('có cảnh báo nguồn bị bỏ do hết trần', any('nguồn:' in w and 'bỏ' in w for w in press.WARNS) and 'CẢNH BÁO' in out)
    chk('ghi store/<ngày>.json dù nguồn chậm', os.path.isfile(f'{tmp}/store/2026-11-23.json'))
    chk('in đúng một dòng tổng thời gian có từng giai đoạn', press.time_line().count('\n') == 0 and all(k in press.time_line() for k in ('nguồn', 'ảnh', 'mạng')))

    # 2) Cache điều kiện: lần 1 lưu ETag/Last-Modified; lần 2 gửi If-None-Match → 304 → dùng bản cũ
    c = {}; seen = []
    def op(url, h):
        seen.append(dict(h))
        if h.get('If-None-Match') == '"v1"': raise urllib.error.HTTPError(url, 304, 'Not Modified', {}, None)
        return RSS, dict(etag='"v1"', lm='Mon, 23 Nov 2026 00:00:00 GMT')
    b1 = press.http_cond('https://example.com/feed', c, op)
    b2 = press.http_cond('https://example.com/feed', c, op)
    chk('lần 1 không gửi điều kiện, lưu etag + last-modified', seen[0] == {} and c['https://example.com/feed']['etag'] == '"v1"' and c['https://example.com/feed']['lm'])
    chk('lần 2 gửi If-None-Match + If-Modified-Since', seen[1].get('If-None-Match') == '"v1"' and 'If-Modified-Since' in seen[1])
    chk('304 → dùng đúng bản cũ trong store/', b1 == RSS and b2 == RSS and os.path.isdir(f'{tmp}/store/feeds'))
    def bad304(url, h): raise urllib.error.HTTPError(url, 304, 'Not Modified', {}, None)
    shutil.rmtree(f'{tmp}/store/feeds')
    try: press.http_cond('https://example.com/feed', c, bad304); r304 = False
    except urllib.error.HTTPError: r304 = True
    chk('304 nhưng mất bản cũ → ném lỗi (không dùng dữ liệu rỗng)', r304)
    def e500(url, h): raise urllib.error.HTTPError(url, 500, 'x', {}, None)
    try: press.http_cond('https://example.com/other', {}, e500); r5 = False
    except urllib.error.HTTPError: r5 = True
    chk('lỗi khác 304 vẫn ném', r5)

    # 3) par_map: job treo bị bỏ đúng hạn, job nhanh giữ kết quả, thứ tự giữ nguyên
    t0 = time.monotonic()
    r = press.par_map(lambda x: (time.sleep(x), x)[1], [0, 8, 0], 3, 1.5)
    chk('par_map: job treo bị bỏ sau ~trần, job nhanh còn nguyên', time.monotonic() - t0 < 3 and r[0] == (0, None) and r[2] == (0, None) and r[1][1] == 'hết trần thời gian')
    chk('net_left không âm, cap được tôn trọng', press.net_left(0.5) <= 0.5 and press.net_left() >= 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print('OK' if all(ok) else 'FAIL'); sys.exit(0 if all(ok) else 1)

#!/usr/bin/env python3
"""Kiểm ảnh + dedup — offline, byte mẫu."""
import os, sys, struct, tempfile, json
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import imgcache as C
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)

def png(w, h): return b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', w, h) + b'\x08\x02\x00\x00\x00' + b'\0' * 20
def gif(w, h): return b'GIF89a' + struct.pack('<HH', w, h) + b'\0' * 20
def jpg(w, h): return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00' + b'\0' * 14 + b'\xff\xdb\x00\x05\0\0\0' + b'\xff\xc0\x00\x11\x08' + struct.pack('>HH', h, w) + b'\x03' + b'\0' * 9
def webp_x(w, h): return b'RIFF\0\0\0\0WEBPVP8X' + b'\x0a\0\0\0' + b'\0\0\0\0' + (w - 1).to_bytes(3, 'little') + (h - 1).to_bytes(3, 'little')
def webp_l(w, h): return b'RIFF\0\0\0\0WEBPVP8L' + b'\0\0\0\0' + b'\x2f' + (((h - 1) << 14) | (w - 1)).to_bytes(4, 'little')
def webp_s(w, h): return b'RIFF\0\0\0\0WEBPVP8 ' + b'\0\0\0\0' + b'\0\0\0' + b'\x9d\x01\x2a' + struct.pack('<HH', w, h)

for n, f in (('png', png), ('gif', gif), ('jpeg', jpg), ('webp-x', webp_x), ('webp-l', webp_l), ('webp-lossy', webp_s)):
    chk(f'kích thước {n}', C.size_of(f(640, 480)) == (640, 480))
chk('rác → None', C.size_of(b'hello world') is None and C.size_of(b'') is None and C.size_of(png(5, 5)[:10]) is None)
# JPEG có đoạn APP lớn phía trước SOF
big = b'\xff\xd8\xff\xe1' + struct.pack('>H', 2000) + b'\0' * 1998 + jpg(800, 600)[2:]
chk('jpeg bỏ qua APP1 lớn', C.size_of(big) == (800, 600))

J = C.judge
chk('ảnh tốt', J('image/png', png(800, 600))['ok'])
chk('content-type có charset/hoa', J('Image/JPEG; x=1', jpg(800, 600))['ok'])
chk('text/html → loại', J('text/html', png(800, 600)) == dict(ok=False, why='not-image'))
chk('không content-type → loại', not J('', png(800, 600))['ok'])
chk('không đọc được size → loại', J('image/png', b'xx')['why'] == 'no-size')
chk('<300 rộng → loại', J('image/png', png(299, 600))['why'] == 'small')
chk('<300 cao → loại', J('image/png', png(800, 299))['why'] == 'small')
chk('đúng 300 → qua', J('image/png', png(300, 300))['ok'])
chk('4:1 → qua', J('image/png', png(1600, 400))['ok'])
chk('>4:1 → loại', J('image/png', png(1604, 400))['why'] == 'ratio')
chk('1:2 → qua', J('image/png', png(400, 800))['ok'])
chk('<1:2 → loại', J('image/png', png(400, 810))['why'] == 'ratio')

chk('norm bỏ utm/fbclid/fragment/www', C.norm_url('https://WWW.a.com/x.jpg?utm_source=t&fbclid=1&w=5#f') == C.norm_url('https://a.com/x.jpg?w=5'))
chk('norm giữ query khác', C.norm_url('https://a.com/x.jpg?w=5') != C.norm_url('https://a.com/x.jpg?w=6'))

root = tempfile.mkdtemp(); calls = []
IMGS = {'https://a.com/good.png': ('image/png', png(800, 600)), 'https://a.com/tiny.png': ('image/png', png(50, 50)),
        'https://a.com/page': ('text/html', b'<html>'), 'https://a.com/wide.jpg': ('image/jpeg', jpg(3000, 300))}
def fetch(u):
    calls.append(u)
    if u in IMGS: return IMGS[u]
    raise OSError('net')
arts = [dict(id=str(i), img=u) for i, u in enumerate(['https://a.com/good.png', 'https://a.com/tiny.png', 'https://a.com/page', 'https://a.com/wide.jpg',
        'https://www.a.com/good.png?utm_source=x', 'https://a.com/good.png#z', 'https://a.com/good.png', 'https://a.com/down.png'])]
arts[1]['img_credit'] = 'c'
r = C.clean(arts, root, fetch)
chk('loại 3 hỏng', r['bad'] == 3 and all('img' not in arts[i] for i in (1, 2, 3)))
chk('giữ 2 bài đầu, bài 3,4 chuyển dự phòng', arts[0].get('img') and arts[4].get('img') and 'img' not in arts[5] and 'img' not in arts[6])
chk('dup đếm đúng', r['dup'] == 2)
chk('bài bị gỡ ghi img_bad, xoá credit', arts[5]['img_bad'] == ['https://a.com/good.png#z'] and 'img_credit' not in arts[1])
chk('lỗi mạng → giữ ảnh, không cache', arts[7]['img'] == 'https://a.com/down.png' and 'https://a.com/down.png' not in json.load(open(f'{root}/store/og/validate.json')))
n = len(calls); C.clean([dict(img='https://a.com/good.png'), dict(img='https://a.com/tiny.png')], root, fetch)
chk('cache: không tải lại URL đã kiểm', len(calls) == n)
chk('cache nhớ cả kết quả loại', json.load(open(f'{root}/store/og/validate.json'))['https://a.com/tiny.png']['why'] == 'small')
chk('bài không ảnh không lỗi', C.clean([dict(id='x')], root, fetch) == dict(bad=0, dup=0))
print(f'{sum(ok)}/{len(ok)}'); sys.exit(0 if all(ok) else 1)

#!/usr/bin/env python3
"""Ảnh từ chính feed RSS/Atom — offline, feed mẫu."""
import os, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import press as P
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)
F = dict(name='S', id='s')
def rss(body, ns=''):
    return f'<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item><title>T</title><link>https://n.example.com/a</link>{body}</item></channel></rss>'.encode()
def atom(body):
    return f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/"><entry><title>T</title><link href="https://n.example.com/a"/>{body}</entry></feed>'.encode()
def img(raw): return P.parse_feed(raw, F)[0]['img']
chk('RSS media:thumbnail', img(rss('<media:thumbnail url="https://c.example.com/t.jpg"/>')) == 'https://c.example.com/t.jpg')
chk('RSS media:content medium=image', img(rss('<media:content url="https://c.example.com/m.jpg" medium="image"/>')) == 'https://c.example.com/m.jpg')
chk('media:content video bị bỏ', img(rss('<media:content url="https://c.example.com/v.mp4" medium="video"/>')) == '')
chk('RSS enclosure image/*', img(rss('<enclosure url="https://c.example.com/e.jpg" type="image/jpeg"/>')) == 'https://c.example.com/e.jpg')
chk('enclosure audio bị bỏ', img(rss('<enclosure url="https://c.example.com/e.mp3" type="audio/mpeg"/>')) == '')
chk('<img> đầu trong content:encoded (description không có ảnh)', img(rss('<description>chỉ chữ</description><content:encoded><![CDATA[<p>x</p><img src="https://c.example.com/ce.jpg">]]></content:encoded>')) == 'https://c.example.com/ce.jpg')
chk('<img> trong description', img(rss('<description><![CDATA[<img src="https://c.example.com/d.jpg"> hi]]></description>')) == 'https://c.example.com/d.jpg')
chk('ưu tiên media hơn <img> thân', img(rss('<description><![CDATA[<img src="https://c.example.com/d.jpg">]]></description><media:thumbnail url="https://c.example.com/t.jpg"/>')) == 'https://c.example.com/t.jpg')
chk('http bị bỏ', img(rss('<media:thumbnail url="http://c.example.com/t.jpg"/>')) == '')
chk('IMG_BAD (logo) bị bỏ, rơi sang ảnh hợp lệ', img(rss('<media:thumbnail url="https://c.example.com/logo.png"/><description><![CDATA[<img src="https://c.example.com/ok.jpg">]]></description>')) == 'https://c.example.com/ok.jpg')
chk('Atom media:thumbnail', img(atom('<media:thumbnail url="https://c.example.com/at.jpg"/>')) == 'https://c.example.com/at.jpg')
chk('Atom media:group > media:content', img(atom('<media:group><media:content url="https://c.example.com/g.jpg" type="image/jpeg"/></media:group>')) == 'https://c.example.com/g.jpg')
chk('Atom summary html escape', img(atom('<summary type="html">&lt;img src="https://c.example.com/s.jpg"&gt;</summary>')) == 'https://c.example.com/s.jpg')
chk('Atom content', img(atom('<content type="html">&lt;p&gt;&lt;img src="https://c.example.com/c.jpg"&gt;&lt;/p&gt;</content>')) == 'https://c.example.com/c.jpg')
chk('Atom link rel=enclosure không bị coi là ảnh bừa', img(atom('')) == '')
# fill_images: bài đã có img từ feed không bị og ghi đè / không tải
import ogimg, tempfile
arts = [dict(url='https://n.example.com/a', img='https://c.example.com/f.jpg'), dict(url='https://n.example.com/b', img='')]
calls = []
def fake(u): calls.append(u); return 'https://c.example.com/og.jpg'
ogimg.fill_images(arts, tempfile.mkdtemp(), 90, fetcher=fake)
chk('feed img giữ nguyên, không tải trang bài đó', arts[0]['img'] == 'https://c.example.com/f.jpg' and calls == ['https://n.example.com/b'])
chk('thiếu → og', arts[1]['img'] == 'https://c.example.com/og.jpg')
sys.exit(0 if all(ok) else 1)

#!/usr/bin/env python3
"""Ảnh đầu tiên trong thân bài khi không có og:image — offline, HTML mẫu."""
import os, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import ogimg as O
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)
B = 'https://news.example.com/2026/post/a'
P = O.parse_page
chk('có og → dùng og, không đụng thân bài', P('<meta property="og:image" content="https://c.example.com/o.jpg"><article><img src="https://c.example.com/b.jpg" width="800" height="400"></article>', B) == 'https://c.example.com/o.jpg')
chk('không og → ảnh lớn đầu tiên', P('<article><p>x</p><img src="https://c.example.com/b.jpg" width="800" height="400"></article>', B) == 'https://c.example.com/b.jpg')
chk('ảnh nhỏ bị bỏ, lấy ảnh sau', P('<article><img src="https://c.example.com/s.jpg" width="120" height="90"><img src="https://c.example.com/big.jpg" width="640"></article>', B) == 'https://c.example.com/big.jpg')
chk('chỉ ảnh nhỏ → rỗng', P('<article><img src="https://c.example.com/s.jpg" width="299" height="900"></article>', B) == '')
chk('không rõ kích thước → bỏ', P('<article><img src="https://c.example.com/u.jpg"></article>', B) == '')
chk('srcset: lấy bản lớn nhất', P('<article><img src="https://c.example.com/t.jpg" srcset="https://c.example.com/a.jpg 400w, https://c.example.com/c.jpg 1200w, https://c.example.com/b.jpg 800w"></article>', B) == 'https://c.example.com/c.jpg')
chk('srcset toàn nhỏ → bỏ', P('<article><img srcset="https://c.example.com/a.jpg 100w, https://c.example.com/b.jpg 200w"></article>', B) == '')
chk('lazy data-src (src là placeholder data:)', P('<article><img src="data:image/gif;base64,R0lGOD" data-src="https://c.example.com/lazy.jpg" width="700" height="500"></article>', B) == 'https://c.example.com/lazy.jpg')
chk('lazy data-srcset', P('<article><img data-srcset="/i/a.jpg 320w, /i/b.jpg 900w"></article>', B) == 'https://news.example.com/i/b.jpg')
chk('URL tương đối → tuyệt đối', P('<main><img src="/img/x.jpg" width="500" height="300"></main>', B) == 'https://news.example.com/img/x.jpg')
chk('chỉ https: http và data bị bỏ', P('<article><img src="http://c.example.com/x.jpg" width="500" height="300"></article>', B) == '' and P('<article><img src="data:image/png;base64,AA" width="500" height="300"></article>', B) == '')
chk('bỏ logo/avatar/sprite/banner-ad qua class/alt', P('<article><img class="site-logo" src="https://c.example.com/a.jpg" width="600" height="400"><img alt="avatar tác giả" src="https://c.example.com/b.jpg" width="600" height="400"><img class="sprite" src="https://c.example.com/c.jpg" width="600" height="400"><img class="banner-ad" src="https://c.example.com/d.jpg" width="600" height="400"><img src="https://c.example.com/ok.jpg" width="600" height="400"></article>', B) == 'https://c.example.com/ok.jpg')
chk('bỏ logo/pixel/svg qua URL', P('<article><img src="https://c.example.com/logo.png" width="600" height="400"><img src="https://c.example.com/pixel.png" width="600" height="400"><img src="https://c.example.com/a.svg" width="600" height="400"></article>', B) == '')
chk('article ưu tiên hơn ảnh đứng trước ngoài article', P('<body><div><img src="https://c.example.com/out.jpg" width="600" height="400"></div><article><img src="https://c.example.com/in.jpg" width="600" height="400"></article></body>', B) == 'https://c.example.com/in.jpg')
chk('không article/main → rơi về body', P('<body><div><img src="https://c.example.com/out.jpg" width="600" height="400"></div></body>', B) == 'https://c.example.com/out.jpg')
chk('ảnh trong header/nav/footer/aside bị bỏ', P('<body><header><img src="https://c.example.com/h.jpg" width="900" height="400"></header><aside><img src="https://c.example.com/s.jpg" width="900" height="400"></aside></body>', B) == '')
chk('HTML hỏng/rỗng không sập', P('', B) == '' and P('<article><img <<< src=', B) == '')
chk('nền http: ảnh tương đối không thành https giả', P('<article><img src="/a.jpg" width="600" height="400"></article>', 'http://old.example.com/p') == '')
sys.exit(0 if all(ok) else 1)

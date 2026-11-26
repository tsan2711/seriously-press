#!/usr/bin/env python3
"""Luật ảnh theo host — offline, bảng URL mẫu."""
import os, sys, tempfile
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, f'{d}/..')
import imgrules as R, ogimg
ok = []
def chk(n, v): ok.append(bool(v)); print(('PASS ' if v else 'FAIL ') + n)
YT = 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg'
TABLE = [
 ('https://github.com/anthropics/claude-code', 'https://opengraph.githubassets.com/1/anthropics/claude-code'),
 ('https://github.com/anthropics/claude-code/', 'https://opengraph.githubassets.com/1/anthropics/claude-code'),
 ('https://github.com/a/b?tab=readme#x', 'https://opengraph.githubassets.com/1/a/b'),
 ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', YT),
 ('https://www.youtube.com/watch?feature=x&v=dQw4w9WgXcQ&t=5s', YT),
 ('https://youtu.be/dQw4w9WgXcQ?t=3', YT),
 ('https://www.youtube.com/shorts/dQw4w9WgXcQ', YT),
 ('https://huggingface.co/meta-llama/Llama-3', 'https://cdn-thumbnails.huggingface.co/social-thumbnails/models/meta-llama/Llama-3.png'),
 ('https://huggingface.co/datasets/o/r', 'https://cdn-thumbnails.huggingface.co/social-thumbnails/datasets/o/r.png'),
 ('https://huggingface.co/spaces/o/r', 'https://cdn-thumbnails.huggingface.co/social-thumbnails/spaces/o/r.png'),
 # lạ / không có luật → rỗng
 ('https://huggingface.co/blog/foo', ''),
 ('https://huggingface.co/docs/x', ''),
 ('https://github.com/anthropics', ''),
 ('https://github.com/a/b/issues/1', ''),
 ('https://arxiv.org/abs/2401.00001', ''),
 ('https://www.reddit.com/r/x/comments/abc/t/', ''),
 ('https://example.com/a', ''), ('', ''), ('ftp://github.com/a/b', ''), ('https://notgithub.com/a/b', ''),
 ('https://evil.com/?u=https://github.com/a/b', ''),
 ('https://www.youtube.com/watch?v=short', ''),
]
for u, want in TABLE: chk(f'{u!r} → {want!r}', R.resolve(u) == want)
# wikipedia: thuần thì rỗng; remote + fetcher mẫu thì ra ảnh
W = 'https://en.wikipedia.org/wiki/Alan_Turing'
chk('wikipedia không remote → rỗng', R.resolve(W) == '')
seen = []
def fj(u): seen.append(u); return {'query': {'pages': {'123': {'thumbnail': {'source': 'https://upload.wikimedia.org/t.jpg'}}}}}
chk('wikipedia API mẫu', R.resolve(W, remote=True, fetcher=fj) == 'https://upload.wikimedia.org/t.jpg')
chk('API gọi đúng lang/title', seen and seen[0].startswith('https://en.wikipedia.org/w/api.php?') and 'titles=Alan_Turing' in seen[0])
chk('wikipedia không có ảnh → rỗng', R.resolve(W, remote=True, fetcher=lambda u: {'query': {'pages': {'-1': {}}}}) == '')
chk('wikipedia fetcher lỗi → rỗng', R.resolve(W, remote=True, fetcher=lambda u: None) == '')
chk('wikipedia ảnh http bị bỏ', R.resolve(W, remote=True, fetcher=lambda u: {'query': {'pages': {'1': {'thumbnail': {'source': 'http://x/t.jpg'}}}}}) == '')
chk('wikipedia Special: bị bỏ', R.resolve('https://en.wikipedia.org/wiki/Special:Random', remote=True, fetcher=fj) == '')
# thêm host mới chỉ bằng toml
with tempfile.TemporaryDirectory() as t:
    p = f'{t}/r.toml'
    open(p, 'w').write('[[rule]]\nname="x"\nmatch=\'https://x\\.test/(?P<id>\\d+)\'\nimage="https://img.x.test/{id}.jpg"\n')
    chk('host mới bằng một khối toml', R.resolve('https://x.test/42', rules=R.load_rules(p)) == 'https://img.x.test/42.jpg')
    chk('toml hỏng → không luật, không ném', R.load_rules(f'{t}/none.toml') == [])
# nối vào fill_images: luật trước bước tải trang
with tempfile.TemporaryDirectory() as t:
    calls = []
    arts = [dict(url='https://github.com/a/b'), dict(url='https://example.com/p'), dict(url='https://youtu.be/dQw4w9WgXcQ', img='https://c.example.com/own.jpg')]
    n, req = ogimg.fill_images(arts, t, fetcher=lambda u: calls.append(u) or '')
    chk('github có ảnh từ luật', arts[0]['img'] == 'https://opengraph.githubassets.com/1/a/b')
    chk('host lạ vẫn đi tải trang', calls == ['https://example.com/p'] and 'img' not in arts[1])
    chk('ảnh từ feed không bị luật ghi đè', arts[2]['img'] == 'https://c.example.com/own.jpg')
    chk('đếm n gồm bài từ luật', n == 1)
sys.exit(0 if all(ok) else 1)

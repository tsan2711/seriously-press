"""H7: tóm tắt meta cho bài thiếu tóm tắt (HN)."""
import sys, os, tempfile; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import ogimg
page = '<meta property="og:description" content="A looped transformer model that reuses layers to reach higher quality at small sizes.">'
assert ogimg.parse_desc(page, 'GLM') .startswith('A looped'); print('PASS meta → tóm tắt')
assert ogimg.parse_desc('<meta name="description" content="ngắn">') == ''; print('PASS quá ngắn → rỗng')
assert len(ogimg.parse_desc('<meta name="description" content="%s">' % ('word ' * 100))) <= 200; print('PASS cắt ≤ 200')
arts = [dict(url='https://x.test/a', title='T', summary=''), dict(url='https://news.ycombinator.com/item?id=1', title='Ask', summary=''), dict(url='https://x.test/b', title='B', summary='có sẵn')]
with tempfile.TemporaryDirectory() as r:
    n, q = ogimg.fill_summaries(arts, r, fetcher=lambda u, t='': 'Đoạn mô tả đủ dài để làm tóm tắt cho bài này, hơn bốn mươi ký tự.', bad=lambda s: False)
    assert n == 1 and arts[0]['summary_by'] == 'meta' and not arts[1]['summary'] and arts[2]['summary'] == 'có sẵn'; print('PASS chỉ gắn bài có URL ngoài, không đè sẵn có')
    n, q = ogimg.fill_summaries([dict(url='https://x.test/a', title='T', summary='')], r, fetcher=lambda u, t='': 1/0)
    assert q == 0; print('PASS cache, không tải lại')
print('OK test_summary_meta')

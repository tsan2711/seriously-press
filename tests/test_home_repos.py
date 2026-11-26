#!/usr/bin/env python3
"""Khối "Repo hay" trang chủ: đọc store/repos (không mạng), lùi về bản trước khi bản mới hỏng/thiếu, nằm trong lưới đã build."""
import sys, os, json, tempfile, unittest, re
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, R)
import theme

def repo(i, **k): return dict(dict(kind='trend', via='trending', name=f'o/r{i}', url=f'https://github.com/o/r{i}', stars=1000 + i, desc='mô tả', solves='giải quyết X'), **k)

class T(unittest.TestCase):
    def folder(self, **files):
        d = tempfile.mkdtemp()
        for n, v in files.items():
            with open(f'{d}/{n.replace("_", "-")[1:]}.json', 'w', encoding='utf8') as f: f.write(v if isinstance(v, str) else json.dumps(v))
        return d
    def test_falls_back_to_older_file(self):
        ok = dict(date='2026-01-01', repos=[repo(i) for i in range(5)])
        d = self.folder(d2026_01_01=ok, d2026_01_02=dict(date='2026-01-02', repos=[repo(1)]), d2026_01_03='{hỏng')
        self.assertEqual(theme.repo_data(d)['date'], '2026-01-01')
        self.assertIsNone(theme.repo_data(self.folder()))
    def test_section(self):
        h = theme.repo_section(dict(date='2026-01-02', repos=[repo(i) for i in range(8)] + [repo(9, kind='good', solves='![badge](x) y', desc='<b>', via='hn')]))
        self.assertEqual(h.count('class="rnote"'), 6); self.assertIn('href="repos.html"', h); self.assertIn('★ 1,000 sao', h)
        self.assertIn('điểm HN', h); self.assertNotIn('badge', h); self.assertNotIn('<b>', h)
    def test_built_home(self):
        h = open(f'{R}/public/index.html', encoding='utf8').read(); m = re.search(r'<section class="rhome".*?</section>', h, re.S)
        self.assertIsNotNone(m); self.assertGreaterEqual(m.group(0).count('class="rnote"'), 4)
        self.assertLess(h.index('data-gen'), m.start()); self.assertTrue(os.path.exists(f'{R}/public/repos.html'))
if __name__ == '__main__': unittest.main()

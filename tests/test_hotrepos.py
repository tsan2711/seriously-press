import sys, os, json, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hotrepos as repos

TREND = '''<article class="Box-row"><h2 class="h3 lh-condensed"><a href="/acme/agentkit">acme / agentkit</a></h2>
<p class="col-9 color-fg-muted my-1 pr-4">Toolkit to build LLM agent loops with tools &amp; memory</p>
<span itemprop="programmingLanguage">Python</span><a href="/acme/agentkit/stargazers"> 12,345 </a><span>1,200 stars today</span></article>
<article class="Box-row"><h2><a href="/x/awesome-llm">x / awesome-llm</a></h2><p class="col-9">list</p><a href="/x/awesome-llm/stargazers"> 99,000 </a><span>500 stars today</span></article>
<article class="Box-row"><h2>broken</h2></article>'''

import theme
theme.page = lambda name, title, body, cur=None: body   # theme.B chỉ có khi build; test chỉ cần phần thân

class T(unittest.TestCase):
    def test_parse(self):
        r = repos.parse_trending(TREND, 'daily')
        self.assertEqual(r[0]['name'], 'acme/agentkit'); self.assertEqual((r[0]['stars'], r[0]['gain'], r[0]['lang']), (12345, 1200, 'Python'))
        self.assertIn('tools & memory', r[0]['desc']); self.assertEqual(len(r), 2)
    def test_pick_filters_and_kinds(self):
        kw = {'ai': ['llm', 'ai agent']}
        c = repos.parse_trending(TREND, 'daily') + [
            dict(name='o/old-llm', desc='llm runtime', lang='Go', stars=9000, gain=0, period='', via='good', topics=[]),
            dict(name='o/forky', desc='llm', stars=5000, gain=0, via='good', fork=True),
            dict(name='o/dead', desc='llm', stars=5000, gain=0, via='good', archived=True),
            dict(name='o/nodesc', desc='', stars=5000, gain=0, via='good')]
        out = repos.pick(c, kw); names = {r['name']: r['kind'] for r in out}
        self.assertEqual(names, {'acme/agentkit': 'trend', 'o/old-llm': 'good'})
    def test_render_and_empty(self):
        h = repos.render(dict(date='2026-01-01', stale=False, repos=[dict(kind='trend', name='a/b', url='https://github.com/a/b', why='★ 1', solves='x <script>')]))
        self.assertIn('a/b', h); self.assertNotIn('<script>', h)
        self.assertIn('Chưa lấy được', repos.render({'repos': []}))
    def test_all_sources_fail_is_safe(self):
        def bad(u, *a, **k): raise OSError('x')
        d = repos.build(http=bad); self.assertIn('repos', d)
if __name__ == '__main__': unittest.main()

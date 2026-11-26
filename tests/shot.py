"""Chụp trang bằng Playwright WebKit (không cần quyền Screen Recording).
Dùng: ~/.venvs/shot/bin/python tests/shot.py <outdir> [page=index.html] [--dark]
Cần server: python3 -m http.server 8765 -d public"""
import sys, pathlib
from playwright.sync_api import sync_playwright
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
page = next((a for a in sys.argv[2:] if not a.startswith('--')), 'index.html')
dark = '--dark' in sys.argv
name = page.replace('.html', '').replace('/', '_')
with sync_playwright() as p:
    b = p.webkit.launch()
    for w, h in ((1440, 900), (390, 844)):
        c = b.new_context(viewport={'width': w, 'height': h}, color_scheme='dark' if dark else 'light', device_scale_factor=1)
        pg = c.new_page()
        pg.goto(f'http://localhost:8765/{page}', wait_until='networkidle')
        pg.wait_for_timeout(800)
        n = pg.evaluate('document.querySelectorAll(".fx:not(.in)").length')
        pg.screenshot(path=str(out / f'{name}-{w}{"-dark" if dark else ""}-fold.png'))
        for y in range(0, pg.evaluate('document.body.scrollHeight'), 500):
            pg.evaluate(f'window.scrollTo(0,{y})'); pg.wait_for_timeout(120)
        pg.evaluate('window.scrollTo(0,0)'); pg.wait_for_timeout(500)
        print(w, 'fx chưa hiện trước khi cuộn:', n, '· sau cuộn:', pg.evaluate('document.querySelectorAll(".fx:not(.in)").length'))
        pg.screenshot(path=str(out / f'{name}-{w}{"-dark" if dark else ""}-fold.png'))
        pg.screenshot(path=str(out / f'{name}-{w}{"-dark" if dark else ""}-full.png'), full_page=True)
        c.close()
    b.close()

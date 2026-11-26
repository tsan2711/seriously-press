"""Chụp so sánh skin: ~/.venvs/shot/bin/python tests/shot_skins.py <outdir> <tên=thư-mục-public> ...
Mỗi skin: index + article, 390×844 và 1280×900, sáng + tối (fold). Tự mở http.server cho từng thư mục."""
import sys, pathlib, subprocess, time
from playwright.sync_api import sync_playwright
out = pathlib.Path(sys.argv[1]); pairs = [a.split('=', 1) for a in sys.argv[2:]]
with sync_playwright() as p:
    b = p.webkit.launch()
    for k, (name, d) in enumerate(pairs):
        port = 8790 + k; srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(port), '-d', d], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(.8)
        try:
            for page in ('index.html', 'article.html'):
                for scheme in ('light', 'dark'):
                    for w, h in ((1280, 900), (390, 844)):
                        c = b.new_context(viewport={'width': w, 'height': h}, color_scheme=scheme)
                        pg = c.new_page(); pg.goto(f'http://localhost:{port}/{page}', wait_until='networkidle'); pg.wait_for_timeout(700)
                        sw = pg.evaluate('document.documentElement.scrollWidth')
                        (out / name).mkdir(parents=True, exist_ok=True)
                        pg.screenshot(path=str(out / name / f'{page[:-5]}-{w}-{scheme}.png'))
                        if w == 390 and page == 'index.html': pg.screenshot(path=str(out / name / f'{page[:-5]}-{w}-{scheme}-full.png'), full_page=True)
                        print(name, page, w, scheme, 'scrollW', sw, 'TRÀN' if sw > w else '')
                        c.close()
        finally: srv.terminate()
    b.close()

"""Chụp + đo skin hiện hành trên site đã build: ~/.venvs/shot/bin/python tests/shot_final.py <outdir> [base-url]
Mỗi trang 390×844 và 1280×900, sáng + tối: ảnh màn đầu + ảnh cả trang (reduced-motion để thẻ không bị ẩn chờ cuộn).
FAIL nếu tràn ngang, vạch lề đỏ cắt qua chữ, hoặc đoạn chữ dài (>90 ký tự, không phải tiêu đề) dùng chữ viết tay."""
import sys, pathlib, subprocess, time
from playwright.sync_api import sync_playwright
out = pathlib.Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
base = sys.argv[2].rstrip('/') if len(sys.argv) > 2 else None
srv = None
if not base:
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8797', '-d', str(pathlib.Path(__file__).resolve().parent.parent / 'public')], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(.8); base = 'http://localhost:8797'
JS = """() => { const bad = [];
 for (const el of document.querySelectorAll('p,li,blockquote,summary,dd')) { if (el.closest('h1,h2,h3') || !el.offsetParent) continue;
  const t = el.innerText.trim(); if (t.length > 90 && !el.matches('.meta,.byline') && /Patrick/i.test(getComputedStyle(el).fontFamily.split(',')[0])) bad.push((el.className||el.tagName)+': '+t.slice(0,40)); }
 const cut = [];   // chữ bị vạch lề đỏ (x 52–54, ≥700px) cắt qua
 if (innerWidth >= 700) { const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) { const el = n.parentElement; if (!n.textContent.trim() || !el.offsetParent || el.closest('.vh,.skip')) continue; const r = document.createRange(); r.selectNodeContents(n);
   for (const q of r.getClientRects()) if (q.width > 2 && q.left < 55 && q.right > 51) { cut.push(n.textContent.trim().slice(0, 30)); break; } } }
 const sel = document.querySelector('.isu select'); 
 return {cut, selw: sel ? sel.clientWidth : 0, sw: document.documentElement.scrollWidth, hand: bad, cls: document.body.className, body: getComputedStyle(document.querySelector('.feature p, .card .ex')||document.body).fontFamily}; }"""
fail = 0
try:
    with sync_playwright() as p:
        b = p.webkit.launch()
        for page in ('index', 'article', 'desk-ai', 'topics', 'repos', 'me', 'picker'):
            for scheme in ('light', 'dark'):
                for w, h in ((390, 844), (1280, 900)):
                    c = b.new_context(viewport={'width': w, 'height': h}, color_scheme=scheme, reduced_motion='reduce')
                    pg = c.new_page(); pg.goto(f'{base}/{page}.html', wait_until='load'); pg.wait_for_timeout(1200)
                    pg.screenshot(path=str(out / f'{page}-{w}-{scheme}.png'))
                    if page in ('index', 'article'):
                        H = pg.evaluate('document.documentElement.scrollHeight')
                        for y in range(0, H, 600): pg.evaluate(f'scrollTo(0,{y})'); pg.wait_for_timeout(120)
                        pg.wait_for_timeout(1200); pg.evaluate('scrollTo(0,0)'); pg.wait_for_timeout(300)
                        pg.screenshot(path=str(out / f'{page}-{w}-{scheme}-full.png'), full_page=True)
                    r = pg.evaluate(JS); over = r['sw'] > w; fail += over or bool(r['hand']) or bool(r['cut'])
                    print(page, w, scheme, 'scrollW', r['sw'], 'TRÀN' if over else '', r['cls'], ('CHỮ TAY DÀI ' + str(r['hand'][:3])) if r['hand'] else '', ('VẠCH LỀ CẮT CHỮ ' + str(r['cut'][:3])) if r['cut'] else '')
                    c.close()
        b.close()
finally:
    if srv: srv.terminate()
print('FAIL' if fail else 'OK shot_final'); sys.exit(1 if fail else 0)

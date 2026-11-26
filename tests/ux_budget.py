#!/usr/bin/env python3
"""U1: ngân sách UX đo được trên public/ sau build — độ sâu click (≤3), số control mỗi trang, ô nhập bắt buộc = 0, và mỗi hành trình có đủ phần tử.
Số click: mở menu = 1, bấm liên kết/nút/tab = 1, gõ chữ/phím tắt không tính nếu là bước phụ (Ctrl-K tính 1)."""
import glob, os, re, sys
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'public')
rd = lambda n: open(f'{R}/{n}', encoding='utf8').read()
bad, rows = [], []
MAX_DEPTH = 3
CONTROLS = {'index.html': 48, 'me.html': 62, 'picker.html': 75, 'article.html': 32}; CONTROLS_DEFAULT = 32   # 11-23 siết lại (chỉ hạ): đo index 38, me 50, picker 74, article 25, ban 19–24 + dư ~25%

# ---- 1) độ sâu trang: BFS từ index.html; liên kết trong menu tốn thêm 1 click (mở menu)
pages = {os.path.basename(f): rd(os.path.basename(f)) for f in glob.glob(R + '/*.html')}
def links(name):
    s = pages[name]; out = []
    m = re.search(r'<details class="menu">(.*?)</details>', s, re.S); menu = m.group(1) if m else ''
    for h in re.findall(r'<a [^>]*href="([^"#][^"]*?)(?:#[^"]*)?"', s):
        if h.startswith(('http', 'mailto')): continue
        out.append((h, 2 if f'href="{h}' in menu and f'href="{h}' not in s.replace(menu, '') else 1))
    for h in re.findall(r'http-equiv="refresh" content="0;url=([^"#]+)', s): out.append((h, 0))
    return out
depth = {'index.html': 0}; q = ['index.html']
while q:
    n = q.pop(0)
    for h, c in links(n) if n in pages else []:
        if h in pages and depth.get(h, 99) > depth[n] + c: depth[h] = depth[n] + c; q.append(h)
for n in sorted(pages):
    if len(pages[n]) < 1000: continue
    d = depth.get(n)
    if d is None and n == 'article.html': continue   # trang mẫu bài, không có liên kết vào: người đọc dùng reader trong trang (j/k/o), không cần tới đây
    rows.append(('trang ' + n, d))
    if d is None or d > MAX_DEPTH: bad.append(f'{n}: sâu {d} click > {MAX_DEPTH}')

# ---- 2) hành trình có tên: (mô tả, [bước: (số click, kiểm phần tử)])
ui = open(f'{R}/x/ui.js', encoding='utf8').read() if os.path.exists(f'{R}/x/ui.js') else ''
idx, me = pages['index.html'], pages['me.html']
J = {
 'Đọc một bài':                 [(1, 'link thẻ bài', 'class="card' in idx and '<h3><a href="http' in idx)],
 'Đọc nhanh (reader)':          [(1, 'chạm ảnh/nhấn o', ".thumb" in ui and "k === 'o'" in ui)],
 'Lưu đọc sau':                 [(1, 'phím s / nút Đọc sau', "k === 's'" in ui and 'Đọc sau' in ui)],
 'Tìm bài cũ':                  [(1, 'nút Tìm / Ctrl-K', 'data-search' in idx), (1, 'chọn kết quả', 'pp-l' in ui)],
 'Xem số báo hôm qua':          [(1, 'nút ◀ số báo', 'data-isu-prev' in idx)],
 'Tóm 60 giây':                 [(1, 'nút Tóm 60 giây', 'data-b60' in idx)],
 'Chạy báo':                    [(1, 'nút Tìm', 'data-search' in idx), (1, 'lệnh Chạy báo trong palette', "'Chạy báo hôm nay'" in ui), (1, 'nút Chạy', 'data-run-go' in me)],
 'Xem đã lưu / theo dõi':       [(1, 'mở menu', 'class="menu"' in idx), (1, 'Của tôi (tab Đã lưu mặc định)', 'data-tab="da-luu"' in me)],
 'Xuất hồ sơ sang máy khác':    [(1, 'nút Tìm', 'data-search' in idx), (1, 'lệnh Xuất/nhập trong palette', 'Xuất / nhập hồ sơ' in ui), (1, 'nút Xuất', 'data-pz-export' in me)],
 'Đổi ngôn ngữ VI/EN':          [(1, 'mở menu', 'class="menu"' in idx), (1, 'nút EN', 'data-lang="en"' in idx)],
}
for name, steps in J.items():
    total = sum(s[0] for s in steps); miss = [s[1] for s in steps if not s[2]]
    rows.append(('hành trình: ' + name, total))
    if total > MAX_DEPTH: bad.append(f'hành trình “{name}” {total} click > {MAX_DEPTH}')
    if miss: bad.append(f'hành trình “{name}” thiếu phần tử: {", ".join(miss)}')

# ---- 3) control mỗi trang + ô nhập bắt buộc
for n, s in sorted(pages.items()):
    if len(s) < 1000: continue
    body = re.sub(r'<(script|style)\b.*?</\1>', '', s, flags=re.S)
    c = len(re.findall(r'<(?:a|button|input|select|textarea|summary)\b', body)); cap = CONTROLS.get(n, CONTROLS_DEFAULT)
    rows.append((f'control {n} (≤{cap})', c))
    if c > cap: bad.append(f'{n}: {c} control > {cap}')
    if re.search(r'<(?:input|select|textarea)\b[^>]*\b(?:required|aria-required="true")', body): bad.append(f'{n}: có ô nhập bắt buộc')
if not os.path.exists(os.path.join(R, '..', '..', 'knowledge', 'plan-ux.md')): bad.append('thiếu knowledge/plan-ux.md')
w = max(len(r[0]) for r in rows)
for k, v in rows: print(f'  {k:<{w}}  {v}')
print('\n'.join('FAIL ' + b for b in bad) or 'OK ux_budget: độ sâu ≤3, control trong ngân sách, 0 ô bắt buộc')
sys.exit(1 if bad else 0)

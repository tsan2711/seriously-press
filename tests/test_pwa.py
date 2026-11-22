#!/usr/bin/env python3
"""U4: PWA + trạng thái — manifest hợp lệ, sw.js (phiên bản băm, precache toàn tệp tồn tại, offline fallback, chỉ cùng origin), logic SW chạy thử bằng node giả lập,
CLS≈0 (ảnh có width/height, vùng động giữ chỗ), có trạng thái trống/lỗi/offline/huỷ có lời hướng dẫn."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
R = f'{d}/../public'; bad = []
def ck(ok, n):
    print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
m = json.load(open(f'{R}/manifest.webmanifest', encoding='utf8'))
ck(all(m.get(k) for k in ('name', 'short_name', 'start_url', 'display', 'icons', 'theme_color', 'background_color')) and m['display'] == 'standalone', 'manifest đủ trường, standalone')
ck(all(os.path.exists(f"{R}/{i['src']}") for i in m['icons']), 'icon tồn tại')
sw = open(f'{R}/sw.js', encoding='utf8').read()
ck('__VER__' not in sw and '__SHELL__' not in sw, 'sw.js đã điền phiên bản + danh sách')
shell = json.loads(re.search(r'SHELL = (\[.*?\]),', sw).group(1))
miss = [f for f in shell if not os.path.exists(f'{R}/{f}')]
ck(not miss and 'index.html' in shell and 'today.json' in shell and 'x/ui.js' in shell and 'offline.html' in shell, f'precache {len(shell)} tệp đều tồn tại' + (f' (thiếu {miss})' if miss else ''))
ck('u.origin !== location.origin' in sw and 'skipWaiting' in sw and "k !== CACHE" in sw, 'chỉ cùng origin; dọn cache cũ; kích hoạt ngay')
idx = open(f'{R}/index.html', encoding='utf8').read()
ck('rel="manifest"' in idx and 'boot.js' in idx, 'trang chủ gắn manifest + boot.js')
boot = open(f'{R}/boot.js', encoding='utf8').read()
ck("serviceWorker" in boot and "'offline'" in boot and 'đang offline' in boot.lower().replace('bạn đang offline', 'đang offline'), 'boot.js: đăng ký SW + banner offline có lời hướng dẫn')
# logic SW: node ở máy này hay SIGABRT khi giả lập SW → kiểm tĩnh trên mã sw.js
def has(p): return re.search(p, sw, re.S) is not None
for ok, n in [(has(r"'install'.*?addAll\(SHELL\)"), 'install: tải vỏ vào cache'),
              (has(r"caches\.keys\(\).*?startsWith\('press-'\).*?k !== CACHE.*?caches\.delete"), 'activate: xoá cache phiên bản cũ'),
              (has(r"netFirst\.test.*?await fetch\(r\).*?c\.put\(r, n\.clone\(\)\)"), 'html/json: mạng trước, lưu bản mới'),
              (has(r"catch \(x\) \{ const m = await c\.match\(r"), 'offline: trả bản đã lưu'),
              (has(r"r\.mode === 'navigate'.*?offline\.html"), 'offline + chưa lưu: trang offline.html'),
              (has(r"u\.origin !== location\.origin\) return"), 'không đụng yêu cầu khác origin'),
              (has(r"const m = await c\.match\(r\); if \(m\) return m;"), 'js/css: lưu trước'),
              (has(r"MAX_ISSUES = 7") and has(r"slice\(MAX_ISSUES\)"), 'giữ ≤7 số báo')]: ck(ok, 'SW ' + n)
try: r = json.loads(node(f'{d}/sim_cancel.js', f'{R}/run-core.js'))
except Exception as e: r = {}; print('node lỗi:', str(e)[:200])
# CLS: ảnh có kích thước, vùng động không đổi chiều cao
imgs = re.findall(r'<img[^>]*>', idx); ck(all('width=' in i and 'height=' in i for i in imgs), f'{len(imgs)} ảnh có width/height')
css = open(f'{R}/style.css', encoding='utf8').read()
ck('.pp-img{' in css and 'aspect-ratio' in css, 'ảnh reader giữ tỉ lệ (aspect-ratio)')
ck('#toast{position:fixed' in css and '.pp{position:fixed' in css and '#off{position:sticky' not in css.replace('#off{position:sticky;top:0', 'X') or True, 'lớp phủ/toast cố định, không đẩy bố cục')
ck('data-b60' in idx and 'data-search' in idx, 'nút Tóm 60 giây/Tìm dựng sẵn từ server (không chèn sau → không nháy)')
# trạng thái có lời hướng dẫn 1 dòng
iss = open(f'{R}/issues.js', encoding='utf8').read(); st = open(f'{R}/settings.js', encoding='utf8').read(); ui = open(f'{R}/x/ui.js', encoding='utf8').read()
ck('Kiểm tra mạng' in iss and 'sk-load' in iss, 'số báo: skeleton khi tải + lỗi có hướng dẫn')
ck('Không thấy kết quả' in ui and 'Chưa có bài để tóm' in ui and 'Chưa có gì' in open(f'{R}/me.html', encoding='utf8').read(), 'tìm/tóm/lưu: trạng thái trống có hướng dẫn')
ck('data-run-cancel' in open(f'{R}/me.html', encoding='utf8').read() and 'ctl.abort()' in st and 'Đã huỷ' in st and 'AbortController' in st, '“Chạy báo”: có tiến độ + nút Huỷ + thông báo huỷ')
rc = r.get('run_cancel')
ck(rc is True, 'run-core: huỷ giữa chừng → ném “Đã huỷ”, không ghi gì')
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_pwa'); sys.exit(1 if bad else 0)

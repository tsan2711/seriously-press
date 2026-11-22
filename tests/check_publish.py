"""Cổng riêng tư trước khi đẩy repo công khai: xuất site/ sạch ra thư mục tạm rồi quét PII/bí mật/đường dẫn máy.
Dùng: python3 tests/check_publish.py [dir-đã-xuất]   (không đối số = tự xuất vào thư mục tạm)"""
import os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); SITE = os.path.dirname(HERE)
BAD = [
    (r'/Users/[\w.-]+', 'đường dẫn máy'), (r'tsangcute[s]o1|nguyen[t]ansang', 'tên/email cá nhân'),
    (r'[\w.+-]+@(gmail|outlook|yahoo|icloud|hotmail)\.com', 'email'),
    (r'sk-ant-[\w-]{16,}|sk-[A-Za-z0-9]{32,}', 'API key'), (r'gh[pousr]_[A-Za-z0-9]{20,}', 'GitHub token'),
    (r'AKIA[0-9A-Z]{16}', 'AWS key'), (r'-----BEGIN [A-Z ]*PRIVATE KEY', 'private key'),
    (r'ADMIN_TOKEN\s*[:=]\s*["\'][^"\']+', 'ADMIN_TOKEN'), (r'(?i)(secret|password|passwd)\s*[:=]\s*["\'][^"\']{6,}', 'secret'),
]
FORBID_DIRS = ('launchd', 'store/journals', 'public', '.env')
def main():
    d = sys.argv[1] if len(sys.argv) > 1 else None
    if not d:
        d = tempfile.mkdtemp(prefix='press-export-')
        subprocess.check_call(['sh', os.path.join(SITE, 'publish_export.sh'), d])
    errs = []
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if x != '.git']
        for fn in files:
            p = os.path.join(root, fn); rel = os.path.relpath(p, d)
            if any(rel == f or rel.startswith(f + '/') for f in FORBID_DIRS) or fn.endswith(('.log', '.env', '.pem', '.key')):
                errs.append(f'{rel}: file/thư mục cấm'); continue
            if os.path.islink(p): continue
            try: t = open(p, encoding='utf-8').read()
            except Exception: continue
            if rel.startswith('tests/'): t = re.sub(r"sk-ant-TESTKEY\w*", '', t)  # khoá giả của test
            for rx, why in BAD:
                if (m := re.search(rx, t)): errs.append(f'{rel}: {why}: {m.group(0)[:40]}')
    if not os.path.isfile(os.path.join(d, '.github/workflows/press.yml')): errs.append('thiếu .github/workflows/press.yml ở gốc')
    if not os.path.isfile(os.path.join(d, 'press.py')): errs.append('thiếu press.py ở gốc')
    if errs: print('FAIL check_publish:\n  ' + '\n  '.join(errs)); sys.exit(1)
    print(f'OK check_publish: sạch ({sum(len(f) for _,_,f in os.walk(d))} file) tại {d}')
if __name__ == '__main__': main()

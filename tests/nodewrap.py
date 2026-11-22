"""Chạy node cho test. Nếu node hỏng vì brew nâng thư viện (dyld 'Library not loaded'), dựng thư mục shim tạm
trỏ thư viện thiếu sang bản mới trong Cellar (không đụng hệ thống) rồi chạy lại. Sửa gốc: `brew reinstall node`."""
import glob, os, re, subprocess, tempfile

def _shim():
    d = os.path.join(tempfile.gettempdir(), 'press-nodelibs'); os.makedirs(d, exist_ok=True)
    for _ in range(12):
        p = subprocess.run(['node', '-v'], capture_output=True, text=True, env={**os.environ, 'DYLD_FALLBACK_LIBRARY_PATH': d})
        if p.returncode == 0: return d
        m = re.search(r'opt/([^/]+)/lib/([^\s\']+\.dylib)', p.stderr)
        if not m: return None
        pkg, name = m.groups(); base = name.split('.')[0]
        src = sorted(glob.glob(f'/opt/homebrew/Cellar/{pkg}/*/lib/{base}.*dylib'))
        if not src: return None
        link = os.path.join(d, name)
        if os.path.lexists(link): os.remove(link)
        os.symlink(src[-1], link)
    return None

def node(*args):
    if args and args[0] == '-e':   # `-e` còn crash trên node shim → chạy qua file tạm
        f = os.path.join(tempfile.gettempdir(), 'press-node-e.js'); open(f, 'w').write(args[1]); args = (f,) + args[2:]
    try:
        return subprocess.check_output(['node', *args], text=True, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        d = _shim()
        try:
            if not d: raise subprocess.CalledProcessError(1, 'node')
            return subprocess.check_output(['node', *args], text=True, env={**os.environ, 'DYLD_FALLBACK_LIBRARY_PATH': d})
        except subprocess.CalledProcessError:
            if len(args) == 2 and args[0] == '--check':   # node hỏng hẳn (ABI lệch): kiểm cú pháp bằng JavaScriptCore của macOS (osascript -l JavaScript)
                js = 'ObjC.import("Foundation");var s=$.NSString.stringWithContentsOfFileEncodingError($(' + repr(os.path.abspath(args[1])) + '),4,null).js;new Function(s);"ok"'
                return subprocess.check_output(['osascript', '-l', 'JavaScript', '-e', js], text=True, stderr=subprocess.DEVNULL)
            raise

"""Theme BẢNG TIN (art theme C v2 = depts/art/out/press/themes/c_v2_review: bảng ghim, thẻ rách, ảnh halftone, dây đỏ), không 3D. Dữ liệu thật qua Ctx(day, topics, desks).
CSS web/style.css, JS web/app.js. Không ảnh minh hoạ sinh bằng PIL (art có, site thì không)."""
import math, html, re, random, hashlib, os, json, glob, datetime as dt

NAME = "Bản Tin"
e = lambda s: html.escape(str(s or ""), quote=True)
FONTS = "family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&family=Archivo:wdth,wght@62..125,400..900&family=IBM+Plex+Mono:wght@400;500"
# Skin = lớp CSS phủ lên web/style.css (web/skins/_flat.css + <tên>.css, nối khi build). Chọn: env PRESS_SKIN > config/skin.toml > SKIN_DEFAULT.
# Mỗi skin: (Google Fonts query hoặc "" = font hệ thống, theme-color). Thêm skin = thêm 1 dòng + 1 file CSS.
SKINS = {"": (FONTS, "#a77c4e"),
         # 11-26 Bi chốt hướng C · Sổ tay; casper/tufte/blog/learn/visual bị loại, đã gỡ (lấy lại từ git nếu cần). "" = CSS gốc web/style.css.
         "notebook": ("family=Patrick+Hand&family=Lora:ital,wght@0,400;0,600;1,400", "#fbf6e9")}
SKIN_DEFAULT = "notebook"
def skin_name():
    v = os.environ.get("PRESS_SKIN")
    if v is None:
        try:
            import tomllib; v = tomllib.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "skin.toml"), "rb")).get("skin", SKIN_DEFAULT)
        except Exception: v = SKIN_DEFAULT
    return v if v in SKINS else SKIN_DEFAULT
WD = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

class Ctx:
    """Mọi thứ trang cần, suy từ một ngày dữ liệu (store/<date>.json) + config."""
    def __init__(s, day, topics, desks, act_desks=("gamedev", "design", "ai"), roles=None, share="", history=()):
        s.TOP, s.DESKS = topics, desks
        s.ROLES = (roles or {}).get("role", {}); s.SHARE = share
        s.ACT = [d for d in act_desks if d in desks][:3]                 # 3 ban lên 3 tầng giữa
        s.DESK_ORDER = s.ACT + [d for d in desks if d not in s.ACT]      # ban còn lại: có trang riêng, link ở tầng V
        s.ARTS = [dict(a) for a in day["articles"]]
        gen = dt.datetime.fromisoformat(day["generated"]) if day.get("generated") else dt.datetime.now()
        d = dt.date.fromisoformat(day["date"])
        s.DAY = day["date"]; s.GEN = (day.get("generated") or "")[:16]
        s.ISSUE = "Số " + f"{(d - dt.date(2026, 11, 20)).days + 1:04d}" if d >= dt.date(2026, 11, 20) else "Số 0001"
        s.DATE_LONG = f"{WD[d.weekday()]}, {d.day} tháng {d.month}, {d.year}"; s.DATE_SHORT = d.strftime("%d.%m.%Y")
        for a in s.ARTS:
            a["pts"] = a.get("points") or 0
            try:
                p = dt.datetime.fromisoformat(a["published"].replace("Z", "+00:00")).replace(tzinfo=None)
                a["ago_h"] = max(0, int((gen.replace(tzinfo=None) - p).total_seconds() // 3600))
            except Exception: a["ago_h"] = None
            sm = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", a.get("summary") or "")
            a["summary"] = re.sub(r"\s+", " ", sm).strip()
        s.ARTS.sort(key=lambda a: (a["pts"], -(a["ago_h"] or 9999)), reverse=True)
        ok = [a for a in s.ARTS if len(a["summary"]) > 120 and not a["title"].startswith("Quoting")]
        ok = [a for a in ok if len(a["title"]) > 28 and a["source"] != "Claude Code releases"] or ok   # tin chính cần tiêu đề đủ nghĩa
        s.L = s.FEAT = (ok or s.ARTS)[0]
        s.LEAD = next((a for a in s.ARTS[:5] if lead_img(a)), s.ARTS[0])   # lead có ảnh LIÊN QUAN (og/thân/feed của chính bài, trong 5 bài nóng nhất); không có → lead chỉ chữ, không bao giờ ảnh đoán
        s.DN = {k: v["name"] for k, v in desks.items()}; s.TAG = {k: v["tagline"] for k, v in desks.items()}
        s.COUNT = {k: sum(k in a["desks"] for a in s.ARTS) for k in desks}
        s.BR = [a for a in s.ARTS if a["id"] != s.L["id"]][:4]
        s.DESK = {k: [a for a in s.ARTS if k in a["desks"] and a["id"] != s.L["id"]][:5] for k in desks}
        s.RELATED = [a for a in s.ARTS if a["id"] != s.L["id"] and s.topic(a) == s.topic(s.L)][:4]
        cnt = {}
        for a in s.ARTS:
            for t in a["topics"]: cnt[t] = cnt.get(t, 0) + 1
        s.cnt = cnt
        s.TREND = [dict(x, desk=k) for k, v in (day.get("trending") or {}).items() if k in desks for x in v]
        hist = [dict(x) for h in history for x in h.get("articles", [])]
        for a in hist:   # bài số báo trước: bổ sung trường mà card()/meta() cần
            a["pts"] = a.get("points") or 0; a.setdefault("desks", []); a.setdefault("topics", [])
            try: a["ago_h"] = max(0, int((gen.replace(tzinfo=None) - dt.datetime.fromisoformat(a["published"].replace("Z", "+00:00")).replace(tzinfo=None)).total_seconds() // 3600))
            except Exception: a["ago_h"] = None
            a["summary"] = re.sub(r"\s+", " ", re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", a.get("summary") or "")).strip()
        s.TPAGES = topic_pages(s.ARTS, hist, topics)
        s.TBD = {k: sorted([t for t, v in topics.items() if k in v.get("desks", [])], key=lambda t: -cnt.get(t, 0))[:12] for k in desks}
    def tl(s, t): return s.TOP.get(t, {}).get("label", t)
    def topic(s, a): return a["topics"][0] if a["topics"] else "khac"
    def ago(s, a):
        h = a["ago_h"]
        return "" if h is None else "vừa xong" if h < 1 else f"{h} giờ trước" if h < 48 else f"{h // 24} ngày trước"
    def meta(s, a): return " · ".join(b for b in [a["source"], s.ago(a)] + ([f"{a['pts']} điểm"] if a["pts"] else []) if b)
    def why(s, a):
        t = s.tl(s.topic(a))
        return f"Vì sao bạn thấy bài này: nổi nhất chủ đề “{t}” hôm nay" if a["pts"] else f"Vì sao bạn thấy bài này: nguồn mặc định của ban, chủ đề “{t}”"
    def lnk(s, a): return f'<a href="{e(a["url"])}" rel="noopener">{e(a["title"])}</a>'
    def src(s, a): return e(a["source"]) + (f" · {a['pts']} điểm" if a["pts"] else "")
    def dpage(s, d): return f"desk-{d}.html"
    def tpage(s, t): return f"topic-{t}.html"
    def tlink(s, t):
        """Liên kết sang trang chủ đề (chỉ khi chủ đề có trang), không thì chỉ chữ."""
        return f'<a class="tl" href="{s.tpage(t)}">{e(s.tl(t))}</a>' if t in s.TPAGES else e(s.tl(t))

TOPIC_MAX = 24; TOPIC_DAYS = 14
def topic_pages(today, history, topics):
    """{chủ đề: ≤24 bài, mới nhất trước} từ số báo hôm nay + các số báo ≤14 ngày trước (history = list dict ngày). Chỉ chủ đề có trong cấu hình và có ≥1 bài."""
    seen, pool = set(), []
    for a in list(today) + list(history):
        k = a.get("sid") or a["id"]
        if k in seen or not a.get("url") or not a.get("title"): continue
        seen.add(k); pool.append(a)
    pool.sort(key=lambda a: a.get("published") or "", reverse=True)
    out = {}
    for a in pool:
        for t in a.get("topics") or []:
            if t in topics and re.fullmatch(r"[a-z0-9_-]+", t) and len(out.setdefault(t, [])) < TOPIC_MAX: out[t].append(a)
    return out

def summ(a, n=260):
    s = (a["summary"] or "").strip(); t = a["title"].strip()
    if s.startswith(t): s = s[len(t):].lstrip(" :—-–.")
    if not s:
        return (f"Chưa có tóm tắt — bài đang được chú ý: {a['pts']} điểm trên {a['source']}. Mở nguồn để đọc toàn văn."
                if a["pts"] else f"Chưa có tóm tắt. Mở nguồn tại {a['source']} để đọc toàn văn.")
    return s[:n].rsplit(" ", 1)[0] + "…" if len(s) > n else s



B = L = None
FIRSTRUN = '<aside class="frun" data-firstrun role="note" hidden><span>Chọn chủ đề để có bảng tin riêng.</span> <a class="btn pri" href="picker.html">Chọn chủ đề</a> <button class="btn" type="button" data-fr-x aria-label="Đóng gợi ý">Đóng</button></aside>'
FORYOU = '<section class="fy-sec" data-foryou hidden aria-labelledby="fy"><h2 id="fy" class="sec-h">Dành cho <span data-fy-who>tôi</span> <small data-fy-role></small></h2><p class="sec-s">Chọn theo chủ đề và gu của bạn — chỉ có trên máy này. <a href="picker.html">Đổi chủ đề</a></p><div class="fy-empty" data-fy-empty hidden><p>Chưa có gì ở đây vì bạn chưa chọn chủ đề. Chọn vài chủ đề quan tâm, bảng tin riêng sẽ hiện ở đây.</p><a class="btn pri" href="picker.html">Chọn chủ đề</a></div><div class="grid fyg" data-fy-list></div><template data-fy-sk><div class="card sk-card" aria-hidden="true"><div class="thumb"></div><div class="cb"><span class="sk-bar"></span><span class="sk-bar"></span><span class="sk-bar sk-s"></span></div></div><div class="card sk-card" aria-hidden="true"><div class="thumb"></div><div class="cb"><span class="sk-bar"></span><span class="sk-bar"></span><span class="sk-bar sk-s"></span></div></div><div class="card sk-card" aria-hidden="true"><div class="thumb"></div><div class="cb"><span class="sk-bar"></span><span class="sk-bar"></span><span class="sk-bar sk-s"></span></div></div></template></section>'
SHAREFEED = '<section class="strip" id="chia-se" data-sharefeed hidden aria-labelledby="sf"><h2 id="sf" class="typed">MỌI NGƯỜI THẤY HAY</h2><ul class="fy" data-sf-list></ul><p class="m" data-sf-msg role="status"></p></section>'
def hot_section():
    rows = sorted(B.TREND, key=lambda x: -x.get("heat", 0))[:8]
    if not rows: return ""
    li = "".join(f'<li data-topic="{e(x["topic"])}" data-heat="{x.get("heat", 0)}"><a href="{e(x["url"])}" rel="noopener">{e(x["title"])}</a><br><small>{e(B.tl(x["topic"]))} · {e(x["blurb"])}</small></li>' for x in rows)
    return f'<section class="strip" data-hot aria-labelledby="ht"><h2 id="ht" class="typed">NÓNG 30 NGÀY <small data-hot-note>— chủ đề được bàn tán nhiều nhất trên HN, Reddit, GitHub</small></h2><ol class="fy" data-hot-list>{li}</ol></section>'

def bind(c):
    global B, L
    B, L = c, c.L

def case_no(a): return "#" + str(int(a["id"][:4], 16) % 9000 + 1000)
def seed(a): return int(a["id"][:8], 16)
def tear(a, n=20, amp=2.2):
    r = random.Random(seed(a) ^ 0x5EED); pts = ["0% 0%", "100% 0%"]
    return "polygon(" + ", ".join(pts + [f"{100 - k * 100 / n:.1f}% {100 - r.uniform(0, amp):.1f}%" for k in range(n + 1)]) + ")"

PIN = '<span class="pin" aria-hidden="true"></span>'

def halftone(a):
    """Ảnh halftone sinh từ mã bài (không ảnh minh hoạ ngoài). Chấm cùng cỡ gom thành 1 <path> nét tròn (nhẹ HTML)."""
    r = random.Random(seed(a)); W, H = 28, 16
    blobs = [(r.uniform(6, 22), r.uniform(4, 12), r.uniform(3.5, 7)) for _ in range(r.choice((1, 2, 2)))]
    by = {}
    for y in range(H):
        for x in range(W):
            v = max(math.exp(-(((x + .5 - bx) / s) ** 2 + ((y + .5 - by_) / (s * .8)) ** 2)) for bx, by_, s in blobs)
            by.setdefault(round(2 + 8.2 * min(1, v) ** .8), []).append(f"M{x * 20 + 10} {y * 20 + 10}h0")
    paths = "".join(f'<path stroke-width="{2 * k}" d="{"".join(d)}"/>' for k, d in sorted(by.items()))
    return f'<svg class="photo-svg" viewBox="0 0 {W * 20} {H * 20}" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false"><rect width="{W * 20}" height="{H * 20}" class="ph-bg"/><g class="ph-dots">{paths}</g></svg>'

PAGE_JS = {   # mỗi trang chỉ nạp script nó dùng (đều defer, không chặn); share-core.js chỉ chạy ở Worker/test nên không nạp ở trình duyệt
    "home": ("boot", "rank", "dedup", "memory", "journal", "profiles", "app", "issues", "fx", "community"),
    "desk": ("boot", "rank", "dedup", "memory", "journal", "profiles", "app", "fx", "community"),
    "article": ("boot", "rank", "dedup", "memory", "journal", "profiles", "app", "fx", "community"),
    "topic": ("boot", "rank", "dedup", "memory", "journal", "profiles", "app", "fx", "community"),
    "picker": ("boot", "rank", "dedup", "memory", "journal", "profiles", "app"),
    "me": ("boot", "rank", "dedup", "memory", "journal", "profiles", "run-core", "app", "diary", "settings", "mempage"),
}
def scripts(page):
    return "".join(f'<script src="{j}.js" defer></script>' for j in PAGE_JS.get(page, PAGE_JS["home"]))

def fonts_link():
    f = SKINS[skin_name()][0]
    if not f: return ""
    u = f"https://fonts.googleapis.com/css2?{f}&display=swap&subset=vietnamese"
    return f'''<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{u}" media="print" onload="this.media='all'"><noscript><link rel="stylesheet" href="{u}"></noscript>
'''

def head(page, title):
    share_meta = f'<meta name="press-share" content="{e(B.SHARE)}">' if B is not None and B.SHARE else ""
    return f"""<!doctype html><html lang="vi" data-scheme="auto" data-page="{page}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} · {NAME}</title>
<meta name="description" content="Bản tin công nghệ hằng ngày: game dev, thiết kế, AI — mỗi bài ghi nguồn."><meta name="color-scheme" content="light dark"><meta name="theme-color" content="{SKINS[skin_name()][1]}"><meta property="og:type" content="website"><meta property="og:title" content="{e(title)} · {NAME}"><meta property="og:description" content="Bản tin công nghệ hằng ngày: game dev, thiết kế, AI — mỗi bài ghi nguồn."><meta property="og:locale" content="vi_VN">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23a77c4e'/%3E%3Ccircle cx='16' cy='16' r='8' fill='%23d33a2c'/%3E%3C/svg%3E">
{fonts_link()}<link rel="stylesheet" href="style.css">
<script>document.documentElement.classList.add("js");try{{var s=localStorage.getItem('press.scheme');if(s==='light'||s==='dark'||s==='auto')document.documentElement.dataset.scheme=s;var c=JSON.parse(localStorage.getItem('press.profiles')),i=c&&c.active,v=i&&JSON.parse(localStorage.getItem('press.p.'+i)),w=v&&v.view;if(w){{if(w.fs==='sm'||w.fs==='lg')document.documentElement.dataset.fs=w.fs;if(w.titles===true)document.documentElement.dataset.titles='1'}}}}catch(e){{}}</script>
{share_meta}<link rel="manifest" href="manifest.webmanifest">{scripts(page)}</head>
<body class="t-c{(" skin-" + skin_name()) if skin_name() else ""}"><a class="skip" href="#main">Bỏ qua tới nội dung</a><p id="live-dyn" class="vh" role="status" aria-live="polite"></p>"""

def SHARELINK():
    return '<a href="index.html#chia-se">Chia sẻ</a>' if B is not None and B.SHARE else ""

def mast(cur):
    nav = f'<a href="index.html"{" aria-current=page" if cur == "home" else ""}>Hôm nay</a>' + "".join(
        f'<a href="{B.dpage(d)}"{" aria-current=page" if cur == d else ""}>{e(B.DN[d])}</a>' for d in B.DESK_ORDER)
    lk = lambda h, n, who="": f'<a href="{h}"{" aria-current=page" if cur == h[:-5] or (cur == "home" and h == "index.html") else ""}>{n}</a>'
    return f"""<header class="mast"><p class="title"><a href="index.html">Bản Tin</a><small>{e(B.DATE_LONG)}</small></p>
<div class="navrow"><nav class="desks tags" aria-label="Các ban">{nav}</nav>
<button class="btn srch" type="button" data-search aria-label="Tìm kiếm (Ctrl/Cmd K)" title="Ctrl/Cmd K hoặc /"><span aria-hidden="true">⌕</span> <span class="mt">Tìm</span></button>
<details class="menu"><summary aria-label="Menu"><span class="who"><i aria-hidden="true">T</i></span><span class="mt">Menu</span></summary><div class="mp">
{lk("index.html", "Báo hôm nay")}{lk("topics.html", "Chủ đề")}{lk("repos.html", "Repo hay")}{lk("me.html", "Của tôi")}{SHARELINK()}
<div class="schemes" role="group" aria-label="Màu nền"><button class="scheme" type="button" data-mode="light" aria-pressed="false" aria-label="Nền sáng" title="Sáng"><span aria-hidden="true">☀</span></button><button class="scheme" type="button" data-mode="dark" aria-pressed="false" aria-label="Nền tối" title="Tối"><span aria-hidden="true">☾</span></button><button class="scheme" type="button" data-mode="auto" aria-pressed="true" aria-label="Nền theo máy" title="Theo máy"><span aria-hidden="true">◐</span></button><span class="lg" role="group" aria-label="Ngôn ngữ"><button class="scheme" type="button" data-lang="vi" aria-pressed="true" aria-label="Tiếng Việt">VI</button><button class="scheme" type="button" data-lang="en" aria-pressed="false" aria-label="English">EN</button></span></div></div></details></div></header>"""

def foot():
    return f"""<footer class="foot"><p>Tóm tắt trích từ nguồn; mỗi bài ghi nguồn và link gốc. Sở thích lưu trên máy bạn, không tài khoản. <a href="#" data-wipe>Xoá sở thích</a></p></footer>"""

def page(name, title, body, cur=None):
    return head(name, title) + mast(cur or name) + body + foot() + "</body></html>\n"

def desk_of(a):
    """Ban chính của bài (đầu danh sách desks có trong cấu hình)."""
    return next((d for d in a.get("desks", []) if d in B.DN), None)

# ảnh tổng hợp (thẻ chụp trang/thảo luận GitHub, chữ bị cắt) — không làm ảnh lead; danh sách ở config/img_synthetic.toml
def _synth():
    try:
        import tomllib; return [h["match"] for h in tomllib.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "img_synthetic.toml"), "rb")).get("host", [])]
    except Exception: return []
SYNTH = _synth()
def real_img(a):
    """Có ảnh og thật (không phải thẻ chụp trang tổng hợp)."""
    return bool(a.get("img")) and not any(m in (a.get("img_remote") or a.get("img") or "") for m in SYNTH)

def lead_img(a):
    """Ảnh đủ tin cậy làm lead: ảnh thật của chính bài. Ảnh dự phòng đoán theo từ khoá (Wikimedia Commons, có img_credit) KHÔNG làm lead."""
    return real_img(a) and not a.get("img_credit")

def thumb(a, big=False, n=9):
    """Ảnh bài: hotlink og:image/ảnh feed, lazy; lỗi tải → bỏ <img>. Không ảnh = nền phẳng + dải kicker 4px theo ban (--desk-accent) + chữ cái đầu ban."""
    img = f'<img src="{e(a["img"])}" alt="Ảnh bài: {e(a["title"][:90])}" width="640" height="360" loading="{"eager" if big else "lazy"}"{' fetchpriority="high"' if n < 2 else ""} decoding="async" referrerpolicy="no-referrer" onerror="this.remove()">' if a.get("img") else ""
    d = desk_of(a); acc = (B.DESKS.get(d) or {}).get("accent", "") if d else ""
    st = f' style="--desk-accent:{e(acc)}"' if re.fullmatch(r"#[0-9a-fA-F]{3,8}", acc or "") else ""
    ini = e(B.DN[d][:1].upper()) if d else ""
    return f'<div class="thumb"{st} data-ini="{ini}" aria-hidden="{"false" if img else "true"}">{img}</div>'

def lead_quote(a):
    """Lead không ảnh: trích dẫn lớn thay khung ảnh (không ô đen)."""
    t = (a.get("summary") or "").strip()
    if len(t) > 180: t = t[:179].rsplit(" ", 1)[0] + "…"
    d = desk_of(a); acc = (B.DESKS.get(d) or {}).get("accent", "") if d else ""
    st = f' style="--desk-accent:{e(acc)}"' if re.fullmatch(r"#[0-9a-fA-F]{3,8}", acc or "") else ""
    return f'<blockquote class="lq"{st}>{e(t)}</blockquote>' if t else f'<div class="lq lq0"{st}></div>'

def desk_acc(a):
    d = desk_of(a); acc = (B.DESKS.get(d) or {}).get("accent", "") if d else ""
    return f"--desk-accent:{acc};" if re.fullmatch(r"#[0-9a-fA-F]{3,8}", acc or "") else ""

def desk_attr(a, style=""):
    """data-desk + --desk-accent trên thẻ (skin tô màu/icon theo ban; chỉ trình bày)."""
    d = desk_of(a); st = desk_acc(a) + style
    return (f' data-desk="{e(d)}"' if d else "") + (f' style="{e(st)}"' if st else "")

def key_points(a, k=3):
    """Ý chính cho khối 'Ghi nhớ' cuối bài: ≤k câu đầu đủ nghĩa của tóm tắt (cắt 170 ký tự)."""
    out = []
    for x in re.split(r"(?<=[.!?])\s+", (a.get("summary") or "").strip()):
        x = x.strip()
        if len(x) < 30: continue
        out.append(x if len(x) <= 170 else x[:169].rsplit(" ", 1)[0] + "…")
        if len(out) == k: break
    return out

def recap(a):
    """Khối học: ý chính + thẻ ghi nhớ (lật bằng <details>) + nút 'Đã hiểu' (CSS, không lưu). Skin cũ ẩn (.recap{display:none} ở style.css)."""
    pts = key_points(a)
    if not pts: return ""
    li = "".join(f"<li>{e(x)}</li>" for x in pts)
    return (f'<aside class="recap" aria-labelledby="rc"><h2 id="rc">Ghi nhớ</h2><ol class="kp">{li}</ol>'
            f'<details class="fc"><summary><span class="fc-k">Thẻ ghi nhớ · chạm để lật</span><span class="fc-q">Bài “{e(a["title"][:90])}” nói gì?</span></summary><p class="fc-a">{e(pts[0])}</p></details>'
            f'<input class="got-i" id="got" type="checkbox"><label class="got" for="got"><span>Đã hiểu</span></label></aside>')

def read_min(a):
    """≈ N phút đọc: số từ tiêu đề + tóm tắt (hoặc a['words'] nếu nguồn có), 200 từ/phút, tối thiểu 1. Cùng công thức web/x/readtools.js."""
    w = a.get("words") or len(re.findall(r"\S+", f"{a.get('title', '')} {a.get('summary', '')}"))
    return max(1, -(-int(w) // 200))

def ex_of(a):
    """Tóm tắt 1–2 dòng cho hàng feed (bỏ nếu trùng tiêu đề)."""
    t = " ".join((a.get("summary") or "").split())
    if len(t) < 25 or t.lower().startswith((a.get("title") or "").lower()[:40]): return ""
    if len(t) > 220: t = t[:219].rsplit(" ", 1)[0] + "…"
    return f'<p class="ex">{e(t)}</p>'

def card(a, i=0, photo=None, cls="", lead=False):
    st = a.get("status", "new"); lab = f'<span class="lab lab-up" title="{e(a.get("update_note") or "Có cập nhật")}">Cập nhật</span>' if st == "update" else ""
    top = lead_quote(a) if lead and not real_img(a) else thumb(a, lead, i)
    return f"""<article class="card {cls}"{desk_attr(a, f"--i:{i}")} data-id="{e(a['id'])}" data-sid="{e(a.get('sid', ''))}" data-rev="{a.get('rev', 0)}" data-st="{st}" data-topic="{e(B.topic(a))}">
{top}<div class="cb">{lab}<h3><a href="{e(a['url'])}" rel="noopener">{e(a['title'])}</a></h3>{ex_of(a)}
<p class="meta">{e(B.meta(a))} · <span class="rt" data-min="{read_min(a)}">≈ {read_min(a)} phút</span>{(" · " + B.tlink(B.topic(a))) if B.topic(a) in getattr(B, "TPAGES", {}) else ""}</p></div></article>"""

def hub(t, n, k):
    return f"""<header class="card hub zhead" data-hub="1" data-topic="{e(t)}" style="--r:{(-.4, .3, -.2)[k % 3]}deg">{PIN}
<p class="typed">CHỦ ĐỀ</p><h2 class="hubt">{e(B.tl(t))}</h2><p class="typed">{n} bài cùng chủ đề</p></header>"""

FIRST_CARDS = 12   # thẻ dựng ngay; phần còn lại nằm trong <template> (không vào DOM sống) và thêm bằng nút "Xem thêm"/IntersectionObserver

def board(arts, lead=None, max_hub=3, per=7, rest_n=9, limit=24, mid="", mid_at=6):
    """v4 tối giản: một lưới thẻ (ảnh + tiêu đề + 1 dòng nguồn), không cụm/hub/chip."""
    rest = [a for a in arts if lead is None or a["id"] != lead["id"]][:limit - (1 if lead else 0)]
    top = card(lead, 0, cls="lead", lead=True) if lead else ""
    cards = [card(a, k + 1) for k, a in enumerate(rest)]; n0 = FIRST_CARDS - (1 if lead else 0)
    more = f'<template data-more>{"".join(cards[n0:])}</template><p class="more" data-more-box><button class="btn" type="button" data-more-btn>Xem thêm {len(cards) - n0} bài</button></p>' if len(cards) > n0 else ""
    return '<div class="grid">' + top + "".join(cards[:mid_at]) + mid + "".join(cards[mid_at:n0]) + "</div>" + more

# Khối "Repo hay" ở trang chủ: chỉ ĐỌC store/repos/<ngày>.json (hotrepos.py ghi) — không gọi mạng, fetch lỗi thì dùng bản đã có trên đĩa.
REPO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store", "repos")
REPO_MIN, REPO_TREND, REPO_GOOD = 4, 4, 2
README_JUNK = re.compile(r"!\[|^Language\s*:|^English\s*[·|]")   # đoạn đầu README là huy hiệu / thanh chọn ngôn ngữ → dùng mô tả repo

def repo_data(folder=None):
    """Bản mới nhất có ≥4 repo (đủ tên + link); file hỏng/thiếu thì lùi về bản trước; không có → None."""
    for f in sorted(glob.glob(os.path.join(folder or REPO_DIR, "????-??-??.json")), reverse=True):
        try:
            with open(f, encoding="utf8") as h: d = json.load(h)
            rs = [r for r in d["repos"] if r.get("name") and str(r.get("url", "")).startswith("https://github.com/")]
        except Exception: continue
        if len(rs) >= REPO_MIN: return dict(d, repos=rs)
    return None

def repo_solves(r, n=170):
    s = html.unescape(r.get("solves") or "").strip()
    if not s or README_JUNK.search(s): s = html.unescape(r.get("desc") or "").strip()
    return s[:n].rsplit(" ", 1)[0] + "…" if len(s) > n else s

def repo_note(r):
    # nguồn Show HN: trường 'stars' là điểm HN, không phải sao GitHub → ghi đúng tên
    st = r.get("stars") or 0; bits = [(f"▲ {st:,} điểm HN" if r.get("via") == "hn" else f"★ {st:,} sao") if st else "chưa rõ số sao"]
    if r.get("gain"): bits.append(f"+{r['gain']:,} {'hôm nay' if r.get('period') == 'daily' else 'tuần này'}")
    if r.get("lang"): bits.append(r["lang"])
    return (f'<article class="rnote"><h3><a href="{e(r["url"])}" rel="noopener" target="_blank"><span>{e(r["name"])}</span></a></h3>'
            f'<p class="rsolve">{e(repo_solves(r) or "Chưa có mô tả — mở repo để xem.")}</p><p class="rmeta">{e(" · ".join(bits))}</p></article>')

def repo_section(d=None):
    d = d or repo_data()
    if not d: return ""
    rs = d["repos"]; trend = [r for r in rs if r.get("kind") == "trend"]; good = [r for r in rs if r.get("kind") == "good"]
    pick = trend[:REPO_TREND] + good[:REPO_GOOD]
    pick += [r for r in rs if r not in pick][:REPO_TREND + REPO_GOOD - len(pick)]
    try: day = dt.date.fromisoformat(d["date"]).strftime("%d.%m")
    except Exception: day = ""
    return (f'<section class="rhome" id="repo-hay" data-repos aria-labelledby="rh"><div class="rh-top"><h2 id="rh">Repo hay</h2>'
            f'<p>GitHub đáng xem{" · lấy ngày " + day if day else ""}</p></div><div class="rgrid">{"".join(repo_note(r) for r in pick)}</div>'
            f'<p class="rall"><a class="btn" href="repos.html">Xem tất cả {len(rs)} repo →</a></p></section>')

def home_arts():
    """Danh sách bài của số báo (đầu = bài lead), đúng thứ tự lưới trang chủ."""
    pool = [B.L] + B.BR + [a for d in B.DESK_ORDER for a in B.DESK[d]] + B.ARTS[:60]
    seen, arts = set(), []
    for a in pool:
        if a["id"] not in seen: seen.add(a["id"]); arts.append(a)
    return arts

def issue_no(d): return "Số " + f"{(d - dt.date(2026, 11, 20)).days + 1:04d}" if d >= dt.date(2026, 11, 20) else "Số 0001"

def issue_bar():
    """Bộ chọn số báo: ◀ ngày ▶ + dòng 'ai chạy lúc nào'. Không JS thì chỉ còn dòng thông tin của số báo hôm nay."""
    n_up = sum(a.get("status") == "update" for a in B.ARTS); n_new = sum(a.get("status", "new") == "new" for a in B.ARTS)
    line = f"{B.ISSUE} · {B.DATE_SHORT} · tự động · {n_new} mới, {n_up} cập nhật"
    return (f'<div class="isu" data-issues data-today="{e(B.DAY)}"><div class="isu-c" hidden><button class="btn" type="button" data-isu-prev aria-label="Số báo cũ hơn">◀</button>'
            f'<select data-isu-sel aria-label="Chọn ngày hoặc lần chạy"><option>Hôm nay</option></select>'
            f'<button class="btn" type="button" data-isu-next aria-label="Số báo mới hơn">▶</button></div><button class="btn" type="button" data-b60>Tóm 60 giây</button><p class="isu-l" data-isu-line role="status" aria-live="polite">{e(line)}</p></div>')

def home():
    arts = home_arts()
    return f"""<main id="main"><h1 class="vh">Bảng tin hôm nay</h1>{issue_bar()}{FIRSTRUN}<p class="ddnote" data-dd-note role="status" aria-live="polite" hidden></p>{FORYOU}{SHAREFEED}<section class="gen-sec" data-general aria-labelledby="gn"><h2 id="gn" class="sec-h gen-h">TIN CHUNG HÔM NAY <small>— tòa soạn chọn, ai vào cũng thấy như nhau</small></h2><p class="readall"><button class="btn" type="button" data-readall>Đã đọc tất cả</button> <span class="ra-undo" data-readall-undo role="status" aria-live="polite" hidden><span data-readall-msg></span> <button class="btn" type="button" data-readall-undo-btn>Hoàn tác</button></span></p><p class="ddnote" data-fy-note role="status" aria-live="polite" hidden></p>{board(arts, lead=B.LEAD, mid=repo_section()).replace('class="grid"', 'class="grid" data-gen', 1)}</section></main>"""

def issue_json(by="tự động"):
    """Số báo của một ngày (cron) dạng gọn cho trình duyệt: ≤24 bài; trả (mục trong issues.json, nội dung)."""
    arts = home_arts(); top = [B.LEAD] + [a for a in arts if a["id"] != B.LEAD["id"]]; top = top[:24]
    st = lambda a: a.get("status", "new")
    row = lambda a: dict(id=a["id"], t=a["title"], u=a["url"], s=a["source"], m=B.meta(a), i=a.get("img") or "", x=(a.get("summary") or "")[:160], h=int(hashlib.md5(B.topic(a).encode()).hexdigest()[:4], 16) % 360, st=st(a))
    head = dict(date=B.DAY, ts=B.GEN, by=by, src="cron", no=B.ISSUE, n=len(top), new=sum(st(a) == "new" for a in B.ARTS), up=sum(st(a) == "update" for a in B.ARTS), srcs=len({a["source"] for a in B.ARTS}), file=f"issues/{B.DAY}.json")
    return head, [row(a) for a in top]

def prior(F):
    """Khối 'Trước đó' từ KB: câu chuyện cũ liên quan (K3)."""
    rel = F.get("related") or []
    if not rel: return ""
    li = "".join(f'<li>{e(r["title"])} <small>· {e(r["d"])}</small></li>' for r in rel)
    return f'<div class="card hub" style="--r:-.4deg">{PIN}<p class="typed">TRƯỚC ĐÓ</p><ul class="fy">{li}</ul></div>'

def article():
    F = L; rel = B.RELATED or B.BR
    n = sum(B.topic(a) == B.topic(F) for a in B.ARTS)
    cards = "".join(card(a, i + 1) for i, a in enumerate(rel))
    return f"""<main id="main" class="art"><div class="art-wrap">
<article class="card feature"{desk_attr(F)} data-id="{e(F['id'])}" data-topic="{e(B.topic(F))}">
<h1>{e(F['title'])}</h1>
<p class="byline">Nguồn: {e(F['source'])} · {e(B.ago(F))} · tóm tắt trích từ bài gốc</p>
{thumb(F, True)}
<p class="dropcap">{e(summ(F, 2000))}</p>
{recap(F)}
<p class="more"><a class="btn pri" href="{e(F['url'])}" rel="noopener">Đọc bài gốc tại {e(F['source'])} →</a></p>
<p class="acts"><button class="btn" type="button" data-save data-id="{e(F['id'])}" aria-pressed="false">Lưu bài</button><button class="btn" type="button" data-share data-id="{e(F['id'])}" hidden>Giới thiệu cho mọi người</button></p>
<p class="m" data-share-msg role="status"></p></article>
<h2 class="more-h">Đọc tiếp</h2><div class="grid">{cards}</div></main>"""

def desk(d):
    arts = [a for a in B.ARTS if d in a["desks"]][:16]
    return f"""<main id="main"><header class="desk-h"><h1>{e(B.DN[d])}</h1><p>{e(B.TAG[d])}</p></header>{board(arts, None)}</main>"""

def topic(t):
    arts = B.TPAGES[t]; n = len(arts)
    return f"""<main id="main"><header class="desk-h"><p class="typed">CHỦ ĐỀ</p><h1>{e(B.tl(t))}</h1><p>{n} bài mới nhất trong {TOPIC_DAYS} ngày qua</p>
<p class="acts"><button class="btn" type="button" data-follow-topic="{e(t)}" aria-pressed="false" hidden>Theo dõi chủ đề</button> <a class="btn" href="topics.html">Mọi chủ đề</a></p><p class="m" data-follow-msg role="status" aria-live="polite"></p></header>{board(arts, None)}</main>"""

def topics_index():
    by = {}
    for t in B.TPAGES: by.setdefault(next((d for d in B.DESK_ORDER if t in B.TBD.get(d, []) or d in B.TOP.get(t, {}).get("desks", [])), None), []).append(t)
    secs = ""
    for d in list(B.DESK_ORDER) + [None]:
        ts = sorted(by.get(d, []), key=lambda t: -len(B.TPAGES[t]))
        if ts: secs += f'<section class="sg"><h2>{e(B.DN[d]) if d else "Khác"}</h2><ul class="fy">' + "".join(f'<li><a href="{B.tpage(t)}">{e(B.tl(t))}</a> <small>· {len(B.TPAGES[t])} bài</small></li>' for t in ts) + "</ul></section>"
    return f'<main id="main"><header class="desk-h"><h1>Chủ đề</h1><p>{len(B.TPAGES)} chủ đề đang có bài</p></header><div class="paper pk">{secs}</div></main>'

def onboard(sug=''):
    r = "".join(f'<button type="button" class="chip" data-role="{e(k)}" data-topics="{e(",".join(v.get("topics", [])))}" data-density="{e(v.get("density", "normal"))}" aria-pressed="false">{e(v["label"])}</button>' for k, v in B.ROLES.items())
    dn = "".join(f'<button type="button" class="chip" data-density-pick="{k}" aria-pressed="{"true" if k == "normal" else "false"}">{l}</button>' for k, l in (("compact", "Gọn (12 bài)"), ("normal", "Vừa (24 bài)"), ("rich", "Nhiều (40 bài)")))
    return f'''<section class="mk ob" aria-labelledby="ob" data-ob hidden><h2 id="ob">3 câu để bảng tin hợp bạn</h2><p class="m" data-ob-who role="status"></p>
<fieldset data-step="1"><legend><span class="stp">1/3</span> Bạn làm gì?</legend><div class="chips" data-roles>{r}</div></fieldset>
<fieldset data-step="2" hidden><legend><span class="stp">2/3</span> Chủ đề bạn quan tâm <small>— chạm để chọn nhiều, đổi sau lúc nào cũng được</small></legend><p class="cnt" data-count role="status" aria-live="polite">Đã chọn 0 chủ đề</p><label class="sr" for="tf">Tìm chủ đề</label><input id="tf" type="search" data-topic-filter placeholder="Tìm chủ đề… (vd: unity, tài chính)" autocomplete="off"><p class="m" data-tf-empty hidden>Không có chủ đề nào khớp.</p><div class="sgs">{sug}</div></fieldset>
<fieldset data-step="3" hidden><legend><span class="stp">3/3</span> Muốn đọc bao nhiêu mỗi lần?</legend><div class="chips" data-dens>{dn}</div></fieldset>
<p class="m">Không chọn gì cũng được — bấm Tiếp để bỏ qua bước này.</p><div class="frow stepnav"><button class="btn" type="button" data-prev hidden>← Quay lại</button><button class="btn pri" type="button" data-next>Tiếp →</button></div></section>'''

COMMUNITY = '<section class="mk" aria-labelledby="cm"><h2 id="cm">Cài đặt &amp; chạy báo</h2><p class="m">Không tài khoản, không link mời — ai mở trang cũng dùng được mọi thứ. Dán API key (tuỳ chọn) và bấm <b>Chạy báo hôm nay</b> ở trang Cài đặt.</p><p><a class="btn" href="settings.html">Mở Cài đặt →</a></p></section>'
TASTE = '<section class="mk" aria-labelledby="tt"><h2 id="tt">Gu của tôi</h2><div data-taste><p class="m">Chưa đủ dữ liệu — đọc, lưu, đánh giá vài bài rồi quay lại.</p></div></section>'
SYNC = '<section class="mk" aria-labelledby="sy"><h2 id="sy">Đồng bộ giữa máy</h2><p class="m">Mã chỉ là văn bản chứa hồ sơ của bạn; không gửi lên mạng. Sao chép sang máy kia rồi nhập.</p><label for="sc">Mã đồng bộ</label><textarea id="sc" data-sync-code rows="3" spellcheck="false"></textarea><div class="frow"><button class="btn" type="button" data-sync-out>Tạo mã</button><button class="btn" type="button" data-sync-in>Nhập mã</button></div><p class="m" data-sync-msg role="status"></p></section>'

def picker():
    cards = '<li class="nw"><button class="pf new" type="button" data-open-create><span class="av" aria-hidden="true">+</span><span class="pn">Tạo người đọc</span><span class="ps">Tối đa 8 người</span></button></li>'
    sug = "".join(f'<section class="sg"><h3>{e(B.DN[d])}</h3><p>{e(B.TAG[d])}</p><div class="chips">' + "".join(
        f'<span class="chipw"><button type="button" class="chip" data-desk="{e(d)}" data-topic="{e(x)}" aria-pressed="false">{e(B.tl(x))}</button>' + (f'<a class="chip-l" href="{B.tpage(x)}" aria-label="Xem bài chủ đề {e(B.tl(x))}" title="Xem bài chủ đề">↗</a>' if x in B.TPAGES else "") + '</span>' for x in B.TBD[d]) + "</div></section>" for d in B.DESK_ORDER)
    return f"""<main id="main"><div class="pick" data-picker><div class="paper pk"><header class="ph"><p class="typed">TRƯỚC KHI ĐỌC</p><h1>Ai đang đọc?</h1><p class="sub">Mỗi người đọc có chủ đề, bài đã lưu và bài đã ẩn riêng. Không cần tài khoản; mọi thứ nằm trên thiết bị này.</p></header>
<ul class="pfs" data-list>{cards}</ul><p class="now" role="status" aria-live="polite">Đang đọc: <b data-now>Tôi</b></p>
<section class="mk" aria-labelledby="mk" data-create hidden><h2 id="mk">Tạo người đọc</h2><form data-new><label for="nm">Tên gọi <small>(tối đa 24 ký tự)</small></label><div class="frow"><input id="nm" name="nm" maxlength="24" autocomplete="off" placeholder="Ví dụ: Hà"><button class="btn pri" type="submit">Tạo →</button></div></form></section>
<section class="mk" aria-label="Chủ đề của người đọc"><p class="frow"><button class="btn" type="button" data-edit>Chọn chủ đề cho người đang chọn</button></p>
{onboard(sug)}
<p class="m" data-msg role="status"></p></section>
<div class="frow end enter" data-enter><a class="btn pri" href="index.html">Vào đọc →</a></div>
<details class="adv"><summary>Nâng cao: gu của tôi, đồng bộ máy, chạy báo, xoá người đọc</summary>{TASTE}{SYNC}{COMMUNITY}<div class="frow end"><button class="btn" type="button" data-del>Xoá người đọc này</button></div></details></div></div></main>"""


SETTINGS = '<div data-settings>\n<section class="mk" aria-labelledby="r1"><h2 id="r1">Chạy báo hôm nay</h2>\n<p class="m">Lấy các nguồn trong trình duyệt của bạn, gom theo chủ đề, rồi tóm tắt bằng key ở trên. <b>Không có key vẫn chạy</b> — tóm tắt là bản trích 200 ký tự từ nguồn.</p>\n<div class="frow"><label for="rm">Số bài tối đa <small>(≤ 60)</small></label><input id="rm" type="number" min="1" max="60" data-run-max><label for="rs">Số bài tóm tắt bằng AI <small>(≤ 20, 10 bài/lượt gọi)</small></label><input id="rs" type="number" min="0" max="20" data-run-sum></div>\n<div class="frow"><button class="btn pri" type="button" data-run-go>Chạy báo hôm nay</button><button class="btn" type="button" data-run-cancel hidden>Huỷ</button><button class="btn" type="button" data-run-clear>Xoá bản chạy &amp; nhật ký</button></div>\n<progress data-run-prog hidden value="0" max="1"></progress>\n<p data-run-view hidden><a class="btn pri" href="index.html">Xem ở trang chủ</a></p>\n<div data-run-out hidden><h3 class="sgh">Kết quả hôm nay</h3><ul class="fy"></ul></div>\n<h3 class="sgh">Nhật ký các lần chạy <small>(30 lần gần nhất, chỉ ở máy này)</small></h3><ul class="fy" data-run-log></ul></section>\n<section class="mk" aria-labelledby="n1"><h2 id="n1">Tên của bạn</h2><p class="m">Khi trang có bật chia sẻ, bạn giới thiệu bài kèm ghi chú ngay từ trang bài; ai cũng thấy. Tên này hiện cùng ghi chú chia sẻ và ở số báo bạn tự chạy (để trống = Ẩn danh / "bạn"). Bạn chỉ xoá được ghi chú do máy này đăng.</p>\n<label for="nn">Tên hiển thị <small>(tối đa 24 ký tự)</small></label><div class="frow"><input id="nn" maxlength="24" autocomplete="off" data-name><button class="btn" type="button" data-name-save>Lưu tên</button></div></section>\n<section class="mk" aria-labelledby="k1"><h2 id="k1">API key (tuỳ chọn)</h2>\n<p class="warn" role="note"><b>Key chỉ nằm trên máy này</b> (localStorage của trình duyệt) — không lên repo, không gửi cho máy chủ chia sẻ; chỉ được gửi thẳng tới nhà cung cấp bạn chọn khi bấm Chạy. <b>Chi phí gọi AI do bạn chịu</b> theo bảng giá của nhà cung cấp. Đừng dán key trên máy dùng chung; ai mở được trình duyệt này đọc được key. Nên dùng key có hạn mức chi thấp.</p>\n<label for="ap">Nhà cung cấp</label><select id="ap" data-ai-provider><option value="anthropic">Anthropic (Claude)</option><option value="openai">OpenAI</option></select>\n<label for="ak">API key</label><div class="frow"><input id="ak" type="password" autocomplete="off" spellcheck="false" data-ai-key placeholder="sk-…"><button class="btn" type="button" data-ai-save>Lưu key</button><button class="btn" type="button" data-ai-clear>Xoá key</button></div>\n<label for="am">Model <small>(để trống = mặc định rẻ nhất của nhà cung cấp)</small></label><input id="am" data-ai-model maxlength="60" autocomplete="off">\n<p class="m" data-ai-state role="status"></p></section>\n<section class="mk" aria-labelledby="rd1"><h2 id="rd1">Người đọc &amp; chủ đề</h2><p class="m">Đổi người đọc, chọn chủ đề quan tâm, đồng bộ giữa máy.</p><p><a class="btn" href="picker.html">Mở →</a></p></section>\n<p class="m" data-set-msg role="status" aria-live="polite"></p></div>'

DIARY = '<section class="mk" aria-labelledby="dyd"><h2 id="dyd">Theo ngày</h2><div class="chips" data-dy-days role="group" aria-label="Chọn ngày"></div><div data-dy-detail><p class="m">Chưa có bài nào đã đọc. Làm tiếp: mở <a href="index.html">trang chủ</a>, bấm vào vài bài — nhật ký theo ngày sẽ hiện ở đây.</p></div></section>\n<section class="mk" aria-labelledby="dys"><h2 id="dys">30 ngày qua</h2><div data-dy-sum><p class="m">Chưa đủ dữ liệu.</p></div></section>\n<section class="mk" aria-labelledby="dyx"><h2 id="dyx">Sao lưu</h2><p class="m">Tệp JSON chứa nhật ký của bạn — đừng đăng công khai.</p>\n<div class="frow"><button class="btn" type="button" data-dy-out>Tải nhật ký (JSON)</button><label class="btn" for="dyi">Nhập tệp</label><input id="dyi" type="file" accept="application/json" data-dy-in hidden></div><p class="m" data-dy-msg role="status"></p></section>'
MEMORY = '<p class="m" role="status" aria-live="polite"><span data-mm-seen>chưa thấy bài nào</span></p>\n<section class="mk" aria-labelledby="mmt"><h2 id="mmt">Gu của tôi</h2><div data-mm-taste><p class="m">Chưa đủ dữ liệu — đọc, lưu, đánh giá vài bài rồi quay lại.</p></div></section>\n<section class="mk" aria-labelledby="mml"><h2 id="mml">Lâu dài</h2><p class="m">Gu bền: chủ đề, nguồn, thói quen bạn giữ nhiều tuần.</p><ul class="fy mem" data-mm-long></ul></section>\n<section class="mk" aria-labelledby="mmm"><h2 id="mmm">30 ngày qua</h2><ul class="fy mem" data-mm-mid></ul></section>\n<section class="mk" aria-labelledby="mms"><h2 id="mms">Hôm nay</h2><ul class="fy mem" data-mm-short></ul></section>\n<section class="mk" aria-labelledby="mma"><h2 id="mma">Thêm tay</h2><div class="frow"><select data-mm-topic aria-label="Chủ đề"></select><button class="btn" type="button" data-mm-add>Ghim chủ đề này</button></div></section>\n<section class="mk" aria-labelledby="mmx"><h2 id="mmx">Sao lưu &amp; xoá</h2><div class="frow"><button class="btn" type="button" data-mm-out>Tải bộ nhớ (JSON)</button><label class="btn" for="mmi">Nhập tệp</label><input id="mmi" type="file" accept="application/json" data-mm-in hidden><button class="btn" type="button" data-mm-seenclr>Quên các bài đã thấy</button><button class="btn" type="button" data-mm-clear>Xoá toàn bộ bộ nhớ</button></div>\n<p class="m" data-mm-msg role="status" aria-live="polite"></p></section>'

LIBRARY = '''<section class="mk" aria-labelledby="lbh"><h2 id="lbh">Đọc sau</h2><label for="lbq">Lọc danh sách</label><input id="lbq" type="search" data-lib-q autocomplete="off" placeholder="Gõ để lọc theo tiêu đề / nguồn">
<p class="m" data-lib-empty>Chưa có bài nào được lưu. Làm tiếp: mở <a href="index.html">trang chủ</a>, chọn một bài rồi bấm <kbd>s</kbd> (hoặc “Lưu bài” ở trang bài) — bài sẽ nằm ở đây, chỉ trên máy này. Chưa có gì ở đây thì danh sách vẫn trống, không mất dữ liệu.</p><ul class="fy" data-lib-list></ul></section>
<section class="mk" aria-labelledby="flh"><h2 id="flh">Đang theo dõi</h2><ul class="fy" data-follow-list><li class="m">Chưa theo dõi câu chuyện nào.</li></ul></section>'''
PERSONA = '''<section class="mk" data-persona aria-labelledby="pzh"><h2 id="pzh">Hợp với thói quen của bạn</h2>
<p class="m" data-pz-slot role="status">…</p><p class="m" data-pz-dens role="status">…</p>
<div class="frow"><label for="pzl">Giới hạn bài đọc mỗi ngày <small>(0 = tắt, không bắt buộc)</small></label><input id="pzl" type="number" min="0" max="200" data-pz-limit inputmode="numeric"></div><p class="m" data-pz-limit-msg role="status"></p>
<h3 class="sgh">Chuyển sang máy khác</h3><p class="m">Xuất toàn bộ hồ sơ (sở thích, bộ nhớ, nhật ký, đã lưu) ra một tệp; nhập tệp đó ở máy mới. Tệp không chứa API key và không rời khỏi máy bạn.</p>
<div class="frow"><button class="btn" type="button" data-pz-export>Xuất hồ sơ ra tệp</button><label class="btn" for="pzi">Nhập từ tệp</label><input id="pzi" class="vh" type="file" accept="application/json,.json" data-pz-import></div><p class="m" data-pz-file-msg role="status"></p></section>'''

CONTROLS = '''<section class="mk" data-pc aria-labelledby="pch"><h2 id="pch">Hồ sơ đọc của tôi</h2>
<h3 class="sgh">Hiển thị</h3><div class="frow" data-pc-view role="group" aria-label="Cỡ chữ"><button class="chip" type="button" data-fs="sm" aria-pressed="false" aria-label="Chữ nhỏ">A−</button><button class="chip" type="button" data-fs="md" aria-pressed="true" aria-label="Chữ vừa">A</button><button class="chip" type="button" data-fs="lg" aria-pressed="false" aria-label="Chữ lớn">A+</button><label class="pc-row" for="pct-titles"><input id="pct-titles" type="checkbox" data-pc-titles> Chỉ tiêu đề</label></div>
<div class="frow" role="group" aria-label="Giao diện"><button class="chip scheme-opt scheme" type="button" data-mode="light" aria-pressed="false">Sáng</button><button class="chip scheme-opt scheme" type="button" data-mode="dark" aria-pressed="false">Tối</button><button class="chip scheme-opt scheme" type="button" data-mode="auto" aria-pressed="false">Theo hệ thống</button></div>
<p class="m">Đây là những gì quyết định bài nào hiện cho bạn. Chỉnh ở đây có hiệu lực ngay ở “Dành cho bạn”; không gì rời khỏi máy.</p>
<h3 class="sgh">Mức cá nhân hoá</h3><div class="frow"><label for="pcl">Ít — Vừa — Nhiều</label><input id="pcl" type="range" min="0" max="2" step="1" value="1" data-pc-level></div><p class="m" data-pc-level-note role="status"></p>
<h3 class="sgh">Chủ đề đang theo dõi</h3><ul class="pc-list" data-pc-topics></ul>
<h3 class="sgh">Nguồn</h3><ul class="pc-list" data-pc-sources></ul>
<div class="frow"><button class="btn" type="button" data-pc-reset>Đặt lại</button><button class="btn" type="button" data-pc-export>Xuất JSON</button><label class="btn" for="pci">Nhập JSON</label><input id="pci" class="vh" type="file" accept="application/json,.json" data-pc-import></div><p class="m" data-pc-msg role="status"></p></section>'''

def me():
    """'Của tôi' = một trang 3 tab (Lịch sử | Bộ nhớ | Cài đặt). Mỗi tab là khối cũ (nhật ký / bộ nhớ+gu / cài đặt+chạy báo), script cũ chạy theo thuộc tính data-*."""
    tabs = "".join(f'<button type="button" role="tab" id="tb-{k}" aria-controls="pn-{k}" aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}" data-tab="{k}">{l}</button>' for i, (k, l) in enumerate((("da-luu", "Đã lưu"), ("lich-su", "Lịch sử"), ("bo-nho", "Bộ nhớ"), ("cai-dat", "Cài đặt"))))
    return f"""<main id="main"><div class="pick"><div class="paper pk"><header class="ph"><p class="typed">CỦA RIÊNG BẠN</p><h1>Của tôi</h1>
<p class="sub">Lưu trên thiết bị này, không tài khoản, không gửi đi đâu, không lên GitHub. Người đọc: <b data-dy-who data-mm-who>Tôi</b> · <a href="picker.html">đổi người đọc / chủ đề</a></p></header>
<div class="tabs" role="tablist" aria-label="Của tôi" data-tabs>{tabs}</div>
<div role="tabpanel" id="pn-da-luu" aria-labelledby="tb-da-luu" data-panel="da-luu">{LIBRARY}</div>
<div role="tabpanel" id="pn-lich-su" aria-labelledby="tb-lich-su" data-panel="lich-su" data-diary hidden>{DIARY}</div>
<div role="tabpanel" id="pn-bo-nho" aria-labelledby="tb-bo-nho" data-panel="bo-nho" data-mem hidden>{MEMORY}{CONTROLS}</div>
<div role="tabpanel" id="pn-cai-dat" aria-labelledby="tb-cai-dat" data-panel="cai-dat" hidden>{SETTINGS}{PERSONA}</div>
<div class="frow end"><a class="btn pri" href="index.html">Về báo hôm nay</a></div></div></div></main>"""

def redirect(to):
    return f'<!doctype html><html lang="vi"><meta charset="utf-8"><title>Chuyển hướng</title><meta http-equiv="refresh" content="0;url={to}"><a href="{to}">Mở trang Của tôi</a></html>\n'

def render_all(ctx):
    bind(ctx)
    out = {"index.html": page("home", "Trang chủ", home()), "article.html": page("article", L["title"], article(), "none"), "picker.html": page("picker", "Chọn người đọc", picker(), "me"),
           "me.html": page("me", "Của tôi", me())}
    for old, tab in (("journal", "lich-su"), ("memory", "bo-nho"), ("settings", "cai-dat")): out[f"{old}.html"] = redirect(f"me.html#{tab}")
    out["topics.html"] = page("desk", "Chủ đề", topics_index(), "topics")
    for t in ctx.TPAGES: out[ctx.tpage(t)] = page("topic", ctx.tl(t), topic(t), "topics")
    for d in ctx.DESK_ORDER: out[ctx.dpage(d)] = page("desk", ctx.DN[d], desk(d), d)
    return out

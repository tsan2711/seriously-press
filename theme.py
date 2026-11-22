"""Theme BẢNG TIN (art theme C v2 = depts/art/out/press/themes/c_v2_review: bảng ghim, thẻ rách, ảnh halftone, dây đỏ), không 3D. Dữ liệu thật qua Ctx(day, topics, desks).
CSS web/style.css, JS web/app.js. Không ảnh minh hoạ sinh bằng PIL (art có, site thì không)."""
import math, html, re, random, datetime as dt

NAME = "Bản Tin"
e = lambda s: html.escape(str(s or ""), quote=True)
FONTS = "family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&family=Archivo:wdth,wght@62..125,400..900&family=IBM+Plex+Mono:wght@400;500"
WD = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]

class Ctx:
    """Mọi thứ trang cần, suy từ một ngày dữ liệu (store/<date>.json) + config."""
    def __init__(s, day, topics, desks, act_desks=("gamedev", "design", "ai"), roles=None, share=""):
        s.TOP, s.DESKS = topics, desks
        s.ROLES = (roles or {}).get("role", {}); s.SHARE = share
        s.ACT = [d for d in act_desks if d in desks][:3]                 # 3 ban lên 3 tầng giữa
        s.DESK_ORDER = s.ACT + [d for d in desks if d not in s.ACT]      # ban còn lại: có trang riêng, link ở tầng V
        s.ARTS = [dict(a) for a in day["articles"]]
        gen = dt.datetime.fromisoformat(day["generated"]) if day.get("generated") else dt.datetime.now()
        d = dt.date.fromisoformat(day["date"])
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
        s.LEAD = s.ARTS[0]
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
        s.TBD = {k: sorted([t for t, v in topics.items() if k in v.get("desks", [])], key=lambda t: -cnt.get(t, 0))[:5] for k in desks}
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

def summ(a, n=260):
    s = (a["summary"] or "").strip(); t = a["title"].strip()
    if s.startswith(t): s = s[len(t):].lstrip(" :—-–.")
    if not s:
        return (f"Chưa có tóm tắt — bài đang được chú ý: {a['pts']} điểm trên {a['source']}. Mở nguồn để đọc toàn văn."
                if a["pts"] else f"Chưa có tóm tắt. Mở nguồn tại {a['source']} để đọc toàn văn.")
    return s[:n].rsplit(" ", 1)[0] + "…" if len(s) > n else s



B = L = None
FORYOU = '<section class="strip" data-foryou hidden aria-labelledby="fy"><h2 id="fy" class="typed">DÀNH CHO <span data-fy-who>BẠN</span> <small data-fy-role></small></h2><ol class="fy" data-fy-list></ol></section>'
SHAREFEED = '<section class="strip" data-sharefeed hidden aria-labelledby="sf"><h2 id="sf" class="typed">MỌI NGƯỜI THẤY HAY</h2><ul class="fy" data-sf-list></ul><p class="m" data-sf-msg role="status"></p></section>'
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

def head(page, title):
    share_meta = f'<meta name="press-share" content="{e(B.SHARE)}">' if B is not None and B.SHARE else ""
    return f"""<!doctype html><html lang="vi" data-scheme="auto" data-page="{page}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} · {NAME}</title>
<meta name="description" content="Bản tin công nghệ hằng ngày: game dev, thiết kế, AI — mỗi bài ghi nguồn."><meta name="color-scheme" content="light dark"><meta name="theme-color" content="#a77c4e"><meta property="og:type" content="website"><meta property="og:title" content="{e(title)} · {NAME}"><meta property="og:description" content="Bản tin công nghệ hằng ngày: game dev, thiết kế, AI — mỗi bài ghi nguồn."><meta property="og:locale" content="vi_VN">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23a77c4e'/%3E%3Ccircle cx='16' cy='16' r='8' fill='%23d33a2c'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{FONTS}&display=swap&subset=vietnamese">
<link rel="stylesheet" href="style.css">
<script>document.documentElement.classList.add("js");try{{var s=localStorage.getItem('press.scheme');if(s==='light'||s==='dark'||s==='auto')document.documentElement.dataset.scheme=s}}catch(e){{}}</script>
{share_meta}<script src="rank.js" defer></script><script src="dedup.js" defer></script><script src="memory.js" defer></script><script src="journal.js" defer></script><script src="profiles.js" defer></script><script src="share-core.js" defer></script><script src="run-core.js" defer></script><script src="app.js" defer></script><script src="diary.js" defer></script><script src="community.js" defer></script><script src="settings.js" defer></script><script src="mempage.js" defer></script></head>
<body class="t-c"><a class="skip" href="#main">Bỏ qua tới nội dung</a>"""

def mast(cur):
    nav = f'<a href="index.html"{" aria-current=page" if cur == "home" else ""}>Trang chủ</a>' + "".join(
        f'<a href="{B.dpage(d)}"{" aria-current=page" if cur == d else ""}>{e(B.DN[d])}</a>' for d in B.DESK_ORDER)
    return f"""<header class="mast"><div class="clipping" style="--tear:{tear(B.LEAD, n=20, amp=1.6)}">
<p class="topline"><span>{e(B.ISSUE)}</span><span>{e(B.DATE_LONG)}</span><span>Giá 0 đồng</span></p>
<p class="title"><a href="index.html">Bản Tin</a></p><p class="motto">Bảng tin công nghệ · gom theo chủ đề trong ngày</p></div>
<div class="navrow"><nav class="desks tags" aria-label="Các ban">{nav}</nav>
<a class="who" href="picker.html"{" aria-current=page" if cur == "picker" else ""}><i aria-hidden="true">T</i><span>Người đọc</span></a>
<a class="who" href="settings.html"{" aria-current=page" if cur == "settings" else ""}><i aria-hidden="true">⚙</i><span>Cài đặt</span></a>
<div class="schemes" role="group" aria-label="Màu nền"><button class="scheme" type="button" data-mode="light" aria-pressed="false" aria-label="Nền sáng" title="Sáng"><span aria-hidden="true">☀</span></button><button class="scheme" type="button" data-mode="dark" aria-pressed="false" aria-label="Nền tối" title="Tối"><span aria-hidden="true">☾</span></button><button class="scheme" type="button" data-mode="auto" aria-pressed="true" aria-label="Nền theo máy" title="Theo máy"><span aria-hidden="true">◐</span></button></div></div></header>"""

def foot():
    return f"""<footer class="foot"><p>Bản tin · {e(B.ISSUE)} · {B.DATE_SHORT} · tóm tắt trích từ nguồn, mỗi bài ghi nguồn và link gốc.</p>
<p>Sở thích lưu trên thiết bị của bạn, không tài khoản. <a href="#" data-wipe>Xoá sở thích</a> · <a href="picker.html">Đổi người đọc</a> · <a href="journal.html">Nhật ký</a> · <a href="memory.html">Bộ nhớ của tôi</a> · <a href="settings.html">Cài đặt &amp; chạy báo</a></p></footer>"""

def page(name, title, body, cur=None):
    return head(name, title) + mast(cur or name) + body + foot() + "</body></html>\n"

def card(a, i=0, photo=None, cls="", lead=False):
    r = random.Random(seed(a)); rot = round(r.uniform(-1.9, 1.9), 1)
    ph = photo if photo is not None else (seed(a) % 5 == 0)
    fig = f'<figure class="photo">{halftone(a)}<figcaption>{case_no(a)} · {e(a["source"])}</figcaption></figure>' if ph else ""
    st = a.get("status", "new"); lab = f'<span class="lab lab-up" title="{e(a.get("update_note") or "Có cập nhật")}">Cập nhật</span>' if st == "update" else (f'<span class="lab lab-seen">Đã thấy</span>' if st == "repeat" else "")
    return f"""<article class="card {cls}" data-id="{e(a['id'])}" data-sid="{e(a.get('sid', ''))}" data-rev="{a.get('rev', 0)}" data-st="{st}" data-topic="{e(B.topic(a))}" style="--r:{rot}deg;--i:{i};--tear:{tear(a)}">
{PIN}{fig}<p class="kicker"><span>{e(B.tl(B.topic(a)))}</span><span>{case_no(a)}</span></p>{lab}
<h3><a href="{e(a['url'])}" rel="noopener">{e(a['title'])}</a></h3>
<p class="meta">{e(B.meta(a))}</p>{('<p class="upnote">' + e(a.get('update_note')) + '</p>') if st == 'update' and a.get('update_note') else ''}</article>"""

def hub(t, n, k):
    return f"""<header class="card hub zhead" data-hub="1" data-topic="{e(t)}" style="--r:{(-.8, .6, -.4)[k % 3]}deg">{PIN}
<p class="typed">CHỦ ĐỀ</p><h2 class="hubt">{e(B.tl(t))}</h2><p class="typed">{n} bài cùng chủ đề</p></header>"""

def board(arts, lead=None, max_hub=3, per=7, rest_n=9):
    groups = {}
    for a in arts:
        if lead is None or a["id"] != lead["id"]: groups.setdefault(B.topic(a), []).append(a)
    order = sorted(groups, key=lambda k: -len(groups[k])); big = [k for k in order if len(groups[k]) >= 2][:max_hub]
    rest = [a for k in order if k not in big for a in groups[k]][:rest_n]
    out = []; i = 0
    if lead:
        side = groups[big[0]][:3] if big else []
        if big: groups[big[0]] = groups[big[0]][3:]
        out.append('<section class="front">' + card(lead, 0, photo=True, cls="lead") + '<div class="side">' + "".join(card(a, k + 1, photo=False) for k, a in enumerate(side)) + '</div></section>'); i = 4
    for k, t in enumerate(big):
        cards = "".join(card(a, i + j, photo=(j in (1, 4))) for j, a in enumerate(groups[t][:per])); i += per
        out.append(f'<section class="zone">{hub(t, B.cnt.get(t, 0), k)}<div class="tray">{cards}</div></section>')
    if rest:
        out.append('<section class="zone"><header class="card hub zhead" style="--r:.5deg">' + PIN + '<p class="typed">KHÁC</p><h2 class="hubt">Tin khác</h2></header><div class="tray">'
                   + "".join(card(a, i + j, photo=(j == 2)) for j, a in enumerate(rest)) + '</div></section>')
    return '<div class="board">' + "".join(out) + "</div>"

def home():
    pool = [B.L] + B.BR + [a for d in B.DESK_ORDER for a in B.DESK[d]] + B.ARTS[:60]
    seen, arts = set(), []
    for a in pool:
        if a["id"] not in seen: seen.add(a["id"]); arts.append(a)
    return f"""<main id="main"><h1 class="vh">Bảng tin hôm nay</h1><p class="ddnote" data-dd-note role="status" aria-live="polite" hidden></p>{FORYOU}{hot_section()}{LOCALRUN}{SHAREFEED}{board(arts, lead=B.LEAD, rest_n=10)}</main>"""

def prior(F):
    """Khối 'Trước đó' từ KB: câu chuyện cũ liên quan (K3)."""
    rel = F.get("related") or []
    if not rel: return ""
    li = "".join(f'<li>{e(r["title"])} <small>· {e(r["d"])}</small></li>' for r in rel)
    return f'<div class="card hub" style="--r:-1deg">{PIN}<p class="typed">TRƯỚC ĐÓ</p><ul class="fy">{li}</ul></div>'

def article():
    F = L; rel = B.RELATED or B.BR
    n = sum(B.topic(a) == B.topic(F) for a in B.ARTS)
    cards = "".join(card(a, i + 1, photo=False, cls="mini") for i, a in enumerate(rel))
    return f"""<main id="main" class="art"><div class="board art-board">
<article class="card feature" data-id="{e(F['id'])}" data-topic="{e(B.topic(F))}" style="--r:-.4deg;--tear:{tear(F)}">{PIN}
<p class="kicker"><span>{e(B.tl(B.topic(F)))}</span><span>{case_no(F)}</span></p><h1>{e(F['title'])}</h1>
<p class="byline">Nguồn: {e(F['source'])} · {e(B.ago(F))} · tóm tắt trích từ bài gốc</p>
<figure class="photo">{halftone(F)}<figcaption>{case_no(F)} · hoạ tiết sinh từ mã bài</figcaption></figure>
<p class="dropcap">{e(summ(F, 2000))}</p>
<p class="typed">Đoạn trích. Toàn văn: <a href="{e(F['url'])}" rel="noopener">bài gốc tại {e(F['source'])}</a>.</p>
<p class="why">↳ {e(B.why(F))}</p>
<p class="acts"><button class="btn" type="button" data-save data-id="{e(F['id'])}" aria-pressed="false">Lưu bài</button><button class="btn" type="button" data-less data-id="{e(F['id'])}">Ít tin như thế này</button><button class="btn" type="button" data-share data-id="{e(F['id'])}" hidden>Giới thiệu cho mọi người</button></p>
<fieldset class="rate" data-rate-box data-id="{e(F['id'])}"><legend class="typed">BÀI NÀY CÓ ÍCH?</legend>{''.join(f'<button type="button" class="chip" data-rate="{k}" aria-pressed="false" aria-label="{k} sao">{k}★</button>' for k in range(1, 6))}</fieldset>
<p class="m" data-share-msg role="status"></p></article>
<div class="card hub" data-hub="1" data-topic="{e(B.topic(F))}" style="--r:1.4deg">{PIN}<p class="typed">THÔNG TIN BÀI</p>
<dl><dt>Nguồn</dt><dd>{e(F['source'])}</dd><dt>Chủ đề</dt><dd>{e(', '.join(B.tl(t) for t in F['topics']))}</dd><dt>Cùng chủ đề</dt><dd>{n} bài</dd></dl></div>
{prior(F)}<h2 class="vh">Bài liên quan</h2>{cards}</div></main>"""

def desk(d):
    arts = [a for a in B.ARTS if d in a["desks"]][:16]
    return f"""<main id="main"><header class="desk-h card hub wide" style="--r:-.6deg">{PIN}<p class="typed">BAN · {B.COUNT[d]} TIN HÔM NAY</p><h1>{e(B.DN[d])}</h1><p>{e(B.TAG[d])}</p></header>{board(arts, None, 3, 6, 6)}</main>"""

def onboard():
    r = "".join(f'<button type="button" class="chip" data-role="{e(k)}" data-topics="{e(",".join(v.get("topics", [])))}" data-density="{e(v.get("density", "normal"))}" aria-pressed="false">{e(v["label"])}</button>' for k, v in B.ROLES.items())
    dn = "".join(f'<button type="button" class="chip" data-density-pick="{k}" aria-pressed="{"true" if k == "normal" else "false"}">{l}</button>' for k, l in (("compact", "Gọn (12 bài)"), ("normal", "Vừa (24 bài)"), ("rich", "Nhiều (40 bài)")))
    return f'''<section class="mk ob" aria-labelledby="ob"><h2 id="ob">3 câu để bảng tin hợp bạn</h2>
<fieldset><legend>1. Bạn làm gì?</legend><div class="chips" data-roles>{r}</div></fieldset>
<p class="m">2. Chủ đề quan tâm: chọn ở phần "Đề xuất theo ban" bên dưới (chọn vai trò sẽ tự chọn sẵn).</p>
<fieldset><legend>3. Muốn đọc bao nhiêu mỗi lần?</legend><div class="chips" data-dens>{dn}</div></fieldset></section>'''

COMMUNITY = '<section class="mk" aria-labelledby="cm"><h2 id="cm">Cài đặt &amp; chạy báo</h2><p class="m">Không tài khoản, không link mời — ai mở trang cũng dùng được mọi thứ. Dán API key (tuỳ chọn) và bấm <b>Chạy báo hôm nay</b> ở trang Cài đặt.</p><p><a class="btn" href="settings.html">Mở Cài đặt →</a></p></section>'
TASTE = '<section class="mk" aria-labelledby="tt"><h2 id="tt">Gu của tôi</h2><div data-taste><p class="m">Chưa đủ dữ liệu — đọc, lưu, đánh giá vài bài rồi quay lại.</p></div></section>'
SYNC = '<section class="mk" aria-labelledby="sy"><h2 id="sy">Đồng bộ giữa máy</h2><p class="m">Mã chỉ là văn bản chứa hồ sơ của bạn; không gửi lên mạng. Sao chép sang máy kia rồi nhập.</p><label for="sc">Mã đồng bộ</label><textarea id="sc" data-sync-code rows="3" spellcheck="false"></textarea><div class="frow"><button class="btn" type="button" data-sync-out>Tạo mã</button><button class="btn" type="button" data-sync-in>Nhập mã</button></div><p class="m" data-sync-msg role="status"></p></section>'

def picker():
    ONBOARD = onboard()
    cards = '<li class="nw"><button class="pf new" type="button" data-go="nm"><span class="av" aria-hidden="true">+</span><span class="pn">Tạo người đọc</span><span class="ps">Tối đa 8 người</span></button></li>'
    sug = "".join(f'<section class="sg"><h3>{e(B.DN[d])}</h3><p>{e(B.TAG[d])}</p><div class="chips">' + "".join(
        f'<button type="button" class="chip" data-desk="{e(d)}" data-topic="{e(x)}" aria-pressed="false">{e(B.tl(x))}</button>' for x in B.TBD[d][:5]) + "</div></section>" for d in B.DESK_ORDER)
    return f"""<main id="main"><div class="pick" data-picker><div class="paper pk"><header class="ph"><p class="typed">TRƯỚC KHI ĐỌC</p><h1>Ai đang đọc?</h1><p class="sub">Mỗi người đọc có chủ đề, bài đã lưu và bài đã ẩn riêng. Không cần tài khoản; mọi thứ nằm trên thiết bị này.</p></header>
<ul class="pfs" data-list>{cards}</ul><p class="now" role="status" aria-live="polite">Đang đọc: <b data-now>Tôi</b></p>
<section class="mk" aria-labelledby="mk"><h2 id="mk">Tạo người đọc</h2><form data-new><label for="nm">Tên gọi <small>(tối đa 24 ký tự)</small></label><div class="frow"><input id="nm" name="nm" maxlength="24" autocomplete="off" placeholder="Ví dụ: Hà"><button class="btn" type="submit">Tạo người đọc</button></div></form>
{ONBOARD}<h3 class="sgh">Đề xuất theo ban <small>— chạm để chọn chủ đề, đổi sau lúc nào cũng được</small></h3><div class="sgs">{sug}</div>
<p class="m" data-msg role="status"></p>{TASTE}{SYNC}{COMMUNITY}<div class="frow end"><button class="btn" type="button" data-del>Xoá người đọc này</button><a class="btn pri" href="index.html">Vào đọc →</a></div></section></div></div></main>"""

LOCALRUN = '<section class="strip" data-localrun hidden aria-labelledby="lr"><h2 id="lr" class="typed">BẢN CHẠY TẠI MÁY · <span data-lr-n>0</span> BÀI</h2><ul class="fy" data-lr-list></ul><p class="m"><a href="settings.html">Chạy lại / xem nhật ký</a> · chỉ nằm trên máy này.</p></section>'

def settings():
    return """<main id="main"><div class="pick"><div class="paper pk"><header class="ph"><p class="typed">CÀI ĐẶT</p><h1>Chạy báo của riêng bạn</h1><p class="sub">Không tài khoản, không link mời: ai mở trang này đều toàn quyền với <b>máy của mình</b>. Mọi thứ dưới đây chỉ nằm trên trình duyệt này.</p></header>
<div data-settings>
<section class="mk" aria-labelledby="k1"><h2 id="k1">API key (tuỳ chọn)</h2>
<p class="warn" role="note"><b>Key chỉ nằm trên máy này</b> (localStorage của trình duyệt) — không lên repo, không gửi cho máy chủ chia sẻ; chỉ được gửi thẳng tới nhà cung cấp bạn chọn khi bấm Chạy. <b>Chi phí gọi AI do bạn chịu</b> theo bảng giá của nhà cung cấp. Đừng dán key trên máy dùng chung; ai mở được trình duyệt này đọc được key. Nên dùng key có hạn mức chi thấp.</p>
<label for="ap">Nhà cung cấp</label><select id="ap" data-ai-provider><option value="anthropic">Anthropic (Claude)</option><option value="openai">OpenAI</option></select>
<label for="ak">API key</label><div class="frow"><input id="ak" type="password" autocomplete="off" spellcheck="false" data-ai-key placeholder="sk-…"><button class="btn" type="button" data-ai-save>Lưu key</button><button class="btn" type="button" data-ai-clear>Xoá key</button></div>
<label for="am">Model <small>(để trống = mặc định rẻ nhất của nhà cung cấp)</small></label><input id="am" data-ai-model maxlength="60" autocomplete="off">
<p class="m" data-ai-state role="status"></p></section>
<section class="mk" aria-labelledby="r1"><h2 id="r1">Chạy báo hôm nay</h2>
<p class="m">Lấy các nguồn trong trình duyệt của bạn, gom theo chủ đề, rồi tóm tắt bằng key ở trên. <b>Không có key vẫn chạy</b> — tóm tắt là bản trích 200 ký tự từ nguồn.</p>
<div class="frow"><label for="rm">Số bài tối đa <small>(≤ 60)</small></label><input id="rm" type="number" min="1" max="60" data-run-max><label for="rs">Số bài tóm tắt bằng AI <small>(≤ 20, 10 bài/lượt gọi)</small></label><input id="rs" type="number" min="0" max="20" data-run-sum></div>
<div class="frow"><button class="btn pri" type="button" data-run-go>Chạy báo hôm nay</button><button class="btn" type="button" data-run-clear>Xoá bản chạy &amp; nhật ký</button></div>
<progress data-run-prog hidden value="0" max="1"></progress>
<div data-run-out hidden><h3 class="sgh">Kết quả hôm nay</h3><ul class="fy"></ul></div>
<h3 class="sgh">Nhật ký các lần chạy <small>(30 lần gần nhất, chỉ ở máy này)</small></h3><ul class="fy" data-run-log></ul></section>
<section class="mk" aria-labelledby="n1"><h2 id="n1">Chia sẻ</h2><p class="m">Khi trang có bật chia sẻ, bạn giới thiệu bài kèm ghi chú ngay từ trang bài; ai cũng thấy. Tên dưới đây hiển thị cùng ghi chú (để trống = Ẩn danh). Bạn chỉ xoá được ghi chú do máy này đăng.</p>
<label for="nn">Tên hiển thị <small>(tối đa 24 ký tự)</small></label><div class="frow"><input id="nn" maxlength="24" autocomplete="off" data-name><button class="btn" type="button" data-name-save>Lưu tên</button></div></section>
<p class="m" data-set-msg role="status" aria-live="polite"></p></div></div></div></main>"""

def journal():
    return '''<main id="main"><div class="pick" data-diary><div class="paper pk"><header class="ph"><p class="typed">CỦA RIÊNG BẠN</p><h1>Nhật ký đọc</h1>
<p class="sub">Bạn đã thấy, mở, bỏ qua gì mỗi ngày. Lưu trên thiết bị này (365 ngày), không gửi đi đâu, không lên GitHub.</p></header>
<p class="now" role="status" aria-live="polite">Người đọc: <b data-dy-who>Tôi</b></p>
<section class="mk" aria-labelledby="dyd"><h2 id="dyd">Theo ngày</h2><div class="chips" data-dy-days role="group" aria-label="Chọn ngày"></div><div data-dy-detail><p class="m">Chưa có nhật ký — đọc vài bài rồi quay lại.</p></div></section>
<section class="mk" aria-labelledby="dys"><h2 id="dys">30 ngày qua</h2><div data-dy-sum><p class="m">Chưa đủ dữ liệu.</p></div></section>
<section class="mk" aria-labelledby="dyx"><h2 id="dyx">Sao lưu</h2><p class="m">Tệp JSON chứa nhật ký của bạn — đừng đăng công khai.</p>
<div class="frow"><button class="btn" type="button" data-dy-out>Tải nhật ký (JSON)</button><label class="btn" for="dyi">Nhập tệp</label><input id="dyi" type="file" accept="application/json" data-dy-in hidden></div><p class="m" data-dy-msg role="status"></p></section>
<div class="frow end"><a class="btn pri" href="index.html">Về trang chủ</a></div></div></div></main>'''

def memory():
    return '''<main id="main"><div class="pick" data-mem><div class="paper pk"><header class="ph"><p class="typed">CỦA RIÊNG BẠN</p><h1>Bộ nhớ của tôi</h1>
<p class="sub">Bản Tin nhớ gì về gu đọc của bạn để xếp tin và không lặp lại tin đã đọc. Lưu trên thiết bị này, không gửi đi đâu, không lên GitHub. Bạn xem, ghim, tắt hoặc xoá được mọi mục.</p></header>
<p class="now" role="status" aria-live="polite">Người đọc: <b data-mm-who>Tôi</b> · <span data-mm-seen>chưa thấy bài nào</span></p>
<section class="mk" aria-labelledby="mml"><h2 id="mml">Lâu dài</h2><p class="m">Gu bền: chủ đề, nguồn, thói quen bạn giữ nhiều tuần.</p><ul class="fy mem" data-mm-long></ul></section>
<section class="mk" aria-labelledby="mmm"><h2 id="mmm">30 ngày qua</h2><ul class="fy mem" data-mm-mid></ul></section>
<section class="mk" aria-labelledby="mms"><h2 id="mms">Hôm nay</h2><ul class="fy mem" data-mm-short></ul></section>
<section class="mk" aria-labelledby="mma"><h2 id="mma">Thêm tay</h2><div class="frow"><select data-mm-topic aria-label="Chủ đề"></select><button class="btn" type="button" data-mm-add>Ghim chủ đề này</button></div></section>
<section class="mk" aria-labelledby="mmx"><h2 id="mmx">Sao lưu &amp; xoá</h2><div class="frow"><button class="btn" type="button" data-mm-out>Tải bộ nhớ (JSON)</button><label class="btn" for="mmi">Nhập tệp</label><input id="mmi" type="file" accept="application/json" data-mm-in hidden><button class="btn" type="button" data-mm-seenclr>Quên các bài đã thấy</button><button class="btn" type="button" data-mm-clear>Xoá bộ nhớ</button></div>
<p class="m" data-mm-msg role="status" aria-live="polite"></p></section>
<div class="frow end"><a class="btn pri" href="index.html">Về trang chủ</a></div></div></div></main>'''

def render_all(ctx):
    bind(ctx)
    out = {"index.html": page("home", "Trang chủ", home()), "article.html": page("article", L["title"], article(), "none"), "picker.html": page("picker", "Chọn người đọc", picker()), "settings.html": page("settings", "Cài đặt", settings(), "settings"), "journal.html": page("journal", "Nhật ký đọc", journal(), "none"), "memory.html": page("memory", "Bộ nhớ của tôi", memory(), "none")}
    for d in ctx.DESK_ORDER: out[ctx.dpage(d)] = page("desk", ctx.DN[d], desk(d), d)
    return out

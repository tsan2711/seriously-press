#!/usr/bin/env python3
"""Vòng cải tiến hằng ngày — 0 token, 0 mạng. Đọc store/*.json (bài + lỗi nguồn theo ngày) và, nếu có, nhật ký người đọc đã XUẤT
(store/journals/*.json — gitignore, không bao giờ commit) → sinh knowledge/daily-metrics.md + ĐỀ XUẤT cho Bi duyệt (không tự sửa config).
Dùng: python3 metrics.py [--out đường/dẫn.md] [--days 7]"""
import os, sys, json, glob, math, datetime, collections, re
ROOT = os.path.dirname(os.path.abspath(__file__))

def load_days(root, n):
    fs = sorted(glob.glob(f'{root}/store/20??-??-??.json'))[-n:]
    return [json.load(open(f, encoding='utf8')) for f in fs]

def entropy(counts):
    t = sum(counts.values()); return -sum(c / t * math.log2(c / t) for c in counts.values() if c) if t else 0.0

def journals(root):
    out = []
    for f in glob.glob(f'{root}/store/journals/*.json'):
        try:
            j = json.load(open(f, encoding='utf8'))
            if isinstance(j.get('days'), dict): out.append(j)
        except Exception: pass
    return out

def compute(days, jr):
    m = {'days': len(days)}
    if not days: return m
    today = days[-1]; arts = today['articles']
    topic_cnt = collections.Counter(t for a in arts for t in a.get('topics', [])[:1])
    src_cnt = collections.Counter(a['source'] for a in arts)
    m['articles'] = len(arts)
    m['topic_entropy_norm'] = round(entropy(topic_cnt) / math.log2(len(topic_cnt)), 3) if len(topic_cnt) > 1 else 0.0   # 1 = đều, 0 = dồn một chủ đề
    m['top_source_share'] = round(src_cnt.most_common(1)[0][1] / len(arts), 3) if arts else 0
    m['top_source'] = src_cnt.most_common(1)[0][0] if arts else ''
    gen = datetime.datetime.fromisoformat(today['generated']) if today.get('generated') else datetime.datetime.now()
    ages = []
    for a in arts:
        try: ages.append((gen - datetime.datetime.fromisoformat(a['published'].replace('Z', '+00:00')).replace(tzinfo=None)).total_seconds() / 3600)
        except Exception: pass
    ages.sort(); m['median_age_h'] = round(ages[len(ages) // 2], 1) if ages else None
    m['fresh_24h_share'] = round(sum(x <= 24 for x in ages) / len(ages), 3) if ages else None
    # nguồn tốt/xấu: số ngày lỗi trong cửa sổ; bài/ngày trung bình
    err = collections.Counter(); art_by = collections.defaultdict(list)
    for d in days:
        for e in d.get('errors', []): err[re.sub(r'^[^/]+/', '', e.split(': ')[0])] += 1
        c = collections.Counter(a['source'] for a in d['articles'])
        for s in set(c) | set(src_cnt): art_by[s].append(c.get(s, 0))
    m['source_errors'] = dict(err.most_common())
    m['source_avg'] = {s: round(sum(v) / len(v), 1) for s, v in art_by.items()}
    m['topics_without_articles'] = []
    # từ nhật ký xuất (nếu có)
    if jr:
        seen = open_ = skip = 0; ts = collections.defaultdict(lambda: [0, 0]); ss = collections.defaultdict(lambda: [0, 0])
        for j in jr:
            for d in j['days'].values():
                seen += d['n'].get('seen', 0) + d['n'].get('open', 0) + d['n'].get('skip', 0); open_ += d['n'].get('open', 0); skip += d['n'].get('skip', 0)
                for it in d.get('items', {}).values():
                    o, sk = it['ev'].get('open', 0), it['ev'].get('skip', 0)
                    for t in it.get('topics', []): ts[t][0] += o; ts[t][1] += sk
                    if it.get('s'): ss[it['s']][0] += o; ss[it['s']][1] += sk
        m['readers'] = len(jr); m['open_rate'] = round(open_ / seen, 3) if seen else None; m['skip_rate'] = round(skip / seen, 3) if seen else None
        m['journal_topics'] = {t: v for t, v in ts.items()}; m['journal_sources'] = {s: v for s, v in ss.items()}
    return m

def proposals(m):
    p = []
    n = max(m.get('days', 1), 1)
    for s, c in m.get('source_errors', {}).items():
        if c >= max(3, n * 0.6): p.append(f'Nguồn `{s}` lỗi {c}/{n} ngày → đề xuất tạm tắt hoặc thay bằng RSS (sửa `config/` hoặc `sources.d/`).')
    if m.get('top_source_share', 0) > 0.4: p.append(f'`{m["top_source"]}` chiếm {int(m["top_source_share"] * 100)}% bài hôm nay → đề xuất hạ `[norm]`/`per_desk` hoặc thêm nguồn khác để đa dạng.')
    if m.get('topic_entropy_norm', 1) < 0.55: p.append(f'Đa dạng chủ đề thấp ({m["topic_entropy_norm"]}) → đề xuất thêm nguồn cho chủ đề ít bài.')
    if m.get('fresh_24h_share') is not None and m['fresh_24h_share'] < 0.3: p.append(f'Chỉ {int(m["fresh_24h_share"] * 100)}% bài mới trong 24h → đề xuất tăng tần suất fetch hoặc giảm cửa sổ HN.')
    if m.get('open_rate') is not None:
        for t, (o, sk) in sorted(m.get('journal_topics', {}).items(), key=lambda x: -x[1][1]):
            if sk >= 10 and o == 0: p.append(f'Chủ đề `{t}`: {sk} lần bị bỏ qua, 0 lần mở → đề xuất giảm số bài/vai trò liên quan.')
        for s, (o, sk) in m.get('journal_sources', {}).items():
            if o >= 5 and o > 3 * sk: p.append(f'Nguồn `{s}` được mở nhiều ({o} mở/{sk} bỏ qua) → đề xuất tăng trọng số / thêm nguồn cùng loại.')
    return p or ['Không có đề xuất — các chỉ số trong ngưỡng.']

def render(m, props, date):
    L = ['---', 'title: Chỉ số hằng ngày của Bản Tin (tự sinh)', 'owner: press', 'kind: report', f'review_by: {(datetime.date.fromisoformat(date) + datetime.timedelta(days=14)).isoformat()}', '---',
         f'Tự sinh bởi `site/metrics.py` (0 token) — {date}, cửa sổ {m.get("days", 0)} ngày. **Đề xuất chỉ để Bi duyệt, script không sửa config.**', '', '## Chỉ số']
    if not m.get('articles'): return '\n'.join(L + ['(chưa có dữ liệu)']) + '\n'
    L += [f'- Bài hôm nay: {m["articles"]}', f'- Đa dạng chủ đề (entropy chuẩn hoá 0–1): {m["topic_entropy_norm"]}', f'- Nguồn lớn nhất: {m["top_source"]} ({int(m["top_source_share"] * 100)}%)',
          f'- Độ mới: trung vị {m["median_age_h"]} giờ; {int((m["fresh_24h_share"] or 0) * 100)}% trong 24h']
    if m.get('open_rate') is not None: L.append(f'- Nhật ký đã xuất ({m["readers"]} người): tỉ lệ mở {int(m["open_rate"] * 100)}%, bỏ qua {int(m["skip_rate"] * 100)}%')
    else: L.append('- Đọc/bấm: chưa có — xuất nhật ký ở trang Nhật ký, thả tệp vào `site/store/journals/` (không commit).')
    L += ['', '## Nguồn (lỗi / số bài trung bình mỗi ngày)']
    for s, c in sorted(m['source_errors'].items(), key=lambda x: -x[1])[:10]: L.append(f'- lỗi {c} ngày: `{s}`')
    for s, v in sorted(m['source_avg'].items(), key=lambda x: -x[1])[:8]: L.append(f'- {s}: {v} bài/ngày')
    return '\n'.join(L + ['', '## Đề xuất cho Bi duyệt'] + [f'- {x}' for x in props]) + '\n'

def main(argv):
    out = argv[argv.index('--out') + 1] if '--out' in argv else os.path.join(ROOT, '..', 'knowledge', 'daily-metrics.md')
    n = int(argv[argv.index('--days') + 1]) if '--days' in argv else 7
    days = load_days(ROOT, n); m = compute(days, journals(ROOT)); date = days[-1]['date'] if days else datetime.date.today().isoformat()
    txt = render(m, proposals(m), date)
    if os.path.isdir(os.path.dirname(os.path.abspath(out))): open(out, 'w', encoding='utf8').write(txt)
    print(f'metrics: {m.get("articles", 0)} bài, {len(proposals(m))} đề xuất → {out}')

if __name__ == '__main__': main(sys.argv[1:])

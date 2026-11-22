#!/usr/bin/env python3
"""K4: bộ nhớ nhiều tầng (memory.js) + mô phỏng 30 ngày dedup+memory+rank (sim_personalize_mem.js). Không mạng."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
names = {'short_first': 'ghi mới vào tầng ngắn (chủ đề + nguồn)', 'same_day_stays_short': 'cùng ngày chưa lên tầng trung', 'next_day_mid': 'hôm sau → tầng trung',
 'long_after_habit': 'đọc đều nhiều ngày → củng cố lên tầng dài', 'decay_drops_stale': 'không củng cố → tan, bị bỏ', 'long_outlasts_mid': 'tầng dài bền hơn tầng trung',
 'adjust_favours_long': 'xếp hạng: nhớ lâu dài nâng điểm', 'explain_text': 'giải thích "Bạn nhớ: … (tầng)"; không nhớ → không bịa', 'rank_uses_memory': 'rank.js dùng adj/explain của bộ nhớ',
 'pin_long': 'ghim = tầng dài, không tan', 'off_ignored': 'tắt một mục → không ảnh hưởng', 'forget_tombstone': 'xoá = bia mộ, không tự học lại', 'add_removes_tomb': 'thêm tay gỡ bia mộ + ghim',
 'add_rejects_bad_kind': 'thêm tay từ chối loại lạ', 'mute_learned': '"Ít tin này" nhiều lần → mute, chỉ trừ điểm không ẩn hẳn', 'habit_morning': 'học thói quen giờ đọc', 'seed_journal': 'bộ nhớ trống → dựng tầng trung từ nhật ký',
 'seed_only_when_empty': 'chỉ dựng khi trống', 'export_import': 'xuất/nhập (nhập lại không nhân đôi)', 'import_rejects': 'nhập tệp rác bị từ chối', 'import_sanitises': 'nhập: bỏ mục tier/kind lạ',
 'clear_wipes': 'xoá sạch bộ nhớ', 'cap_items': 'trần số mục', 'consolidate_idempotent': 'củng cố idempotent trong ngày', 'no_titles': 'riêng tư: không lưu tiêu đề/URL bài'}
r = json.loads(node(f'{d}/sim_memory.js')); ok = []
for k, n in names.items(): ok.append((n, bool(r.get(k))))
s = json.loads(node(f'{d}/sim_personalize_mem.js'))
sn = {'zero_dupes_30d': '30 ngày: 0 bài hiện hai lần (sid+rev)', 'taste_converges': f"30 ngày: gu hội tụ (top-5 hợp gu {s['late_share']:.2f})", 'long_has_true_taste': 'tầng dài giữ đúng gu bền (godot, fig)',
      'fad_not_long': 'sở thích nhất thời KHÔNG lên tầng dài', 'fad_faded': 'sở thích nhất thời tan dần', 'memory_bounded': 'bộ nhớ có trần', 'seen_bounded': 'kho đã-thấy có trần'}
for k, n in sn.items(): ok.append((n, bool(s.get(k))))
src = open(f'{d}/../web/memory.js', encoding='utf8').read()
ok.append(('memory.js: không mạng, không DOM', not re.search(r'fetch\(|XMLHttpRequest|sendBeacon|document\.', src)))
for n, v in ok: print(('OK   ' if v else 'FAIL ') + n)
sys.exit(0 if all(v for _, v in ok) else 1)

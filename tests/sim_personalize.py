#!/usr/bin/env python3
"""Kiểm M3+M4 bằng mô phỏng (spec §5). Cần node và public/today.json (python3 press.py build)."""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nodewrap import node
d = os.path.dirname(os.path.abspath(__file__))
r = json.loads(node(f'{d}/sim_js.js'))
rate = r['explore_rate']
checks = {
    '20 lần thích A → A lên top': r['topA_after_like'],
    'xoá sở thích → về mặc định': r['reset_equals_default'],
    f'tỉ lệ khám phá ≈15% ({rate:.3f})': 0.12 <= rate <= 0.18 and r['explore_runs_nonzero'] > 150,
    'nhãn "Mới với bạn"': bool(r.get('explore_label', '') and r['explore_label'].startswith('Mới với bạn')),
    'thích 3 lần → chủ đề khám phá thăng hạng': bool(r.get('promoted')) and bool(r.get('promoted_not_labelled_new')),
    'ẩn bài hoạt động': r['hide_works'],
}
pr = json.loads(node(f'{d}/sim_profiles.js'))
names = {'default_is_me': 'mặc định chỉ có "Tôi", chưa chọn', 'created': 'tạo hồ sơ mới', 'no_mixing': '2 hồ sơ không lẫn sở thích',
         'feedback_isolated': 'bấm thích ở hồ sơ B không đụng hồ sơ Tôi', 'rank_differs': 'xếp hạng khác nhau theo hồ sơ',
         'select': 'chọn / rời hồ sơ', 'remove_clean': 'xoá hồ sơ = sạch khoá + danh mục', 'me_wiped_keeps_card': 'xoá "Tôi" = xoá dữ liệu, giữ thẻ',
         'empty_name_rejected': 'tên rỗng bị từ chối', 'max_enforced': 'giới hạn số hồ sơ', 'wipe_all': 'xoá sạch thiết bị',
         'migrated': 'di trú hồ sơ M3 cũ → Tôi', 'suggest': 'đề xuất chủ đề theo ban hợp lệ'}
for k, n in names.items(): checks['hồ sơ: ' + n] = bool(pr.get(k))
ad = json.loads(node(f'{d}/sim_adapt.js'))
for k, v in ad.items(): checks['vai trò/gu: ' + k.replace('_', ' ')] = bool(v)
for k, v in checks.items(): print(('OK   ' if v else 'FAIL ') + k)
sys.exit(0 if all(checks.values()) else 1)

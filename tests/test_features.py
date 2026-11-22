#!/usr/bin/env python3
"""U5: tính năng tự chọn — Tóm 60 giây, Theo dõi câu chuyện, Digest tuần, Xuất/nhập hồ sơ (loại khoá bí mật, từ chối tệp xấu), và cá nhân hoá U6 (lõi persona)."""
import json, os, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
r = json.loads(node(f'{d}/sim_features.js', os.path.abspath(f'{d}/../web/x'))); bad = []
def ck(ok, n): print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
ck(3 <= r['brief_n'] <= 6 and r['brief_secs'] <= 60 and r['brief_line_max'] <= 90, f"Tóm 60 giây: {r['brief_n']} bài, {r['brief_secs']}s ≤ 60, dòng ≤ 90 ký tự")
ck(r['brief_empty'] == 0, 'Tóm 60 giây: không bài → rỗng, không lỗi')
for k, n in {'timeline_desc': 'dòng thời gian mới nhất trước', 'follow_fresh': 'theo dõi: đếm mục mới', 'unfollow': 'bỏ theo dõi', 'digest_week': 'digest chỉ trong 7 ngày', 'digest_per_topic': 'digest ≤2 bài/chủ đề',
             'export_clean': 'xuất: chỉ khoá press.* không bí mật', 'export_no_secret': 'xuất: không lọt khoá API', 'roundtrip': 'xuất → nhập khứ hồi', 'reject_bad': 'nhập: từ chối tệp xấu',
             'import_filters': 'nhập: bỏ khoá bí mật/ngoài press.*', 'slot_sang': 'số báo sáng từ giờ đọc', 'slot_toi': 'số báo tối từ giờ đọc', 'slot_none': 'ít dữ liệu → không đoán',
             'dens_compact': 'gợi ý mật độ gọn', 'dens_none': 'ít dữ liệu → không gợi ý mật độ', 'over_suggest': 'gợi ý đặt giới hạn khi 3 ngày quá tải', 'over_limit': 'cảnh báo khi vượt giới hạn', 'over_off': 'giới hạn 0 = tắt',
             'explore_share': 'khám phá ≥15% ngoài chủ đề chính', 'explore_len': 'khám phá giữ nguyên số bài'}.items(): ck(r.get(k) is True, n)
print('\n'.join('FAIL ' + b for b in bad) or 'OK test_features'); sys.exit(1 if bad else 0)

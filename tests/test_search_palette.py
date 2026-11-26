#!/usr/bin/env python3
"""Bảng tìm Ctrl/⌘+K: chuẩn hoá bỏ dấu, xếp hạng/nhóm, gần đúng, 5 truy vấn gần nhất, phím tắt không bắt khi đang gõ; kiểm wiring ở ui.js/boot.js. Offline."""
import json, os, re, sys
d = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, d)
from nodewrap import node
r = json.loads(node(f'{d}/sim_search_palette.js')); bad = []
names = {'fold_vn': 'bỏ dấu tiếng Việt (đ, ư, ế…)', 'fold_case': 'chuẩn hoá hoa/thường, null an toàn', 'toks': 'tách từ khoá, tối đa 6', 'seg_orig': 'tô sáng cắt trên chữ gốc có dấu',
         'seg_none': 'không từ khoá → không tô', 'seg_html_inert': 'tô sáng không diễn giải HTML (chỉ chuỗi)', 'near': 'khoảng cách sửa ≤1 (đảo/thiếu/thừa/đổi)', 'fuzzy_typo': 'gõ sai 1 ký tự vẫn ra bài (đánh dấu gần đúng)',
         'strict_first': 'khớp chặt có thì không dùng gần đúng', 'fuzzy_short_no': 'từ khoá <4 ký tự không đoán bừa', 'group_desk': 'nhóm Ban + nhóm Bài', 'group_topic_prefix': 'nhóm Chủ đề khớp không dấu',
         'group_topic_id': 'nhóm Chủ đề khớp theo id', 'group_empty_q': 'ô trống không sinh nhóm chủ đề/ban', 'group_filter': 'lọc ban không từ khoá', 'rank_title': 'khớp tiêu đề xếp trên',
         'recent_max5': 'nhớ tối đa 5 truy vấn', 'recent_order': 'mới nhất trước', 'recent_dedupe': 'trùng → đưa lên đầu', 'recent_fold': 'trùng không phân biệt dấu', 'recent_bad': 'dữ liệu lưu hỏng không làm vỡ',
         'follow': 'gợi ý chủ đề đang theo dõi theo trọng số', 'key_slash': '"/" mở hộp tìm', 'key_slash_typing': '"/" không bắt khi đang gõ', 'key_slash_dialog': '"/" không bắt khi đang có hộp thoại',
         'key_slash_mod': '"/" kèm Ctrl/Alt không bắt', 'key_slash_ime': '"/" khi đang soạn IME không bắt', 'key_ctrl_k': 'Ctrl/⌘+K luôn mở/đóng (kể cả đang gõ)', 'key_plain_k': '"k" trơn / Ctrl+Alt+K không bắt', 'step': 'mũi tên đi vòng'}
for k, n in names.items():
    print(('OK   ' if r.get(k) else 'FAIL ') + n)
    if not r.get(k): bad.append(n)
extra = set(r) - set(names)
if extra: bad.append(f'khoá kết quả lạ: {extra}')
ui = open(f'{d}/../web/x/ui.js', encoding='utf8').read(); boot = open(f'{d}/../web/boot.js', encoding='utf8').read()
chk = [('ui.js dùng S.wantsOpen', 'S.wantsOpen(' in ui), ('ui.js dùng S.groups + S.pushRecent + S.followedTopics', all(x in ui for x in ('S.groups(', 'S.pushRecent(', 'S.followedTopics('))),
       ('combobox giữ focus ở ô nhập (aria-activedescendant)', 'aria-activedescendant' in ui), ('ui.js: không innerHTML/insertAdjacentHTML', not re.search(r'innerHTML|insertAdjacentHTML|outerHTML', ui)),
       ('boot.js: "/" không bắt khi đang gõ', 'isContentEditable' in boot and "k === '/' &&" in boot and 'isComposing' in boot), ('Esc đóng + trả focus (open/close)', "e.key === 'Escape'" in ui and 'back.focus()' in ui)]
for n, ok in chk:
    print(('OK   ' if ok else 'FAIL ') + n); ok or bad.append(n)
sys.exit(1 if bad else 0)

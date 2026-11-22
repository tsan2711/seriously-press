Thả file `*.toml` vào đây để thêm nguồn, KHÔNG sửa mã. Mỗi nguồn:
  [[feed]]
  desk = "gamedev"          # ban nhận (bắt buộc; ban phải có trong config/desks/)
  id = "ten-ngan"           # duy nhất
  name = "Tên hiển thị"
  url = "https://…/feed"    # RSS/Atom
  roles = ["marketing"]     # tuỳ chọn: chỉ gợi ý cho vai trò này (không lọc bài)
Bài mới tự gắn chủ đề theo từ khoá trong config/topics.toml (không khớp → chủ đề đầu của ban).
Muốn thêm chủ đề/ban mới: thêm khối [topic.x] vào topics.toml hoặc file config/desks/<ban>.toml.

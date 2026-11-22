# Worker chia sẻ (tuỳ chọn, Cloudflare free) — việc cần Bi: tài khoản Cloudflare
Không có Worker thì site vẫn chạy đủ (hồ sơ, gu, đồng bộ mã); chỉ ẩn "Mọi người thấy hay".
1. `npm i -g wrangler && wrangler login`
2. `wrangler kv namespace create PRESS` → ghi id vào `wrangler.toml` (mẫu dưới)
3. Không có secret nào (không admin/tài khoản). Đặt `PROXY_HOSTS` = `python3 press.py hosts` (proxy `/fetch` cho nút Chạy báo).
4. Sửa `ALLOW_ORIGIN` = origin Pages (vd `https://<user>.github.io`), `wrangler deploy`
5. Điền URL Worker vào `config/share.toml` (`endpoint = "https://….workers.dev"`), build lại.
6. Gửi một URL trang cho mọi người — không mời, không đăng nhập.
Giới hạn free: 100k request/ngày, 1k ghi KV/ngày. Chia sẻ: ≤10/ngày/máy, ≤30/ngày/IP, ≤300/ngày toàn cục.

```toml
# wrangler.toml
name = "press-share"
main = "share-worker.js"
compatibility_date = "2026-11-01"
kv_namespaces = [{ binding = "PRESS", id = "<id từ bước 2>" }]
[vars]
ALLOW_ORIGIN = "https://<user>.github.io"
PROXY_HOSTS = "<kết quả python3 press.py hosts>"
```

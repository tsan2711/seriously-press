#!/bin/sh
# Xuất site/ sạch ra thư mục $1 (repo công khai). Loại: launchd/ (đường dẫn máy), public/ (CI tự build), __pycache__, store/journals, cache tải về store/feeds + store/commons (nội dung thô của bên thứ ba, có email; CI tự tải lại).
set -e
OUT="${1:?usage: publish_export.sh <dir>}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT"
cd "$HERE"
git ls-tree -r --name-only HEAD . |   # từ HEAD (không phụ thuộc index — phiên khác có thể đang giữ index.lock)
   grep -v -e '^launchd/' -e '^public/' -e '^store/journals/' -e '^store/feeds/' -e '^store/commons/' -e '^topics.toml$' | while read -r f; do
  mkdir -p "$OUT/$(dirname "$f")"; cp "$f" "$OUT/$f"
done
ln -sf config/topics.toml "$OUT/topics.toml"

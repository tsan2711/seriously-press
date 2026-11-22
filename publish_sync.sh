#!/bin/sh
# Đẩy site/ sạch lên repo công khai tsan2711/seriously-press (check_publish chạy trước). Dùng: sh site/publish_sync.sh
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"; W="${TMPDIR:-/tmp}/press-pub-sync"
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE
rm -rf "$W" && git clone -q https://github.com/tsan2711/seriously-press.git "$W"
E="$W.export"; rm -rf "$E"; sh "$HERE/publish_export.sh" "$E"
python3 "$HERE/tests/check_publish.py" "$E"
rsync -a --delete --exclude .git "$E/" "$W/"
cd "$W" && git add -A && { git diff --cached --quiet && echo "không đổi" || { git -c user.name=tsan2711 -c user.email=tsan2711@users.noreply.github.com commit -qm "Bản Tin: đồng bộ từ site/" && git push -q && echo "đã đẩy"; }; }

#!/bin/sh
# Chạy hằng ngày bởi launchd. Chỉ ghi vào store/, public/ và knowledge/daily-metrics.md. KHÔNG push gì.
cd "$(dirname "$0")" && python3 press.py all && python3 metrics.py

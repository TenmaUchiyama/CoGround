#!/usr/bin/env bash
# どこからでも `fetch_check ...` で呼べるようにするラッパー
source /etc/ros_env.sh
exec python3 -m fetch_check.cli "$@"

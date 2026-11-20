#!/usr/bin/env bash
# コンテナ (root) からホストのデスクトップ (横のモニタ) に RViz / Gazebo を出せるようにする。
# SSH 越しの make でも効くよう、ログイン中のデスクトップ (:0) を対象にする。失敗しても止めない。
D="${DISPLAY_OVERRIDE:-:0}"
if ! command -v xhost >/dev/null; then
  echo "[allow_x] xhost がありません (sudo apt install x11-xserver-utils)。画面が出ないかもしれません" >&2
  exit 0
fi
# XAUTHORITY が無い (SSH) ときは GDM / 通常の場所を探す
if [ -z "${XAUTHORITY:-}" ] || [ "$D" != "${DISPLAY:-}" ]; then
  for f in "/run/user/$(id -u)/gdm/Xauthority" "$HOME/.Xauthority" /run/user/$(id -u)/.mutter-Xwaylandauth.*; do
    [ -f "$f" ] && { export XAUTHORITY="$f"; break; }
  done
fi
if DISPLAY="$D" xhost +local:docker >/dev/null 2>&1; then
  echo "[allow_x] $D への表示を許可しました"
else
  echo "[allow_x] $D に xhost できませんでした。横のモニタでログインした端末から 'xhost +local:docker' を一度実行してください" >&2
fi
exit 0

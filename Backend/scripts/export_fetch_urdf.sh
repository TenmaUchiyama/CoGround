#!/usr/bin/env bash
# fetch-sim イメージから Fetch の URDF とメッシュを Unity プロジェクトへ書き出す
# 使い方: bash scripts/export_fetch_urdf.sh   (先に docker compose build しておくこと)
# 出力:   UserApp/CoGround/Assets/URDF/Fetch/fetch.urdf
#         UserApp/CoGround/Assets/URDF/Fetch/fetch_description/meshes/...
# Unity では fetch.urdf を右クリック → "Import Robot from Selected URDF file"
set -euo pipefail

IMAGE="${IMAGE:-coground/fetch-sim:noetic}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${1:-$SCRIPT_DIR/../../UserApp/CoGround/Assets/URDF/Fetch}"

mkdir -p "$OUT_DIR"
OUT_DIR="$(cd "$OUT_DIR" && pwd)"

# package://fetch_description/... を URDF Importer が解決できるよう、
# URDF と同じフォルダに fetch_description/ を置く
docker run --rm --entrypoint bash -v "$OUT_DIR:/out" "$IMAGE" -c '
  set -e
  PKG=/opt/ros/noetic/share/fetch_description
  rm -rf /out/fetch_description
  mkdir -p /out/fetch_description
  cp -r "$PKG/meshes" /out/fetch_description/
  cp "$PKG/package.xml" /out/fetch_description/
  cp "$PKG/robots/fetch.urdf" /out/fetch.urdf
'
echo "書き出し完了: $OUT_DIR"
ls "$OUT_DIR" "$OUT_DIR/fetch_description/meshes" | head -50

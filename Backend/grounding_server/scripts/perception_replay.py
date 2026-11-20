"""記録したフレーム（logs/sequences/<名前>/<番号>/{rgb.jpg, depth.bin, meta.json}）を、順に perception に流し直す。

Quest で 1 回記録すれば、あとは PC だけでしきい値や処理を変えて同じ入力で確かめられる（ロードマップの「PC で先に検証」）。
grounding_server のコンテナの中で動かす:

  docker compose exec grounding_server python scripts/perception_replay.py logs/sequences/phase0_initial --reset
  docker compose exec grounding_server python scripts/perception_replay.py logs/sequences/a logs/sequences/b --reset

--reset  始める前に記憶と追跡を全部消す（同じ記録を何度も試すとき）
フォルダを複数渡すと、続けて流す（例: 初期状態 → 視点変更 → 移動）。
"""

import argparse
import sys
from pathlib import Path

import httpx


def frames(directory: Path) -> list[Path]:
    if (directory / "meta.json").exists():
        return [directory]
    return sorted(p for p in directory.iterdir() if (p / "meta.json").exists())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sequences", type=Path, nargs="+")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    with httpx.Client(base_url=args.server, timeout=300) as client:
        if args.reset:
            client.delete("/perception/memory").raise_for_status()
            print("memory and tracks reset")
        total_calls = 0
        for sequence in args.sequences:
            for frame in frames(sequence):
                files = {"rgb": ("rgb.jpg", (frame / "rgb.jpg").read_bytes(), "image/jpeg"),
                         "depth": ("depth.bin", (frame / "depth.bin").read_bytes(), "application/octet-stream")}
                response = client.post("/perception/frame", files=files,
                                       data={"meta": (frame / "meta.json").read_text(encoding="utf-8")})
                if response.status_code != 200:
                    print(f"{frame}: HTTP {response.status_code}: {response.text}", file=sys.stderr)
                    return 1
                r = response.json()
                total_calls += r["vlm"]["calls"]
                f = r["frame"]
                print(f"\n{frame}  run={r['run_id']}  vlm_calls={r['vlm']['calls']}  located={f['located']}/{len(r['objects'])}  "
                      f"depth={f['depth_coverage']:.0%}  total={r['timings_ms']['total']:.0f}ms")
                for o in r["objects"]:
                    position = ", ".join(f"{v:+.2f}" for v in o["position"]) if o.get("position") else "-"
                    print(f"  [{o['detection_id']}] {o['object_id'] or '-':<8} {o['track'] or o['source']:<9} {o['class']:<14} "
                          f"-> {o['category'] or '-':<14} {o['attributes'].get('fragility', '-'):<15} ({position})")
                for key in ("displaced", "missing"):
                    if f[key]:
                        print(f"  {key}: {f[key]}")
                if f["merged"]:
                    print(f"  merged: {f['merged']}")
        stats = client.get("/perception/memory").json()["stats"]
        print(f"\nVLM calls in this replay: {total_calls}\nmemory: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

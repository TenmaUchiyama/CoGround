"""画像を perception に流して、結果を表にして出す（Milestone 1 の確認用）。

grounding_server のコンテナの中で動かす（tests/ と scripts/ はマウントされている）:

  docker compose exec grounding_server python scripts/perception_run.py tests/images/scene_initial.jpg
  docker compose exec grounding_server python scripts/perception_run.py tests/images/scene_initial.jpg --repeat 10
  docker compose exec grounding_server python scripts/perception_run.py tests/images/ --reset
  docker compose exec grounding_server python scripts/perception_run.py a.jpg --object-ids mug_a,cup_b,glass_c

--repeat N   同じ画像を N 回送る。VLM を呼ぶのが初回の 1 回だけかを最後に判定する
--reset      始める前に記憶を全部消す
--reanalyze  属性があっても VLM に聞き直す
残るファイル（入力・分割結果・SoM 画像・JSON）は logs/perception/<run_id>/。ブラウザなら /perception/ui。
"""

import argparse
import io
import sys
from pathlib import Path

import httpx
from PIL import Image


def as_jpeg(path: Path) -> bytes:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return path.read_bytes()
    buffer = io.BytesIO()
    with Image.open(path) as image:
        image.convert("RGB").save(buffer, "JPEG", quality=92)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("input", type=Path, help="画像、または画像の入ったフォルダ")
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--object-ids", help="検出の左からの順に付ける ID（カンマ区切り）")
    parser.add_argument("--reanalyze", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    files = [args.input] if args.input.is_file() else sorted(
        p for p in args.input.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    if not files:
        parser.error(f"no images in {args.input}")
    params = {}
    if args.object_ids:
        params["object_ids"] = args.object_ids
    if args.reanalyze:
        params["reanalyze"] = "true"

    ok = True
    with httpx.Client(base_url=args.server, timeout=300) as client:
        if args.reset:
            client.delete("/perception/memory").raise_for_status()
            print("memory reset")
        for path in files:
            data = as_jpeg(path)
            calls = []
            for n in range(1, args.repeat + 1):
                response = client.post("/perception/analyze", params=params, content=data,
                                       headers={"Content-Type": "image/jpeg"})
                if response.status_code != 200:
                    print(f"{path.name} #{n}: HTTP {response.status_code}: {response.text}", file=sys.stderr)
                    return 1
                result = response.json()
                calls.append(result["vlm"]["calls"])
                t = result["timings_ms"]
                print(f"\n{path.name} #{n}  run={result['run_id']}  objects={len(result['objects'])}  "
                      f"vlm_calls={result['vlm']['calls']}  segment={t.get('segment', 0):.0f}ms  "
                      f"vlm={t.get('vlm', 0):.0f}ms  total={t['total']:.0f}ms")
                if result["vlm"].get("error"):
                    print(f"  VLM error: {result['vlm']['error']}")
                if n == 1 or result["vlm"]["calls"]:
                    for o in result["objects"]:
                        a = o["attributes"]
                        print(f"  [{o['detection_id']}] {o['object_id']:<10} {o['class']:<15} -> {o['category'] or '-':<15} "
                              f"{a.get('material', '-'):<8} {a.get('fragility', '-'):<15} {o['vlm_status']:<9} "
                              f"v{o['attribute_version']} ({o['source']})  {a.get('appearance', '')}")
            if args.repeat > 1:
                # 初回は新しい物体があれば 1 回、2 回目からは 0 回のはず
                passed = sum(calls[1:]) == 0
                ok = ok and passed
                print(f"\n{path.name}: {args.repeat} requests -> VLM called {sum(calls)} time(s) "
                      f"(per request: {calls})  {'PASS' if passed else 'FAIL: repeated requests called the VLM again'}")
        stats = client.get("/perception/memory").json()["stats"]
        print(f"\nmemory: {stats}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

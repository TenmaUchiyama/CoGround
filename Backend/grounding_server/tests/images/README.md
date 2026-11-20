# テスト画像（Phase 0）

perception（検出 → SoM → VLM → 記憶）を、毎回同じ入力で確かめるための写真を置く。
材質や見た目の違う物体を 3 つ（例: 陶器のマグ、プラスチックのコップ、ガラスのコップ）机に並べて撮る。

| ファイル | 撮るもの | 使う Phase |
| --- | --- | --- |
| `scene_initial.jpg` | 3 つが並んでいる最初の状態 | 1〜3 |
| `scene_view_left.jpg` / `scene_view_right.jpg` | 同じ並びを、カメラを左右に振って撮る | 5（再認識） |
| `scene_moved.jpg` | 1 つを別の位置に移した | 6（変化の検出） |
| `scene_added.jpg` / `scene_swapped.jpg` | 物体を足した / 1 つを入れ替えた | 6 |

動画（視点の移動）は `tests/sequences/` に置く。

確かめ方:

```
docker compose exec grounding_server python scripts/perception_run.py tests/images/scene_initial.jpg --reset --repeat 10
```

またはブラウザで `http://<host>:8000/perception/ui`。

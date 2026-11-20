# fetch_real — 実機 Fetch の確認ツール

実機 Fetch の上で動かす Docker イメージ。Fetch で「何ができて、何ができないか」を **安全な順に 1 つずつ確かめる** ための `fetch_check` が入っている。

- いま（段階 A）: **読むだけ**の確認（level 0）と CLI
- 次（段階 B）: 首・グリッパー・胴・台車を少し動かす確認（level 1）、MoveIt / Navigation（level 2）
- その次（段階 C）: Web UI（ブラウザで 1 つずつ実行、ライブ表示、全停止）

全体の計画と手順は `Backend/docs/REAL_FETCH_QUICKSTART.md`。

---

## しくみ

```
┌─────── Fetch 本体 ──────────────────────────────┐
│ 出荷時のまま: roscore, ドライバ, コントローラ, カメラ  │
│        ▲ ROS (localhost:11311)                    │
│ ┌──── Docker: fetch_real (Noetic, 画面なし) ────┐  │
│ │ fetch_check … 確認項目を実行して結果を出す     │  │
│ └────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

- `roscore` は **Fetch 本体のものを使う**。このコンテナでは起動しない
- `network_mode: host`（ROS の通信はポートを固定できないため）
- シムで試すときは、`fetch_sim` コンテナのネットワークに相乗りして、シムの `roscore` を使う

---

## クイックスタート（シムで試す）

Fetch に載せる前に、手元のシム（`fetch_sim`）で動きを確かめる。

```bash
cd Backend
make up               # シムを起動 (動いていれば不要。カメラやレーザーも見たいなら make gazebo-headless)
make real-build       # 初回 / Dockerfile を変えたとき
make real-sim-check   # シムにつないで level 0 を全部実行
```

結果の例（Gazebo なしのシム）:

```
PASS  sys.master           http://localhost:11311 / ノード 20 / トピック 120
PASS  sys.nodes            19 ノードすべてに届いた
SKIP  sys.battery          BatteryState のトピックが無い (シムには無い)
WARN  sys.planners         起動していない: amcl (自己位置推定), /map (地図)
PASS  sense.joint_states   60.0 Hz
...
PASS 4  WARN 2  FAIL 0  SKIP 9
```

| 表示 | 意味 |
|---|---|
| **PASS** | OK |
| **WARN** | 動くが気になる（周期が低い、地図がない、時計がずれている…）。`→` の行に次に見ること |
| **FAIL** | できない / 壊れている。`→` の行に次に見ること |
| **SKIP** | このモードでは確かめられない（シムにバッテリーは無い、など） |

ほかの使い方:

```bash
make real-sim-check CHECK="'sense.*' -v"     # センサーだけ、測った値も表示
make real-sim-shell                          # コンテナに入る (中で fetch_check list / run ...)
make real-sim-down                           # 止める
```

コンテナの中では:

```bash
fetch_check list -v                 # 確認項目の一覧と説明
fetch_check run                     # level 0 を全部
fetch_check run sys.battery sense.tf
fetch_check run 'sense.head_*' -v   # パターンで選ぶ ('' で囲む)
fetch_check run --duration 5        # トピックを長めに測る
```

結果は毎回 `docker/fetch_real/reports/日時-モード.json` に保存される（git には入らない）。

---

## 実機 Fetch に載せる（まだやらない。手順だけ）

事前に管理者に確認: Fetch に Docker が入っているか / 入れてよいか、ディスクの空き（イメージは約 2.3 GB）。

```bash
# 手元の PC で
cd Backend
make real-build
make real-save                                   # -> fetch-real.tar.gz
scp fetch-real.tar.gz fetch@fetch1:
scp -r docker/fetch_real fetch@fetch1:fetch_real # compose.yaml とソース

# Fetch で
ssh fetch@fetch1
docker load < fetch-real.tar.gz
cd fetch_real
docker compose up -d                             # 常駐 (Fetch を再起動しても自動で起動する)
docker exec -t fetch_real fetch_check run        # 確認
```

Fetch 上で Makefile を使う場合は、`Backend/` ごと置いて `make real-up` / `make real-check` でもよい。

### 自分の PC から Fetch を確認する（Docker を Fetch に置かない場合）

```bash
ROS_MASTER_URI=http://fetch1:11311 ROS_IP=<自分のIP> make real-up
make real-check
```
このとき `sys.master` / `sys.nodes` がネットワーク設定の誤り（`ROS_IP` 未設定、ホスト名が引けない）を教えてくれる。

---

## 確認項目（level 0 = 読むだけ）

| ID | 何を見る | FAIL / WARN になる例 |
|---|---|---|
| `sys.master` | roscore に届くか、自分の名乗るホスト名 | マスターが別マシンなのに自分の名前が 127.x |
| `sys.nodes` | 全ノードに直接届くか | 「トピックは見えるのにデータが来ない」の原因 |
| `sys.runstop` | ランストップ（`RobotState.runstopped`） | ランストップ中 → WARN、ドライバ異常 → FAIL |
| `sys.battery` | 残量 | 30% 未満 WARN / 15% 未満 FAIL |
| `sys.controllers` | 腕・胴・首・グリッパーのアクション、台車の速度指令、コントローラの状態 | 無い / error 状態 |
| `sys.diagnostics` | `/diagnostics` の ERROR / WARN | モーター・ボードの異常 |
| `sys.planners` | move_group / move_base / amcl / `/map` | 起動していないだけなら WARN |
| `sense.joint_states` | 周期、全関節が出ているか | 関節が欠けている |
| `sense.base_scan` | レーザー：周期、有効な距離の割合 | レーザーが塞がれている |
| `sense.odom` / `sense.imu` | 周期 | 遅い / 来ない |
| `sense.head_rgb` / `head_depth` / `head_points` | 頭のカメラ：周期、解像度 | 遅い（Wi-Fi の帯域）/ 来ない |
| `sense.tf` | odom→base_link、腕、カメラ、map→odom | つながっていない |

すべてのセンサー項目は **時刻のずれ**（受信時刻 − `header.stamp`）も見る。0.5 秒を超えたら WARN（PC と Fetch の時計が合っていない）。

---

## 確認項目を足す

`ros_pkgs/fetch_check/src/fetch_check/checks/` に関数を書いて `@check` を付けるだけ。Web UI（段階 C）にも自動で出る。

```python
from ..core import check, ok, warn, fail
from .. import ros_util as ru

@check("sense.wrist_ft", 0, "手首の力センサー", "例: 周期を見る")
def wrist_ft(ctx):
    s = ru.sample_topic("/wrist_ft", ctx.duration)
    if s.count == 0:
        return ctx.missing("/wrist_ft が来ない")   # 実機なら FAIL、シムなら SKIP
    return ok(f"{s.rate_hz:.0f} Hz", **s.summary_details())
```

- ソースはコンテナにマウントしてあるので、**保存して次の `fetch_check run` から反映**（再ビルド不要）
- 新しい ROS の型（msg）を使うときは Dockerfile の apt に追加して `make real-build`

| ファイル | 役割 |
|---|---|
| `core.py` | Check の登録 (`@check`)・実行 (`run_check`)・結果の型 (`Result`, `Status`) |
| `ros_util.py` | トピックの周期を測る (`sample_topic`)、ノードへの到達確認 (`ping_nodes`) など |
| `checks/system.py` | `sys.*` |
| `checks/sensors.py` | `sense.*` |
| `cli.py` | `fetch_check list / run` |

---

## 注意

- Fetch 出荷時の ROS は **Melodic** のことが多い。このコンテナは **Noetic**。標準のメッセージは通信できるが、確認は実機で初めて行う
- トピック名（`/battery_state`, `RobotState`, `/cmd_vel` か `/base_controller/command` か）は Fetch の構成で違うことがある。違っていたら `checks/` を直す
- 段階 A の確認は **ロボットを動かさない**。動かす確認（level 1 以上）は段階 B で、モーション許可を付けたときだけ動く

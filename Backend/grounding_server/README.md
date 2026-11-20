| **ルールバンク**（ルールを一覧・登録・訂正・削除する） | http://localhost:8000/rules |
# CoGround Grounding Server

ルールのグラウンディング（ルールのコンパイル、属性推定、適用判定、説明）を担うサーバー。Unity（Quest）とは WebSocket でつながる。
ROS（`Backend/docker/fetch_sim`）とは別のプロセスで、別のコンテナで動く。

```
 Unity (Quest / Editor)                         grounding_server (FastAPI, :8000)
  CoGroundServerClient ── ws://<host>:8000/ws ──>  Session ─ Router ─ handlers/*
                                                    │
                                                    └─ Services (StateStore, Hub, LLM; 後で VLM / clingo)
  ROS-TCP-Connector ──── :10000 ──> fetch_sim (ROS1 / MoveIt)   ← こちらとは独立
```

`scene.update` で受け取ったシーンと、ルール（片付けルール `rules.set` / `rules.compile` と家庭ルール `norms.set` / `norms.compile`）から Plan を作り、全クライアントに配る。
動作計画（`motion.*`。台車の移動も含めて、動かさずに計画し、通しで見返せる）と、Plan の実行（`exec.*`）もここが受け持つ：
step を 1 つずつロボットに実行させ、実行中も止める・飛ばす・行き先を変えることができる（「Plan（動作計画）を作る」「Plan を実行する」）。
画像からの物体の認識・属性の推定・記憶は `perception/`（「物体の認識・属性・記憶（perception）」）。

## 起動

Docker で動かす（WSL に python3-venv が無くてもよい。Docker Desktop が Windows の 8000 番を公開するので Quest からも届く）。
すべて `Backend/grounding_server` で実行する。

| やりたいこと | コマンド |
|---|---|
| ビルド（初回、`pyproject.toml` を変えた後） | `make build` |
| 起動（コードを変えると自動で再起動） | `make up` |
| ログを見る（リアルタイム。詳しくは「ログを見る」） | `make logs` / `docker logs -f coground_grounding_server` |
| テスト | `make test` |
| 疎通確認（WebSocket で `system.ping`） | `make ping` |
| 停止 | `make down` |
| 死活確認 / 状態 / method 一覧 | `curl localhost:8000/health` / `/api/state` / `/api/protocol` |
| ブラウザで REST を確認 | http://localhost:8000/docs |
| **テスト画面**（Unity の代わりにブラウザから試す） | http://localhost:8000/ui （別の PC からは `http://<サーバーの IP>:8000/ui`） |

### テスト画面（`/ui`）

ブラウザで開くと、Unity と同じ WebSocket（`/ws`）でサーバーにつながる。Unity とつないだままでも使える（状態は全員に配られる）。

- **シーン**: 上から見た図。「サンプルのシーンを送る」で机の上のシーン、「棚のシナリオを送る」でシーンとルールを送る（`tests/fixtures` の JSON）。物をドラッグすると、その位置で `scene.update` を送り、Plan が作り直される
- **物体**: サーバーが受け取って持っている物体の表（種類、出どころ・検出の確信度、いまの場所）。「行き先」を選ぶと、その物をそこへ運ぶ step ができる（`plan.place`）。ルールは見ない
- **ルール**: 言葉で足す（`rules.compile`、LLM）か、属性・値・行き先を選んで足す（`rules.set`）。1 つずつ消せる
- **Plan**: step の表。行にマウスを置くと、図の矢印が太くなる。動作計画・実行の状態と、step ごとの「飛ばす」「やり直す」もここ。
  「Plan（動作計画）を作る」で計画すると、シーケンスバー（再生 / つまみ / 区切りの帯）が出て、図に台車の通り道・止まる位置・台車・運ぶ物が出る。行をクリックすると、その step の始まりへ飛ぶ
- **実行**: 実行（先に動作計画が要る。「Plan なしでも実行」で省ける） / 区切りで止める / いますぐ止める / 続ける、確認と失敗の方針、わざと失敗させる（`exec.*`）。Unity も ROS も無しで、代役のロボットで試せる
- **ロボット単体テスト**（右上）: Plan を通さずにスキルを 1 つだけ動かす（`robot.*`）。
  どちらも「Plan」で先に動かさずに計画できる（`robot.plan`）。計画は Unity の Ghost（`CoGroundTaskPlanPlayer`）が再生し、Web UI には結果と区切りの帯が出る。
  MoveIt: ロボットが机の前にいる前提で、物体の一覧の「Plan」→「Pick（計画どおり）」でその場でつかむ / 「元の場所へ戻す」。横幅がどちら向きも 9 cm 以上の物には ⚠（指の間に入らない）。
  Nav: 図をクリック（ドラッグで向き）するか座標・家具の止まる位置を選び、「Plan」で経路を確かめて「Goal へ移動」（move_base。ROS は NAV=true）
- **method を直接呼ぶ**: すべての method を、params の JSON を書いて呼べる（stream と中断も）
- **通信のログ**: 送ったもの・届いたものを新しい順に表示する

画面は `coground_server/static/ui.html` の 1 ファイル（ビルド不要）。書き換えたら、ブラウザを読み込み直すだけでよい。

### ルールバンク（`/rules`）

ルールの管理だけを行う画面（テスト画面のヘッダーの「ルールバンク」からも開ける）。同じ WebSocket につなぐので、テスト画面や Unity と同時に開いても状態はそろう。

- **一覧**: 家庭ルール（義務・禁止・許可）と片付けルールを 1 つの表に並べる。許可（例外）は元の禁止の下に出る。種類・文字で絞り込め、家の時計でいま効くかを出す
- **詳細**: いつ・対象・要求と、いまのシーンで対象になる物体。いつ効くかの訂正（`rules.update`）、例外を足す（`rules.add_exception`）、JSON で直す・複製・消す（`norms.set` / `rules.set`）
- **言葉で登録**: `norms.compile`（家庭ルール）か `rules.compile`（片付けルール）。範囲や解除時刻が決まらないものは「登録の途中」に入り、領域と解除時刻を選んで確定する（`rules.confirm` / `rules.discard_pending`）
- **フォームで作る**: ひな形（領域に入らない・物に触らない・物を置く・子供が近いと止まる・例外・片付け）から埋めて登録する
- **書き出す / 読み込む**: いまのルールを JSON に書き出す。読み込むと、いまのルールを置き換える

**ルールは `data/rule_bank.json` に自動で残る**（`coground_server/rulebank.py`）。家庭ルール・片付けルール・住人が決めた領域・登録の途中のルールが変わるたびに書き出し、
サーバーを起動したときに読み込むので、再起動（コードを変えたときの自動の再起動も）で消えない。シーン・依頼・Plan は残さない。

- ファイルの場所は `COGROUND_RULE_BANK`（compose.yaml。空にすると残さない）。コンテナの `/app/data` はホストの `./data`
- 読めないファイルは `rule_bank.json.broken` に退避して、空から始める
- 片付けルールも残るが、Unity の `CoGroundRulesSender` がつながるたびに `rules.set` で置き換える
- テスト（`make test`）は本物のファイルに触らない（`tests/conftest.py`）

画面は `coground_server/static/rules.html` の 1 ファイル。

確認用クライアント（コマンドライン）:

```bash
docker compose exec grounding_server python scripts/ws_client.py call debug.count '{"count": 5}'
docker compose exec grounding_server python scripts/ws_client.py call scene.update @tests/fixtures/tabletop_scene.json
docker compose exec grounding_server python scripts/ws_client.py listen     # event を見続ける
```

### ログを見る

`make up` はコンテナをバックグラウンド（`-d`）で起動する。バックグラウンドのままでも、ログはリアルタイムで見られる。

```bash
docker logs -f coground_grounding_server          # どこからでも（-f で流し続ける。--tail 100 で直近から）
make logs                                         # Backend/grounding_server で
```

`Ctrl+C` で止まるのはログの表示だけで、サーバーは動き続ける。Docker Desktop でも Containers → `coground_grounding_server` → Logs で見られる。

- **`docker attach` は使わない。** サーバーのプロセスに直接つながるので、そこで `Ctrl+C` を押すとサーバーが止まる。
- ログを起動したターミナルに出したいときは、`-d` を付けずに `docker compose up` で起動する（この場合は `Ctrl+C` でサーバーも止まる）。

ログの例（1 つの request につき、受信と結果の 2 行が出る）:

```
session 8d9f3818: connected from 172.22.0.1:59690       ← Unity が接続した
session 8d9f3818: system.ping [u-1] <- request           ← 要求が届いた（[ ] は request の id。Unity は u-N）
session 8d9f3818: system.ping [u-1] -> ok (1ms)          ← 応答した（ok / error / cancelled と処理時間）
state v1 -> 2 client(s)                                  ← state.updated を全クライアントに送った
session 626083f8: nope [cli-1] rejected: unknown_method  ← 処理する前に断った（WARNING）
```

届いた event の中身まで見たいときは、`compose.yaml` の `COGROUND_LOG_LEVEL` を `debug` にして `make down && make up`。

### Quest から接続する

`ws://<Windows の LAN IP>:8000/ws`。ROS-TCP（10000 番）と同じように Windows のファイアウォールを開ける（管理者 PowerShell）:

```powershell
New-NetFirewallRule -DisplayName "CoGround grounding server 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
```

## プロトコル

1 メッセージ = 1 つの JSON オブジェクト（テキストフレーム）。`type` で 4 種類を分ける。

| 通信の形 | 流れ | 用途の例 |
|---|---|---|
| 要求→応答（REST のような通信） | `request` → `response` | `scene.update`、`state.get` |
| 要求→途中経過→応答（ストリーム①） | `request` → `stream` × 0..N → `response` | ルールのコンパイルの進捗、VLM の結果を順に返す |
| 通知（ストリーム②） | `event`（どちら向きも可、返事なし） | `state.updated`、`client.log` |
| 中断 | `cancel` | 長い LLM 呼び出しを止める |

### Unity → サーバー

```jsonc
{"type": "request", "id": "u-1", "method": "scene.update", "params": {...}}  // params は省略可
{"type": "cancel",  "id": "u-1"}
{"type": "event",   "event": "client.log", "data": {"level": "info", "message": "..."}}
```

### サーバー → Unity

```jsonc
{"type": "response", "id": "u-1", "ok": true,  "result": {...}}
{"type": "response", "id": "u-1", "ok": false, "error": {"code": "invalid_params", "message": "...", "details": ...}}
{"type": "stream",   "id": "u-1", "data": {...}}
{"type": "event",    "event": "state.updated", "data": {...}}
```

### 約束事

- **1 つの request には必ず 1 つの response が返る**（成功・失敗・キャンセルのどれか）。`stream` は必ずその `response` より前に届く。
- `id` はクライアントが決める（接続内で一意。処理中の id を再利用すると `duplicate_id`）。
- request は並行に処理される。応答の順番は送った順とは限らないので、`id` で突き合わせる。
- 終わった request への `cancel` は無視される（行き違いは普通に起きる）。
- id の分からない不正なメッセージには `session.error` イベントで知らせる。接続は切らない。
- **状態は差分ではなく全体を送る。** 状態が変わるたびに `version` を 1 増やした全体を `state.updated` で全員に送る。接続直後にも送るので、再接続すれば最新に戻れる。
- 座標は Unity のワールド座標（メートル、左手系、Y 上）。ベクトルは `[x, y, z]`、回転は `[x, y, z, w]`。物体 ID は Unity が決め、MoveIt の collision object 名と揃える。

### エラーコード（`error.code`）

| code | 意味 |
|---|---|
| `bad_message` | JSON として読めない / メッセージの形式が違う |
| `unknown_method` | method が無い（`details.available` に一覧） |
| `invalid_params` | params がスキーマに合わない（`details` に Pydantic のエラー） |
| `llm_failed` | LLM を呼べなかった（認証が無い、時間切れなど） / 決めた型の答えが返らなかった |
| `duplicate_id` | 同じ id の request が処理中 |
| `cancelled` | `cancel` で止めた |
| `invalid_state` | いまの状態ではできない（実行中ではないのに `exec.pause` など。`details.execution` にいまの状態） |
| `internal_error` | サーバー内の想定外の例外 |
| （Unity 側のみ）`not_connected` / `timeout` / `disconnected` | `CoGroundServerClient` が出す |

### サーバーからのイベント

| event | data |
|---|---|
| `session.welcome` | `{session_id, server_version, protocol_version, methods}`（接続直後） |
| `state.updated` | `{version, updated_at, scene: {frame, objects, regions}, rules, placements, plan, norms, task, clock, corrections, motion, execution}`（`norms` / `task` / `clock` / `corrections` は「家庭ルールと依頼」。`motion` は動作計画の要約、`execution` は実行の状態。「Plan（動作計画）を作る」「Plan を実行する」。`plan` は計画が無ければ `null`。`placements` は手で指定した行き先 `[{object_id, target_region}]`） |
| `session.error` | `{code, message, details?}` |

### method（現在）

| method | params | result |
|---|---|---|
| `system.ping` | なし | `{pong, server_time}` |
| `system.reset` | なし（まっさらにする: 実行・動作計画・単体テストの計画を止めて消し、ロボットの持っている物を忘れ、腕を初期姿勢へ戻す。ROS の latch した古い計画・経路も消える。ルールとシーンの物体は残す。Web UI の「まっさらにする」） | `{ok, detail, robot}` |
| `system.describe` | なし | method と params スキーマの一覧 |
| `state.get` | なし | `state.updated` と同じ全体状態 |
| `scene.update` | `SceneSnapshot`（`coground_server/models.py`、例は `tests/fixtures/tabletop_scene.json`） | `{version, objects, regions}` |
| `rules.set` | `{rules: Rule[]}`（片付けルール全体を置き換える。空で消す。家庭ルールの並びに収納先の義務として入り、`norms.set` のルールは消さない） | `{version, rules, steps, unknown_regions}` |
| `rules.compile` | `{text, mode?: append / replace, apply?: bool}`（自然言語 → ルール。LLM を使う） | `{stage}` を stream で送ったあと `{rules, unresolved, applied, version?, steps?}` |
| `plan.place` | `{object_id, target_region}`（物体の行き先を手で指定する。ルールは見ない） | `{version, already_there, step}` |
| `plan.unplace` | `{object_id?}`（手で指定した行き先を消す。省略すると全部） | `{version, placements}` |
| `norms.set` | `{norms: NormRule[]}`（片付けルール以外の家庭ルールを置き換える。空で消す。`rules.set` のルールは消さない） | `{version, norms, steps}` |
| `norms.compile` | `{text, author?, apply?}`（住人の言葉 → 家庭ルール。LLM を使う。範囲が言葉だけでは決まらない・解除時刻が言われていないルールは `pending` に入り、判定には使わない） | `{stage}` を stream で送ったあと `{norms, pending: [{rule, pending_refs, unresolved, notes}], unresolved, applied, version?}` |
| `rules.confirm` | `{rule_id, refs?: {仮の参照: 領域の ID}, until?, keep_open?}`（登録の途中のルールを確定する。足りないものがあれば `invalid_params`。勝手に補わない） | `{version, rule, pending_rules}` |
| `rules.discard_pending` | `{rule_id}`（登録の途中のルールを捨てる） | `{version, pending_rules}` |
| `rules.update` | `{rule_id, from?, until?, requester?}`（家庭ルールの Scope を訂正する。渡した項目だけ変える。例: 19 時からにして） | `{version, correction}` |
| `rules.add_exception` | `{exception_of, requester?, object_id?, where?, from?, until?, original_text?, author?, id?}`（元の禁止に例外を足す） | `{version, rule, correction}` |
| `zones.define` | `{id?, label?, polygon: [[x, y, z], ...]}` か `{..., box}`（住人が決めた床の範囲。Unity ワールド座標。`scene.update` のあとも残る） | `{version, zone, pending_rules}` |
| `zones.update` | `{id, polygon / box, label?}`（範囲を訂正する） | `{version, correction}` |
| `zones.remove` | `{id}` | `{version}` |
| `people.update` | `{people: [{id, kind: child / adult / unknown, position}], valid_for?}`（人の位置を置き換える。見えている間は 1 秒に数回送る） | `{version, people, held}` |
| `monitor.get` | なし | `{held, active, holds, keepout, monitors}`（実行中の監視。hold の記録） |
| `task.request` | `{text, requester?, source_region?, object_ids?, interpret?}`（片付けを依頼する。対象の物体はここで決まる。`source_region` を省略すると、シーンに 1 つだけある机。`interpret: true` で、言葉から対象を LLM に決めさせる） | `{version, task, counts, steps, unresolved}` |
| `task.get` | なし | `{task, counts}`（いまの依頼。無ければ `null`） |
| `task.report` | なし | `{summary, message, counts, rows: [{object_id, exec_state, destination, sentence, reasons, missing, route, holds}], corrections}`（住人に伝える形） |
| `task.close` | なし（依頼を閉じる。記録は残る。Plan は依頼なしの作り方に戻る） | `{version}` |
| `objects.set_attribute` | `{object_id, key, value}`（住人が属性を訂正する。`value: null` で訂正を取り消す） | `{version, correction: {before, after, affected_rule_ids, changes}, counts}` |
| `clock.get` / `clock.reset` | なし（家の時計を読む / 実時刻に戻す） | `{now, tz, overridden, frozen}`（以下 `clock.*` は同じ） |
| `clock.set` | `{time, freeze?}`（`time` は `HH:MM` か ISO 8601。`freeze: true` でその時刻に止める） | |
| `clock.advance` | `{seconds}`（時計を進める） | |
| `motion.plan` | `{step_ids?}`（動作計画を作る。空なら ok の step を全部） | `{step_id, detail}` を stream で送ったあと、`motion` の要約 |
| `motion.get` | なし | `{timeline_id, timeline, step_ids, steps}`（通しで再生する時間軸）。無ければ `null` |
| `motion.clear` | なし（動作計画を捨てる） | `{motion}` |
| `motion.inject_infeasible` | `{object_ids}`（その物体の step を計画できないことにする。代役のロボットのときだけ） | `{infeasible}` |
| `motion.inject_obstacles` | `{polygons}`（床の障害物。Unity の `[x, z]` の多角形。空で消す。代役のロボットのときだけ） | `{obstacles}` |
| `sequence.add` | `{object_id, target_region?, index?}`（step を足す。置き先は収納ルールと照合する。省略するとルールが決める。`index` は挿入位置、省略で最後） | `{version, first_affected, rechecking, steps, preview}`（以下 `sequence.*` は同じ） |
| `sequence.remove` | `{object_id}`（step を外す。その物は動かさない） | |
| `sequence.move` / `sequence.reorder` | `{object_id, index}` / `{object_ids}`（1 つ動かす / 順序をまとめて変える） | |
| `exec.start` | `{step_ids?, allow_unplanned?, preview_id?, revalidate?}`（空なら、検証できた step を全部。渡すと、その step だけをその順に。動作計画が無い・古い step があれば断る。`allow_unplanned: true` で計画なしでも動かす。`preview_id` は下の「シーケンスの編集と、検証済みの予測」） | `{version, execution}`（以下 `exec.*` は同じ） |
| `exec.pause` / `exec.stop` / `exec.resume` | なし（区切りで止める / いますぐ止める / 続きから） | |
| `exec.skip` / `exec.retry` | `{step_id}`（飛ばす / 記録を消してもう一度） | |
| `exec.confirm` | なし（確認待ちの step を進める） | |
| `exec.set_policy` | `{confirm?: auto / each_step, on_failure?: pause / continue}` | |
| `exec.reset` | なし（実行の記録を全部消す） | |
| `exec.inject_failure` | `{skill?: pick / place, detail?}`（次の動きをわざと失敗させる。代役のロボットのときだけ） | `{pending_failures}` |
| `robot.plan` | `{skill: pick, object_id}` / `{skill: navigate, x, z, yaw_deg?}`（単体テスト。動かさずに計画する。pick は台車を動かさない。結果は `/coground/task/plan_result` にも出るので Unity の Ghost が再生する） | `{detail}` を stream したあと `{status: ok / infeasible, reason, duration, stops, timeline}`（timeline は関節角を除く） |
| `robot.pick` | `{object_id, use_plan?}`（単体テスト。台車は動かさずにその場でつかむ。同じ物体の `robot.plan` があれば、その軌道を再生する。計画の後に物体が 2 cm 以上動いていたら使わない） | phase を `{phase, detail}` で stream したあと `{skill, object_id, state, detail, holding}`（失敗も ok の応答で、`state` が failed） |
| `robot.place_back` | `{object_id?}`（単体テスト。持っている物を、つかんだ元の場所へ戻す） | 同上 |
| `robot.navigate` | `{x, z, yaw_deg?}`（単体テスト。Unity のワールド座標の Goal へ台車を動かす。ROS は NAV=true。経路は move_base がその場で作る） | 同上 |
| `robot.cancel` | なし（単体テストのスキルを止める。Plan の実行中は `exec.stop`） | `{robot}` |
| `session.identify` | `{actor: user / llm / script}`（この接続の操作をだれのものとして記録するか） | `{session_id, actor}` |
| `log.tail` | `{n?, type?: rpc / exec / skill / motion}` | `{events}`（直近の記録） |
| `llm.ping` | なし | `{reply}`（LLM に届くかの確認。数秒かかる） |
| `debug.observe_placement` | `{mode: auto / none / 領域の ID}`（置いたあとの配置先の観測をどう返すか。代役のロボットのときだけ） | `{mode}` |
| `debug.count` | `{count, interval}` | `{i, of}` を stream で送ったあと `{done}` |
| `debug.fail` | `{code, message}` | 必ずそのエラーで失敗 |

画像（物体の切り出しなど）は WebSocket に載せず、後で REST のアップロード（`POST /api/images`）を足し、WebSocket では `image_id` だけを送る予定。

## データの型

`coground_server/models.py` にまとめてある（Pydantic）。中心は Plan で、可視化は 2 種類とも同じ Plan を描く。

| 型 | 内容 | 例 |
|---|---|---|
| `SceneSnapshot` / `SceneObject` / `SceneRegion` | いまの状態。物体は `category`、`attributes`（ルール照合用）、`region_id`、`observation` を持つ。領域は `polygon`（床面）か `box`（高さあり） | `tests/fixtures/tabletop_scene.json` |
| `Rule` | `condition`（属性 = 値）と `target_region` | |
| `Utterance` / `InteractionEvent` | タスク実行の入力（音声、実演） | |
| `Plan` / `Step` | 処理の出力。step は `from` / `to` / `rule_id` / `status` / `locked` / `trajectory_id` / `verdicts` | |
| `NormRule` | 家庭ルール（義務・禁止・許可）。`coground_server/norms/model.py` | `tests/test_norms.py` の R1〜R3b |
| `Verdict` | ルールの判定（違反 / 適合 / 非適用 / 未確定、予測か観測か、足りない事実） | |
| `TaskRecord` / `TaskRow` | 依頼の記録。行は物体 1 つ（収納先、ルールごとの判定、実行の状態、判定の履歴）。`coground_server/norms/task.py` | |
| `Correction` | 修正（`move` / `reject` / `reorder`）。どの版の Plan に対するものかを `plan_version` で持つ | |
| `Scenario` | 実験用の台本（最初のシーン、ルール、正しい計画、見せる計画、仕込んだ誤り） | `tests/fixtures/shelf_scenario.json` |
| `TrialLog` | 計測（`view_toggle` / `step_select` / `correction` / `approve`） | |

物体（`SceneObject`）はシミュレーション（Unity 上の仮想物体）と検出で同じ型。違うのは `observation.source`（`simulation` / `detection` / `manual`）と属性の `source`（`ground_truth` / `detector` / `vlm` / `user`）だけ。

- `category` だけ送れば、`role`（`item` / `receptacle` / `surface`）と `group`（`dish` / `cutlery` / `trash` など）はカテゴリ表（`coground_server/taxonomy.py`）から埋める。表に無い category も受け付ける（`item` / `other`）
- 属性は値だけ（`{"fragile": true}` = 真値）か、`{"value", "source", "confidence"}`
- シンク・ごみ箱・机などは `place_zone`（box）を持ち、その物体と同じ ID の領域になる。ルールの `target_region` や Step の `region_id` にそのまま使える
- `region_id` を省略すると、物体の中心を含むいちばん小さい box の領域を入れる
- ルールの条件には属性のほか `category` / `group` / `role` も書ける（`{"attribute": "group", "equals": "dish"}`）
- Unity 側の型は `Assets/Main/Script/Scene/`（`CoGroundSceneTypes.cs`、シミュレーション用の `CoGroundSceneObject`、送信する `CoGroundSceneReporter`）

`Correction` / `TrialLog` を受ける method・event はまだ無い。
ROS 側が動作計画・実行で扱う型は `docker/fetch_sim/ros_pkgs/coground_control/scripts/plan_types.py`（Plan のうちロボットに必要な部分と、軌道）。

## Plan を作る

### ルールは 1 つの並び

片付けルール（`rules.set`、属性 = 値 → 行き先）と家庭ルール（`norms.set`、義務・禁止・許可）は、サーバーでは 1 つの家庭ルールの並び（`state.norms`）に入る。
片付けルールは「置き終わったとき、その領域にあること」という義務に直して持つ（`origin = "tidy"`）。

- `rules.set` は `origin = tidy` だけ、`norms.set` はそれ以外だけを置き換える（ID が重なるとエラー）
- `state.rules` は、片付けルールを元の形（`Rule`）で見たもの。`rules.update` などで訂正して元の形で書けなくなったものは入らない（`norms` には残る）
- テスト画面 `/ui` のルール欄は、片付けルールの表の下に、それ以外の家庭ルールを出す（編集はルールバンク `/rules`）

### 依頼が無いとき

依頼（`task.request`）が無くても、**シーンの運ぶ物（`role = item`）すべてを暗黙の依頼にして、依頼があるときと同じ判定で計画する**（`norms/planner.py`）。
そのため「割れ物に触るな」のような禁止は、依頼が無くても効く（その物は `deferred` の step になる）。違いは次の 2 つ。

- 収納先を決める義務がどれも当てはまらない物は step にしない（依頼があるときは「収納先を決める取り決めが無い」で保留にする）
- 判定は行に記録しない（`task` は `null` のまま。`task.report` は使えない）

収納先を決める義務も手の指定も無ければ（禁止だけなら）、`plan` は `null`。

### 照合のしかた

シーンかルールが変わるたびに、サーバーが Plan を作り直す（LLM は使わない。片付けルールだけのときは、`coground_server/planner.py` と同じ結果になる）。
手で指定した行き先（`plan.place`）がある物は、ルールを照合せずにその行き先へ運ぶ step になる（`rule_id` は `null`、`locked` は `true`）。置いてよいかどうかはサーバーでは確かめない。その物が行き先に入ったら、指定は消える。

1. **ルール照合**: 運ぶ物（`role = item`）ごとに、条件が合うルールを探す
2. **目標**: 合ったルールの `target_region` を行き先にする。すでにそこにある物は step にしない
3. **置き位置**: 行き先の領域の底で、ほかの物と重ならない場所を中央に近い順に探す（床面で見た円どうしの重なり）
4. **順序**: シーンの物体の並び順のまま

| step の `status` | 意味 |
|---|---|
| `ok` | 行き先が決まった。空きが無いときは中央に置き、`message` に書く（シンク・ごみ箱は書かない） |
| `ambiguous` | 合うルールが複数あり、行き先が違う（`to` は `null`、候補は `candidate_rule_ids`） |
| `unmatched` | 合ったルールの行き先の領域がシーンに無い（`to` は `null`、`message` に理由） |

- ルールに合わない物は step にならない。ルールが 1 つも無ければ `plan` は `null`
- step の中身が前と同じなら Plan はそのまま（Unity が同じシーンを送り直しても `id` は変わらない）。変わったら新しい `id`（`plan_1`, `plan_2`, ...）になる
- `base_scene_version` は、その Plan を作ったときの `state.version`

```bash
docker compose exec grounding_server python scripts/ws_client.py call scene.update @tests/fixtures/tabletop_scene.json
docker compose exec grounding_server python scripts/ws_client.py call rules.set '{"rules": [{"id": "r1", "text": "食器はシンクへ", "condition": {"attribute": "group", "equals": "dish"}, "target_region": "sink_1"}]}'
curl -s localhost:8000/api/state | python3 -m json.tool      # plan.steps を見る
```

### 検出した物体の属性（VLM）

ルール照合で読む属性（`fragile`、`trash` など）は、検出した物体（`observation.source = "detection"`）についてはサーバーが付ける（`coground_server/vlm.py`）。
Unity（検出器、VR シミュレーションでは `MockSimulatedObjects`）が送るのは、カテゴリ・位置・大きさまででよい。

- 付けるのは、届いた物体がまだ持っていない属性だけ（Unity や検出器が送った値が優先）。付けた値は `source = "vlm"`
- 住人の訂正（`objects.set_attribute`）は VLM の値よりさらに優先する
- `COGROUND_VLM`: `off`（既定）/ `mock`（`compose.yaml` では `mock`）。`mock` は `COGROUND_VLM_MOCK_FILE`（既定は同梱の `vlm_mock_attributes.json`）の答えを、カテゴリ（`by_category`）か物体 ID（`by_id`、優先）で引いて返す
- 本物の VLM（切り出し画像 `observation.image_id` から推定）は、`AttributeProvider` を実装して `make_attribute_provider` に足す

## 家庭ルールと依頼

住人が登録した取り決め（割れ物に触るな、皿は上段、など）に従って片付ける。設計は `Documents/CoGround_Home_Rules.md`、コードは `coground_server/norms/`。
判定できるのは **接触の禁止（R1）**、**時刻つきの進入禁止（R2）**、**収納先の義務（R3）**、**子供が近くにいる間の停止（R4）**。
R2 と R4 は台車の動きについてのルールで、動作計画と実行中の監視が判定する（下の「台車の動きについてのルール（R2・R4）」）。

流れ:

1. `norms.set` で家庭ルールを入れる（依頼が無くても、運ぶ物すべてに同じ判定をした Plan ができる。上の「依頼が無いとき」）
2. `task.request` で依頼する。**対象の物体はここで決まり、あとでシーンが変わっても選び直さない**（収納した物が机から無くなっても、「2 点中 1 点」の分母は変わらない）
3. 対象ごとに、収納先（R3）と、つかんでよいか（R1）を判定して Plan を作る。運べない物は `deferred` の step になり、行に理由が残る
4. `exec.start` で実行する。置いたあと、**配置先を観測してから**収納済みにする（「Plan を実行する」）
5. `task.report` で、物体ごとの結果と理由を読む
6. `objects.set_attribute`（属性）、`rules.update`（Scope）、`zones.update`（範囲）、`rules.add_exception`（例外）で訂正すると、判定をやり直し、**訂正の前後で変わった項目**を返す

家庭ルールの例（R1 と R3a）:

```jsonc
{"id": "R1", "original_text": "Fragileなものを触るな", "norm": "prohibition",        // obligation / prohibition / permission
 "target": {"kind": "object", "where": {"attribute": "fragile", "equals": true}},  // どの物体に関係するか
 "requirement": {"window": "whole", "predicate": "contact"}}                       // どこを調べ、何を禁止するか
{"id": "R3a", "original_text": "皿は食器棚の上段に、コップは下段に", "norm": "obligation",
 "target": {"kind": "object", "where": {"attribute": "category", "equals": "plate"}},
 "requirement": {"window": "at_place_complete", "predicate": "placed_in", "args": {"region": "shelf_upper"}}}
```

- `scope`: いつ効くか。`{"from": "18:00", "until": null}`（家の時計）、`{"requester": "user_01"}`（その人が依頼したときだけ）、`{"when": {"predicate": "near_child", "args": {"distance": 5.0}}}`（その状態のときだけ）
- `exception_of`: 許可（`permission`）に書くと、その ID の禁止の例外になる（「私が指示したときだけ触ってよい」）。依頼者が分からなければ、例外の成立は未確定
- `rules.set` の片付けルール（属性 = 値 → 領域）は、収納先の義務として一緒に使う。手で指定した行き先（`plan.place`）は、ここでもルールより先

判定（`Verdict`）:

| `value` | 意味 |
|---|---|
| `violated` | 違反の証拠がある |
| `compliant` | 評価した範囲で適合 |
| `not_applicable` | 適用されない（対象に合わない、時間外など） |
| `undetermined` | 足りない事実によって結論が変わる（`missing` に、何が分かればよいか。例: `{"entity_id": "plate_X", "key": "attr:fragile"}`） |

`basis` は `predicted`（計画に対する予測）か `observed`（観測）。属性に値が無い物体は「不明」として扱う（割れ物かどうか分からない皿は、接触の禁止が未確定になり、保留する）。

依頼は `state.updated` の `task` に入る:

```jsonc
{"id": "task_1", "text": "机の上のものを全部片づけて", "requester": null, "source_region": "table_01",
 "rows": [
   {"object_id": "plate_A", "label": "plate",
    "destination": "shelf_upper", "destination_rule_ids": ["R3a"],      // 指定先は上段
    "verdicts": {"R1": {"value": "violated", "basis": "predicted", ...}}, // つかむと R1 に反する（予測）
    "exec_state": "deferred", "reason": "「Fragileなものを触るな」（R1）に反するので、触れずに残す",
    "missing": [], "history": [...]},                                    // history は判定の履歴（上書きしない）
   {"object_id": "cup_B", "destination": "shelf_lower", "exec_state": "done", ...}],
 "corrections": [...]}                                                   // 属性の訂正と、それで変わった項目
```

`exec_state`: `pending` / `deferred`（保留。理由は `reason`）/ `in_progress` / `placed_unverified`（置いた。配置先の観測待ち）/ `done`（収納先で観測した）/ `misplaced`（別の場所で観測した）/ `unverified`（観測が来なかった）/ `failed`。
触れずに保留した物は「違反の予測により保留」で、実行時の違反ではない。

属性の訂正（`objects.set_attribute`）:

- 訂正はシーンとは別に持つ（`state.updated` の `corrections`）。`scene.update` はシーン全体を置き換えるが、訂正はそのあとも効く
- 返る `correction.changes` は、訂正の前後で変わった行と項目だけ（`{object_id, what: destination / exec_state / verdict:<ルール ID>, before, after}`）。ここに無いものは変わっていない
- `affected_rule_ids` は、その属性を読むルール

家の時計（`clock.*`）は、ルールの「18 時以降」などを判定する時計。デモ・評価では `clock.set {"time": "17:55"}` のように差し替える。タイムゾーンは `COGROUND_HOME_TZ`（既定 `Asia/Tokyo`）。

代役のロボットで試す:

```bash
W="docker compose exec grounding_server python scripts/ws_client.py call"
$W norms.set '{"norms": [...]}'                 # R1, R3a, R3b
$W task.request '{"text": "机の上のものを全部片づけて"}'
$W exec.start '{"allow_unplanned": true}'
$W task.report                                  # 2点中1点を収納しました。…
$W objects.set_attribute '{"object_id": "plate_A", "key": "fragile", "value": false}'
```

通しの例は `tests/test_correction.py` の `test_minimal_demo_over_websocket`。

### 台車の動きについてのルール（R2・R4）

```jsonc
{"id": "R2", "original_text": "夕方6時以降は子供が遊びまわるから、リビングのこのあたりには入るな", "norm": "prohibition",
 "scope": {"from": "18:00", "until": null},
 "target": {"kind": "zone", "id": "zone_play"},                             // zones.define で決めた範囲（シーンの領域の ID でもよい）
 "requirement": {"window": "during_base_motion", "predicate": "footprint_overlaps",
                 "transition": {"from": false, "to": true}}}                // 外から中に入ること（もう中にいるだけなら反しない）
{"id": "R4", "original_text": "子供が5m以内にいるときは台車を止めろ", "norm": "obligation",
 "scope": {"when": {"predicate": "near_child", "args": {"distance": 5.0}}},
 "target": {"kind": "robot"}, "requirement": {"window": "whole", "predicate": "base_stopped"}}
```

台車の外形は半径 0.30 m の円（`COGROUND_ROBOT_RADIUS`。move_base の costmap と同じ）。

**計画側（`motion.plan`）**: 計画した台車の経路を、計画を始めた時刻 + t で家の時計の時刻に直して R2 を判定する。

1. まず、領域を避けずに計画する。17:58 に通る経路は、18 時からの禁止に反しない（遠回りさせない）
2. 違反が出たら、その領域を避ける範囲（keepout）に入れて計画し直す
3. それでも通れない step は外し、依頼の行を保留にする（`exec_state: deferred`、`verdicts.R2` が違反の予測）。
   探した条件は、行の `route`（計画した時刻、避けた領域、回ごとの結果）と、`motion` の `attempts` に残る

経路による保留は、`motion.plan` をやり直すか、ルール・領域・時計が変わると解ける（判定は「経路を計画し直すまで未確定」に戻る）。
`motion` の要約には、避けた領域（`keepout`）と、実行中に見張る条件（`monitors: [{rule_id, predicate, entities, response: replan / hold}]`）も入る。

**実行側（監視。`coground_server/monitor.py`）**: 台車が動いている間、0.1 秒ごとに「このまま進んだら反するか」を調べる。

- R2（`response: replan`）: 禁止が効いている時刻に境界を越えそうなら、**手前で止めて、領域を避ける経路を計画し直す**。
  予測では 17:58 に入れるはずだった経路も、出発が遅れて 18:02 になれば止まる。17:59 に入って 18:00 に中にいるだけなら、何もしない
- R4（`response: hold`）: 子供が近くにいる間は台車を止める。**人の位置が観測できなくなったとき**（`people.update` が 2 秒届かない。
  `COGROUND_PEOPLE_TIMEOUT`）と、近くの人が子供かどうか分からないとき（`kind: unknown`）も止める
- 止め方は **hold**: スキルは取り消さず、台車だけを止める（物は持ったまま。腕は止めない）。
  hold を解くのは、子供が離れたときではなく、**残りの経路の再検証が済んだとき**（止まっている間に 18 時を過ぎていれば、領域を避ける経路に替えてから再開する）
- 合う経路が無ければ、スキルを止めてその物を保留にする（持っているときは、持ったまま実行を止める）
- つかむ直前には、いまの時刻と属性で R1 をもう一度判定する（訂正で「割れ物」になった、時刻で効き始めた禁止）

hold の記録は `state.updated` の `execution.monitor.holds`（と `monitor.get`、`task.report` の行の `holds`）:

```jsonc
{"id": "hold_1", "rule_ids": ["R4"], "object_id": "cup_B", "outcome": "released",   // released / blocked / skill_ended
 "requested": {"t": "…17:55:00+09:00", "base": [3.0, 0.0, 0.0], "distance": {"R4": 3.0}},  // 止めるよう求めた時刻・位置・相手との距離
 "stopped":   {"t": "…17:55:00+09:00", "base": [3.05, 0.0, 0.0], "distance": {"R4": 2.95}, "confirmed": true, "after": 0.2},  // 実際に止まった
 "replans": [{"keepout": [], "ok": true, "verdicts": {"R2": "violated"}},           // 再検証: 元の経路は、もう zone_play を通れない
             {"keepout": ["zone_play"], "ok": true, "verdicts": {"R2": "compliant"}}],
 "released": {"t": "…18:02:00+09:00", "base": [3.05, 0.0, 0.0]}, "keepout_after": ["zone_play"]}
```

移動が終わると、動いている間に観測した状態に対する判定（`basis: observed`）が、依頼の行に残る。

人の位置は `people.update` で送る（`state.updated` の `people` と `scene.people`）。領域は `zones.define` で送る（`state.updated` の `zones`。`scene.update` では消えない）。
座標はどちらも Unity のワールド座標で、高さは使わない。

代役のロボットで試す（代役は、領域を避ける折れ線の経路を 0.1 m ずつ進む）:

```bash
$W zones.define '{"id": "zone_play", "polygon": [[-1, 0, 4.5], [1, 0, 4.5], [1, 0, 5.5], [-1, 0, 5.5]]}'
$W norms.set '{"norms": [...]}'                 # R2, R3, R4
$W people.update '{"people": [], "valid_for": 0}'   # 「誰もいない」。valid_for: 0 で、送り直さなくても有効のまま
$W clock.set '{"time": "18:05", "freeze": true}'
$W task.request '{"text": "机の上のものを全部片づけて"}'
$W motion.plan                                  # keepout: ["zone_play"]、attempts が 2 回
$W exec.start
$W monitor.get
```

テストは `tests/test_home_rules.py`（計画側・実行側・R4）。

### 訂正と、言葉からの登録

訂正はどれも `{correction: {kind, entity_id, key, before, after, affected_rule_ids, changes}}` を返し、依頼の `corrections` に残る。

| method | `kind` | 例 |
|---|---|---|
| `objects.set_attribute` | `attribute` | この皿は割れ物ではない |
| `rules.update` | `rule` | 19 時からにして（`{"rule_id": "R2", "from": "19:00"}`） |
| `zones.update` | `zone` | 範囲はここまで |
| `rules.add_exception` | `exception` | 私が頼んだときは、この皿に触ってよい（`{"exception_of": "R1", "requester": "user_01", "object_id": "plate_A"}`） |

言葉からの登録（`norms.compile`）は、仕様の JSON の形（上の R1〜R4 と同じ）のルールを作る:

- すぐ確定できるルールは `norms` に入り、`apply` ならそのまま効く
- 「このあたり」のように範囲が言葉だけでは決まらないルールは `pending` に入る（`target.id` は `zone_ref_1` のような仮の名前、`pending_refs` にその参照）。
  Quest で囲んだ範囲が `zones.define` で届いたら、`rules.confirm {"rule_id": "N1", "refs": {"zone_ref_1": "zone_1"}}` で確定する
- 解除時刻が言われていない（`until: null`）ルールも `pending`（`unresolved: ["scope.until"]`）。**勝手に補わない**。
  `rules.confirm` に `until` を渡すか、`keep_open: true`（決めないままにする、と住人が決めた）を渡す
- 登録の途中のルールは `state.updated` の `pending_rules` に入り、判定には使わない

`rules.compile`（旧 Rule を作る）はそのまま残してある。テストは `tests/test_rule_registration.py`。

## Plan（動作計画）を作る

実行の前に、ロボットを動かさずに「移動 → つかむ → 移動 → 置く」を Plan の全 step について通しで計画する（`motion.plan`、`coground_server/motion.py`。
ROS の `pick_place_server.py` が仮想のロボットで計画する。台車の止まる位置は、物体の手前の候補から、腕が届いて経路があるものを選ぶ）。

- **依頼（`task.request`）を受けると、自動で動作計画を始める**（`Services.start_auto_motion_plan`。応答の `motion_planning` が true）。
  Plan だけでは腕が届くか・禁止区域を通らずに行けるかが分からないので、Unity は動作計画の結果が出てから依頼の結果を見せる。
  実行中・計画中・ok の step が無いときは始めない。`COGROUND_AUTO_MOTION_PLAN=0` で無効
- 結果は 1 本の時間軸（台車の位置、腕の関節角、物を持っている区間、区切り）。テスト画面のシーケンスバーと、Unity の `CoGroundTaskPlanPlayer`（Ghost）で、行ったり来たりして見返せる
- 計画できない step は `infeasible`（理由つき）。計画した後に物体が 2 cm 以上動いた、置き位置が変わった step は `stale`（古い）になる
- **止まる位置**: 家具（place_zone を持つ物）に、Unity で `CoGroundApproachPoint`（子の空の GameObject。位置 = 台車の中心、+Z = 台車の正面）を置くと、
  `scene.update` の `approach_poses` で届き、その家具から取る・その家具に置くときに、まずそこを試す。だめなときだけ物体のまわりから自動で選ぶ。
  どちらを使ったかは `motion.steps[...].stop_source`（`approach` / `auto` / `stay`）。テスト画面では図の水色の円、Plan の表の「(自動)」
- 行き先がごみ箱・箱・シンク（`receptacle`）なら「落とす」: 上面の 5 cm 上で離す。机・棚には、そっと置く
- 要約は `state.updated` の `motion`:
  `{status: none / planning / ready / failed, error, progress, plan_id, timeline_id, duration, steps: {s1: {status: ok / infeasible / stale, reason, t0, t1}}}`。
  時間軸そのものは大きいので `motion.get` で読む（`timeline_id` が変わったら読み直す）

## シーケンスの編集と、検証済みの予測

住人が決めるのは「何を、どの順で、どこへ」。作業の候補（Plan の step）・検証済みの動作計画・実行結果は別のもので、
**After に出すのは、その順番で把持・移動・配置まで実行できると検証できた結果だけ**（「皿を棚に置く」という候補ができただけでは、移動予定にしない）。

- **順序**は依頼の行の並び（`task.rows`）。`sequence.add` / `remove` / `move` / `reorder` で変える（実行中は不可）。
  変えると、最初に影響を受ける step 以降の検証結果を未確認に戻し（`first_affected`）、自動で検証し直す
- **検証**は順序どおりに、前の step を終えた状態から行う。成立した step の物体は置き先へ移り、成立しなかった物は元の場所に残った状態で次を検証する
  （ROS の `pick_place_server.py` は仮想のシーンで、代役のロボットは `request.world` で追う）。
  置き位置も順序どおりに決め、置ける空きが無ければその step は `infeasible`（「No free space …」。入れ物は重なってよい）
- **`sequence.add` の置き先**は、収納先を決めるルールと照合する。ルールと違えば保留（理由つき）。触れない物（割れ物など）を足すと、step は入るが保留になる
- **予測**は `state.updated` の `motion.preview`。ステップ別の予測・最終 After・実行が、この同じ版を見る:

  ```
  {id, status: none / checking / ready / unverified, executable, notice,
   steps: [{step_id, index, object_id, label, from_region, to_region, to_position,
            state: move / stay_rule / stay_infeasible / checking / unverified, reason, blocked_by}],
   suggestion: {kind: "reorder", object_id, order, message} | null}
  ```

  `move` = 検証できた / `stay_rule` = 家庭ルールにより残す / `stay_infeasible` = 動作が成立せず残す（経路が無い、空きが無い、手前の物がじゃま） /
  `checking` = 確認中 / `unverified` = 未確認（計画の失敗・タイムアウト、検証のあとで状況が変わった。実行の対象から外れる）。
  「k 番目の step の後」の状態は、`index <= k` の `move` の物だけを置き先へ移したもの（Unity の `CoGroundAfterView.SetViewStep`）
- **順序変更の提案**（`suggestion`）: じゃまな物（`blocked_by`）が後ろの step で動くなら、その後ろへ回す順序を提案する。
  採用するかは住人が決める（`sequence.reorder` に `order` を渡す）。採用したら検証し直し、その結果で After が変わる
- **実行**: `exec.start {"preview_id": <住人が見た preview.id>}`。次のときは始めない:
  検証中 / いまの `preview.id` と違う（編集のあとの古い After） / 未確認の step がある / 動かせる物が無い。
  既定（`revalidate`）では、始める直前に動作計画をやり直す（プレビューのあとで環境が変わったかもしれない）。
  動かす対象・順序・置き先が変わったら、始めずに断り、`preview.notice` に何が変わったかを入れる。住人が更新後の After を確認して、新しい `preview_id` で呼び直す
- 成立しない step があっても、成立する step は実行できる。成立しない物は取りに行かない（`execution.steps[...].status = blocked`）

```bash
$W task.request '{"text": "机の上を片づけて"}'
$W state.get | jq .motion.preview                 # 検証が済むと status: ready
$W sequence.move '{"object_id": "plate", "index": 0}'
$W sequence.add '{"object_id": "glass", "target_region": "shelf_upper", "index": 1}'
$W exec.start '{"preview_id": "pv_…"}'
```

受け入れテストは `tests/test_sequence_preview.py`（禁止区域と迂回路、並べ替え、追加・削除、配置までの検証、プレビュー後の環境変化）。

## Plan を実行する

Plan の step を上から順に、ロボットに実行させる（`coground_server/executor.py`）。step 1 つは「移動 → つかむ（pick）→ 移動 → 置く（place）」。
**先に動作計画が要る**（無い・古い step があれば `exec.start` は断る。`allow_unplanned: true` なら、移動せずにその場で腕だけ計画して動かす）。
計画した止まる位置へ移動し、台車がほぼぴったり（1 cm / 1° 以内）止まって、いまのシーンでもぶつからなければ**計画した軌道をそのまま再生**する。
だめなら**その場で計画し直す**。どちらだったかは `history` と記録の `mode`（`replay` / `replanned`）に残る。
**動きが 1 つ終わるたびに Plan を読み直す**ので、実行中に Plan を変えると、次の動きから効く。
**置く動作が成功しても、まだ `done` にしない。** 配置先の観測（Unity の `scene.update`）を待ち、行き先の領域にあれば `done`、別の場所なら `misplaced`、
観測が来なければ `unverified` にする（待つのは `COGROUND_OBSERVE_TIMEOUT` 秒、既定 5。`misplaced` / `unverified` は失敗と同じ扱いで、既定では止まって待つ）。

| やりたいこと | 方法 |
|---|---|
| 計画する（実行の前に） | `motion.plan` |
| 始める / 一部だけ実行する | `exec.start` / `exec.start {"step_ids": ["s2", "s1"]}` |
| いまの動きが終わったら止める（物を持ったまま止まることもある） | `exec.pause` |
| いますぐ止める | `exec.stop` |
| 続きから（持っていれば、置くところから） | `exec.resume` |
| 実行中に行き先を変える | `plan.place`（持っている物でも、置く前なら新しい行き先に置く） |
| step を飛ばす（実行中なら止めて、持っていれば元の場所へ戻す） | `exec.skip` |
| 失敗した step をやり直す | `exec.retry` のあと `exec.resume` |
| つかむ前に毎回、人に聞く | `exec.set_policy {"confirm": "each_step"}` → 待ちになったら `exec.confirm` |
| 失敗しても止まらず次へ進む | `exec.set_policy {"on_failure": "continue"}` |

決まりごと:

- 持っている物の step が無くなったら（飛ばした、行き先の指定を消した、置くのに失敗してやり直さなかった）、**つかんだ元の場所へ戻す**
- 失敗すると、既定では止まって待つ（`mode: paused`、`reason: "failed: ..."`）。やり直す（`exec.retry`）か、そのまま `exec.resume` で次へ
- 手で指定した行き先（`plan.place`）は、運び終わっても、ルールがその物をよそへ運び直すあいだは残る（残さないと往復する）

実行の状態は `state.updated` の `execution` に入る:

```jsonc
{"mode": "running",              // idle / running / paused
 "reason": "",                   // paused の理由（user / stopped / failed: ...）、idle なら finished
 "pausing": false,               // exec.pause を受けて、いまの動きが終わるのを待っている
 "confirm": "auto", "on_failure": "pause",
 "waiting_confirm": null,        // 確認を待っている step の id
 "current": {"step_id": "s1", "object_id": "glass_cup_1", "skill": "pick", "phase": "approaching", "detail": ""},
 "steps": {"s1": {"status": "picking", "detail": ""}},   // pending / moving_to_pick / picking / holding / moving_to_place / placing / placed_unverified / done / misplaced / unverified / failed / skipped / blocked
 "history": [{"object_id": "...", "skill": "pick", "state": "succeeded", "detail": "", "mode": "replay"}],  // skill: navigate / pick / place / put_back
 "robot": {"kind": "fake", "connected": true, "holding": null, "busy": false}}
```

### ロボット（代役か、ROS か）

| | いつ | 何が起きる |
|---|---|---|
| 代役（`fake`） | `COGROUND_ROSBRIDGE_URL` が無いとき（既定） | ROS も Unity も要らない。動きを順に進めるだけで、置いた結果（配置先の観測の代わり）はサーバーのシーンに書く。`exec.inject_failure` で失敗を、`debug.observe_placement` で配置先違い・観測なしを起こせる |
| ROS（`rosbridge`） | `.env` に `COGROUND_ROSBRIDGE_URL=ws://host.docker.internal:9090`（ROS が別のマシンならその IP） | `pick_place_server.py` の `/coground/skill/*` を呼ぶ（`Backend/README.md`）。物の位置は Unity の `scene.update` で届く |

### 記録（だれが・いつ・何を）

呼ばれた method（`rpc`）、実行の状態の変化（`exec`）、ロボットの動きの始まり・phase・結果（`skill`）を、1 行 1 件の JSON で `logs/events.jsonl` に書き足す（`COGROUND_EVENT_LOG`）。
直近の 500 件は `log.tail` でも読める。だれの操作かは、接続ごとに `session.identify` で名乗る（既定は `user`）。`scene.update` は中身を記録しない（大きいので）。

## LLM

LLM の呼び出しは `coground_server/llm/` にまとめてある。ほかのコードは「入力 → Pydantic モデル」の関数だけを使う。

| ファイル | 内容 |
|---|---|
| `llm/client.py` | LLM を 1 回呼ぶ口（`LlmClient`）。本物は 2 つで、`make_llm` が環境変数で選ぶ（下の表）。ツールは使わせず、JSON Schema に合った答えを 1 つ返させる。テストでは `FakeLlm` |
| `llm/compile_rule.py` | 自然言語 → `Rule`。いまのシーンの領域・物体・語彙を見せて選ばせる。行き先がシーンに無いものは、ルールにせず `unresolved` に入れる |

| 口 | 認証 | 中身 |
|---|---|---|
| `AnthropicApiLlm`（`api`） | `ANTHROPIC_API_KEY` | `anthropic` SDK で Messages API を直接呼ぶ。答えの型は structured outputs（`output_config.format`）で縛る。モデルの既定は `claude-opus-5-5`。断られた（`refusal`）ときはサーバー側で別のモデルが答え直す（`fallbacks: "default"`）。CLI を起動しないので速い。使った分だけ API の料金がかかる |
| `AgentSdkLlm`（`agent_sdk`） | `CLAUDE_CODE_OAUTH_TOKEN`（または API キー） | Claude Agent SDK（`claude-agent-sdk`。Claude Code の CLI を子プロセスで動かす）。サブスクリプションで動かせる。1 回呼ぶたびに CLI を起動するので数秒かかる |

**認証**: `.env.example` を `.env` という名前で写し、`ANTHROPIC_API_KEY` か `CLAUDE_CODE_OAUTH_TOKEN`（ホストで `claude setup-token` を実行して作る）を書いて、`make down && make up`（`anthropic` を足したので、初回は `make build` も）。`.env` は Git に入れない。
`COGROUND_LLM_BACKEND`（`api` / `agent_sdk`）を省略すると、`ANTHROPIC_API_KEY` があれば `api` を使う。

```bash
docker compose exec grounding_server python scripts/ws_client.py call llm.ping
docker compose exec grounding_server python scripts/ws_client.py call rules.compile '{"text": "食器は流しに入れて、ごみは分別して捨てて"}'
```

- `agent_sdk` は 1 回呼ぶたびに CLI を起動するので、数秒かかる。何度も続けて呼ぶ処理（物体ごとの属性推定など）には向かない
- 呼び出しの記録（プロンプト、答え、かかった時間、使った口、`api` ならトークン数と request id）は `logs/llm.jsonl` に足されていく（`COGROUND_LLM_LOG`）
- モデルと effort は `COGROUND_LLM_MODEL` / `COGROUND_LLM_EFFORT`、待つ秒数は `COGROUND_LLM_TIMEOUT`（既定 120）
- 別の SDK に替えるときは、`LlmClient` を実装したクラスを作って `Services.llm` に渡す

## method を足す

`coground_server/handlers/` にモジュールを作り、`handlers/__init__.py` の `build_router()` に加える。

```python
from pydantic import BaseModel
from ..rpc import RequestContext, Router

router = Router()

class CompileParams(BaseModel):
    text: str

@router.method("rules.compile", params=CompileParams, streams=True, description="NL ルール → Rule IR")
async def compile_rule(ctx: RequestContext, p: CompileParams):
    await ctx.stream({"stage": "llm"})          # 途中経過（任意）
    ...
    await ctx.services.publish_state()          # 全体状態を変えたら必ず呼ぶ
    return {"rule_id": "R1"}                    # result になる
```

- params は Pydantic モデルで検証される（合わなければ自動で `invalid_params`）。
- `RpcError(code, message, details)` を投げると、そのままエラー応答になる。
- 長い処理は `cancel` で `asyncio.CancelledError` が投げられて止まる。

## Unity 側

`UserApp/CoGround/Assets/Main/Script/Server/`

- `CoGroundServerClient.cs`: 接続、自動再接続、`RequestAsync`（stream・timeout・cancel 対応）、`SendEventAsync`、`StateUpdated` / `On(event)`
- `CoGroundServerDemo.cs`: 動作確認用（接続時の ping、インスペクタのメニューから `debug.count` や `scene.update` を試す）

`UserApp/CoGround/Assets/Main/Script/Home/`（家庭ルール用。まだ Unity でコンパイル・動作確認していない）

- `CoGroundZone.cs`: 床の範囲（角に置いた Transform の多角形）を `zones.define` で送る。角を動かすと送り直す。
  `Confirm Pending Rules` を付けると、範囲の参照が 1 つだけの登録の途中のルールを、この範囲で `rules.confirm` する
  （解除時刻が要るルールは `Confirm Until` か `Keep Open` を決めておく）。台車がいま避けている領域は輪郭の色が変わる
- `CoGroundPerson.cs` / `CoGroundPeopleReporter.cs`: シーンの人（ダミーの子供など）の位置を `people.update` で 0.2 秒ごとに送る。
  人がいなくても空のリストを送り続ける（送らないと 2 秒で「観測なし」になり、R4 があれば台車が止まる）
- `CoGroundHomeStatus.cs`: 家の時計、停止中かどうかと理由（hold）、避けている領域、依頼の行ごとの状態、登録の途中のルールを文字で出す。
  `Robot Anchor` に台車を入れると、止めている間だけその上に「停止中」を出す
- `CoGroundHomeCommands.cs`: 依頼（`task.request`）、言葉からの登録（`norms.compile` / `rules.confirm`）、
  訂正（`objects.set_attribute` / `rules.update` / `rules.add_exception` / `zones.update`）、結果（`task.report`）、時計（`clock.set`）を送る。
  インスペクタの右上メニュー（⋮）から試す。UI や音声からは同じ名前の public メソッドを呼ぶ

`Plan/CoGroundPlanView.cs` は、保留（`deferred`）の step を物体の上のラベルだけで出し、理由と、違反・未確定になった家庭ルールを並べる。
弧と置き位置のゴーストを出すのは、検証できた（`motion.preview` で `move`）step だけ。

`UserApp/CoGround/Assets/Main/Script/Plan/`（シーケンスと予測）

- `CoGroundSequencePanel.cs`: 作業順序の一覧（状態と理由）、並べ替え・削除・追加、時点の切り替え（Before / After 1 / … / Final）、
  順序変更の提案、検証し直し、実行（`preview_id` つき）。メニュー `CoGround > シーケンス パネルを置く`。UI は Play のときに自分で組み立てる
- `CoGroundAfterView.cs`: 選んだ時点までに動く物だけ、元の位置を薄くして（Diminish）置き先に予測位置を出す。残る物には理由のラベル
- `CoGroundFuture.cs`: `motion.preview` を読む共通の判定（`StateOf` / `MovedAtView` / `UpToIndex`）

```csharp
var client = CoGroundServerClient.Instance;
JToken pong = await client.RequestAsync("system.ping");
await client.RequestAsync("debug.count", new { count = 5 }, onStream: d => Debug.Log(d));
client.StateUpdated += state => Debug.Log(state["version"]);
```

## 物体検出（YOLO-World）— 別コンテナ `detector`

検出は grounding_server とは別のコンテナ `coground_detector`（:8001, イメージ `coground/detector:dev`,
`Dockerfile.detect`）で動く。アプリは `coground_server/detect_app.py`。grounding_server（:8000）は
torch を持たず、`/detect` も持たない。Unity / Quest は :8001 に直接 JPEG を送る（中継なし）。

```bash
make build      # 初回のみ。detector は重み（yolov8s-worldv2 と CLIP）をイメージに入れる
make up         # grounding_server（:8000）と detector（:8001, GPU）をまとめて起動
make up-cpu     # NVIDIA Container Toolkit が無いマシン：detector を CPU で（遅い）
make down / ps / logs
make detect-restart / detect-logs / detect-test   # detector だけ
```

ブラウザで `http://<host>:8001/detect/ui`。`--reload` は付けていないので、コードを変えたら `make detect-restart`。
両方とも `restart: unless-stopped` なので、Docker やマシンを再起動しても起動し直す。
GPU ドライバに合わせて `Dockerfile.detect` の `BASE` を選ぶ（usa-lab はドライバ 470 → cuda11.8 版）。

`POST /detect` accepts raw `image/jpeg` and returns
`{"predictions":[{"label":"plastic_bottle","score":0.82,"box":[10,20,80,90]}]}`.
Coordinates are absolute pixels in the input JPEG, in `[xmin,ymin,xmax,ymax]`
order. No EXIF rotation is applied. No detections returns an empty array.
This endpoint does not write scene state; Quest must later send `scene.update`.

Startup loads one model, sets its vocabulary and runs one warm-up inference.
Startup fails if dependencies, weights, or the requested GPU cannot be loaded.
`COGROUND_DETECT_ENABLED=0` skips loading (then `/detect` returns 503). Use **one worker**
so that vocabulary and busy state are shared by all requests. While receiving or
processing an image, or updating vocabulary, additional requests return 429
(`Retry-After: 1`); clients should discard that frame. There is no frame queue.
Unsupported media types return 415, invalid JPEGs return 400, and bodies above
10 MiB return 413. Decoded images are limited to 16 megapixels.

Configuration via environment variables:

| Variable | Default | Meaning |
| --- | --- | --- |
| `COGROUND_DETECT_ENABLED` | `1` | `0` で読み込まない（detector コンテナ内） |
| `COGROUND_DETECT_MODEL` | `/models/yolov8s-worldv2.pt`（イメージ内） | Weights name/path |
| `COGROUND_DETECT_DEVICE` | `0` | GPU index (`cpu` for manual CPU trials) |
| `COGROUND_DETECT_CONF` | `0.25` | Confidence threshold |
| `COGROUND_DETECT_IMGSZ` | `640` | Inference resolution |
| `COGROUND_DETECT_VOCAB` | packaged `detection_vocab.json` | Prompt/label JSON array |
| `COGROUND_DETECT_DEBUG_DIR` | unset | Save input JPEG, annotated JPEG and prediction JSON |

The initial mapping is plastic bottle → plastic_bottle, cup → cup, mug → mug,
plate → plate, paper cup → paper_cup, crumpled tissue → tissue,
snack wrapper → wrapper. `GET /detect/vocabulary` returns the current mapping.
Change it without restarting:

```bash
curl -X PUT http://localhost:8001/detect/vocabulary \
  -H 'Content-Type: application/json' \
  -d '{"entries":[{"prompt":"plastic bottle","label":"plastic_bottle"},{"prompt":"mug","label":"mug"}]}'
curl http://localhost:8001/detect -H 'Content-Type: image/jpeg' --data-binary @test.jpg
```

Updates replace the entire mapping, run under the inference lock, and last until
restart. Edit the configured JSON file for persistence. These routes use the same
trusted-network assumption as the existing debug API. Debug output is opt-in and
is not automatically pruned.

Quest-free verification:

```bash
make detect-test   # 偽モデルのテスト（grounding_server のイメージでも python -m pytest で通る）
docker compose run --rm detector python scripts/detect_folder.py ./images ./logs/detect-folder
```

The folder script accepts JPEG/PNG, saves input/annotated JPEG and JSON in a
subdirectory per image, and prints predictions plus inference time (not network RTT).

### ブラウザで検出を試す

`make up` のあと **http://<host>:8001/detect/ui** を開く。

1. JPEG・PNG・WebPを選択、または画像をドロップします。
2. 送信画像の長辺を選び、「検出する」を押します。画像はブラウザでJPEG化されます。
3. 枠・カテゴリ・信頼度・通信＋推論時間を確認します。初回はモデルのウォームアップで遅くなる場合があります。
4. 語彙を編集して「語彙を適用」を押し、再検出すると言い回しの違いを比較できます。
5. 必要に応じて枠付きPNGやレスポンスJSONを保存します。

表示時間にはHTTP通信とサーバー側の処理を含み、ブラウザの画像変換時間は含みません。
送信サイズは画像の解像度であり、モデルの推論サイズ `COGROUND_DETECT_IMGSZ` とは別です。
語彙の適用はサーバー全体に影響し、再起動までは維持されます。
GPU が無い場合は `make up-cpu` で CPU でも試せます（処理速度は低下します）。

## 物体の認識・属性・記憶（perception）

写真 1 枚から、物体を見つけ（YOLOE-seg）、番号を重ねた画像（Set-of-Mark）を VLM に 1 回だけ見せて属性を聞き、
物体ごと（`object_id`）に覚える。同じ物体をもう一度見ても VLM は呼ばない。コードは `coground_server/perception/`。

```
 画像 ─> detector :8001 POST /segment（YOLOE-seg。矩形・マスク・クラス。detection_id = 画像の中だけの番号）
      ─> 記憶に object_id で聞く ─┬ 属性がある（completed）─────────────> 保存した値を返す（VLM 0 回）
                                  ├ ほかの依頼が解析中（pending）──────> その結果を待つ（VLM 0 回）
                                  └ 新しい / 前に失敗した ─> SoM 画像 ─> VLM 1 回（まとめて聞く）─> 記憶に書く
```

| ファイル | 役目 |
| --- | --- |
| `segmentation.py`（detector 側） | YOLOE-seg。`POST /segment`、`GET /segment/status`。語彙は `/detect` と共通 |
| `perception/segment_client.py` | detector の `/segment` を呼ぶ |
| `perception/som.py` | Set-of-Mark 画像（番号つき）と、確認用の分割結果の画像 |
| `perception/vlm_analyzer.py` | 元の画像と SoM 画像を VLM に渡し、番号ごとの `category` / `material` / `fragility` / `appearance` を受け取る |
| `perception/object_store.py` | Object Memory。`vlm_status`（pending / completed / failed）、`attribute_version`、VLM を呼んだ回数 |
| `perception/pipeline.py` | 上をつなぐ。run ごとに入力・途中の画像・JSON・時間を残す |
| `perception/api.py` | REST と画面 |

**試す**: `make up` のあと **http://<host>:8000/perception/ui**（画像を選んで Analyze。「Analyze ×10」で、VLM が初回の 1 回だけかを確かめる）。
コマンドなら:

```bash
docker compose exec grounding_server python scripts/perception_run.py tests/images/scene_initial.jpg --reset --repeat 10
```

テスト画像の撮り方は `tests/images/README.md`。

REST（:8000）:

| | |
| --- | --- |
| `POST /perception/analyze` | 本文 = JPEG（`Content-Type: image/jpeg`）。`?object_ids=mug_a,cup_b`（検出の左からの順に付ける ID）、`?reanalyze=true`（VLM に聞き直す） |
| `GET /perception/memory` | 覚えている物体と、VLM を呼んだ回数 |
| `DELETE /perception/memory`、`DELETE /perception/memory/{object_id}` | 全部 / 1 つ忘れる |
| `GET /perception/runs`、`GET /perception/runs/{run_id}/{file}` | 最近の run と、残したファイル |

`object_id` は、いまは固定（自動の再認識はまだ無い）: 呼ぶ側が `object_ids` で渡すか、検出の左からの順番で `obj_001`, `obj_002`, ... を振る。
同じ並びの写真なら同じ ID になる。物体を足したり並べ替えたりすると順番がずれる（位置と見た目で同じ物体を見つけるのは次の段階）。

残るもの:

| 場所 | 中身 |
| --- | --- |
| `logs/perception/<run_id>/` | `input.jpg` / `detections.json` / `segmentation_overlay.jpg` / `som.jpg` / `attributes.json`（VLM を呼んだ run だけ）/ `result.json` |
| `logs/perception/runs.jsonl` | 1 行 1 run。VLM を呼んだ回数、解析した / 記憶から返した `object_id`、かかった時間 |
| `logs/llm.jsonl` | VLM の呼び出し（`name = "analyze_objects"`）のプロンプト・答え・秒 |
| `data/object_memory.json` | 物体の記憶（再起動しても残る） |

環境変数（compose.yaml）: `COGROUND_DETECTOR_URL`（既定 `http://detector:8001`）、`COGROUND_OBJECT_MEMORY`、`COGROUND_PERCEPTION_RUNS`、
detector 側は `COGROUND_SEGMENT_ENABLED` / `COGROUND_SEGMENT_MODEL` / `COGROUND_SEGMENT_CONF`。
VLM は LLM と同じ口（`llm/client.py`。API キーでも Claude Agent SDK でも画像を渡せる）。

### 再認識と変化の判定（`perception/association.py`）

視点を変えても同じ物体に同じ `object_id` を付け、動いた・足された・入れ替わった・無くなったを区別する。
方式は Embodied VideoAgent に従う（コードは CoGround で書き起こしたもの）:

> Yue Fan, Xiaojian Ma, Rongpeng Su, Jun Guo, Rujie Wu, Xi Chen, Qing Li. "Embodied VideoAgent: Persistent Memory from
> Egocentric Videos and Embodied Sensors Enables Dynamic Scene Understanding." ICCV 2025.

1 フレームごとに: マスク + 深度 + カメラ姿勢から物体の 3D の箱を作る → あるはずの場所が空いている物体を「動いた候補」にする →
その場の物体とは箱の重なりで照合 → 残りは動いた候補と見た目・大きさで照合 → どれにも合わなければ新しい物体。

| 起きたこと | 結果 | VLM |
| --- | --- | --- |
| 視点を変えた、視界から外して戻した | `same`（同じ ID） | 呼ばない |
| 物体が動いた | `moved`（同じ ID、場所を更新） | 呼ばない |
| 物体を足した | `new` | その物体だけ |
| 同じ場所で入れ替えた | 新しい物体が `new`、古い物体は `displaced` | 新しい物体だけ |
| 取り除いた | `displaced` → 30 秒で `missing`。戻れば同じ ID | 呼ばない |
| 見えないだけ（視界の外、手前に物がある） | `present` のまま | 呼ばない |

「同じ場所で入れ替えた」は論文の方式に足した部分（その場の照合でも見た目を確かめる）。見た目の特徴量が無いと区別できない。

しきい値（`AssociationConfig`）は最初の値で、実際の深度で決め直す（環境変数 `COGROUND_REID_<名前>`、例 `COGROUND_REID_SWAP_SIMILARITY=0.4`）。

### Quest のフレームを送る（`POST /perception/frame`）

Unity の `CoGroundFrameSender`（`UserApp/.../Assets/Main/Script/Perception/`）が、RGB・環境深度・撮影時のカメラを 1 フレームにまとめて送る。
サーバーは深度を RGB に合わせ（`perception/frame.py`）、検出（`/segment?embed=1`、DINOv2 の特徴量つき）を 3D の箱にし、
`ObjectTracker` で ID を決めてから、新しい物体だけ VLM に聞く。

| multipart | 中身 |
| --- | --- |
| `rgb` | パススルーカメラの JPEG |
| `depth` | `_EnvironmentDepthTexture` の左目を画素ごとに float32 × 4: (NDC の深度 0..1, 読んだ u, 読んだ v, 1)。行の順は問わない |
| `meta` | JSON: `timestamp`、`rgb`（`width` / `height` / `fx` / `fy` / `cx` / `cy`（送った画像の画素、y は下向き）/ `pose`（Unity のワールド座標の位置と Quaternion））、`depth`（`width` / `height` / `format: "rgba32f_uv"` / `reprojection`: `_EnvironmentDepthReprojectionMatrices[0]` を行ごと 16 個） |

深度を読んだ uv を画素ごとに送るので、テクスチャの上下の向き（Vulkan で反転するか）に左右されない。
ワールド座標は Unity のまま（y = 上）。答えの物体には `track`（`new` / `same` / `moved`）と `position` / `size`（3D の箱、m）が付き、
`frame` に `displaced` / `missing`（このフレームで空いた・無くなった物体）が入る。深度が足りず 3D にできない検出は `source: "unlocated"`（記憶にも VLM にも回さない）。

`?record=<名前>` で `logs/sequences/<名前>/<番号>/` にそのまま残し（`?analyze=false` なら残すだけ）、PC で流し直せる:

```bash
docker compose exec grounding_server python scripts/perception_replay.py logs/sequences/<名前> --reset
```

run には `depth_overlay.jpg`（RGB に、合わせた深度を色で重ねたもの）が残る。物体の上に深度の色が乗っていれば位置合わせは合っている。
3D で追っている物体は `data/object_tracks.json` に残る（再起動しても同じ ID）。

この段階の属性（`material` / `fragility`）は記憶に入るだけで、Plan のルール照合（`fragile` など。`vlm.py`）にはまだつながっていない。

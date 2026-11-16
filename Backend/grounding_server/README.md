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

`scene.update` で受け取ったシーンと、`rules.set` / `rules.compile` で受け取ったルールから Plan を作り、全クライアントに配る（M0）。
動作計画（MoveIt）、属性推定（VLM）、修正（`Correction`）の受け取りはまだ無い。

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
- **ルール**: 言葉で足す（`rules.compile`、LLM）か、属性・値・行き先を選んで足す（`rules.set`）。1 つずつ消せる
- **Plan**: step の表。行にマウスを置くと、図の矢印が太くなる
- **method を直接呼ぶ**: すべての method を、params の JSON を書いて呼べる（stream と中断も）
- **通信のログ**: 送ったもの・届いたものを新しい順に表示する

画面は `coground_server/static/ui.html` の 1 ファイル（ビルド不要）。書き換えたら、ブラウザを読み込み直すだけでよい。

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
| `internal_error` | サーバー内の想定外の例外 |
| （Unity 側のみ）`not_connected` / `timeout` / `disconnected` | `CoGroundServerClient` が出す |

### サーバーからのイベント

| event | data |
|---|---|
| `session.welcome` | `{session_id, server_version, protocol_version, methods}`（接続直後） |
| `state.updated` | `{version, updated_at, scene: {frame, objects, regions}, rules, plan}`（`plan` は計画が無ければ `null`） |
| `session.error` | `{code, message, details?}` |

### method（現在）

| method | params | result |
|---|---|---|
| `system.ping` | なし | `{pong, server_time}` |
| `system.describe` | なし | method と params スキーマの一覧 |
| `state.get` | なし | `state.updated` と同じ全体状態 |
| `scene.update` | `SceneSnapshot`（`coground_server/models.py`、例は `tests/fixtures/tabletop_scene.json`） | `{version, objects, regions}` |
| `rules.set` | `{rules: Rule[]}`（ルール全体を置き換える。空で消す） | `{version, rules, steps, unknown_regions}` |
| `rules.compile` | `{text, mode?: append / replace, apply?: bool}`（自然言語 → ルール。LLM を使う） | `{stage}` を stream で送ったあと `{rules, unresolved, applied, version?, steps?}` |
| `llm.ping` | なし | `{reply}`（LLM に届くかの確認。数秒かかる） |
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
| `Plan` / `Step` | 処理の出力。step は `from` / `to` / `rule_id` / `status` / `locked` / `trajectory_id` | |
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

## Plan を作る（M0）

シーンかルールが変わるたびに、サーバーが Plan を作り直す（`coground_server/planner.py`。LLM は使わない）。

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

## LLM

LLM の呼び出しは `coground_server/llm/` にまとめてある。ほかのコードは「入力 → Pydantic モデル」の関数だけを使う。

| ファイル | 内容 |
|---|---|
| `llm/client.py` | LLM を 1 回呼ぶ口（`LlmClient`）。本物の `AgentSdkLlm` は Claude Agent SDK（`claude-agent-sdk`。Claude Code の CLI を子プロセスで動かす）。ツールは使わせず、JSON Schema に合った答えを 1 つ返させる。テストでは `FakeLlm` |
| `llm/compile_rule.py` | 自然言語 → `Rule`。いまのシーンの領域・物体・語彙を見せて選ばせる。行き先がシーンに無いものは、ルールにせず `unresolved` に入れる |

**認証**: `.env.example` を `.env` という名前で写し、`CLAUDE_CODE_OAUTH_TOKEN`（ホストで `claude setup-token` を実行して作る）か `ANTHROPIC_API_KEY` を書いて、`make down && make up`。`.env` は Git に入れない。

```bash
docker compose exec grounding_server python scripts/ws_client.py call llm.ping
docker compose exec grounding_server python scripts/ws_client.py call rules.compile '{"text": "食器は流しに入れて、ごみは分別して捨てて"}'
```

- 1 回呼ぶたびに CLI を起動するので、数秒かかる。何度も続けて呼ぶ処理（物体ごとの属性推定など）には向かない
- 呼び出しの記録（プロンプト、答え、かかった時間）は `logs/llm.jsonl` に足されていく（`COGROUND_LLM_LOG`）
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

```csharp
var client = CoGroundServerClient.Instance;
JToken pong = await client.RequestAsync("system.ping");
await client.RequestAsync("debug.count", new { count = 5 }, onStream: d => Debug.Log(d));
client.StateUpdated += state => Debug.Log(state["version"]);
```

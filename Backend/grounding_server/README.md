# CoGround Grounding Server

ルールのグラウンディング（ルールのコンパイル、属性推定、適用判定、説明）を担うサーバー。Unity（Quest）とは WebSocket でつながる。
ROS（`Backend/docker/fetch_sim`）とは別のプロセスで、別のコンテナで動く。

```
 Unity (Quest / Editor)                         grounding_server (FastAPI, :8000)
  CoGroundServerClient ── ws://<host>:8000/ws ──>  Session ─ Router ─ handlers/*
                                                    │
                                                    └─ Services (StateStore, Hub; 後で LLM / VLM / clingo)
  ROS-TCP-Connector ──── :10000 ──> fetch_sim (ROS1 / MoveIt)   ← こちらとは独立
```

現在は通信の土台だけで、判定ロジック（M0〜M4）はまだ無い。`scene.update` で受け取ったシーンを保持し、全クライアントに配る。

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

確認用クライアント（Unity の代わり）:

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

型だけで、Plan を作る処理や `Correction` / `TrialLog` を受ける method・event はまだ無い。
ROS 側が動作計画・実行で扱う型は `docker/fetch_sim/ros_pkgs/coground_control/scripts/plan_types.py`（Plan のうちロボットに必要な部分と、軌道）。

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

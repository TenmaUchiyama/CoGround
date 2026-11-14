# Fetch シミュレーションを VR に重ねるための準備

> 全体の構成とコマンド一覧は `Backend/README.md`。MoveIt もコンテナ内で起動する。既定は Gazebo なし（`docker compose up`）で、以下の Gazebo を使う手順は `GAZEBO=true docker compose up` で起動する。

```
[Docker: fetch_sim (ROS1 Noetic)]                         [Unity: UserApp/CoGround]
 Gazebo ── /joint_states ──throttle 30Hz──> /unity/joint_states ─┐
        ── /gazebo/model_states ─relay──> /unity/fetch_pose ──────┤  ROS-TCP-Endpoint
        ── /odom ────────throttle 30Hz──> /unity/odom ────────────┤  :10000  ──TCP──> ROS-TCP-Connector
                                                                  │                    ├ FetchJointStateSubscriber (関節)
                                                                  │                    └ FetchBasePoseSubscriber (位置: SimWorldOrigin 基準)
```

## 1. Backend（済み / 確認手順）

| 追加・変更 | 内容 |
|---|---|
| `docker/fetch_sim/Dockerfile` | ROS-TCP-Endpoint v0.7.0（ROS1 版）と `coground_vr_bridge` をビルド。既定 CMD を `vr_sim.launch` に変更 |
| `docker/fetch_sim/compose.yaml` | `10000:10000` を公開。`GAZEBO_GUI=false` でヘッドレス起動 |
| `docker/fetch_sim/ros_pkgs/coground_vr_bridge/` | `vr_sim.launch`（Gazebo + Endpoint + `/unity/*` トピック）、`model_pose_relay.py`（Gazebo world 座標の真値姿勢） |
| `scripts/export_fetch_urdf.sh` | イメージ内の `fetch_description` を Unity の `Assets/URDF/Fetch/` に書き出す |

```bash
cd Backend/docker/fetch_sim
docker compose build
docker compose up                 # Gazebo GUI あり
GAZEBO_GUI=false docker compose up  # ヘッドレス

# 確認 (別ターミナル)
docker exec -it fetch_sim bash -ic 'rostopic hz /unity/joint_states /unity/fetch_pose'
```

### Unity に渡すトピック

| トピック | 型 | 用途 |
|---|---|---|
| `/unity/joint_states` | sensor_msgs/JointState | 関節角（30Hz） |
| `/unity/fetch_pose` | geometry_msgs/PoseStamped | Gazebo world 座標の base_link 真値（30Hz）。重ね合わせではこちらを使う |
| `/unity/odom` | nav_msgs/Odometry | 実機と同じ扱いにしたいとき用（スリップでずれる） |

### Quest から PC へ接続する場合（Windows 側）

Docker Desktop が Windows ホストの 10000 番を公開する。Quest からは **Windows の LAN IP** に接続する。
管理者 PowerShell でファイアウォールを開ける:

```powershell
New-NetFirewallRule -DisplayName "CoGround ROS-TCP 10000" -Direction Inbound -Protocol TCP -LocalPort 10000 -Action Allow -Profile Private
ipconfig   # Wi-Fi アダプタの IPv4 を確認
```

## 2. Unity（パッケージ追加済み / 手作業が必要な部分）

`Packages/manifest.json` に追加済み（次回 Unity 起動時に解決される）:

| パッケージ | バージョン | 備考 |
|---|---|---|
| com.unity.robotics.ros-tcp-connector | git v0.7.0 | **Windows に Git が必要**（UPM が git を使う） |
| com.unity.robotics.urdf-importer | git v0.5.2 | Runtime は Editor/Standalone のみ。Android(Quest) 非対応 → 下記参照 |
| com.unity.xr.openxr | 1.19.0 | |
| com.unity.xr.meta-openxr | 2.7.0 | Quest のパススルー（AR Foundation 6.x を連れてくる） |
| com.unity.xr.interaction.toolkit | 3.7.0 | 原点合わせのつかみ操作など |

### 手順

1. **Unity を開いてパッケージ解決を待つ**（エラーが出たら Console を確認）
2. **URDF 書き出し**: `bash Backend/scripts/export_fetch_urdf.sh`
3. **URDF 取り込み**: Project で `Assets/URDF/Fetch/fetch.urdf` を右クリック → *Import Robot from Selected URDF file*
   - Axis Type: `Y Axis`、Mesh Decomposer: `VHACD` か `Unity`（どちらでもよい）
4. 生成された `fetch` GameObject に
   - `FetchJointStateSubscriber`（右クリック → *Bind From URDF (Editor)* で関節を登録しておくと確実）
   - `FetchBasePoseSubscriber`（`Sim World Origin` に下記の空 GameObject を割り当て）
5. 空 GameObject `SimWorldOrigin` を作る。これが **Gazebo の world 原点 = 現実の部屋の基準点**。これを動かせば重ね合わせ位置が変わる
6. **Robotics > ROS Settings**: Protocol `ROS1`、ROS IP Address = Editor なら `127.0.0.1`、Quest なら PC の LAN IP、Port `10000`
7. **XR**: Build Settings で Android に切り替え → Project Settings > XR Plug-in Management > Android で `OpenXR` を有効化 → OpenXR の Feature Groups で `Meta Quest` 系（Meta Quest Support / Camera (Passthrough) / Session）を有効化
   - パススルーで重ねる場合: カメラの Clear Flags を Solid Color・背景 alpha 0、AR Camera Manager を XR Origin のカメラに追加
8. **Player Settings (Android)**: Internet Access = `Require`（ROS-TCP の通信に必要）、Scripting Backend = IL2CPP、ARM64

### MoveIt を Unity から操作する（RViz の MotionPlanning と同じ操作）

スクリプト: `UserApp/CoGround/Assets/Main/Script/`

| スクリプト | 役割 |
|---|---|
| `MoveItArmPanel` | オレンジの目標（手先）、Plan / Execute / Plan & Execute / Stop、グリッパー開閉、状態表示（画面左上のパネル） |
| `MoveItTrajectoryPreview` | 計画結果を緑の半透明ロボットで繰り返し再生（`MoveItArmPanel` を付けると自動で追加） |
| `FetchGhost` | 半透明の表示を作る共通処理 |

1. `fetch`（`RosJointToFetch` などが付いている GameObject）に **`MoveItArmPanel` を追加**する（設定は既定のままでよい）
2. Backend を起動（`make moveit` なら RViz も開くので見比べられる）→ Unity で Play
3. パネルの「目標を選択」→ Scene ビューの移動・回転ツールでオレンジの手先を動かす
4. **Plan** → 緑のロボットが計画した動きを繰り返す → **Execute** で実行（**Plan & Execute** で一度に）
   - 「目標を止めたら自動で Plan」をオンにすると、目標を動かして止めるたびに計画する
   - 「目標 = 現在」で目標を今の手先に戻す

目標は Unity の World 座標のまま `frame_id: world` で `/coground/arm/goal_pose` に送る。ROS 側は `auto_execute` が false（既定）のまま使う。
Quest で半透明が表示されない（シェーダーが削られる）場合は、Inspector の `Goal Material` / `Ghost Material` に半透明のマテリアルを指定する。
VR では `MoveItArmPanel.Goal` の Transform を手でつかめるようにし、`Plan()` / `Execute()` などを UI のボタンから呼ぶ（未実装）。

### 机などを MoveIt の衝突物体にする（Planning Scene）

1. Cube を置いて机の形にし（位置・回転・スケールは自由）、**`MoveItCollisionBox` を追加**する（形は BoxCollider を使う）
2. Play すると ROS の `scene_sync.py` が Planning Scene に `unity/<GameObject 名>` として登録し、MoveIt はそれを避けて計画する
   - 動かすとすぐ反映。無効化・削除・Play 停止（3 秒届かない）で消える
   - RViz の MotionPlanning では緑の箱として見える
3. 名前はシーン内で重複させない（同じ名前だと 1 つの物体として上書きされる）

### Pick & Place（机の上の箱を指定した場所へ運ぶ）

1. Unity のメニュー **CoGround > Pick & Place デモを配置** を押す → Fetch の正面に机・`BoxA`（赤）・`BoxB`（青）・置き場所 `PlaceA` / `PlaceB` が置かれる（`fetch` に `MoveItArmPanel` が無ければ追加される）。シーンを保存する
2. `make moveit` → Unity で Play
3. パネルの **Pick & Place** で「運ぶ箱」と「置き場所」を選び **運ぶ**。状態は `opening → approaching → descending → grasping → lifting → moving → lowering → releasing → retreating → succeeded`
   - **Stop** で中断。箱を持ったまま止まった場合は、同じ箱をもう一度「運ぶ」と置く手順から再開する

#### 半透明のゴーストで置き場所を指定する

各箱（`MoveItPickable`）には同じ色の半透明のゴーストが重なって表示される。**ゴーストを動かして離すと、ロボットがそこへ運ぶ。**

- 空中で離しても真下の面（机など）に合わせる。向きは水平の回転だけ使う。下に面が無ければ取り消してゴーストを箱に戻す
- 運んでいる間ゴーストは置き場所に残り、終わると箱に重なる。失敗したら箱の位置に戻る
- 2 つ続けて動かしてもよい（`MoveItPickPlaceQueue` が 1 つずつ順番に送る）。**Stop** で順番待ちも取り消す
- Editor: 再生中に Scene ビューでゴースト（`<箱の名前> (ghost)`）を動かして止めると、0.5 秒で置いたとみなす
- **VR（Distance Grab など）**: `MoveItPickable` の `Ghost Prefab` に、つかむためのコンポーネントを付けた **1 m の立方体**の prefab を指定する（箱の大きさに拡大縮小される）。`Commit When Still` をオフにし、離したときのイベントで `MoveItPickable.CommitGhost()` を呼ぶ
  - prefab に Rigidbody を付けるなら **isKinematic** にする（重力で落ちると「動かした」とみなされる）
  - 未設定のときのゴーストは BoxCollider（isTrigger）付きの Cube。ロボットや箱と物理で押し合わない

| コンポーネント | 付ける物 | 役割 |
|---|---|---|
| `MoveItCollisionBox` | 机・箱 | Planning Scene に衝突物体として登録 |
| `MoveItPickable` | 運ぶ箱（`MoveItCollisionBox` と一緒に） | 半透明のゴースト（置き場所の指定）、パネルで選べるようにする、つかんでいる間は `gripper_link` の子にして手に追従させる |
| `MoveItPickPlaceQueue` | （自動で作られる） | 運ぶ指令を順番に `pick_place_server` へ送る |
| `MoveItPlaceTarget` | 置き場所（空の GameObject） | 位置 = 置いたときの箱の底面の中心、向き = 箱の向き。再生中は半透明の板で表示 |

制約（ROS 側 `pick_place_server.py`）:
- 上からつかむだけ。箱は傾いていないこと、指の間（10 cm）に入る幅であること
- 胴体を上げても届くのは Fetch の正面 0.8 m 程度まで（机の高さ 0.70 m のとき）。届かないと `failed: ... 届かない` になる
- Unity では物理でつかまない（ROS が「くっつけた」間だけ手の子にする）

### 動作確認の順番（おすすめ）

1. Editor（Play）+ `127.0.0.1` で、Gazebo の Fetch と Unity の Fetch が同じ動きをするか
   - `docker exec -it fetch_sim bash -ic 'rosrun teleop_twist_keyboard teleop_twist_keyboard.py cmd_vel:=/teleop/cmd_vel'` で動かす
   - 関節の向きや符号が逆なら URDF 取り込み時の Axis Type を確認
2. Quest Link（PC VR）で Editor から確認
3. Quest 単体ビルドで LAN 接続

## 3. 注意点・未決事項

- **URDF Importer が Quest で動かない件**: 取り込んだプレハブには `UrdfJoint` などの URDF Importer コンポーネントが付く。Android ビルドでは「Missing Script」の警告になるが動作には影響しない。自作スクリプトは実行時に URDF Importer に依存しない作りにしてある（対応表で関節を解決）
- **Unity 6 と URDF Importer v0.5.2**: 公式サポートは 2020.2 世代。取り込み時にエラーが出たら知らせてほしい
- **重ね合わせの精度**: `SimWorldOrigin` の合わせ方（床の位置合わせ・マーカー・空間アンカー）は未実装。まずは手動配置か XRI でつかんで動かす想定
- **Gazebo の環境物（机・物体）** は Unity に送っていない。必要になったら `/gazebo/model_states` を同様に中継する
- ROS1 Noetic は EOL（2025-05）。将来 ROS 2 に移すなら ROS-TCP-Endpoint の `main-ros2` ブランチを使う

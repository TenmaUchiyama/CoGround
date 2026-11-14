# CoGround Backend — 何をどう使うか

迷ったらまずここを見る。詳細手順は `docs/` 以下。

## 全体像

ROS はすべて **ROS1 Noetic（Docker コンテナ `fetch_sim` の中）** で動かす。WSL 本体に ROS は入れない。
**Gazebo は必須ではない。** 既定では Gazebo を起動せず、MoveIt の計画結果をそのまま関節角として Unity に送る。

```
            ┌──────────── Docker: fetch_sim (ROS1 Noetic) ──────────────────┐
 ① ロボット │  [既定] 運動学だけのロボット (物理なし)                        │
            │  [GAZEBO=true] Gazebo + Fetch (物理あり)                       │
            │  [実機] 実機の Fetch (予定)                                    │
            │        ↑ 実行指令        │ /joint_states                       │
 ③ MoveIt   │  move_group ─────────────┘                                     │
            │     ↑ 計画・実行                                               │
 ④ 指令     │  arm_command_server (/coground/*)                              │
 ② Unity通信│  ROS-TCP-Endpoint :10000 + /unity/* (30Hz)                     │
            └────────┼───────────────────────────────────────────────────────┘
                     │ TCP
              Unity (Editor / Quest)
```

| 部品 | launch ファイル | 既定（Gazebo なし） | `GAZEBO=true` | 実機（予定） |
|---|---|---|---|---|
| ① ロボット | 既定: `kinematic_robot.launch` / Gazebo: `fetch_gazebo/playground.launch` | 運動学だけ | Gazebo | 実機 |
| MoveIt の実行先 | `moveit.launch` の `fake_execution` | 疑似コントローラ（計画どおりの関節角を出す） | Gazebo のコントローラ | 実機のコントローラ |
| ロボットの置き場所 | | **Unity が決める**（`/coground/robot/base_pose` → TF `world`→`base_link`） | Gazebo の真値（`/unity/fetch_pose`） | Unity で現実のロボットに合わせる（予定） |
| ② Unity 通信 | `unity_bridge.launch` | 使う | 使う | 使う |
| ③ MoveIt | `moveit.launch` | 使う | 使う | 使う |
| ④ 腕・グリッパーの指令 | `coground_control/control.launch` | 使う | 使う | 使う |
| まとめて起動 | `vr_sim.launch` | **これだけ起動すればよい**（`gazebo:=` で切り替え） | | （未作成） |

どちらを使うか:
- **既定（Gazebo なし）**: 軽い。MoveIt で計画した動きを Unity で見たいだけならこれ。物理・接触・台車の移動は無い。
- **`GAZEBO=true`**: 重力や物との接触、台車の移動、センサーが必要なとき。

自前パッケージの場所: `docker/fetch_sim/ros_pkgs/`

| パッケージ | 役割 |
|---|---|
| `coground_vr_bridge` | 起動まわり（`vr_sim.launch` など）と Unity への中継（`/unity/*`） |
| `coground_control` | MoveIt を使った指令ノード（`/coground/*`）: 腕・グリッパー（`arm_command_server.py`）、衝突物体（`scene_sync.py`）、Pick & Place（`pick_place_server.py`）。Unity・実機に依存しない |

`ros_pkgs/` 以下はコンテナにマウントしているので、**launch や Python の変更は `docker compose restart` だけで反映される**。
ノード・パッケージの追加や `CMakeLists.txt` / `package.xml` の変更は `docker compose build` が必要。
Fetch 本体の URDF・MoveIt 設定（[fetch_ros](https://github.com/fetchrobotics/fetch_ros)）は apt の `ros-noetic-fetch-*`（0.9.1）を使っている。中身を変えたくなったら fetch_ros をソースで `ros_pkgs/` に入れる。

### グラウンディングサーバー（ROS とは別）

ルールのグラウンディングを担う FastAPI サーバーは `grounding_server/` にある（Unity と WebSocket `:8000` でつながる。ROS には依存しない）。使い方とプロトコルは `grounding_server/README.md`。

## よく使うコマンド

すべて `Backend/docker/fetch_sim` で実行する。

| やりたいこと | コマンド |
|---|---|
| Dockerfile を変えた / パッケージ・ノードを追加した後 | `docker compose build` |
| launch や Python を変えた後 | `docker compose restart` |
| 動作確認（MoveIt + 指令ノード + Unity 向け出力） | `bash ../../scripts/smoke_test.sh` |
| 計画したら即実行するモード | `AUTO_EXECUTE=true docker compose up` |
| 起動（Gazebo なし: MoveIt + Unity 通信） | `docker compose up` |
| Gazebo ありで起動（画面あり） | `GAZEBO=true docker compose up` |
| Gazebo ありで起動（画面なし） | `GAZEBO=true GAZEBO_GUI=false docker compose up` |
| **MoveIt を起動して RViz で操作**（起動済みなら RViz だけ開く） | `make moveit`（odom 基準は `make moveit-odom`。Backend 直下） |
| RViz も出す（Unity の World 基準） | `RVIZ=true docker compose up`（`make rviz`） |
| RViz も出す（odom 基準） | `RVIZ=true RVIZ_FRAME=odom docker compose up`（`make rviz-odom`） |
| 起動中に RViz をもう 1 つ開く | `make rviz-world` / `make rviz-odom-add`（Backend 直下。再起動しない） |
| MoveIt なし | `MOVEIT=false docker compose up` |
| コンテナに入る | `docker exec -it fetch_sim bash` |
| コンテナで 1 コマンド実行 | `docker exec -it fetch_sim bash -c 'rosrun パッケージ ノード'`（`bash -c` を付ける。`docker exec fetch_sim rosrun ...` 直接は不可） |
| Unity と同じ方法で接続できるか確認 | `python3 ../../scripts/check_unity_connection.py`（Quest 用には Windows の LAN IP を引数に） |
| Unity 向けトピックの確認 | `docker exec -it fetch_sim bash -ic 'rostopic hz /unity/joint_states /unity/fetch_pose'` |
| 台車をキーボードで動かす（Gazebo あり: Gazebo の台車 / なし: Unity の `FetchCmdVelDriver` が動かす） | `make teleop`（Backend 直下） |
| 停止 | `docker compose down` |

## RViz と TF

### RViz で MoveIt を操作する（`make moveit`）

1. オレンジの手先（目標）をドラッグする。目標は Planning タブの Goal State（`random valid` など）でも選べる
2. 左下の MotionPlanning パネル → Planning タブで **Plan**（緑の半透明が計画結果）→ **Execute**（**Plan & Execute** で一度に）
3. Gazebo なしなら、実行した動きは `/joint_states` 経由で Unity のロボットにも反映される

計画グループは Planning Group で切り替える（`arm` / `arm_with_torso` / `gripper`）。

RViz の設定は `ros_pkgs/coground_vr_bridge/rviz/` にある（`fetch_moveit_config` の `moveit.rviz` をコピーして手を加えたもの）。
RViz で変えた表示は File > Save Config でここに上書きすれば次回から使われる（マウントしているのでビルド不要）。

| 設定 | 基準 (Fixed Frame) | 見えるもの |
|---|---|---|
| `world.rviz` | `world` = Unity の World | MoveIt の計画、TF（world / odom / base_link）、`/odom` の軌跡（オレンジの矢印） |
| `odom.rviz` | `odom` | 同上。odom の原点からどう動いたかを見る |

両方とも LaserScan（`/base_scan`）と PointCloud2（`/head_camera/...`）を無効の状態で入れてある（Gazebo ありのときにチェックを入れて使う）。

TF は Gazebo の有無にかかわらず `world → odom → base_link` になる:

| | `world → odom` | `odom → base_link` |
|---|---|---|
| Gazebo なし | `base_pose_tf.py`: Unity から最初に届いた位置で固定 | `base_pose_tf.py`: そこからの移動量（`/odom` も出す） |
| `GAZEBO=true` | `world_odom_tf.py`: Gazebo の真値と `/odom` から計算 | Gazebo（車輪オドメトリ） |

Gazebo なしで odom の原点を取り直したいときは `docker compose restart`。

## Unity から腕を動かす（`/coground/*`）

**座標の基準は Unity の World**（= ROS の `world` フレーム）。Unity の `FetchBasePosePublisher` がロボットの置き場所を送るので、
物体などの位置は Unity の World 座標を `To<FLU>()` して `frame_id: world` で送ればよい（ロボット基準への変換は ROS 側で行う）。
将来 Quest の部屋アンカーを基準にするときは、Unity 側で基準にする Transform を差し替える。

Unity で RViz と同じように操作する（目標をドラッグ → Plan → Execute、計画結果のプレビュー）には、`fetch` に `MoveItArmPanel` を付ける（`docs/VR_OVERLAY_SETUP.md`）。

標準メッセージだけなので Unity 側でメッセージ生成は不要（ROS-TCP-Connector 同梱の型で足りる）。
既定は「計画 → Unity でプレビュー → execute で実行」。`AUTO_EXECUTE=true` なら計画後すぐ実行。

| 向き | トピック | 型 | 内容 |
|---|---|---|---|
| Unity → ROS | `/coground/robot/base_pose` | geometry_msgs/PoseStamped | Unity の World での `base_link` の位置・向き（`To<FLU>()` 済み、frame_id `world`）。TF `world`→`base_link` になる。届くまでは原点（Gazebo なしのときだけ） |
| Unity → ROS | `/coground/arm/goal_pose` | geometry_msgs/PoseStamped | 手先（`wrist_roll_link`）の目標。frame_id は **`world`（Unity の World をそのまま `To<FLU>()`）** か `base_link`。TF で `base_link` に変換して計画する |
| Unity → ROS | `/coground/arm/goal_joints` | sensor_msgs/JointState | 関節角の目標（name と position だけ使う。一部の関節だけでもよい） |
| Unity → ROS | `/coground/arm/execute` | std_msgs/Empty | 直前の計画を実行 |
| Unity → ROS | `/coground/arm/stop` | std_msgs/Empty | 実行中の動作を止める |
| Unity → ROS | `/coground/scene/objects` | visualization_msgs/MarkerArray | 衝突物体の箱（Unity の `MoveItCollisionBox` が送る）。CUBE のみ、`text` = 名前、`action` ADD / DELETE、frame_id `world`。`scene_sync.py` が Planning Scene の `unity/<名前>` にする。3 秒届かないと消える |
| Unity → ROS | `/coground/gripper/command` | std_msgs/Float64 | 指の開き幅 [m]（0.0 = 閉、0.1 = 全開） |
| Unity → ROS | `/coground/pick_place/command` | std_msgs/String (JSON) | 箱を運ぶ。`{"object": "BoxA", "frame_id": "world", "place": {"position": [x,y,z], "orientation": [x,y,z,w]}}`（position = 置いたときの箱の中心）。`pick_place_server.py` が受ける |
| ROS → Unity | `/coground/pick_place/status` | std_msgs/String | `accepted`（指令を受け付けた）→ `opening` … `succeeded` / `failed`、または `rejected`（`: 詳細` が付く） |
| ROS → Unity | `/coground/pick_place/attached` | std_msgs/String | 手にくっついている箱の名前（`""` = なし）。Unity の `MoveItPickable` がこの間、箱を手に追従させる |
| ROS 内部 | `/coground/pick_place/held` | std_msgs/String | 扱い中の箱。`scene_sync.py` はこの間 Unity の値で上書きしない |
| ROS → Unity | `/coground/arm/planned_trajectory` | trajectory_msgs/JointTrajectory | 計画結果（プレビュー用。失敗時は空） |
| ROS → Unity | `/coground/arm/status` | std_msgs/String | `planning` / `planned` / `plan_failed` / `executing` / `succeeded` / `exec_failed` / `stopped` / `rejected`（`: 詳細` が付く） |

計画・実行中に来た目標は `rejected: busy` で捨てる。計画は 1 回実行すると破棄される。

コマンドラインで試す:

```bash
docker exec -it fetch_sim bash -ic 'rostopic pub -1 /coground/arm/goal_pose geometry_msgs/PoseStamped "{header: {frame_id: base_link}, pose: {position: {x: 0.6, y: 0.2, z: 0.9}, orientation: {w: 1.0}}}"'
docker exec -it fetch_sim bash -ic 'rostopic echo /coground/arm/status'
docker exec -it fetch_sim bash -ic 'rostopic pub -1 /coground/arm/execute std_msgs/Empty "{}"'
```

## MoveIt の使い方（ROS1 / Python）

コンテナ内で `moveit_commander` を使う。計画グループ名は `arm`（胴体込みは `arm_with_torso`）、グリッパーは `gripper`。

```python
import sys, rospy, moveit_commander
from geometry_msgs.msg import PoseStamped
moveit_commander.roscpp_initialize(sys.argv)
rospy.init_node("example")
arm = moveit_commander.MoveGroupCommander("arm")
p = PoseStamped(); p.header.frame_id = "base_link"   # 座標は base_link 基準
p.pose.position.x, p.pose.position.y, p.pose.position.z = 0.6, 0.2, 0.9
p.pose.orientation.w = 1.0
arm.set_pose_target(p)
arm.go(wait=True)   # 計画 + 実行（既定は Unity のロボット、GAZEBO=true なら Gazebo の腕が動く）
```

計画だけして実行しない: `arm.plan()`。実機で絶対に動かしたくない確認時は `moveit.launch` を `fake_execution:=true` で起動する。

## 実機に切り替えるとき（予定）

- ① を起動せず、コンテナの `ROS_MASTER_URI` を実機の roscore に向ける。② と ③ はそのまま使う。
- ROS1 は双方向に通信するため、WSL2 は `networkingMode=mirrored`、コンテナは `network_mode: host` と `ROS_IP` の設定が必要になる見込み。
- 実機用の launch（`vr_real.launch`）は未作成。

## ドキュメント

- `docs/VR_OVERLAY_SETUP.md` — Unity / Quest 側の設定と重ね合わせの手順

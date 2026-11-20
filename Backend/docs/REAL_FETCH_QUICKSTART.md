# 実機 Fetch クイックスタート & ToDo

実機の Fetch を動かせるようになり、最終的に「サーバーが卓上の物を理解する」ところまで行くための、**やる順番つきの手順書**。
上から順に進めればよい。各ステップに「✅ できたかの確認」がある。確認できるまで次へ進まない。

> VR (Quest) と grounding_server は **Phase 0〜2 では使わない**。まず Fetch 単体で動かす練習をする。

---

## 全体の地図

```
Phase 0  安全と準備        ← 触る前に必ず読む
Phase 1  Fetch とつなぐ    ← PC と Fetch を ROS でつなぐ
Phase 2  実機で Navigation / MoveIt   ← Fetch 単体で動かす練習
Phase 3  Meta Quest の SceneData を共有  ← Gazebo/RViz で見てから実機
Phase 4  サーバーで「卓上に何があるか」を理解
```

| Phase | ゴール | 目安 |
|---|---|---|
| 0 | 安全手順を覚え、実機の前に座れる | 半日 |
| 1 | PC から Fetch のトピックが見える | 半日〜1日 |
| 2 | 地図を作り、指定地点へ走り、腕を MoveIt で動かせる | 数日 |
| 3 | Quest の部屋/机データが RViz に出る → 実機座標と合う | 数日〜1週間 |
| 4 | 机の写真/点群から「何がどこにあるか」がサーバーで分かる | 1〜2週間 |

---

## 用語ミニ辞典（初心者向け）

| 言葉 | 一言で |
|---|---|
| ROS | ロボット用のソフトをつなぐ仕組み。プログラム同士が「トピック」で話す |
| トピック | プログラム間の掲示板。例: `/cmd_vel` に速度を書くと台車が動く |
| roscore / ROS master | トピックの案内所。Fetch 本体で動いている |
| Navigation (move_base) | 「あそこへ行け」と言うと障害物を避けて走ってくれる |
| MoveIt | 「手先をここへ」と言うと腕の動きを計画して動かしてくれる |
| RViz | ロボットの見ているものを 3D で表示する画面（**見るだけ**でなく目標指定もできる） |
| Gazebo | 仮想のロボットを動かすシミュレータ（練習・事前確認用） |
| TF | 「物の位置は、どこを基準にした座標か」の情報。座標ずれの原因 No.1 |
| SceneData (Quest) | Quest が部屋をスキャンして作る壁・床・机・家具の情報 |

---

## Phase 0: 安全と準備（最初に必ず）

実機は人にぶつかると怪我をする。**Fetch は重く、腕も速い。**

### ToDo

- [ ] **ランストップ（非常停止）の場所を確認**する。ロボット背面の赤いボタンと、ワイヤレスのランストップがある
  - 押す → モータが止まる。解除するとまた動く
- [ ] 実機を使うときは**必ず 2 人以上**、または 1 人が常にランストップに手が届く状態にする
- [ ] 床のケーブル・椅子を片づけ、走る範囲 1.5 m 以内に人を入れない
- [ ] 最初の動作は**速度を落とす**（台車 0.2 m/s 以下、腕は MoveIt の velocity scaling 0.1〜0.2）
- [ ] 研究室の Fetch の **ホスト名 / IP / ユーザー / パスワード**を先輩か管理者に聞いてメモ
  - ここでは仮に `fetch1`（ホスト名）とする。自分の環境の値に読み替える
- [ ] Fetch の ROS バージョンを聞く（出荷時は **Melodic / Ubuntu 18.04** が多い。このリポジトリの Docker は **Noetic**）

✅ できたか: ランストップを押すとどうなるか、口で説明できる。

---

## Phase 1: PC と Fetch をつなぐ

### 仕組み
Fetch 本体に `roscore` がいる。自分の PC は「その案内所を教えてもらう」設定をすれば、Fetch のトピックが見える。

```
自分の PC (Docker, Noetic) ──同じネットワーク──> Fetch (roscore, Melodic)
        ROS_MASTER_URI=http://fetch1:11311
```

### ToDo

- [ ] 自分の PC と Fetch を**同じネットワーク（同じ Wi-Fi/LAN）**につなぐ
- [ ] `ping fetch1` が通る（通らなければ IP で `ping 192.168.x.x`）
- [ ] 双方で名前解決できるようにする（片方向だと「トピックは見えるのにデータが来ない」になる）
  - 自分の PC の `/etc/hosts` に `192.168.x.x fetch1` を追記
  - Fetch 側にも自分の PC のホスト名/IP を入れてもらう
- [ ] 環境変数を設定（ターミナルを開くたびに必要。`.bashrc` に書くと楽）

  ```bash
  export ROS_MASTER_URI=http://fetch1:11311
  export ROS_IP=<自分のPCのIP>      # `hostname -I` で確認
  ```
- [ ] Docker で使う場合は `network_mode: host` にする（compose の設定を確認。bridge だと ROS の通信が通らないことが多い）
- [ ] `rostopic list` で Fetch のトピックが出る
- [ ] `rostopic echo /joint_states -n1` で数値が流れてくる（**ここが「本当につながった」の目印**）
- [ ] RViz を起動し、Fixed Frame を `base_link` にして RobotModel を追加 → Fetch の姿勢が実機と同じ

### つまずいたら
| 症状 | 原因と対処 |
|---|---|
| `Unable to communicate with master` | `ROS_MASTER_URI` の綴り、ネットワーク、ファイアウォール |
| `rostopic list` は出るが `echo` で何も来ない | `ROS_IP` 未設定、または Fetch 側が自分のホスト名を引けない |
| RViz のロボットが真っ白/ばらばら | `robot_description` が見えていない、または TF が来ていない |
| ROS のバージョン違いでメッセージエラー | Melodic↔Noetic は基本的に会話できるが、`rosbag` や一部のカスタム msg は注意 |

✅ できたか: 自分の PC の RViz に、動かした実機の腕がリアルタイムで追従する。

> 💡 **うまくいかないときの逃げ道**: 自分の PC 側のソフト（MoveIt など）を使わず、**Fetch 本体にログインして直接起動**する方法もある（`ssh fetch@fetch1`）。まずはこちらで動作確認 → 慣れたら PC 側へ移す、でも構わない。

> 🧰 **確認ツール**: `Backend/docker/fetch_real`（`fetch_check`）を使うと、Phase 1〜2-A の確認（マスター・ノードへの到達・センサーの周期・TF・バッテリー・ランストップなど）を 1 コマンドで済ませられる。使い方は `Backend/docker/fetch_real/README.md`。

---

## Phase 2: 実機で Navigation と MoveIt を使う

### 2-A. 実機の状態を知る（読むだけ・動かさない）

- [ ] 次のトピックが出ているか確認
  | トピック | 意味 |
  |---|---|
  | `/base_scan` | 台車のレーザー（障害物を見る） |
  | `/odom` | 台車が「自分は何 m 動いた」と思っている値 |
  | `/joint_states` | 腕・頭・グリッパーの角度 |
  | `/head_camera/rgb/image_raw` | 頭のカメラ画像 |
  | `/head_camera/depth_registered/points` | 頭のカメラの点群（Phase 4 で使う） |
  | `/cmd_vel` または `/base_controller/command` | 台車への速度指令 |
- [ ] `rqt_image_view` でカメラ画像が見える
- [ ] RViz に LaserScan（`/base_scan`）と PointCloud2 を表示できる

### 2-B. 台車を手動で動かす（最初の一歩）

- [ ] **周りを確認し、ランストップに手を置く**
- [ ] teleop で少しだけ動かす（このリポジトリの `make teleop` は**シミュレータ用**。実機は topic 名を確認して使う）

  ```bash
  rosrun teleop_twist_keyboard teleop_twist_keyboard.py cmd_vel:=/cmd_vel
  ```
  - 動かないとき: `rostopic info /cmd_vel` で購読者がいるか見る。名前違いなら `/base_controller/command`
- [ ] 前進 → 停止 → 回転が思った通りに動く
- [ ] キーを離すと止まる（止まらなければ即ランストップ）

### 2-C. 地図を作る（SLAM）

「地図なしでは Navigation はできない」。最初に 1 回、部屋の地図を作る。

- [ ] 地図作成ノードを起動（Fetch 標準: `fetch_navigation` の `build_map.launch`）

  ```bash
  roslaunch fetch_navigation build_map.launch
  ```
- [ ] RViz に `/map` を出して、teleop でゆっくり部屋を一周する
- [ ] 壁がきれいに描かれたら保存

  ```bash
  rosrun map_server map_saver -f ~/maps/lab_room
  ```
  → `lab_room.pgm` と `lab_room.yaml` ができる
- [ ] 保存した地図の場所をメモし、**git には入れても入れなくても良いが、場所は README に残す**

### 2-D. 地図を使って自律走行（Navigation）

- [ ] 地図つきで Navigation を起動

  ```bash
  roslaunch fetch_navigation fetch_nav.launch map_file:=$HOME/maps/lab_room.yaml
  ```
- [ ] RViz の **「2D Pose Estimate」** で、地図上の今の位置と向きを教える（これで自己位置が合う）
- [ ] レーザーの点（赤/緑）が地図の壁に重なれば OK。ずれていたらもう一度 Pose Estimate
- [ ] RViz の **「2D Nav Goal」** で近い場所（1〜2 m 先）を指定 → 走る
- [ ] 人が前を横切ったら避ける/止まることを確認（**必ず安全を確保してから**）
- [ ] 狭い場所で止まる/ぐるぐる回る場合は costmap の `inflation_radius` を見直す

✅ できたか: 地図上の 3 か所を 2D Nav Goal で往復できる。

> 参考: このリポジトリの `docker/fetch_sim/ros_pkgs/coground_control/config/nav` と `launch/nav.launch` に、シミュレータ用の move_base 設定がある。実機用の設定を作るときの手本になる（そのまま実機に使わず、パラメータを確認してコピーする）。

### 2-E. MoveIt で腕を動かす

- [ ] **腕の周りに物・人がいない**ことを確認
- [ ] MoveIt を起動（Fetch 標準）

  ```bash
  roslaunch fetch_moveit_config move_group.launch
  ```
- [ ] RViz に **MotionPlanning** 表示を追加（`fetch_moveit_config` の `moveit.rviz` を開くと最初から入っている）
- [ ] 対話マーカー（球と矢印）で手先を少し動かし → **Plan** → 軌道を目で確認 → **Execute**
  - 最初は `Plan` だけ押して動きを眺める。安全そうなら `Execute`
  - Velocity Scaling を **0.1〜0.2** にする
- [ ] 名前つき姿勢（`tuck` など）に戻せる。使えるのは `arm_with_torso` / `arm` グループ
- [ ] グリッパーを開閉できる（`gripper` グループ）
- [ ] **障害物を追加**する: RViz の Scene Objects で箱を机の位置に置く → 計画が箱を避ける
- [ ] Python で動かす最小例（`moveit_commander`）

  ```python
  import sys, rospy, moveit_commander
  moveit_commander.roscpp_initialize(sys.argv)
  rospy.init_node("first_move")
  arm = moveit_commander.MoveGroupCommander("arm")
  arm.set_max_velocity_scaling_factor(0.1)
  print(arm.get_current_pose())      # まず読むだけ
  ```

✅ できたか: RViz で指定した手先位置へ、安全な速度で腕が動く。

### 2-F. シミュレータで予行演習（実機を動かす前の習慣）

実機でやる前に、まず同じことをシミュレータでやると安全。このリポジトリでできる:

```bash
cd Backend
make build          # 初回のみ
make gazebo         # Gazebo + MoveIt
make test-moveit    # 腕の動作テスト
make teleop         # 台車を動かす
```
詳しい意味は `Backend/README.md` と `docs/SYSTEM_OVERVIEW.md`。

---

## Phase 3: Meta Quest の SceneData を共有する

### 目的
Quest が持つ部屋の形（壁・床・机など）を ROS に渡し、Fetch から見えるようにする。**まず Gazebo/RViz で見て、次に実機。**

### 先に決めること（ここが一番の落とし穴）

**Quest の座標系と Fetch の座標系は別物**。以下の 2 つを必ず決める。

- [ ] 座標系の違いを確認する
  | | Unity (Quest) | ROS |
  |---|---|---|
  | 上方向 | **Y** | **Z** |
  | 手系 | 左手系 | 右手系 |
  | 単位 | m | m |
  | 変換 | `ros.x = unity.z`, `ros.y = -unity.x`, `ros.z = unity.y`（このリポジトリの既存コードのやり方に合わせる） |
- [ ] **共通の基準点を決める**（例: 床の一点 + 向き、またはマーカー）。Quest の起動ごとに原点が変わるため、毎回これで合わせる必要がある
  - 簡単: 机の角や床のマーカー（AprilTag / ArUco）を Quest と Fetch の両方で見て基準にする
  - 既存の `world_odom_tf.py` が world→odom の TF を扱っているので、同じ形で `world→quest_origin` を作ると流れが揃う

### 3-A. 受け取れる形式を決める（ToDo）

- [ ] Quest の何を共有したいかを書き出す
  - [ ] 床・壁・天井（Scene Mesh）
  - [ ] 机・家具（Scene Anchors / 箱の大きさ）
  - [ ] 物体（自分で置く CoGroundSceneObject）
  - [ ] 手の位置・視線（今回は後回しでよい）
- [ ] Unity 側の既存コード `Scene/CoGroundSceneReporter` は何を送っているか読む（`Backend/docs/SYSTEM_OVERVIEW.md` §Unity の `Scene/`）
- [ ] 形式を決める。**おすすめは「箱（中心 + 大きさ + 向き）の一覧」**。メッシュより軽く、MoveIt の障害物にそのまま使える

### 3-B. Gazebo / RViz で見る（実機の前）

- [ ] Unity から ROS へ箱の一覧を送る（既存の `/coground/scene/objects` が手本。`scene_sync.py` が受けて MoveIt の障害物にしている）
- [ ] RViz に **PlanningScene** を出し、箱が表示される
- [ ] 箱を `visualization_msgs/MarkerArray` でも出し、色を付けて見やすくする（机=茶、壁=灰）
- [ ] **Unity の位置を動かすと RViz の箱も同じだけ動く**ことを確認（座標変換の検証）
- [ ] Gazebo に同じ寸法の机を置き、MoveIt の計画が机を避けることを確認

### 3-C. 実機で試す

- [ ] 基準点（マーカー）を決めて床にテープなどで印を付ける
- [ ] Quest で部屋をスキャン → 基準点を Quest 上で指定 → ROS へ送信
- [ ] RViz で **実機のレーザー/点群**と **Quest の壁・机**を重ねて表示する
- [ ] 重なっていれば成功。ずれていたら:
  - 向きが 90° 違う → 軸の変換ミス
  - 一定量ずれる → 基準点の置き間違い
  - 大きさが違う → 単位または Scale
- [ ] ずれ量をメモし、許容範囲を決める（例: 3 cm 以内ならつかめる、5 cm 以上は要補正）
- [ ] 補正方法を決める（基準マーカーの再検出、Fetch のカメラで再位置合わせ）

✅ できたか: RViz 上で Quest の机の天面が、Fetch の点群の机の天面とだいたい重なる。

---

## Phase 4: サーバーで「卓上に何があるか」を理解する

### 目的
机の上の物を検出し、`いくつ・何・どこ` を `grounding_server` が持てるようにする。
既存のサーバーは **Unity が教える真値**（`scene.update`）を使っている。それを **カメラ由来の検出結果**に置き換える／併用する段階。

### 4-A. 何を理解したいか決める

- [ ] 対象の物を 3〜5 種類に絞る（例: コップ・ボトル・箱・ボール）
- [ ] 出力形式を決める。既存の `scene.update` に合わせるのが楽
  ```json
  { "objects": [ {"id": "cup_1", "type": "cup", "position": [x, y, z], "size": [w, d, h]} ] }
  ```
- [ ] 評価基準を決める（例: 位置誤差 2 cm 以内、種類の正答率 90%）

### 4-B. 机の天面を見つける

- [ ] 頭を机の方へ向け、`/head_camera/depth_registered/points` を受ける
- [ ] 点群を ROS の座標系（`base_link` か `world`）に変換（TF を使う）
- [ ] 平面検出（RANSAC）で**机の面**を見つける。Phase 3 の Quest の机と比較すると答え合わせができる
- [ ] 机の面より **上にある点**だけ残す → それが「物」

### 4-C. 物を切り出す（セグメンテーション）

- [ ] 残った点をクラスタリング（距離でグループ分け）→ 1 グループ = 1 個の物
- [ ] 各グループの**中心・大きさ（バウンディングボックス）**を計算する
- [ ] RViz に Marker で表示して、目で正しさを確認

### 4-D. 何の物か分類する

選択肢（易→難）:
1. **色や大きさで決める**（実験用に物を決めておくなら十分）
2. **2D 物体検出**（YOLO など）の結果を点群の位置に対応づける
3. **VLM（画像+言語モデル）** に「この机の上に何がある？」と聞く（既存の LLM 連携の延長でできる）

- [ ] まず 1 を作り、動いたら 2 / 3 に置き換える
- [ ] 検出結果に**信頼度**（0〜1）を付ける

### 4-E. サーバーにつなぐ

- [ ] ROS 側ノード（例: `scene_perception.py`）を作り、4-C/D の結果を Fetch → サーバーに送る
  - 送り方は既存の `RosbridgeRobot`（rosbridge :9090）が使える
- [ ] サーバー側に、受け取った物体リストで `scene.update` 相当の状態を更新する処理を追加
- [ ] **真値モード**（Unity から）と **検出モード**（カメラから）を切り替えられるようにする
- [ ] Web UI（`/ui`）に検出された物が表示される
- [ ] 既存の planner（ルール → Plan）が検出された物を対象に Plan を作れる
- [ ] 2 つの比較（Unity 真値 vs 検出値）を記録し、誤差を数字で出す

✅ できたか: 机に物を 3 つ置くと、サーバーの UI に 3 つ表示され、位置誤差が許容内。

---

## 進捗チェックリスト（コピーして使う）

```
Phase 0  [ ] ランストップ確認  [ ] 2人体制  [ ] 低速設定  [ ] IP/パスワード入手
Phase 1  [ ] ping  [ ] rostopic list  [ ] joint_states 受信  [ ] RViz でロボット追従
Phase 2  [ ] topics 確認  [ ] teleop  [ ] 地図作成  [ ] Nav Goal 往復
         [ ] MoveIt Plan  [ ] MoveIt Execute  [ ] 障害物回避  [ ] シムで予行演習
Phase 3  [ ] 座標系の決定  [ ] 基準点の決定  [ ] RViz に Quest の箱  [ ] 移動追従を確認
         [ ] 実機の点群と重ね合わせ  [ ] ずれ量の記録
Phase 4  [ ] 机の面検出  [ ] 物のクラスタ  [ ] 分類  [ ] サーバー連携  [ ] 精度評価
```

## ふりかえり用メモ欄

| 日付 | やったこと | 詰まったこと | 解決方法 |
|---|---|---|---|
| | | | |

## 困ったときの順番

1. **まず止める**（ランストップ）。原因は後で考える
2. `rostopic list` / `rostopic echo` でデータが来ているか見る
3. `rqt_graph` でノードのつながりを見る
4. `tf` を疑う: `rosrun tf view_frames` で TF の木を PDF にする
5. それでもダメなら、**シミュレータで再現**してから先輩に聞く（再現手順があると解決が速い）

## 注意（このドキュメントの限界）

- コマンドやパッケージ名（`fetch_navigation`, `fetch_moveit_config` など）は Fetch の標準的な構成に基づく。**研究室の Fetch のバージョン・設定で違う場合がある**ので、最初に管理者へ確認すること
- 実機での確認は未実施。実際に試して違った部分は、このファイルに追記・修正していくこと

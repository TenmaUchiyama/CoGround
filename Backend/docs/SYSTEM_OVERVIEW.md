# CoGround 全体の流れ（Unity / grounding_server / ROS）

迷ったときに頭の中で追うための地図。細かい手順・トピックの JSON は次を見る:
`Backend/README.md`（ROS 側）、`grounding_server/README.md`（サーバーとプロトコル）、各スクリプト冒頭の docstring。

---

## 1. 登場人物と 2 本の経路

```mermaid
flowchart LR
    subgraph U["Unity (Editor / Quest)"]
        UV["表示<br/>ロボット本体・Ghost・Plan"]
        UM["手動操作<br/>腕パネル・Ghost つかみ・台車目標"]
        US["シーン報告<br/>CoGroundSceneReporter"]
    end

    subgraph S["grounding_server (FastAPI :8000)"]
        SP["planner.py<br/>ルール → Plan (何をどこへ)"]
        SM["motion.py<br/>動作計画の依頼"]
        SE["executor.py<br/>step を順に実行"]
        SR["robot.py<br/>RosbridgeRobot / FakeRobot"]
        UI["Web UI (/ui)"]
    end

    subgraph R["ROS (Docker fetch_sim, Noetic)"]
        EP["ROS-TCP-Endpoint :10000"]
        RB["rosbridge :9090"]
        PP["pick_place_server.py"]
        AC["arm_command_server.py"]
        MG["move_group (MoveIt)"]
    end

    US -- "WebSocket: scene.update" --> SP
    SP -- "state.updated (plan)" --> UV
    UI -- "rules / motion.plan / exec.*" --> SP
    SM --> SR
    SE --> SR
    SR -- "経路B: /coground/task/*, /coground/skill/*" --> RB --> PP

    UM -- "経路A: /coground/arm/*, pick_place/command, base/*" --> EP
    EP --> AC
    EP --> PP
    EP -- "/unity/*, plan_result など" --> UV

    AC -- moveit_commander --> MG
    PP -- moveit_commander --> MG
```

| 経路 | 通り道 | 使いどころ |
|---|---|---|
| **A: 直結** | Unity ⇄ ROS-TCP-Endpoint (:10000) | 手動操作（腕パネル、Ghost で置き場所指定、台車の目標）と、**表示用のデータすべて**（関節角・台車位置・計画結果） |
| **B: サーバー経由** | Unity → サーバー (:8000) → rosbridge (:9090) → ROS | ルールに基づくタイディ（計画 → 実行）。**いまのメイン** |

経路 B でも、ロボットが動いた結果は経路 A（`/unity/*`）で Unity に表示される。

---

## 2. ROS の中身

### 2.1 ノード構成

```mermaid
flowchart TB
    subgraph IN["入口"]
        EP["ROS-TCP-Endpoint :10000<br/>(Unity)"]
        RB["rosbridge :9090<br/>(grounding_server)"]
    end

    subgraph CTRL["coground_control（自作の指令ノード）"]
        AC["arm_command_server.py<br/>腕・グリッパー単発"]
        PP["pick_place_server.py<br/>移動→つかむ→移動→置く"]
        SS["scene_sync.py<br/>Unity の箱 → 衝突物体"]
        TP["trajectory_path.py<br/>手先の通り道"]
        BC["base_command_server.py<br/>台車の目標 (NAV=true)"]
    end

    subgraph MOVEIT["MoveIt / Nav"]
        MG["move_group<br/>fake_execution=true"]
        MB["move_base (NAV=true)"]
    end

    subgraph ROBOT["運動学ロボット (Gazebo なし)"]
        JSP["joint_state_publisher"]
        RSP["robot_state_publisher → TF"]
        FBD["fake_base_driver.py (NAV=true)<br/>cmd_vel を積分"]
        BPT["base_pose_tf.py (NAV=false)<br/>Unity の位置 → TF"]
    end

    EP --> AC & PP & SS & BC
    RB --> PP
    AC -- moveit_commander --> MG
    PP -- "moveit_commander<br/>/compute_fk, /apply_planning_scene" --> MG
    PP --> MB
    SS -- "/collision_object" --> MG
    BC --> MB
    MB -- "/coground/base/cmd_vel" --> FBD
    MG -- "/move_group/fake_controller_joint_states" --> JSP
    JSP -- "/joint_states" --> RSP
    JSP -- "/joint_states → throttle 30Hz → /unity/joint_states" --> EP
    FBD -- "TF world→base_link, /odom, /unity/base_pose" --> EP
```

起動の入口は `vr_sim.launch` だけ。`NAV` は既定で `true`（`make up` でも台車を ROS 側で動かす）。デモ一式は `make coground`。

### 2.2 自作トピックと MoveIt の関係

`/coground/*` は **MoveIt に直接届くトピックではない**。自作ノードが受け取り、
**`moveit_commander`（MoveIt 公式の Python クライアント）** で move_group の標準 action / service を呼ぶ。
Unity が MoveIt のメッセージ型を生成しなくて済むように、Unity とは標準メッセージ（`PoseStamped`、`Empty`、`String` の JSON など）だけでやりとりする。

腕を 1 回動かす例（`arm_command_server.py`）:

```mermaid
sequenceDiagram
    participant U as Unity<br/>(MoveItArmPanel)
    participant A as arm_command_server.py
    participant M as move_group
    participant J as joint_state_publisher

    U->>A: /coground/arm/goal_pose (PoseStamped, world)
    Note over A: TF で world → base_link
    A->>M: arm.plan()  [action /move_group, plan_only]
    M-->>A: RobotTrajectory
    A-->>U: /coground/arm/planned_trajectory（計画結果を外に出すだけ）
    A-->>U: /coground/arm/status "planned"
    Note over U: 緑 Ghost で再生 (MoveItTrajectoryPreview)

    U->>A: /coground/arm/execute (Empty)
    A->>M: arm.execute(last_plan)  [action /execute_trajectory]
    M->>J: /move_group/fake_controller_joint_states
    J-->>U: /joint_states → /unity/joint_states (30Hz)
    Note over U: RosJointToFetch が本体の関節に反映
    A-->>U: /coground/arm/status "succeeded"
```

| moveit_commander の呼び出し | 裏で使う MoveIt 標準のもの |
|---|---|
| `plan()` | action `/move_group`（plan_only） |
| `execute()` | action `/execute_trajectory` |
| `stop()` | topic `/trajectory_execution_event` |
| `gripper.go()` | action `/move_group`（計画 + 実行） |

### 2.3 pick_place_server.py の 3 つの入口

| 入口 | 使う人 | 内容 |
|---|---|---|
| `/coground/pick_place/command` | Unity（経路 A） | 箱を指定場所へ運ぶ（手動操作用） |
| `/coground/task/plan_request` → `plan_result` | サーバー（経路 B） | **動かさずに**全 step を計画し、通しで再生できる時間軸（台車・関節・持っている区間）を返す |
| `/coground/skill/goal` → `feedback` / `state` | サーバー（経路 B） | `navigate` / `pick` / `place` を 1 つずつ実行。`plan_ref` 付きなら計画した軌道を再生（`replay`）、だめならその場で計画し直す（`replanned`） |

出力 `/coground/pick_place/attached` が出ている間、Unity は物体をグリッパーに追従させる。

---

## 3. Unity の中身（`Assets/Main/Script/`）

```mermaid
flowchart LR
    subgraph SRV["サーバーとやりとり (WebSocket :8000)"]
        SC["Server/CoGroundServerClient"]
        SR["Scene/CoGroundSceneReporter<br/>+ CoGroundSceneObject<br/>+ CoGroundApproachPoint"]
        PV["Plan/CoGroundPlanView"]
        RS["Plan/CoGroundRulesSender (確認用)"]
    end

    subgraph ROS["ROS とやりとり (TCP :10000)"]
        RJ["Fetch/RosJointToFetch<br/>← /unity/joint_states"]
        RBP["Navigation/RosBasePoseToFetch<br/>← /unity/base_pose (NAV=true)"]
        FBP["Fetch/FetchBasePosePublisher<br/>→ /coground/robot/base_pose (NAV=false)"]
        TPP["MoveIt/CoGroundTaskPlanPlayer<br/>← /coground/task/plan_result"]
        AP["MoveIt/MoveItArmPanel + TrajectoryPreview/Line<br/>⇄ /coground/arm/*"]
        CB["MoveIt/MoveItCollisionBox<br/>→ /coground/scene/objects"]
        PK["PickPlace/MoveItPickable + Queue<br/>→ /coground/pick_place/command"]
        RN["Navigation/RosBaseNavigator<br/>⇄ /coground/base/*"]
        NM["Navigation/NavMapPublisher<br/>→ /coground/nav/map_unity"]
    end

    SR --> SC
    RS --> SC
    SC --> PV
```

| フォルダ | 役割 |
|---|---|
| `Fetch/` | ロボット本体の表示（関節角）と、NAV=false のときの台車位置の送信 |
| `Navigation/` | 台車。`RosBaseNavigator` / `RosBasePoseToFetch` が NAV=true 用。`BaseNavigator` 系は ROS を使わない旧方式 |
| `MoveIt/` | 腕の手動操作と計画の表示。`CoGroundTaskPlanPlayer` が動作計画を通しで再生（シーケンスバー） |
| `PickPlace/` | Ghost をつかんで離す → そこへ運ぶ（経路 A の手動 Pick & Place） |
| `Scene/` | 物体・場所・止まる位置をサーバーへ（`scene.update`、値は真値） |
| `Plan/` | サーバーの Plan を描く（「物 → 行き先」の弧とラベル） |
| `Server/` | サーバーとの WebSocket |

---

## 4. メインの流れ（経路 B: タイディ）

```mermaid
sequenceDiagram
    autonumber
    participant U as Unity
    participant W as Web UI (/ui)
    participant S as grounding_server
    participant P as pick_place_server (ROS)
    participant M as move_group

    U->>S: scene.update（物体・場所・止まる位置）
    W->>S: rules.compile / rules.set
    Note over S: planner.py: ルール → Plan（step = 物 1 つ）
    S-->>U: state.updated (plan)
    Note over U: CoGroundPlanView が「物 → 行き先」を描く

    W->>S: motion.plan
    S->>P: /coground/task/plan_request（rosbridge）
    P->>M: 仮想ロボットで 移動→pick→移動→place を全部計画
    P-->>S: /coground/task/plan_result（時間軸）
    P-->>U: /coground/task/plan_result（TCP :10000）
    Note over U: CoGroundTaskPlanPlayer が半透明ロボットで通し再生

    W->>S: exec.start
    loop step ごと
        S->>P: /coground/skill/goal navigate → pick → navigate → place (plan_ref 付き)
        P->>M: 計画どおり再生 (replay) / だめなら計画し直し (replanned)
        P-->>S: /coground/skill/feedback（phase, succeeded / failed）
        M-->>U: /unity/joint_states, /unity/base_pose, /coground/pick_place/attached
        Note over U: 本体のロボットが動き、物体が手に付いて動く
    end
    S-->>U: state.updated (execution)
```

いまの範囲: 物体の種類・位置・置き場所はシミュレーションの真値が届く。**探索（look_for）はまだ範囲外**で、実行の単位は pick / place（+ navigate）。
`motion.plan` / `exec.*` はいま Web UI から操作する（Unity からは送っていない）。

---

## 5. 混乱しやすい点

| 点 | 中身 |
|---|---|
| **台車の位置を誰が決めるか** | `NAV=false`: Unity（`FetchBasePosePublisher` → `base_pose_tf.py`）。`NAV=true`（`make coground`）: ROS（`fake_base_driver.py` → `/unity/base_pose` → `RosBasePoseToFetch`） |
| **座標** | サーバーは Unity 座標（左手系・Y 上）。ROS は右手系・Z 上、frame `world` = Unity の World。変換は位置 `(x,y,z) → (z,-x,y)`（Unity の `To<FLU>()` と同じ）。サーバーの `robot.py` が ROS に渡すときに変換する |
| **`/coground/*` は MoveIt のトピックではない** | 自作ノードが受けて `moveit_commander` で MoveIt を呼ぶ（2.2） |
| **`plan_types.py` は使われていない** | 中の `/coground/plan/*` はどこからも使われていない。実際は `/coground/task/*`（計画）と `/coground/skill/*`（実行） |
| **手動の経路はメインと別** | `MoveItArmPanel`、Ghost の Pick & Place、`BaseNavigator`（Unity だけの台車）はデバッグ・手動用 |
| **代役ロボット** | サーバーに `COGROUND_ROSBRIDGE_URL` が無いと `FakeRobot` になり、ROS なしで動く（ROS は呼ばれない） |

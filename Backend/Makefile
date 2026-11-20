.DEFAULT_GOAL := help

COMPOSE := docker compose --project-directory docker/fetch_sim -f docker/fetch_sim/compose.yaml
SERVICE := fetch_sim
# コンテナからホストの画面に出す許可 (RViz / Gazebo の画面を使うターゲットの先頭で呼ぶ)
ALLOW_X := bash scripts/allow_x.sh
# 実機 Fetch 用の確認ツール (docker/fetch_real)。シムで試すときは compose.sim.yaml を重ねる
REAL_COMPOSE := docker compose --project-directory docker/fetch_real -f docker/fetch_real/compose.yaml
REAL_SIM_COMPOSE := $(REAL_COMPOSE) -f docker/fetch_real/compose.sim.yaml
REAL_IMAGE := coground/fetch-real:noetic
# make real-check CHECK="'sense.*' -v" のように fetch_check run に渡す引数
CHECK ?=

.PHONY: help build up coground test test-moveit test-nav moveit moveit-odom gazebo gazebo-headless rviz rviz-odom rviz-world rviz-odom-add ps logs shell enter teleop restart stop down real-build real-sim real-sim-check real-sim-shell real-sim-down real-up real-check real-shell real-down real-save

help:
	@printf '%s\n' 'build  Build image' 'coground  Start the CoGround demo (MoveIt + ROS move_base base navigation, NAV=true) and check it' 'test-moveit  Arm smoke test (plan/execute via /coground/arm/*)' 'test-nav  Check Unity base pose reaches ROS TF (Play NavSim first; WATCH=10 to follow)' 'test  test-moveit + test-nav' 'up  Start MoveIt + Unity bridge' 'moveit  Start MoveIt and open RViz to operate it (world)' 'moveit-odom  Same, RViz in odom frame' 'gazebo  Start with Gazebo GUI' 'gazebo-headless  Start Gazebo without GUI' 'rviz  Start with RViz (world = Unity World)' 'rviz-odom  Start with RViz (odom)' 'rviz-world / rviz-odom-add  Open another RViz in the running container' 'ps  Show container status' 'logs  Follow logs' 'shell / enter  Open ROS shell' 'teleop  Drive the base (Gazebo, or Unity FetchCmdVelDriver without Gazebo)' 'restart  Restart service' 'stop  Stop service' 'down  Remove containers and network' '' '--- 実機 Fetch 確認ツール (docker/fetch_real) ---' 'real-build  Build the fetch_real image' 'real-sim  Start fetch_real attached to the running fetch_sim' 'real-sim-check  Run checks against the sim (CHECK="...")' 'real-sim-shell / real-sim-down' 'real-up / real-check / real-shell / real-down  Same on the robot (run on Fetch)' 'real-save  Save the image to fetch-real.tar.gz for copying to Fetch'

build:
	$(COMPOSE) build $(SERVICE)

up:
	$(COMPOSE) up -d $(SERVICE)

# デモ一式 (MoveIt + ROS の move_base による台車ナビゲーション) を起動して揃ったか確かめる。既定で RViz も開く (RVIZ=false で無効)
coground:
	bash scripts/coground_up.sh

test-moveit:
	bash scripts/smoke_test.sh

test-nav:
	bash scripts/nav_check.sh

test: test-moveit test-nav

# MoveIt を起動して操作用の RViz を開く (起動済みなら RViz だけ開く)
moveit:
	$(ALLOW_X)
	bash scripts/moveit_rviz.sh

moveit-odom:
	$(ALLOW_X)
	FRAME=odom bash scripts/moveit_rviz.sh

gazebo:
	$(ALLOW_X)
	GAZEBO=true GAZEBO_GUI=true $(COMPOSE) up -d $(SERVICE)

gazebo-headless:
	GAZEBO=true GAZEBO_GUI=false $(COMPOSE) up -d $(SERVICE)

rviz:
	$(ALLOW_X)
	RVIZ=true $(COMPOSE) up -d $(SERVICE)

rviz-odom:
	$(ALLOW_X)
	RVIZ=true RVIZ_FRAME=odom $(COMPOSE) up -d $(SERVICE)

# 起動中のコンテナに RViz をもう 1 つ開く (再起動しない)
rviz-world:
	$(ALLOW_X)
	$(COMPOSE) exec -d $(SERVICE) bash -c 'roslaunch coground_vr_bridge rviz.launch frame:=world'

rviz-odom-add:
	$(ALLOW_X)
	$(COMPOSE) exec -d $(SERVICE) bash -c 'roslaunch coground_vr_bridge rviz.launch frame:=odom'

ps:
	$(COMPOSE) ps -a

logs:
	$(COMPOSE) logs -f $(SERVICE)

shell enter:
	$(COMPOSE) exec $(SERVICE) bash

# repeat_rate: 押している間 10Hz で送り続ける / key_timeout: キーを離して 0.6 秒で停止指令
# Gazebo あり: Gazebo の台車が動く / Gazebo なし: Unity の FetchCmdVelDriver が台車を動かす
teleop:
	$(COMPOSE) exec $(SERVICE) bash -ic 'rosrun teleop_twist_keyboard teleop_twist_keyboard.py cmd_vel:=/teleop/cmd_vel _repeat_rate:=10.0 _key_timeout:=0.6'

restart:
	$(COMPOSE) restart $(SERVICE)

stop:
	$(COMPOSE) stop $(SERVICE)

down:
	$(COMPOSE) down

# ---- 実機 Fetch 確認ツール (docker/fetch_real) ----
real-build:
	$(REAL_COMPOSE) build fetch_real

# シムの fetch_sim のネットワークに相乗りして起動 (fetch_sim が先に動いている必要がある)
real-sim:
	@docker inspect -f '{{.State.Running}}' fetch_sim 2>/dev/null | grep -q true || { echo 'fetch_sim が動いていない (make up / make gazebo-headless)'; exit 1; }
	$(REAL_SIM_COMPOSE) up -d fetch_real

real-sim-check: real-sim
	docker exec -t fetch_real_sim fetch_check run $(CHECK)

real-sim-shell:
	docker exec -it fetch_real_sim bash

real-sim-down:
	$(REAL_SIM_COMPOSE) down

# 以下は Fetch 本体の上で実行する
real-up:
	$(REAL_COMPOSE) up -d fetch_real

real-check:
	docker exec -t fetch_real fetch_check run $(CHECK)

real-shell:
	docker exec -it fetch_real bash

real-down:
	$(REAL_COMPOSE) down

# Fetch へ運ぶ: scp fetch-real.tar.gz fetch1: && ssh fetch1 'docker load < fetch-real.tar.gz'
real-save:
	docker save $(REAL_IMAGE) | gzip > fetch-real.tar.gz
	@ls -lh fetch-real.tar.gz

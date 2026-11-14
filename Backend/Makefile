.DEFAULT_GOAL := help

COMPOSE := docker compose --project-directory docker/fetch_sim -f docker/fetch_sim/compose.yaml
SERVICE := fetch_sim

.PHONY: help build up moveit moveit-odom gazebo gazebo-headless rviz rviz-odom rviz-world rviz-odom-add ps logs shell enter teleop restart stop down

help:
	@printf '%s\n' 'build  Build image' 'up  Start MoveIt + Unity bridge' 'moveit  Start MoveIt and open RViz to operate it (world)' 'moveit-odom  Same, RViz in odom frame' 'gazebo  Start with Gazebo GUI' 'gazebo-headless  Start Gazebo without GUI' 'rviz  Start with RViz (world = Unity World)' 'rviz-odom  Start with RViz (odom)' 'rviz-world / rviz-odom-add  Open another RViz in the running container' 'ps  Show container status' 'logs  Follow logs' 'shell / enter  Open ROS shell' 'teleop  Drive the base (Gazebo, or Unity FetchCmdVelDriver without Gazebo)' 'restart  Restart service' 'stop  Stop service' 'down  Remove containers and network'

build:
	$(COMPOSE) build $(SERVICE)

up:
	$(COMPOSE) up -d $(SERVICE)

# MoveIt を起動して操作用の RViz を開く (起動済みなら RViz だけ開く)
moveit:
	bash scripts/moveit_rviz.sh

moveit-odom:
	FRAME=odom bash scripts/moveit_rviz.sh

gazebo:
	GAZEBO=true GAZEBO_GUI=true $(COMPOSE) up -d $(SERVICE)

gazebo-headless:
	GAZEBO=true GAZEBO_GUI=false $(COMPOSE) up -d $(SERVICE)

rviz:
	RVIZ=true $(COMPOSE) up -d $(SERVICE)

rviz-odom:
	RVIZ=true RVIZ_FRAME=odom $(COMPOSE) up -d $(SERVICE)

# 起動中のコンテナに RViz をもう 1 つ開く (再起動しない)
rviz-world:
	$(COMPOSE) exec -d $(SERVICE) bash -c 'roslaunch coground_vr_bridge rviz.launch frame:=world'

rviz-odom-add:
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

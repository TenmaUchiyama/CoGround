.DEFAULT_GOAL := help
# grounding_server（:8000）と detector（YOLO-World, :8001）を compose.yaml でまとめて扱う
COMPOSE := docker compose
# GPU の無いマシン用（detector を CPU で動かす）
COMPOSE_CPU := $(COMPOSE) -f compose.yaml -f compose.cpu.yaml
SERVICE := grounding_server
DETECT := detector

.PHONY: help build up up-cpu down ps logs test shell ping detect-build detect-restart detect-logs detect-test

help:
	@printf '%s\n' \
	  'build  Build both images (detector downloads weights the first time)' \
	  'up  Start grounding_server :8000 + detector :8001 (GPU)' \
	  'up-cpu  Same, detector on CPU (no NVIDIA Container Toolkit)' \
	  'down  Stop and remove both' \
	  'ps  Show status' \
	  'logs  Follow logs of both' \
	  'test  Run grounding_server tests' \
	  'shell  Open shell in grounding_server container' \
	  'ping  Call system.ping over WebSocket' \
	  '' \
	  '--- detector だけ ---' \
	  'detect-build  Rebuild detector image' \
	  'detect-restart  Restart detector after code changes (no auto reload)' \
	  'detect-logs  Follow detector logs' \
	  'detect-test  Run detection tests (CPU, fake model)'

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

up-cpu:
	$(COMPOSE_CPU) up -d

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

test:
	$(COMPOSE) run --rm --no-deps $(SERVICE) python -m pytest -q

shell:
	$(COMPOSE) run --rm $(SERVICE) bash

ping:
	$(COMPOSE) exec $(SERVICE) python scripts/ws_client.py call system.ping

detect-build:
	$(COMPOSE) build $(DETECT)

detect-restart:
	$(COMPOSE) restart $(DETECT)

detect-logs:
	$(COMPOSE) logs -f $(DETECT)

# 偽モデルなので GPU なしで動かす
detect-test:
	$(COMPOSE_CPU) run --rm --no-deps $(DETECT) python -m pytest -q tests/test_detection.py tests/test_segmentation.py

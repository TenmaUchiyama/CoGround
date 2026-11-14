.DEFAULT_GOAL := help
COMPOSE := docker compose
SERVICE := grounding_server

.PHONY: help build up down logs test shell ping

help:
	@printf '%s\n' 'build  Build image' 'up  Start server on :8000 (auto reload)' 'down  Stop' 'logs  Follow logs' 'test  Run tests in container' 'shell  Open shell in container' 'ping  Call system.ping over WebSocket'

build:
	$(COMPOSE) build $(SERVICE)

up:
	$(COMPOSE) up -d $(SERVICE)

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f $(SERVICE)

test:
	$(COMPOSE) run --rm --no-deps $(SERVICE) python -m pytest -q

shell:
	$(COMPOSE) run --rm $(SERVICE) bash

ping:
	$(COMPOSE) exec $(SERVICE) python scripts/ws_client.py call system.ping

COMPOSE ?= podman compose
ENV = set -a; [ -f .env ] && . ./.env; set +a;

.PHONY: up down psql sync sync-hist run test
up:        ; $(COMPOSE) up -d
down:      ; $(COMPOSE) down
psql:      ; podman exec -it futbol-db psql -U futbol -d futbol
sync:      ; $(ENV) python -m sync.sync_bsd
sync-hist: ; $(ENV) python -m sync.sync_bsd --historicos
run:       ; $(ENV) uvicorn app.main:app --reload
test:      ; pytest -q

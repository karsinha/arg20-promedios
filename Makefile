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

.PHONY: timer-on timer-off
timer-on:
	mkdir -p ~/.config/systemd/user
	cp deploy/futbol-sync.* deploy/futbol-live.service ~/.config/systemd/user/
	systemctl --user daemon-reload
	systemctl --user enable --now futbol-sync.timer futbol-live.service
timer-off:
	systemctl --user disable --now futbol-sync.timer futbol-live.service

.PHONY: migrate
migrate:   ; for f in db/migrations/*.sql; do podman exec -i futbol-db psql -U futbol -d futbol < $$f; done
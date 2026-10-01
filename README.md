# Futbol Argentina

Liga Profesional Argentina 2026 al estilo Promiedos. FastAPI + PostgreSQL + Jinja2/HTMX. Detalle y hallazgos: `docs/PROYECTO.md`.

## Estructura
```
arg20-promedios/
├── app/                     # la web (solo LEE de la base)
│   ├── main.py
│   ├── core/                # config, pool de Postgres, Jinja2
│   ├── modules/
│   │   ├── portada.py       # portada y pestañas (tabla + fixture + jugadores)
│   │   ├── parcial.py       # fragmentos HTMX
│   │   ├── seo.py · og.py   # SEO, sitemap y tarjetas Open Graph
│   │   ├── descenso_pagina.py
│   │   ├── torneo/          # tablas, playoffs, descenso, copas (queries + router + funciones puras)
│   │   ├── club/            # página de club y "Mi club"
│   │   └── jugadores/       # goleadores y asistidores
│   ├── templates/           # home.html, club.html, macros.html, partials/
│   └── static/              # css/, js/, crests/
├── sync/                    # sync_bsd.py · live.py · cambios.py (unico que escribe)
├── db/                      # schema.sql y migrations/
├── deploy/                  # timers y servicios systemd
├── scripts/                 # probe_bsd.py, equipos_abreviaturas.py, optimizar_escudos.py, checks/
├── tests/
├── docs/                    # PROYECTO.md, maqueta/home.html
├── compose.yaml · Makefile · requirements.txt · .env.example

## Puesta en marcha
```bash
bash scripts/migrar_estructura.sh      # una vez: mueve tus archivos actuales
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                   # completar BSD_TOKEN
make up                                # base nueva (o usa tu contenedor futbol-db)
make sync-hist && make sync            # historicos + partidos y stats
python scripts/equipos_abreviaturas.py # simulacion; luego --aplicar
make run                               # http://127.0.0.1:8000
make test
```

# Futbol Argentina

Liga Profesional Argentina 2026 al estilo Promiedos. FastAPI + PostgreSQL + Jinja2/HTMX. Detalle y hallazgos: `docs/PROYECTO.md`.

## Estructura
```
futbol-argentina/
├── app/                     # la web (solo LEE de la base)
│   ├── main.py
│   ├── core/                # config, pool de Postgres, Jinja2
│   ├── modules/
│   │   ├── portada.py       # compone los bloques de la home
│   │   ├── torneo/          # tablas, fixture, selector (queries + router)
│   │   └── jugadores/       # goleadores y asistidores
│   │   # futuros: usuarios/, foro/ (mismo molde: queries.py + router.py)
│   ├── templates/           # home.html, macros.html, partials/ (fragmentos HTMX)
│   └── static/css/
├── sync/sync_bsd.py         # job BSD -> PostgreSQL (unico que escribe)
├── db/
│   ├── schema.sql           # esquema completo (base vacia)
│   └── migrations/          # cambios para bases ya creadas (001_...)
├── scripts/                 # probe_bsd.py, equipos_abreviaturas.py, checks/
├── tests/
├── docs/                    # PROYECTO.md, maqueta/home.html
├── compose.yaml · Makefile · requirements.txt · .env.example
```

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

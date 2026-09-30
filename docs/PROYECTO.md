# Futbol Argentina (MVP estilo Promiedos)

Web de una sola liga: **Liga Profesional Argentina 2026** (30 equipos). Stack: Python, FastAPI, PostgreSQL. Meta futura: foro.

## Layout (6 bloques)
1. Título · 2. "Liga Profesional" · 3. Selector: Clausura / Apertura / Anual / Promedios · 4. Tabla (por zona A/B en Clausura y Apertura) · 5. Fixture (por fecha) · 6. Goleadores y asistidores

## Decisiones
- Monolito FastAPI modular (torneo, jugadores, foro, usuarios). Frontend: Jinja2 + HTMX.
- Fuente de datos principal: **BSD** (sports.bzzoiro.com). Highlightly/OpenFoot quedan opcionales.
- `sync/` es el único que escribe en la base; `app/` solo lee.
- Anual y Promedios se **calculan** desde los partidos (vistas SQL), no se guardan.
- Goleadores y asistidores suman `player-stats` por partido (BSD no trae incidentes de gol).
- Escudos: originales en `crests_raw/` → `scripts/optimizar_escudos.py` → `app/static/crests/<abreviatura>.webp`. Si falta uno, la web muestra el círculo con la abreviatura.
- Nombre/abreviatura propios: `scripts/equipos_abreviaturas.py` (BSD es inconsistente). Sin abreviatura la web usa las 3 primeras letras del nombre.

## Estado
- [x] Maqueta visual, `schema.sql` v2, `probe_bsd.py`
- [x] `sync_bsd.py` funcionando (goles en contra confirmados a mano)
- [x] API FastAPI con los 6 bloques conectados + rediseño de la web
- [x] Escudos (30) y script de optimización
- [ ] **Validar las tablas** con `scripts/checks/cruce_tabla.py` (Clausura vs BSD; Apertura/Anual vs CSV externo). En curso: `/standings/` de 2026 trae una estructura distinta a la esperada; el script ahora busca las filas de equipos recorriendo toda la respuesta.
- [ ] Reglamento AFA (desempates, playoffs en Anual/Promedios, ventana 2024–2026)
- [ ] Sync automático (cron/timer) y límites/términos de BSD
- [ ] Páginas de equipo y de partido; partidos en vivo
- [ ] Usuarios/auth → foro (hilos por partido primero)

## Estructura del repo
```
app/        core/ (config, db, templating) · modules/ (portada, torneo, jugadores) · templates/ · static/ (css, crests)
sync/       sync_bsd.py
db/         schema.sql · migrations/
scripts/    probe_bsd.py · equipos_abreviaturas.py · optimizar_escudos.py · checks/
crests_raw/ originales de escudos
tests/ · docs/ · compose.yaml · Makefile · requirements.txt
```
`sync_bsd.py` y `equipos_abreviaturas.py` leen `BSD_TOKEN`/`DATABASE_URL` del entorno (no del `.env`; `make sync` los carga). `cruce_tabla.py` sí lee `.env`.

## Hallazgos de la sonda
- Liga Profesional = `league_id 85`. Auth: `Authorization: Token <BSD_TOKEN>`. Base: `/api/v2`.
- Temporadas: 2026 = id 1635 (**un solo id** para Apertura y Clausura); 2025 = Apertura 1637 + Clausura 1636; 2024 = 1638 (una sola etapa, 28 equipos, 27 fechas).
- **Apertura vs Clausura 2026:** `group_name` dice "Clausura, Group X" en todos los partidos. Se separan por fecha: `event_date < 2026-06-15` = Apertura. 240 partidos de zona por torneo (210 group-stage + 30 interzonales; 16 fechas de 15 partidos).
- `stage`: `group-stage` = zona, `league-phase` = interzonales (cuentan para la tabla), `round-of-16`/`quarterfinals`/`semifinals`/`final` = playoffs (15 partidos, del Apertura). Pasan los 8 primeros de cada zona. En playoffs `group_name` es inconsistente.
- Estados: `finished`, `notstarted`, `postponed`.
- Postergado con reemplazo: Sarmiento–River fecha 11 (id 223766) tiene otro id para la nueva fecha (604493). `replaced_by` viene en `null`: se detecta por equipos + fecha + instancia (`reprogramado = true`).
- **Goles/asistencias:** `/events/{id}/player-stats/` → `goals` y `goal_assist`. La suma por equipo coincide con el marcador salvo goles en contra (no se asignan a nadie). Sin minutos de gol.
- **Jugadores:** `/players/{id}/` → `name`, `short_name`, `position`, `current_team_id`.
- **Tablas históricas:** `/leagues/85/standings/?season_id=...`. Para 2026 solo trae el Clausura; las filas de equipo no están donde se asumía (ver cruce_tabla).
- Nombres de equipo inconsistentes entre endpoints ("Club Atlético Platense" vs "Platense"): usar `ext_id` y nuestras abreviaturas.

## Pendientes / a verificar
- Cómo filtra fechas `/events/` (`date_from`/`date_to` devolvieron partidos futuros).
- Reglamento AFA: ¿Anual/Promedios excluyen playoffs? ¿ventana 2024–2026? ¿desempates? (supuestos en `schema.sql`; hoy se ordena por pts, dg, gf).
- Goles en contra y penales en `player-stats`.
- Límites reales y términos de uso de BSD (7.500 req/día viene de un README ajeno).
- Equipos ascendidos en Promedios (sin historial de todos los años).
- Si `sync_bsd.py --historicos` falla con `KeyError: 'team_id'`, corregir igual que en cruce_tabla.
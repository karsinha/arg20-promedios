# Futbol Argentina (MVP estilo Promiedos)

Web de una sola liga: **Liga Profesional Argentina 2026** (30 equipos). Stack: Python, FastAPI, PostgreSQL. Meta futura: foro.

## Layout (6 bloques)
1. Título "Futbol Argentina" · 2. "Liga Profesional"
3. Selector: Clausura / Apertura / Anual / Promedios
4. Tabla de posiciones · 5. Fixture (por fecha) · 6. Goleadores y asistidores

## Decisiones
- Monolito FastAPI modular (torneo, jugadores, foro, usuarios). Frontend: Jinja2 + HTMX.
- Fuente de datos principal: **BSD** (sports.bzzoiro.com). Highlightly/OpenFoot quedan opcionales.
- Un job en segundo plano sincroniza BSD → PostgreSQL; la web lee solo de la base.
- Anual y Promedios se **calculan** desde los partidos (vistas SQL), no se guardan.
- Goleadores y asistidores se calculan sumando `player-stats` por partido (BSD no trae incidentes de gol).

## Estado
- [x] Maqueta visual (HTML publicado como artifact, datos de ejemplo)
- [x] `schema.sql` v2 (ajustado a los datos reales de BSD)
- [x] `probe_bsd.py` (sonda de cobertura) — ya corrida, resultados abajo
- [ ] Job de sincronización BSD → PostgreSQL (`sync_bsd.py`, primer borrador sin probar)
- [ ] API FastAPI + conectar los 6 bloques
- [ ] Usuarios/auth → foro (hilos por partido primero) → en vivo, páginas de equipo/partido

## Hallazgos de la sonda
- Liga Profesional = `league_id 85`. Auth: `Authorization: Token <BSD_TOKEN>`. Base: `/api/v2`.
- Temporadas: 2026 = id 1635 (**un solo id** para Apertura y Clausura); 2025 = Apertura 1637 + Clausura 1636; 2024 = 1638 (una sola etapa `regular-season`, 28 equipos, 27 fechas).
- **Apertura vs Clausura 2026:** `group_name` dice "Clausura, Group X" en todos los partidos, no sirve. Se separan por fecha: `event_date < 2026-06-15` = Apertura. Verificado: 240 partidos de zona en el Apertura (210 group-stage + 30 interzonales).
- `stage`: `group-stage` = zona, `league-phase` = interzonales (cuentan para la tabla), `round-of-16`/`quarterfinals`/`semifinals`/`final` = playoffs (15 partidos, todos del Apertura). En playoffs `group_name` es inconsistente.
- Estados: `finished`, `notstarted`, `postponed`.
- Partido postergado con reemplazo: Sarmiento–River fecha 11 (id 223766, postponed) tiene otro id para la nueva fecha (604493). `replaced_by` viene en `null`, hay que detectarlo por equipos + fecha + instancia.
- **Goles/asistencias:** `/events/{id}/player-stats/` → `goals` y `goal_assist` por jugador. En 5 partidos de prueba la suma de goles por equipo coincide con el marcador. Sin minutos de gol.
- **Jugadores:** `/players/{id}/` devuelve `name`, `short_name`, `position`, `current_team_id`. `player-stats` trae solo `player_id`.
- **Tablas históricas:** `/leagues/85/standings/?season_id=...` devuelve `standings[]` con `played`, `pts`, etc. Para 2026 solo trae el Clausura.
- Nombres de equipo inconsistentes entre endpoints ("Club Atlético Platense" vs "Platense"): usar `ext_id` y nuestras propias abreviaturas.

## Pendientes / a verificar
- Cómo filtra fechas `/events/` (`date_from`/`date_to` devolvieron partidos futuros).
- Reglamento AFA: ¿Anual/Promedios excluyen playoffs? ¿ventana 2024–2026? ¿desempates de la tabla? (supuestos en `schema.sql`).
- Goles en contra y penales en `player-stats` (los 5 partidos de prueba no los cubren).
- Límites reales y términos de uso de BSD (7.500 req/día viene de un README ajeno).
- Qué pasa con los equipos ascendidos en Promedios (no tienen historial de todos los años).

## Archivos
```
futbol-argentina/
├── PROYECTO.md
├── probe_bsd.py
├── schema.sql        (v2)
└── sync_bsd.py       (borrador)
```
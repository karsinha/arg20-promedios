# ARG20 · Futbol Argentina (MVP estilo Promiedos)

Web de una sola liga: **Liga Profesional Argentina 2026** (30 equipos). Stack: Python, FastAPI, PostgreSQL. Meta futura: comunidad integrada con los datos.

## Visión y principios
Filosofía: **datos confiables + herramientas útiles + experiencia rápida + comunidad**. "El lugar donde consultás todo lo que importa del fútbol argentino", no un portal de noticias.
- Rápida, minimalista, mobile-first, pocas distracciones.
- La IA es opcional y complementaria: el backend es la fuente de verdad y los cálculos son deterministas.
- La comunidad va pegada a los datos (comentarios por partido y por club), no como un foro aislado.
- No agregar estadísticas solo por tenerlas: cada métrica responde una pregunta útil.
- Banco de ideas completo: `ARG20_ideas_y_roadmap.md`. Este archivo guarda lo decidido y el orden de trabajo.

## Layout actual
1. Título · 2. "Liga Profesional" · 3. Selector: Clausura / Apertura / Anual / Promedios / Playoffs · 4. Tabla (por zona A/B en Clausura y Apertura; cuadro en Playoffs) · 5. Fixture (por fecha, con refresco cada 30 s si hay un partido en juego) · 6. Goleadores y asistidores

## Decisiones
- Monolito FastAPI modular (torneo, jugadores, foro, usuarios). Frontend: Jinja2 + HTMX.
- Fuente de datos principal: **BSD** (sports.bzzoiro.com). Highlightly/OpenFoot quedan opcionales.
- `sync/` es el único que escribe en la base; `app/` solo lee.
- Anual y Promedios se **calculan** desde los partidos (vistas SQL), no se guardan.
- Goleadores y asistidores suman `player-stats` por partido.
- Escudos: originales en `crests_raw/` → `scripts/optimizar_escudos.py` → `app/static/crests/<abreviatura>.webp`. Si falta uno, la web muestra el círculo con la abreviatura.
- Nombre/abreviatura propios: `scripts/equipos_abreviaturas.py` (BSD es inconsistente). Sin abreviatura la web usa las 3 primeras letras del nombre.
- **Sync en tres piezas** para cuidar la cuota de BSD: `sync_bsd.py` completo cada 4 h, `cambios.py` cada hora (1 llamada a `/fixtures/changes/`; solo si hay cambios refresca partidos), `live.py` cada 30 s pero solo si la base indica un partido en ventana (0 llamadas fuera de horario). Los jobs que escriben los mismos datos comparten `flock`.
- **Stats con reintentos acotados:** `partido.stats_ok` y `stats_intentos` (tope `MAX_INTENTOS_STATS` = 8); un `player-stats` vacío ya no se repite para siempre ni borra stats buenas.
- **Playoffs:** `app/modules/torneo/playoffs.py` arma el cuadro con una función pura. Proyectado con las posiciones actuales mientras no haya octavos cargados; real (con resultados y penales) cuando existen partidos `playoff`.
- **Mi club sin cuentas** (`localStorage`) como primer paso de personalización; las cuentas llegan con la comunidad.

## Estado
- [x] Maqueta visual, `schema.sql` v2, `probe_bsd.py`
- [x] `sync_bsd.py` funcionando (goles en contra confirmados a mano)
- [x] API FastAPI con los 6 bloques conectados + rediseño de la web
- [x] Escudos (30) y script de optimización
- [x] Sync automático: timers de sync completo y cambios, servicio live (`make timer-on`)
- [x] Marcador en vivo (`live.py` + refresco HTMX). **Sin probar en un partido real**: el nombre del campo id de `/events/live/` está asumido (`id` con fallback `event_id`); el primer tick con datos loguea las claves.
- [x] Pestaña Playoffs (cuadro proyectado y real, penales). Validada con el Apertura 2026 (8 octavos y los 15 partidos coinciden).
- [x] Apertura validado: las posiciones por zona reproducen los 8 cruces de octavos (incluye 4 empates de puntos resueltos por DG).
- [x] Descenso: marca roja en Anual y Promedios (último puesto) y aviso de empate. Falta la calculadora.
- [] Validar el resto de las tablas con `scripts/checks/cruce_tabla.py` (Clausura vs BSD; Anual vs CSV externo). Falta el desempate por goles a favor, que ningún caso real probó.
- [ ] Todo lo demás está en el Roadmap de abajo.

## Roadmap (priorizado)
Criterio: lo que hace volver a diario es **mi club + el partido de hoy + qué se juega mi equipo**. La comunidad retiene, pero un foro vacío espanta: va al final. Se prioriza lo barato y lo compartible antes que lo costoso.

### Fase A · Ahora (casi todo sale de datos que ya están en la base)
1. **URLs limpias, SEO y compartir.** Primero porque cambiar rutas con tráfico es caro. Pasar de `/modo/xxx` y `?modo=` a las rutas objetivo (ver abajo). Title y meta description por página, Open Graph con tarjeta de resultado, `sitemap.xml`, `robots.txt`.
2. **Modo oscuro.** El CSS ya usa variables de color; redefinirlas bajo `prefers-color-scheme` y `data-theme`.
3. **Mi club** con `localStorage`: posición, puntos, próximo partido y últimos 5.
4. **Página de club** (`/club/<slug>`): próximo partido, últimos resultados, forma (últimos 5), fixture completo, local/visitante, goleadores y asistidores del equipo. Se calcula desde `partido`, sin llamadas nuevas a BSD.
5. **Descenso:** marca de zona de descenso en Anual y Promedios (con aviso de empate en puntos, que se define por partido de desempate) y página `/descenso`. Después, la calculadora.
6. **Fuentes y última actualización** en el pie (ya existe `partido.actualizado_en`).
7. **Línea de clasificación** (8.º puesto) en las tablas de zona.

### Fase B · Después (lo que diferencia al producto)
- **Página de partido** con línea de tiempo de goles y tarjetas. Antes, verificar `/events/{id}/incidents/` con un partido terminado: la documentación de BSD lo lista, pero la sonda inicial dijo que no traía incidentes de gol.
- **Resumen de la fecha** (resultados, tabla, qué cambió, goleadores): muy compartible.
- **Evolución de posiciones** por fecha (se calcula desde `partido`).
- **Récords** y **H2H** (como relleno de las páginas de club).
- **Simulador** y **calculadora de clasificación**: determinista, repite la lógica de las vistas con resultados hipotéticos. Trabajo grande, dejar para después de descenso.
- **PWA básica** (instalable y con caché).

### Fase C · Más adelante
- Usuarios (registro, login, club favorito guardado).
- **Comentarios por partido** y encuestas, con reportes, moderación y anti-spam. Si hay comunidad por club, que sea la sección de comentarios del club.
- Notificaciones (push/email) sobre PWA y usuarios ya andando.

### Fuera por ahora
Foro general, reputación, historial de cambios de datos (alcanza con `actualizado_en`), comparador de jugadores, estadísticas avanzadas como xG (BSD mezcla xG medido y estimado), IA, buscador global (hasta tener historial), historial de temporadas completo (depende de cuánta historia da BSD).

### Dependencias y riesgos
- **Clasificación a Libertadores y Sudamericana:** la regla de cupos 2026 no está confirmada. Hacer primero descenso y dejar copas hasta verificar el reglamento.
- **Filtros de primer y segundo tiempo** en las tablas: el detalle del partido trae marcador al entretiempo, pero habría que bajarlo y guardarlo. Se saltea por ahora; local/visitante sale de `partido` sin costo.
- **Incidentes de gol:** ver Fase B, página de partido.

## URLs objetivo
Estructura a diseñar ya, aunque se implemente por etapas:
```
/                          portada (Clausura por defecto)
/torneo/clausura  /torneo/apertura  /torneo/anual  /torneo/promedios  /torneo/playoffs
/fecha/14                  fixture de una fecha (resumen de la fecha)
/partido/<slug>            ej. river-racing-2026-14
/club/<slug>               ej. river
/goleadores  /asistidores
/descenso  /simulador
/historial/<anio>
```
Hoy: `/`, `/modo/{modo}`, `/torneo/fixture`, `/torneo/playoffs`, `/jugadores`, `/sitemap.xml`, `/robots.txt`;. Los fragmentos HTMX pueden quedar bajo un prefijo (`/parcial/...`) para no mezclarlos con las páginas indexables.

## Estructura del repo
```
app/        core/ (config, db, templating) · modules/ (portada, torneo [queries, router, modos, playoffs], jugadores) · templates/ · static/ (css, crests)
sync/       sync_bsd.py · live.py · cambios.py
db/         schema.sql · migrations/ (001 vistas, 002 stats_intentos, 003 penales)
deploy/     futbol-sync.service/.timer · futbol-cambios.service/.timer · futbol-live.service
scripts/    probe_bsd.py · equipos_abreviaturas.py · optimizar_escudos.py · checks/
crests_raw/ originales de escudos
tests/ · docs/ · compose.yaml · Makefile · requirements.txt
```
`sync_bsd.py`, `live.py`, `cambios.py` y `equipos_abreviaturas.py` leen `BSD_TOKEN`/`DATABASE_URL` del entorno (no del `.env`; `make sync` los carga; los servicios systemd usan `EnvironmentFile`). `cruce_tabla.py` sí lee `.env`.

## Hallazgos de la sonda
- Liga Profesional = `league_id 85`. Auth: `Authorization: Token <BSD_TOKEN>`. Base: `/api/v2`.
- Temporadas: 2026 = id 1635 (**un solo id** para Apertura y Clausura); 2025 = Apertura 1637 + Clausura 1636; 2024 = 1638 (una sola etapa, 28 equipos, 27 fechas).
- **Apertura vs Clausura 2026:** `group_name` dice "Clausura, Group X" en todos los partidos. Se separan por fecha: `event_date < 2026-06-15` = Apertura. 240 partidos de zona por torneo (210 group-stage + 30 interzonales; 16 fechas de 15 partidos).
- `stage`: `group-stage` = zona, `league-phase` = interzonales (cuentan para la tabla), `round-of-16`/`quarterfinals`/`semifinals`/`final` = playoffs (15 partidos, del Apertura). Pasan los 8 primeros de cada zona. En playoffs `group_name` es inconsistente.
- **Cuadro de playoffs (partido único, local el mejor ubicado, final en sede neutral):** octavos 1A–8B, 4B–5A, 2B–7A, 3A–6B, 1B–8A, 4A–5B, 2A–7B, 3B–6A; llave binaria en ese orden (cada par consecutivo alimenta un cuarto, cada par de cuartos una semifinal). Verificado con los 15 partidos del Apertura.
- **Penales:** el detalle `/events/{id}/` trae `penalty_shootout: {home, away}`; `home_score`/`away_score` son solo tiempo reglamentario. `extra_time_score` vino `null` en un partido que se definió por penales: no se sabe si BSD informa el suplementario, por eso solo se guardan penales.
- Estados: `finished`, `notstarted`, `postponed` (vistos); `inprogress`, `suspended`, `abandoned` (de la documentación, mapeados pero sin ver en datos reales).
- `GET /events/live/`: partidos en vivo, caché de 10–30 s; `status=live|upcoming|finished|...` disponible como filtro en `/events/`.
- `GET /fixtures/changes/`: solo transiciones a estados alterados (postergado, cancelado...) y cambios de horario; el avance normal no aparece. Registra desde el día que se lanzó el endpoint. Formato tomado de la documentación, sin verificar con datos reales.
- Postergado con reemplazo: Sarmiento–River fecha 11 (id 223766) tiene otro id para la nueva fecha (604493). `replaced_by` viene en `null`: se detecta por equipos + fecha + instancia (`reprogramado = true`).
- **Goles/asistencias:** `/events/{id}/player-stats/` → `goals` y `goal_assist`. La suma por equipo coincide con el marcador salvo goles en contra (no se asignan a nadie). Sin minutos de gol.
- **Jugadores:** `/players/{id}/` → `name`, `short_name`, `position`, `current_team_id`.
- **Tablas históricas:** `/leagues/85/standings/?season_id=...`. Para 2026 solo trae el Clausura; las filas de equipo no están donde se asumía: `standings_rows` ahora las busca recorriendo toda la respuesta.
- Nombres de equipo inconsistentes entre endpoints ("Club Atlético Platense" vs "Platense"): usar `ext_id` y nuestras abreviaturas.

## Reglamento AFA 2026 (por prensa, sin texto oficial)
- Anual = puntos de las fases de zona de Apertura y Clausura (sin playoffs). Promedios = últimas tres temporadas (2024–2026). Dos descensos: último de la Anual y peor promedio.
- Empate en puntos en zona de descenso: partido de desempate (art. 26.2), no diferencia de gol. El orden por pts, dg, gf es solo de presentación.
- **Inicio de temporada:** la ventana de Promedios está escrita en tres lugares (`v_promedios`, `HIST` en `sync_bsd.py`, columnas del template). En 2027 hay que correrla a 2025–2027, cargar 2026 como histórico y crear el torneo nuevo.

## Pendientes / a verificar
- Texto oficial del reglamento: desempate exacto en tablas de zona (se usa pts, dg, gf), y si el doble último baja al anteúltimo de la Anual (reportes repetidos, sin fuente oficial).
- Equipos ascendidos en Promedios (sin historial de todos los años): qué regla aplica.
- Reglas de cupos a Libertadores y Sudamericana 2026.
- Campo id y forma real de `/events/live/` y de `/fixtures/changes/` (confirmar en el primer partido / primera corrida).
- `/events/{id}/incidents/`: ¿trae goles con minuto en este torneo y con este plan?
- Si BSD informa el tiempo suplementario y en qué campo.
- Penales en `player-stats` (¿cuentan como gol?).
- Límites reales y términos de uso de BSD (7.500 req/día viene de un README ajeno).
- Cómo filtra fechas `/events/` (`date_from`/`date_to` devolvieron partidos futuros).
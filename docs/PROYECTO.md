# ARG20 · Futbol Argentina (MVP estilo Promiedos)

Web de una sola liga: **Liga Profesional Argentina 2026** (30 equipos). Stack: Python, FastAPI, PostgreSQL, Jinja2 + HTMX. Meta futura: comunidad integrada con los datos.

## 1. Visión y principios
Filosofía: **datos confiables + herramientas útiles + experiencia rápida + comunidad**. "El lugar donde consultás todo lo que importa del fútbol argentino", no un portal de noticias.
- Rápida, minimalista, mobile-first, pocas distracciones.
- La IA es opcional y complementaria: el backend es la fuente de verdad y los cálculos son deterministas.
- La comunidad va pegada a los datos (comentarios por partido y por club), no como un foro aislado.
- No agregar estadísticas solo por tenerlas: cada métrica responde una pregunta útil.
- Banco de ideas completo: `ARG20_ideas_y_roadmap.md`. Este archivo guarda lo decidido y el orden de trabajo.

## 2. Estado

### Hecho
- [x] Maqueta visual, `schema.sql` v2, `probe_bsd.py`.
- [x] `sync_bsd.py` funcionando (goles en contra confirmados a mano).
- [x] Web FastAPI con los 6 bloques conectados y rediseño.
- [x] Escudos (30) y script de optimización.
- [x] Sync automático: timers de sync completo y cambios, servicio live (`make timer-on`).
- [x] Marcador en vivo (`live.py` + refresco HTMX). **Sin probar en un partido real**: el nombre del campo id de `/events/live/` está asumido (`id` con fallback `event_id`); el primer tick con datos loguea las claves.
- [x] Pestaña Playoffs (cuadro proyectado y real, penales). Validada con el Apertura 2026 (8 octavos y los 15 partidos coinciden).
- [x] Apertura validado: las posiciones por zona reproducen los 8 cruces de octavos (incluye 4 empates de puntos resueltos por DG).
- [x] Tabla Anual con zonas: Libertadores (campeones + 3 mejores que no sean campeones), Sudamericana (6 siguientes) y descenso (último). Promedios marca el último. Aviso de empate en la zona de descenso.
- [x] URLs limpias (`/torneo/<modo>`, 301 desde las viejas), title, description, canonical y Open Graph básico por página, `sitemap.xml` (incluye clubes) y `robots.txt`.
- [x] Modo oscuro (`theme.css`, `data-theme`, respeta `prefers-color-scheme`).
- [x] Fuentes y "última actualización" en el pie.
- [x] Línea de clasificación (8.º puesto) en las tablas de zona.
- [x] **Página de club** `/club/<slug>`: forma (últimos 5), posición en Clausura y Anual, local/visitante, próximo partido, últimos resultados, fixture completo y goleadores/asistidores del club. Slug corto por club (`equipo.slug`, migración 005); los escudos de tablas, fixture y playoffs linkean al club.
- [x] **Mi club** sin cuentas (`localStorage`): botón en la página del club y tarjeta en la portada (`/parcial/club/<slug>`).
- [x] **Página `/descenso`**: Anual y Promedios (fondo de cada tabla) con margen, partidos restantes y estado matemático (Salvado / Desciende, con desigualdades estrictas: un empate no define nada). Enlazada desde las leyendas de Anual y Promedios.El peor promedio sale del pool de la Anual: si también es último de la Anual, baja el siguiente (aviso de traspaso en la leyenda).

### Pendiente inmediato
- [ ] Validar el resto de las tablas con `scripts/checks/cruce_tabla.py` (Clausura vs BSD; Anual vs CSV externo). Falta el desempate por goles a favor, que ningún caso real probó.
- [ ] Calculadora de descenso (qué necesita cada equipo para salvarse), sobre `/descenso`.
- [ ] Open Graph con tarjeta de resultado (imagen).
- [ ] Todo lo demás está en el Roadmap.

## 3. Layout y URLs

### Portada
1. Título · 2. "Liga Profesional" · 3. Mi club (si hay uno elegido) · 4. Selector: Clausura / Apertura / Anual / Promedios / Descenso / Playoffs · 5. Tabla (por zona A/B en Clausura y Apertura; cuadro en Playoffs) · 6. Fixture (por fecha, con refresco cada 30 s si hay un partido en juego) · 7. Goleadores y asistidores.

### URLs actuales
```
/                          portada (Clausura)
/torneo/apertura  /torneo/anual  /torneo/promedios  /torneo/descenso  /torneo/playoffs
/club/<slug>               ej. /club/river
/descenso                  es "pestaña del selector (Anual y Promedios: margen, restantes, estado y puntos necesarios)
/sitemap.xml  /robots.txt  /salud
/parcial/...               fragmentos HTMX (no indexables): modo, fixture, playoffs, jugadores, club
```
Redirecciones 301: `/?modo=xxx` → `/torneo/xxx` y `/torneo/clausura` → `/`.

### URLs objetivo (se implementan por etapas)
```
/fecha/14                  fixture de una fecha (resumen de la fecha)
/partido/<slug>            ej. river-racing-2026-14
/goleadores  /asistidores
/simulador
/historial/<anio>
```

## 4. Decisiones

### Arquitectura y datos
- Monolito FastAPI modular (torneo, jugadores, club; después foro y usuarios). Molde de cada módulo: `queries.py` + `router.py`; la lógica de dominio va en funciones puras.
- Fuente de datos principal: **BSD** (sports.bzzoiro.com). Highlightly/OpenFoot quedan opcionales.
- `sync/` es el único que escribe en la base; `app/` solo lee.
- Anual y Promedios se **calculan** desde los partidos (vistas SQL), no se guardan.
- Goleadores y asistidores suman `player-stats` por partido.
- Nombre, abreviatura y slug propios por equipo: `scripts/equipos_abreviaturas.py` (BSD es inconsistente). Sin abreviatura la web usa las 3 primeras letras del nombre; sin slug el escudo no linkea.
- Escudos: originales en `crests_raw/` → `scripts/optimizar_escudos.py` → `app/static/crests/<abreviatura>.webp`. Si falta uno, la web muestra el círculo con la abreviatura.

### Sync
- **Tres piezas** para cuidar la cuota de BSD: `sync_bsd.py` completo cada 4 h, `cambios.py` cada hora (1 llamada a `/fixtures/changes/`; solo si hay cambios refresca partidos), `live.py` cada 30 s pero solo si la base indica un partido en ventana (0 llamadas fuera de horario). Los jobs que escriben los mismos datos comparten `flock`.
- **Stats con reintentos acotados:** `partido.stats_ok` y `stats_intentos` (tope `MAX_INTENTOS_STATS` = 8); un `player-stats` vacío ya no se repite para siempre ni borra stats buenas.
- Postergado con reemplazo: se detecta por equipos + fecha + instancia y el original queda `reprogramado = true` (el fixture lo oculta).

### Tablas y reglas
- **Playoffs:** `torneo/playoffs.py` arma el cuadro con una función pura. Proyectado con las posiciones actuales mientras no haya octavos cargados; real (con resultados y penales) cuando existen partidos `playoff`.
- **Descenso:** `torneo/descenso.py` (puro) marca el último de Anual y Promedios, avisa si hay empate en la zona y calcula el estado matemático (`cotas_pts`, `cotas_promedio`, `estados`) con fracciones exactas. Los partidos restantes salen de `partido` (`queries.partidos_restantes`), sin llamadas nuevas a BSD.
- **Copas:** `torneo/copas.py` (puro) asigna Libertadores y Sudamericana desde la Anual. El esquema de cupos **no está confirmado** (ver Pendientes).
- El orden de las tablas es pts, dg, gf: solo de presentación. Un empate en puntos en zona de descenso se define por partido de desempate.
- Promedios se resuelve primero; su descendido no ocupa lugar en la Anual (descenso.marcar(..., excluidos=...), traspaso, estados_anual).

### Front, SEO y personalización
- Jinja2 + HTMX. Los fragmentos viven bajo `/parcial/` para no mezclarse con las páginas indexables.
- Colores como variables CSS; el modo oscuro redefine variables (`theme.css`). Los estilos nuevos usan solo variables.
- **Mi club sin cuentas** (`localStorage`, clave `mi_club`, guarda el slug) como primer paso de personalización; las cuentas llegan con la comunidad. La tarjeta de la portada la arma el servidor y queda fuera de `#main`, así sobrevive al cambio de pestaña.

### Club
- `club/resumen.py` es puro: recibe los partidos del equipo y devuelve fixture, próximo, últimos 5, forma y registro local/visitante (solo fase de zona).
- Un playoff empatado y definido por penales cuenta como **E** en la forma (tiempo reglamentario); el marcador muestra los penales.
- Goleadores del club: salen de la vista anual, donde el equipo de cada jugador es el del último partido de la temporada.
- Slugs elegidos a mano en `SLUGS` (`equipos_abreviaturas.py`). Si se cambia uno ya publicado, hay que redirigir el viejo.

## 5. Roadmap (priorizado)
Criterio: lo que hace volver a diario es **mi club + el partido de hoy + qué se juega mi equipo**. La comunidad retiene, pero un foro vacío espanta: va al final. Se prioriza lo barato y lo compartible antes que lo costoso.

### Fase A · Ahora (sale de datos que ya están en la base)
1. Open Graph con tarjeta de resultado.
2. **Calculadora de descenso** sobre `/descenso` (la página, la marca en Anual y Promedios y el estado matemático ya están).
3. Validar tablas con `cruce_tabla.py`.

### Fase B · Después (lo que diferencia al producto)
- **Página de partido** con línea de tiempo de goles y tarjetas. Antes, verificar `/events/{id}/incidents/` con un partido terminado: la documentación de BSD lo lista, pero la sonda inicial dijo que no traía incidentes de gol.
- **Resumen de la fecha** (resultados, tabla, qué cambió, goleadores): muy compartible.
- **Evolución de posiciones** por fecha (se calcula desde `partido`).
- **Récords** y **H2H** (como relleno de las páginas de club).
- **Simulador** y **calculadora de clasificación**: determinista, repite la lógica de las vistas con resultados hipotéticos. Trabajo grande, dejar para después de descenso.
- **PWA básica** (instalable y con caché).

### Fase C · Más adelante
- Usuarios (registro, login, club favorito guardado; reemplaza al `localStorage`).
- **Comentarios por partido** y encuestas, con reportes, moderación y anti-spam. Si hay comunidad por club, que sea la sección de comentarios del club.
- Notificaciones (push/email) sobre PWA y usuarios ya andando.

### Fuera por ahora
Foro general, reputación, historial de cambios de datos (alcanza con `actualizado_en`), comparador de jugadores, estadísticas avanzadas como xG (BSD mezcla xG medido y estimado), IA, buscador global (hasta tener historial), historial de temporadas completo (depende de cuánta historia da BSD).

### Dependencias y riesgos
- **Copas:** la regla de cupos 2026 no está confirmada; la tabla Anual usa el esquema de `copas.py` y la leyenda lo aclara.
- **Filtros de primer y segundo tiempo** en las tablas: el detalle del partido trae marcador al entretiempo, pero habría que bajarlo y guardarlo. Se saltea por ahora; local/visitante sale de `partido` sin costo (ya está en la página de club).
- **Incidentes de gol:** ver Fase B, página de partido.

## 6. Reglamento AFA 2026 (por prensa, sin texto oficial)
- Anual = puntos de las fases de zona de Apertura y Clausura (sin playoffs). Promedios = últimas tres temporadas (2024–2026). Dos descensos: último de la Anual y peor promedio.
- Empate en puntos en zona de descenso: partido de desempate (art. 26.2), no diferencia de gol. El orden por pts, dg, gf es solo de presentación.
- **Inicio de temporada:** la ventana de Promedios está escrita en tres lugares (`v_promedios`, `HIST` en `sync_bsd.py`, columnas del template). En 2027 hay que correrla a 2025–2027, cargar 2026 como histórico, crear el torneo nuevo y actualizar `ANIO` en `torneo/modos.py`. Si sube un equipo nuevo, agregarlo a `LISTA` y `SLUGS` en `equipos_abreviaturas.py` (el `assert` de `SLUGS` avisa si falta) y sumar su escudo.

## 7. Hallazgos de la sonda (BSD)
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

## 8. Pendientes / a verificar
- Texto oficial del reglamento: desempate exacto en tablas de zona (se usa pts, dg, gf), y Adoptado como regla (el siguiente de la Anual); sin texto oficial todavía.
- Equipos ascendidos en Promedios (sin historial de todos los años): qué regla aplica.
- **Cupos a copas:** el esquema usado (campeones de Apertura y Clausura + 3 de la Anual, 6 a Sudamericana) no está confirmado con el reglamento. Constantes en `torneo/copas.py`. Tampoco hay criterio de desempate definido para empates fuera del descenso.
- Campo id y forma real de `/events/live/` y de `/fixtures/changes/` (confirmar en el primer partido / primera corrida).
- `/events/{id}/incidents/`: ¿trae goles con minuto en este torneo y con este plan?
- Si BSD informa el tiempo suplementario y en qué campo.
- Penales en `player-stats` (¿cuentan como gol?).
- Límites reales y términos de uso de BSD (7.500 req/día viene de un README ajeno).
- Cómo filtra fechas `/events/` (`date_from`/`date_to` devolvieron partidos futuros).
- `README.md`: la estructura que lista quedó vieja (falta `club/`, `sync/live.py`, `sync/cambios.py`, `deploy/`).
- htmx se carga desde unpkg sin SRI: fijar con hash antes de producción.

## 9. Estructura del repo
```
app/        main.py · core/ (config, db, templating)
            modules/  portada.py · parcial.py (fragmentos HTMX) · seo.py · contexto de la pestaña Descenso
                      torneo/ (queries, router, modos, playoffs, descenso, copas)
                      jugadores/ (queries, router)
                      club/ (queries, resumen [puro], router)
            templates/ (base, home, club, descenso, macros, partials/)
            static/    css/ (app, crests, club, theme) · js/mi_club.js · crests/
sync/       sync_bsd.py · live.py · cambios.py
db/         schema.sql · migrations/ (001 vistas jugadores, 002 stats_intentos, 003 penales,
            004 reparar stats_ok, 005 slug_equipo)
deploy/     futbol-sync.service/.timer · futbol-cambios.service/.timer · futbol-live.service
scripts/    probe_bsd.py · equipos_abreviaturas.py · optimizar_escudos.py · migrar_estructura.sh
            checks/ (cruce_tabla, check_eventos, check2, check3)
crests_raw/ originales de escudos (no se sube al repo)
tests/      test_app · test_club · test_copas · test_cruce · test_descenso · test_descenso_pagina · test_playoffs · test_sync_reglas
docs/       PROYECTO.md · maqueta/home.html
compose.yaml · Makefile · requirements.txt · .env.example
```
`sync_bsd.py`, `live.py`, `cambios.py` y `equipos_abreviaturas.py` leen `BSD_TOKEN`/`DATABASE_URL` del entorno (no del `.env`; `make sync` los carga; los servicios systemd usan `EnvironmentFile`). `cruce_tabla.py` sí lee `.env`.

## 10. Operación
```
make up                      # base local (podman compose)
make sync-hist && make sync  # históricos + partidos y stats
make run                     # http://127.0.0.1:8000
make test
make timer-on / timer-off    # timers y servicio live (systemd --user)
```
- **Migraciones:** `make migrate` corre todas las de `db/migrations/`; la 002 falla si la columna ya existe (inofensivo). Para una sola: `podman exec -i futbol-db psql -U futbol -d futbol < db/migrations/00X_nombre.sql`.
- **Equipos** (nombre corto, abreviatura y slug): `python scripts/equipos_abreviaturas.py` simula; con `--aplicar` escribe (necesita `DATABASE_URL` en el entorno).
- **Escudos:** `python scripts/optimizar_escudos.py` (`--simular`, `--forzar`, `--size`, `--calidad`).
- **Cruce de tablas:** `python scripts/checks/cruce_tabla.py [--torneo apertura|anual --externa archivo.csv]`.

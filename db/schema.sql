-- Futbol Argentina · esquema v2 (PostgreSQL 14+)
-- Ajustado con los hallazgos de la sonda de BSD (league_id 85).
-- ext_id = id del proveedor (BSD). Permite re-sincronizar sin duplicar.
--
-- CAMBIOS RESPECTO A v1
--  * Se elimina evento_partido: BSD no trae incidentes de gol. Goles y asistencias
--    salen de /events/{id}/player-stats/ (campos goals y goal_assist por jugador).
--  * Se agrega estadistica_jugador (una fila por jugador y partido).
--  * partido: columnas `instancia` (stage crudo), `interzonal` y `reprogramado`.
--  * torneo: Apertura y Clausura 2026 comparten el mismo season de BSD (1635), por
--    eso ext_id ya no es unico. Se separan por fecha (ver REGLAS DE SINCRONIZACION).
--  * Se quita tipo_evento.

CREATE TYPE tipo_torneo    AS ENUM ('apertura', 'clausura');
CREATE TYPE fase_partido   AS ENUM ('zona', 'playoff');
CREATE TYPE estado_partido AS ENUM ('programado', 'en_juego', 'finalizado', 'suspendido', 'postergado');

CREATE TABLE temporada (
  id    SERIAL PRIMARY KEY,
  anio  INT NOT NULL UNIQUE
);

CREATE TABLE torneo (
  id            SERIAL PRIMARY KEY,
  temporada_id  INT NOT NULL REFERENCES temporada(id),
  tipo          tipo_torneo NOT NULL,
  ext_season_id BIGINT,                 -- 1635 para ambos torneos de 2026 (no es unico)
  UNIQUE (temporada_id, tipo)
);

CREATE TABLE equipo (
  id            SERIAL PRIMARY KEY,
  ext_id        BIGINT UNIQUE,
  nombre        TEXT NOT NULL,          -- nombre propio nuestro (BSD es inconsistente: "Club Atletico Platense" vs "Platense")
  nombre_corto  TEXT,
  abreviatura   VARCHAR(4),
  zona_2026     CHAR(1) CHECK (zona_2026 IN ('A','B')),
  escudo_url    TEXT
);

CREATE TABLE jugador (
  id            SERIAL PRIMARY KEY,
  ext_id        BIGINT UNIQUE,
  nombre        TEXT NOT NULL,          -- GET /players/{id}/ -> name
  nombre_corto  TEXT,                   -- short_name, ej. "J. Candia"
  posicion      TEXT,                   -- position (F, M, D, G)
  equipo_id     INT REFERENCES equipo(id)   -- current_team_id (equipo actual)
);

CREATE TABLE partido (
  id               SERIAL PRIMARY KEY,
  ext_id           BIGINT UNIQUE,
  torneo_id        INT NOT NULL REFERENCES torneo(id),
  fase             fase_partido NOT NULL DEFAULT 'zona',
  instancia        TEXT,                -- stage crudo de BSD: group-stage, league-phase, round-of-16, ...
  interzonal       BOOLEAN NOT NULL DEFAULT false,   -- stage = 'league-phase'
  fecha_nro        INT,                 -- round_number (en playoffs puede ser NULL)
  fecha_hora       TIMESTAMPTZ,         -- event_date viene en UTC
  local_id         INT NOT NULL REFERENCES equipo(id),
  visitante_id     INT NOT NULL REFERENCES equipo(id),
  goles_local      INT,
  goles_visitante  INT,
  estado           estado_partido NOT NULL DEFAULT 'programado',
  reprogramado     BOOLEAN NOT NULL DEFAULT false,   -- true = original postergado que ya tiene un reemplazo con otro id
  stats_ok         BOOLEAN NOT NULL DEFAULT false,   -- player-stats bajadas con datos
  stats_intentos   INT NOT NULL DEFAULT 0,           -- intentos sin datos (tope en sync_bsd.py)
  pen_local        INT,                              -- definicion por penales (solo playoffs empatados)
  pen_visitante    INT,
  actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (local_id <> visitante_id)
);
CREATE INDEX ix_partido_torneo_fecha ON partido (torneo_id, fecha_nro);
CREATE INDEX ix_partido_hora ON partido (fecha_hora);

-- Una fila por jugador y partido (de player-stats). Sirve para goleadores y asistidores.
CREATE TABLE estadistica_jugador (
  partido_id   INT NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
  jugador_id   INT NOT NULL REFERENCES jugador(id),
  equipo_id    INT NOT NULL REFERENCES equipo(id),   -- team_id del partido (no el equipo actual)
  minutos      INT NOT NULL DEFAULT 0,
  goles        INT NOT NULL DEFAULT 0,
  asistencias  INT NOT NULL DEFAULT 0,
  amarillas    INT NOT NULL DEFAULT 0,
  rojas        INT NOT NULL DEFAULT 0,
  PRIMARY KEY (partido_id, jugador_id)
);
CREATE INDEX ix_estadistica_jugador ON estadistica_jugador (jugador_id);

-- Puntos de temporadas pasadas para Promedios (carga unica desde /standings/):
--   2024: season 1638 (regular-season, 27 fechas). Columnas played y pts.
--   2025: season 1637 (Apertura) + 1636 (Clausura), sumando played y pts de cada equipo.
-- Equipos ascendidos no tienen fila en los anios que no jugaron en primera.
CREATE TABLE puntos_historicos (
  equipo_id  INT NOT NULL REFERENCES equipo(id),
  anio       INT NOT NULL,
  pj         INT NOT NULL,
  pts        INT NOT NULL,
  PRIMARY KEY (equipo_id, anio)
);

-- ---------------------------------------------------------------------------
-- VISTAS. Reglamento LPF 2026: Anual y Promedios cuentan solo partidos de fase 'zona'
-- (incluye interzonales); los playoffs no suman. Promedios = ultimas 3 temporadas (2024-2026).
-- Ojo: el orden por dg/gf es de presentacion; un empate en puntos en zona de descenso
-- se define con partido de desempate (art. 26.2 del reglamento), no por diferencia de gol.
-- ---------------------------------------------------------------------------

CREATE VIEW v_resultado_equipo AS
SELECT p.torneo_id, t.temporada_id, p.local_id AS equipo_id,
       p.goles_local AS gf, p.goles_visitante AS gc,
       CASE WHEN p.goles_local > p.goles_visitante THEN 3
            WHEN p.goles_local = p.goles_visitante THEN 1 ELSE 0 END AS pts
FROM partido p JOIN torneo t ON t.id = p.torneo_id
WHERE p.estado = 'finalizado' AND p.fase = 'zona'
UNION ALL
SELECT p.torneo_id, t.temporada_id, p.visitante_id,
       p.goles_visitante, p.goles_local,
       CASE WHEN p.goles_visitante > p.goles_local THEN 3
            WHEN p.goles_visitante = p.goles_local THEN 1 ELSE 0 END
FROM partido p JOIN torneo t ON t.id = p.torneo_id
WHERE p.estado = 'finalizado' AND p.fase = 'zona';

-- Tabla de un torneo (Apertura o Clausura). Filtrar por torneo_id y, si se quiere
-- por zona, por zona_2026. Orden sugerido en la consulta: pts DESC, dg DESC, gf DESC
-- (verificar los desempates del reglamento).
CREATE VIEW v_tabla_torneo AS
SELECT r.torneo_id, e.id AS equipo_id, e.nombre, e.zona_2026,
       COUNT(*) AS pj,
       COUNT(*) FILTER (WHERE r.pts = 3) AS pg,
       COUNT(*) FILTER (WHERE r.pts = 1) AS pe,
       COUNT(*) FILTER (WHERE r.pts = 0) AS pp,
       SUM(r.gf) AS gf, SUM(r.gc) AS gc, SUM(r.gf - r.gc) AS dg,
       SUM(r.pts) AS pts
FROM v_resultado_equipo r JOIN equipo e ON e.id = r.equipo_id
GROUP BY r.torneo_id, e.id, e.nombre, e.zona_2026;

-- Tabla anual: Apertura + Clausura de la misma temporada.
CREATE VIEW v_tabla_anual AS
SELECT r.temporada_id, e.id AS equipo_id, e.nombre,
       COUNT(*) AS pj,
       COUNT(*) FILTER (WHERE r.pts = 3) AS pg,
       COUNT(*) FILTER (WHERE r.pts = 1) AS pe,
       COUNT(*) FILTER (WHERE r.pts = 0) AS pp,
       SUM(r.gf) AS gf, SUM(r.gc) AS gc, SUM(r.gf - r.gc) AS dg,
       SUM(r.pts) AS pts
FROM v_resultado_equipo r JOIN equipo e ON e.id = r.equipo_id
GROUP BY r.temporada_id, e.id, e.nombre;

-- Promedios: (pts 2024 + 2025 + 2026) / (pj de esos anios). Ajustar la ventana segun el reglamento.
CREATE VIEW v_promedios AS
WITH actual AS (
  SELECT a.equipo_id, te.anio, a.pj, a.pts
  FROM v_tabla_anual a JOIN temporada te ON te.id = a.temporada_id
), todo AS (
  SELECT equipo_id, anio, pj, pts FROM puntos_historicos
  UNION ALL
  SELECT equipo_id, anio, pj, pts FROM actual
)
SELECT e.id AS equipo_id, e.nombre,
       COALESCE(SUM(pts) FILTER (WHERE anio = 2024), 0) AS pts_2024,
       COALESCE(SUM(pts) FILTER (WHERE anio = 2025), 0) AS pts_2025,
       COALESCE(SUM(pts) FILTER (WHERE anio = 2026), 0) AS pts_2026,
       COALESCE(SUM(pj), 0) AS pj,
       CASE WHEN SUM(pj) > 0 THEN ROUND(SUM(pts)::numeric / SUM(pj), 3) ELSE 0 END AS promedio
FROM equipo e LEFT JOIN todo t ON t.equipo_id = e.id AND t.anio BETWEEN 2024 AND 2026
GROUP BY e.id, e.nombre;

-- Goleadores y asistidores por torneo (y por temporada para la pestania Anual).
-- Cuenta todas las fases (incluye playoffs). El equipo mostrado es el del ULTIMO partido
-- del jugador en ese torneo/temporada (no el equipo actual: jugadores que se fueron a
-- otra liga tienen current_team_id fuera de nuestra tabla y saldrian sin equipo).
-- Goleadores: ORDER BY goles DESC, asistencias DESC. Asistidores: ORDER BY asistencias DESC, goles DESC.
-- Los goles en contra no se le asignan a nadie (BSD no los atribuye): correcto para goleadores.
CREATE VIEW v_stats_jugador_torneo AS
WITH base AS (
  SELECT p.torneo_id, s.jugador_id, s.equipo_id, p.fecha_hora, s.minutos, s.goles, s.asistencias
  FROM estadistica_jugador s
  JOIN partido p ON p.id = s.partido_id AND p.estado = 'finalizado'
), ult AS (
  SELECT DISTINCT ON (torneo_id, jugador_id) torneo_id, jugador_id, equipo_id
  FROM base
  ORDER BY torneo_id, jugador_id, fecha_hora DESC
)
SELECT b.torneo_id, j.id AS jugador_id, j.nombre, u.equipo_id,
       COUNT(*) FILTER (WHERE b.minutos > 0) AS pj,
       SUM(b.goles) AS goles,
       SUM(b.asistencias) AS asistencias,
       SUM(b.minutos) AS minutos
FROM base b
JOIN jugador j ON j.id = b.jugador_id
JOIN ult u ON u.torneo_id = b.torneo_id AND u.jugador_id = b.jugador_id
GROUP BY b.torneo_id, j.id, j.nombre, u.equipo_id;

CREATE VIEW v_stats_jugador_anual AS
WITH base AS (
  SELECT t.temporada_id, s.jugador_id, s.equipo_id, p.fecha_hora, s.minutos, s.goles, s.asistencias
  FROM estadistica_jugador s
  JOIN partido p ON p.id = s.partido_id AND p.estado = 'finalizado'
  JOIN torneo t ON t.id = p.torneo_id
), ult AS (
  SELECT DISTINCT ON (temporada_id, jugador_id) temporada_id, jugador_id, equipo_id
  FROM base
  ORDER BY temporada_id, jugador_id, fecha_hora DESC
)
SELECT b.temporada_id, j.id AS jugador_id, j.nombre, u.equipo_id,
       COUNT(*) FILTER (WHERE b.minutos > 0) AS pj,
       SUM(b.goles) AS goles,
       SUM(b.asistencias) AS asistencias,
       SUM(b.minutos) AS minutos
FROM base b
JOIN jugador j ON j.id = b.jugador_id
JOIN ult u ON u.temporada_id = b.temporada_id AND u.jugador_id = b.jugador_id
GROUP BY b.temporada_id, j.id, j.nombre, u.equipo_id;

-- ---------------------------------------------------------------------------
-- REGLAS DE SINCRONIZACION (BSD -> base), verificadas con la sonda
-- ---------------------------------------------------------------------------
-- Partidos: GET /events/?league_id=85&season_id=1635 (496 partidos de 2026).
--  * torneo: event_date < '2026-06-15' => apertura, si no => clausura.
--    (group_name dice "Clausura, Group X" en TODOS los partidos: no sirve para esto.)
--  * fase: stage IN ('group-stage','league-phase') => 'zona'; el resto
--    (round-of-16, quarterfinals, semifinals, final) => 'playoff'.
--  * interzonal: stage = 'league-phase' (60 partidos, 30 por torneo).
--  * zona_2026 del equipo: sale de group_name ("Clausura, Group A" => 'A') en partidos
--    group-stage. En playoffs group_name es inconsistente: no usarlo.
--  * estado: finished => finalizado, notstarted => programado, postponed => postergado.
--    Otros valores (en juego, suspendido): loguearlos si aparecen y mapearlos a mano.
--  * reprogramado: si hay un partido 'postponed' y otro con mismo season, stage,
--    round_number, local y visitante pero distinto id, el postergado queda
--    reprogramado = true (replaced_by viene en null, no se puede usar).
--    Ejemplo: 223766 (Sarmiento-River, 04/10, postponed) y 604493 (07/10, notstarted).
--    El fixture debe filtrar reprogramado = false.
--  * Control esperado: 240 partidos de zona por torneo (210 group-stage + 30 interzonales).
-- Goles y asistencias: GET /events/{id}/player-stats/ -> player_stats[]:
--    player_id, team_id, minutes_played, goals, goal_assist, yellow_card, red_card.
--    Control: la suma de goals por equipo debe igualar el marcador; si no, loguear
--    (posibles goles en contra) en vez de corregir en silencio.
-- Jugadores: GET /players/{id}/ -> id, name, short_name, position, current_team_id.
--    Pedir solo los player_id que todavia no estan en la tabla jugador.
-- Historicos: GET /leagues/85/standings/?season_id=1638 / 1637 / 1636 ->
--    standings[]: team_id, played, pts. Cargar en puntos_historicos.
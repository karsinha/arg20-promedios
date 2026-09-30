-- Futbol Argentina · esquema inicial (PostgreSQL 14+)
-- ext_id = id del proveedor de datos (BSD). Permite re-sincronizar sin duplicar.

CREATE TYPE tipo_torneo   AS ENUM ('apertura', 'clausura');
CREATE TYPE fase_partido  AS ENUM ('zona', 'playoff');
CREATE TYPE estado_partido AS ENUM ('programado', 'en_juego', 'finalizado', 'suspendido', 'postergado');
CREATE TYPE tipo_evento   AS ENUM ('gol', 'penal', 'gol_en_contra', 'amarilla', 'roja');

CREATE TABLE temporada (
  id    SERIAL PRIMARY KEY,
  anio  INT NOT NULL UNIQUE
);

CREATE TABLE torneo (
  id            SERIAL PRIMARY KEY,
  temporada_id  INT NOT NULL REFERENCES temporada(id),
  tipo          tipo_torneo NOT NULL,
  ext_id        BIGINT,
  UNIQUE (temporada_id, tipo)
);

CREATE TABLE equipo (
  id           SERIAL PRIMARY KEY,
  ext_id       BIGINT UNIQUE,
  nombre       TEXT NOT NULL,
  abreviatura  VARCHAR(4),
  zona_2026    CHAR(1) CHECK (zona_2026 IN ('A','B')),
  escudo_url   TEXT
);

CREATE TABLE jugador (
  id         SERIAL PRIMARY KEY,
  ext_id     BIGINT UNIQUE,
  nombre     TEXT NOT NULL,
  equipo_id  INT REFERENCES equipo(id)   -- equipo actual (puede cambiar)
);

CREATE TABLE partido (
  id                  SERIAL PRIMARY KEY,
  ext_id              BIGINT UNIQUE,
  torneo_id           INT NOT NULL REFERENCES torneo(id),
  fase                fase_partido NOT NULL DEFAULT 'zona',
  fecha_nro           INT,
  fecha_hora          TIMESTAMPTZ,
  local_id            INT NOT NULL REFERENCES equipo(id),
  visitante_id        INT NOT NULL REFERENCES equipo(id),
  goles_local         INT,
  goles_visitante     INT,
  estado              estado_partido NOT NULL DEFAULT 'programado',
  actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (local_id <> visitante_id)
);
CREATE INDEX ix_partido_torneo_fecha ON partido (torneo_id, fecha_nro);
CREATE INDEX ix_partido_hora ON partido (fecha_hora);

CREATE TABLE evento_partido (
  id           SERIAL PRIMARY KEY,
  ext_id       BIGINT UNIQUE,
  partido_id   INT NOT NULL REFERENCES partido(id) ON DELETE CASCADE,
  equipo_id    INT NOT NULL REFERENCES equipo(id),
  jugador_id   INT REFERENCES jugador(id),
  asistente_id INT REFERENCES jugador(id),
  tipo         tipo_evento NOT NULL,
  minuto       INT
);
CREATE INDEX ix_evento_jugador ON evento_partido (jugador_id) WHERE tipo IN ('gol','penal');
CREATE INDEX ix_evento_asistente ON evento_partido (asistente_id) WHERE asistente_id IS NOT NULL;

-- Puntos de temporadas pasadas para Promedios (se cargan una sola vez).
CREATE TABLE puntos_historicos (
  equipo_id  INT NOT NULL REFERENCES equipo(id),
  anio       INT NOT NULL,
  pj         INT NOT NULL,
  pts        INT NOT NULL,
  PRIMARY KEY (equipo_id, anio)
);

-- ---------------------------------------------------------------------------
-- VISTAS. SUPUESTO A VERIFICAR con el reglamento de la AFA: solo cuentan los
-- partidos de fase 'zona' para Anual y Promedios (los playoffs no suman).
-- Si el reglamento dice otra cosa, se cambia en v_resultado_equipo.
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

-- Tabla de un torneo (Apertura o Clausura). Filtrar por torneo_id (y zona_2026 si se quiere por zona).
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

-- Promedios: (pts 2024 + 2025 + año en curso) / (pj de esos años). Ajustar la ventana de años según el reglamento.
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

-- Goleadores y asistidores (se filtra por torneo con JOIN a partido si hace falta).
CREATE VIEW v_goleadores AS
SELECT j.id AS jugador_id, j.nombre, ev.equipo_id, COUNT(*) AS goles
FROM evento_partido ev JOIN jugador j ON j.id = ev.jugador_id
WHERE ev.tipo IN ('gol','penal')
GROUP BY j.id, j.nombre, ev.equipo_id;

CREATE VIEW v_asistidores AS
SELECT j.id AS jugador_id, j.nombre, ev.equipo_id, COUNT(*) AS asistencias
FROM evento_partido ev JOIN jugador j ON j.id = ev.asistente_id
WHERE ev.tipo IN ('gol','penal')
GROUP BY j.id, j.nombre, ev.equipo_id;
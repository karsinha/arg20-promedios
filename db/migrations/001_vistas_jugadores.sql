-- Goleadores/asistidores: usar el equipo DONDE JUGO (no el equipo actual) y agregar la vista anual.
-- Se corre una sola vez sobre la base existente:
--   podman exec -i futbol-db psql -U futbol -d futbol < migracion_vistas_jugadores.sql

CREATE OR REPLACE VIEW v_stats_jugador_torneo AS
WITH base AS (
  SELECT p.torneo_id, s.jugador_id, s.equipo_id, p.fecha_hora, s.minutos, s.goles, s.asistencias
  FROM estadistica_jugador s
  JOIN partido p ON p.id = s.partido_id AND p.estado = 'finalizado'
), ult AS (   -- equipo del ultimo partido del jugador en ese torneo
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

CREATE OR REPLACE VIEW v_stats_jugador_anual AS
WITH base AS (
  SELECT t.temporada_id, s.jugador_id, s.equipo_id, p.fecha_hora, s.minutos, s.goles, s.asistencias
  FROM estadistica_jugador s
  JOIN partido p ON p.id = s.partido_id AND p.estado = 'finalizado'
  JOIN torneo t ON t.id = p.torneo_id
), ult AS (   -- equipo del ultimo partido del jugador en la temporada
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
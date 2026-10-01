-- Repara stats_ok tras el bug de marcas invertidas en sync_stats:
--  * partidos con stats cargadas -> completos (no se vuelven a bajar)
--  * partidos finalizados sin stats -> pendientes, con los intentos en cero
-- Idempotente. Correr una vez:  make migrate
UPDATE partido p SET stats_ok = true
WHERE p.estado = 'finalizado'
  AND EXISTS (SELECT 1 FROM estadistica_jugador s WHERE s.partido_id = p.id);

UPDATE partido p SET stats_ok = false, stats_intentos = 0
WHERE p.estado = 'finalizado'
  AND NOT EXISTS (SELECT 1 FROM estadistica_jugador s WHERE s.partido_id = p.id);
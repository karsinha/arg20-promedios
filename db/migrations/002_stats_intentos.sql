ALTER TABLE partido
  ADD COLUMN stats_ok        BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN stats_intentos  INT     NOT NULL DEFAULT 0;

-- Los partidos que ya tienen stats cargadas quedan como completos.
UPDATE partido p SET stats_ok = true
WHERE EXISTS (SELECT 1 FROM estadistica_jugador s WHERE s.partido_id = p.id);
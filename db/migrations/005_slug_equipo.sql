-- URL corta de cada club (/club/<slug>). Idempotente.
-- Se llena con: python scripts/equipos_abreviaturas.py --aplicar
ALTER TABLE equipo ADD COLUMN IF NOT EXISTS slug TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS equipo_slug_key ON equipo (slug);

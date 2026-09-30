#!/usr/bin/env bash
# Mueve los archivos que ya tenias a la nueva estructura. Correr UNA vez, desde cualquier carpeta.
set -euo pipefail
cd "$(dirname "$0")/.."
mover() {
  if [ -f "$1" ]; then
    mkdir -p "$(dirname "$2")"
    git mv "$1" "$2" 2>/dev/null || mv "$1" "$2"
    echo "  $1 -> $2"
  else
    echo "  (no esta, se omite) $1"
  fi
}
mover schema.sql                      db/schema.sql
mover migracion_vistas_jugadores.sql  db/migrations/001_vistas_jugadores.sql
mover sync_bsd.py                     sync/sync_bsd.py
mover probe_bsd.py                    scripts/probe_bsd.py
mover check_eventos.py                scripts/checks/check_eventos.py
mover check2.py                       scripts/checks/check2.py
mover check3.py                       scripts/checks/check3.py
mover PROYECTO.md                     docs/PROYECTO.md
mover home.html                       docs/maqueta/home.html
echo "Listo. Los scripts se corren desde la raiz: python scripts/probe_bsd.py"

"""
Carga nombre_corto y abreviatura de los equipos (BSD es inconsistente con los nombres).
Empareja por similitud de nombre, SIN tocar la base: revisa la salida y recien ahi corre --aplicar.
Lo que quede sin emparejar se arregla a mano en LISTA (tercer campo = texto de busqueda).

  python scripts/equipos_abreviaturas.py             # simulacion
  python scripts/equipos_abreviaturas.py --aplicar   # escribe en la base (usa DATABASE_URL)
"""
import argparse, difflib, os, sys, unicodedata

import psycopg

# (nombre para mostrar, abreviatura, texto de busqueda opcional)
LISTA = [
    ("Aldosivi", "ALD", ""), ("Argentinos Juniors", "ARG", ""), ("Atlético Tucumán", "ATU", ""),
    ("Banfield", "BAN", ""), ("Barracas Central", "BAR", ""), ("Belgrano", "BEL", ""),
    ("Boca Juniors", "BOC", ""), ("Central Córdoba (SdE)", "CCO", "central cordoba santiago del estero"),
    ("Defensa y Justicia", "DYJ", ""), ("Deportivo Riestra", "RIE", ""),
    ("Estudiantes (LP)", "EST", "estudiantes la plata"), ("Estudiantes (RC)", "ERC", "estudiantes rio cuarto"),
    ("Gimnasia (LP)", "GLP", "gimnasia la plata"), ("Gimnasia (M)", "GME", "gimnasia mendoza"),
    ("Huracán", "HUR", ""), ("Independiente", "IND", ""), ("Independiente Rivadavia", "IRI", ""),
    ("Instituto", "INS", ""), ("Lanús", "LAN", ""), ("Newell's Old Boys", "NOB", ""),
    ("Platense", "PLA", ""), ("Racing Club", "RAC", ""), ("River Plate", "RIV", ""),
    ("Rosario Central", "ROS", ""), ("San Lorenzo", "SLO", ""), ("Sarmiento", "SAR", ""),
    ("Talleres", "TAL", ""), ("Tigre", "TIG", ""), ("Unión", "UNI", "union santa fe"),
    ("Vélez Sarsfield", "VEL", ""),
]


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    dsn = os.environ.get("DATABASE_URL") or sys.exit("Falta DATABASE_URL.")
    with psycopg.connect(dsn) as conn:
        equipos = conn.execute("SELECT id, nombre FROM equipo").fetchall()
        pares = sorted(
            ((difflib.SequenceMatcher(None, norm(e[1]), norm(busq or nom)).ratio(), e, (nom, ab))
             for e in equipos for nom, ab, busq in LISTA), key=lambda x: -x[0])
        usados_e, usados_l, res = set(), set(), []
        for r, e, l in pares:
            if r < 0.6 or e[0] in usados_e or l[0] in usados_l:
                continue
            usados_e.add(e[0]); usados_l.add(l[0]); res.append((r, e, l))
        for r, e, l in sorted(res, key=lambda x: x[2][0]):
            print(f"{r:.2f}  {e[1]:<38} -> {l[0]} ({l[1]})")
        print("\nSin emparejar (base):", [e[1] for e in equipos if e[0] not in usados_e])
        print("Sin emparejar (lista):", [n for n, _, _ in LISTA if n not in usados_l])
        if a.aplicar:
            for _, e, (nom, ab) in res:
                conn.execute("UPDATE equipo SET nombre_corto = %s, abreviatura = %s WHERE id = %s", (nom, ab, e[0]))
            print(f"\n{len(res)} equipos actualizados.")
        else:
            print("\nSimulacion: no se escribio nada. Usa --aplicar para guardar.")


if __name__ == "__main__":
    main()

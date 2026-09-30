"""
Cruza nuestra tabla (vistas SQL) contra una fuente externa, equipo por equipo.

  * clausura  -> contra /standings/ de BSD (para 2026 BSD trae solo el Clausura).
  * apertura / anual -> contra un CSV que armes vos (Promiedos, AFA...): abrev,pj,pts[,pg,pe,pp,gf,gc,dg]

Compara PJ, puntos y, si la fuente los trae, PG/PE/PP/GF/GC/DG. Si la fuente trae posicion,
tambien compara el orden dentro de cada zona (sirve para validar los desempates).

Uso (desde la raiz; lee BSD_TOKEN y DATABASE_URL del .env si existe):
  python scripts/checks/cruce_tabla.py
  python scripts/checks/cruce_tabla.py --torneo apertura --externa apertura.csv
  python scripts/checks/cruce_tabla.py --torneo anual --externa anual.csv
Sale con codigo 1 si encuentra diferencias.
"""
import argparse, csv, os, sys
from pathlib import Path

CAMPOS = ["pj", "pg", "pe", "pp", "gf", "gc", "dg", "pts"]
# nombres posibles de cada campo en /standings/ (se prueban en orden; no sabemos cuales usa BSD)
NOMBRES_BSD = {
    "pj": ("played", "matches_played", "mp"), "pg": ("won", "wins", "w"),
    "pe": ("drawn", "draws", "d"), "pp": ("lost", "losses", "l"),
    "gf": ("goals_for", "gf", "scored", "goals_scored"), "gc": ("goals_against", "ga", "gc", "conceded"),
    "dg": ("goal_difference", "goal_diff", "gd"), "pts": ("pts", "points"),
}
NOMBRES_POS = ("position", "rank", "pos")


def cargar_env(ruta=".env"):
    p = Path(ruta)
    if not p.exists():
        return
    for linea in p.read_text().splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def primero(fila, nombres):
    for n in nombres:
        if fila.get(n) is not None:
            return fila[n]
    return None


# ------------------------------------------------------------ fuentes externas
def standings_rows(st):
    if not st:
        return []
    if st.get("standings"):
        return st["standings"]
    out = []
    for v in (st.get("zones") or st.get("groups") or {}).values():
        if isinstance(v, list):
            out += v
    return out


def id_equipo(f):
    """team_id puede venir en la fila, o dentro de f["team"] (dict o numero)."""
    if not isinstance(f, dict):
        return None
    if f.get("team_id") is not None:
        return f["team_id"]
    t = f.get("team")
    if isinstance(t, dict):
        for k in ("id", "team_id", "ext_id"):
            if t.get(k) is not None:
                return t[k]
    return t if isinstance(t, int) else None


def aplanar_filas(filas):
    """Si BSD agrupa por zona ([{group_name, teams: [...]}]) baja hasta las filas de equipos."""
    out = []
    for f in filas:
        if isinstance(f, dict) and id_equipo(f) is None:
            sub = [v for v in f.values() if isinstance(v, list) and v and isinstance(v[0], dict)]
            if sub:
                out += aplanar_filas(sub[0])
                continue
        out.append(f)
    return out


def plano(f):
    """La fila mas los campos de sus dicts anidados (ej. f["stats"]["played"]), sin pisar los propios."""
    p = dict(f)
    for v in f.values():
        if isinstance(v, dict):
            for k, x in v.items():
                p.setdefault(k, x)
    return p


def buscar_filas(obj, ruta="", prof=0):
    """Recorre TODA la respuesta y junta las filas de equipo (tienen id de equipo y puntos),
    sin importar como las agrupe BSD. Devuelve [(ruta, fila)]."""
    if prof > 6:
        return []
    if isinstance(obj, dict):
        if id_equipo(obj) is not None and primero(plano(obj), NOMBRES_BSD["pts"]) is not None:
            return [(ruta, obj)]
        return [x for k, v in obj.items() for x in buscar_filas(v, f"{ruta}.{k}" if ruta else str(k), prof + 1)]
    if isinstance(obj, list):
        return [x for v in obj for x in buscar_filas(v, ruta + "[]", prof + 1)]
    return []


def forma(x, prof=0):
    """Resumen corto de la estructura de un JSON (para diagnosticar)."""
    if isinstance(x, dict):
        return {k: forma(v, prof + 1) if prof < 3 else "..." for k, v in x.items()}
    if isinstance(x, list):
        return [f"{len(x)} items", forma(x[0], prof + 1)] if x and prof < 3 else f"{len(x)} items"
    return x


def externa_bsd(league_id, season_id):
    import json, requests
    from collections import Counter
    r = requests.get(f"https://sports.bzzoiro.com/api/v2/leagues/{league_id}/standings/",
                     params={"season_id": season_id}, timeout=30,
                     headers={"Authorization": f"Token {os.environ['BSD_TOKEN']}"})
    if r.status_code != 200:
        sys.exit(f"BSD respondio HTTP {r.status_code}: {r.text[:200]}")
    crudo = r.json()
    halladas = buscar_filas(crudo)
    if not halladas:
        print("No encontre filas de equipos (id + puntos) en la respuesta de BSD. Estructura:")
        print(json.dumps(forma(crudo), ensure_ascii=False, indent=1, default=str)[:3000])
        sys.exit("Pegame esa estructura y ajusto el script.")
    print("Filas de equipos por ubicacion:", dict(Counter(ruta for ruta, _ in halladas)))
    ext, pos = {}, {}
    for _, f in halladas:
        pl, eid = plano(f), id_equipo(f)
        if eid in ext:
            print(f"  ! equipo {eid} aparece mas de una vez en la respuesta; uso la primera")
            continue
        ext[eid] = {c: primero(pl, n) for c, n in NOMBRES_BSD.items()}
        pos[eid] = primero(pl, NOMBRES_POS)
    print(f"Campos de BSD (primera fila): {sorted(plano(halladas[0][1]).keys())}")
    return ext, pos


def externa_csv(ruta):
    ext = {}
    with open(ruta, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            r = {k.strip().lower(): (v.strip() if v else v) for k, v in r.items()}
            ext[r["abrev"].upper()] = {c: (int(r[c]) if r.get(c) not in (None, "") else None) for c in CAMPOS}
    return ext, {}


# ------------------------------------------------------------ nuestra base
def tabla_db(torneo, por):
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        t = conn.execute(
            """SELECT t.id, t.temporada_id FROM torneo t JOIN temporada te ON te.id = t.temporada_id
               WHERE te.anio = 2026 ORDER BY (t.tipo::text = %s) DESC LIMIT 1""",
            ("clausura" if torneo == "anual" else torneo,)).fetchone()
        if not t:
            sys.exit("No hay torneos 2026 en la base. Corre: make sync")
        vista, clave, valor = (("v_tabla_anual", "temporada_id", t[1]) if torneo == "anual"
                               else ("v_tabla_torneo", "torneo_id", t[0]))
        zona = "NULL" if torneo == "anual" else "e.zona_2026"
        cur = conn.execute(
            f"""SELECT e.ext_id, COALESCE(e.abreviatura, UPPER(LEFT(e.nombre, 3))) AS abrev, e.nombre,
                       {zona} AS zona, v.pj, v.pg, v.pe, v.pp, v.gf, v.gc, v.dg, v.pts
                FROM {vista} v JOIN equipo e ON e.id = v.equipo_id WHERE v.{clave} = %s""", (valor,))
        cols = [d.name for d in cur.description]
        filas = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {f[por]: f for f in filas}


# ------------------------------------------------------------ comparacion (logica pura)
def comparar(db, ext):
    """-> (diferencias [(clave, campo, nuestro, externo)], solo_db, solo_ext, campos_comparados)"""
    difs, campos = [], set()
    for k in db.keys() & ext.keys():
        for c in CAMPOS:
            if ext[k].get(c) is None:
                continue
            campos.add(c)
            if int(db[k][c]) != int(ext[k][c]):
                difs.append((k, c, int(db[k][c]), int(ext[k][c])))
    return difs, set(db) - set(ext), set(ext) - set(db), campos


def comparar_orden(db, pos_ext):
    """Nuestro orden dentro de cada zona (pts, dg, gf) contra la posicion externa.
    Devuelve (lista de [(clave, nuestra, externa)], motivo_si_se_omite)."""
    pos = {k: int(v) for k, v in pos_ext.items() if v is not None and k in db}
    if not pos:
        return [], "la fuente no trae posicion"
    zonas = {}
    for k, f in db.items():
        zonas.setdefault(f["zona"], []).append(k)
    if max(pos.values()) > max(len(v) for v in zonas.values()):
        return [], "la posicion de la fuente es global, no por zona"
    difs = []
    for ks in zonas.values():
        ks.sort(key=lambda k: (-db[k]["pts"], -db[k]["dg"], -db[k]["gf"], db[k]["nombre"]))
        for i, k in enumerate(ks, 1):
            if k in pos and pos[k] != i:
                difs.append((k, i, pos[k]))
    return difs, None


# ------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--torneo", choices=("clausura", "apertura", "anual"), default="clausura")
    ap.add_argument("--externa", help="CSV de referencia (obligatorio para apertura y anual)")
    a = ap.parse_args()
    cargar_env()
    if not os.environ.get("DATABASE_URL"):
        sys.exit("Falta DATABASE_URL (en el entorno o en .env).")
    if a.externa:
        ext, pos = externa_csv(a.externa); por = "abrev"
    elif a.torneo == "clausura":
        if not os.environ.get("BSD_TOKEN"):
            sys.exit("Falta BSD_TOKEN (en el entorno o en .env).")
        ext, pos = externa_bsd(85, 1635); por = "ext_id"
    else:
        sys.exit(f"Para {a.torneo} hace falta --externa con un CSV (BSD solo trae el Clausura de 2026).")

    db = tabla_db(a.torneo, por)
    difs, solo_db, solo_ext, campos = comparar(db, ext)
    nombre = lambda k: db[k]["nombre"] if k in db else str(k)

    print(f"\nEquipos: {len(db)} nuestros, {len(ext)} en la fuente. Campos comparados: {', '.join(c for c in CAMPOS if c in campos)}")
    if campos <= {"pj", "pts"}:
        print("  (la fuente no trae goles ni PG/PE/PP: no se pudo validar DG/GF/GC)")
    for k in sorted(solo_db, key=nombre):
        print(f"  ! solo en nuestra base: {nombre(k)}")
    for k in sorted(solo_ext, key=str):
        print(f"  ! solo en la fuente: {k}")
    malos = sorted({d[0] for d in difs}, key=nombre)
    for k in malos:
        det = ", ".join(f"{c}: {n} vs {e}" for kk, c, n, e in difs if kk == k)
        print(f"  x {nombre(k):<30} {det}    (nuestro vs fuente)")
    coinciden = len(db.keys() & ext.keys()) - len(malos)
    print(f"\nCoinciden en todo: {coinciden} equipos | con diferencias: {len(malos)}")

    dif_orden, motivo = comparar_orden(db, pos) if pos else ([], "la fuente no trae posicion")
    if motivo:
        print(f"Orden (desempates): no comparado, {motivo}.")
    else:
        for k, nuestra, ext_pos in sorted(dif_orden, key=lambda x: nombre(x[0])):
            print(f"  ~ {nombre(k):<30} posicion {nuestra} (nuestra) vs {ext_pos} (fuente)")
        print(f"Orden: {'igual en todas las zonas' if not dif_orden else str(len(dif_orden)) + ' posiciones distintas: revisar desempates'}")
    sys.exit(1 if (difs or solo_db or solo_ext or dif_orden) else 0)


if __name__ == "__main__":
    main()
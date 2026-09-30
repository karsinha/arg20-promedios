"""
Sonda de cobertura de BSD (sports.bzzoiro.com) para la Liga Profesional Argentina.

No asume nombres de campos: guarda el JSON crudo en ./bsd_dump/ y te dice
qué hay y qué falta (tabla, fixture, eventos de gol, asistencias, stats de jugador).

Uso:
  pip install requests
  export BSD_TOKEN="tu_token"          # Cuenta -> API key en sports.bzzoiro.com
  python probe_bsd.py                  # autodetecta la liga
  python probe_bsd.py --league-id 123  # si ya conocés el id
"""
import argparse, json, os, sys, time
from datetime import date, timedelta
from pathlib import Path
import requests

BASE = "https://sports.bzzoiro.com/api/v2"
TOKEN = os.environ.get("BSD_TOKEN")
DUMP = Path("bsd_dump"); DUMP.mkdir(exist_ok=True)
S = requests.Session()
S.headers["Authorization"] = f"Token {TOKEN}"


def get(path, **params):
    """GET con manejo de errores comunes. Devuelve JSON o None."""
    url = path if path.startswith("http") else BASE + path
    time.sleep(0.2)  # suave con la cuota
    try:
        r = S.get(url, params=params, timeout=30)
    except requests.RequestException as e:
        print(f"  ! error de red: {e}"); return None
    if r.status_code in (401, 403):
        sys.exit("Token inválido o sin permiso (401/403). Revisá BSD_TOKEN.")
    if r.status_code == 402:
        print(f"  ! {path} requiere plan de pago (402)"); return None
    if r.status_code == 429:
        print("  ! límite de requests (429). Esperá y reintentá."); return None
    if r.status_code != 200:
        print(f"  ! {path} -> HTTP {r.status_code}"); return None
    return r.json()


def save(name, data):
    (DUMP / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))


def items(j):
    """Normaliza: lista, dict paginado ({'results': [...]}) o dict suelto."""
    if j is None: return []
    if isinstance(j, list): return j
    if isinstance(j, dict):
        for k in ("results", "data", "items", "seasons"):
            if isinstance(j.get(k), list): return j[k]
        return [j]
    return []


def paths(obj, prefix="", depth=3):
    """Todas las rutas de claves (hasta depth) de un objeto JSON."""
    out = []
    if depth < 0: return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            out.append(p); out += paths(v, p, depth - 1)
    elif isinstance(obj, list) and obj:
        out += paths(obj[0], prefix + "[]", depth - 1)
    return out


def grep(obj, *words):
    return [p for p in paths(obj) if any(w in p.lower() for w in words)]


def first(d, *keys):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""): return d[k]
    return None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--league-id", type=int)
    a = ap.parse_args()
    if not TOKEN: sys.exit("Falta la variable BSD_TOKEN.")

    # 1) Liga
    print("\n[1] Buscando la Liga Profesional...")
    lid = a.league_id
    if not lid:
        found, url, pages = [], "/leagues/", 0
        j = get(url, limit=200)
        while j is not None and pages < 10:
            pages += 1
            for l in items(j):
                blob = json.dumps(l, ensure_ascii=False).lower()
                if "argentin" in blob and ("profesional" in blob or "primera" in blob or "liga" in blob):
                    found.append(l)
            nxt = j.get("next") if isinstance(j, dict) else None
            j = get(nxt) if nxt else None
        save("leagues_argentina", found)
        for l in found:
            print("   candidato:", first(l, "id"), first(l, "name"), first(l, "country"))
        if not found: sys.exit("No apareció ninguna liga argentina. Revisá bsd_dump/ o pasá --league-id.")
        lid = first(found[0], "id")
    print(f"   usando league_id={lid}")

    # 2) Temporadas
    print("\n[2] Temporadas...")
    seasons = items(get(f"/leagues/{lid}/seasons/"))
    save("seasons", seasons)
    for s in seasons[:8]:
        print("  ", {k: s.get(k) for k in list(s)[:6]})
    cur = next((s for s in seasons if s.get("is_current")), seasons[0] if seasons else None)
    sid = first(cur, "id", "season_id") if cur else None
    print(f"   temporada actual: {sid}  |  ¿hay 2024 y 2025? revisá seasons.json (necesario para Promedios)")

    # 3) Tabla
    print("\n[3] Tabla de posiciones...")
    rows = []
    for s in [x for x in seasons if x.get("year", 0) >= 2024]:
        stid = s.get("id")
        st = get(f"/leagues/{lid}/standings/", season_id=stid)
        save(f"standings_{stid}", st)
        r = items(st)
        print(f"   season {stid} ({s.get('name')}): {len(r)} filas/grupos")
        if r and not rows: rows = r
        if r: print("     claves:", paths(r[0], depth=2)[:20])
        print("     zonas/grupos ->", grep(st, "group", "zone", "zona", "stage")[:6])

    # 4) Partidos de los últimos 14 días
    print("\n[4] Partidos recientes...")
    hoy = date.today()
    ev = items(get("/events/", league_id=lid, date_from=(hoy - timedelta(days=14)).isoformat(), date_to=hoy.isoformat(), limit=100))
    save("events_recent", ev)
    print(f"   partidos: {len(ev)}")
    if ev: print("   claves:", paths(ev[0], depth=2)[:30])

    # 5) Cobertura de goles / asistencias / stats de jugador (muestra de hasta 5 partidos)
    print("\n[5] Cobertura de goleadores y asistencias (muestra)...")
    ok_gol = ok_asist = ok_pstats = 0
    muestra = ev[:5]
    for e in muestra:
        eid = first(e, "id")
        det = get(f"/events/{eid}/")
        ps = get(f"/events/{eid}/player-stats/")
        save(f"event_{eid}", det); save(f"event_{eid}_playerstats", ps)
        g = grep(det, "incident", "goal", "scorer")
        s = grep(det, "assist") + grep(ps, "assist")
        if g or grep(ps, "goal"): ok_gol += 1
        if s: ok_asist += 1
        if items(ps): ok_pstats += 1
    n = len(muestra) or 1
    print(f"   con datos de gol:        {ok_gol}/{len(muestra)}")
    print(f"   con datos de asistencia: {ok_asist}/{len(muestra)}")
    print(f"   con stats por jugador:   {ok_pstats}/{len(muestra)}")

    # 6) Estructura de la temporada 2026: ¿cómo se distinguen Apertura y Clausura?
    print("\n[6] Estructura 2026 (todos los partidos de la temporada)...")
    from collections import Counter
    allev, j, pages = [], get("/events/", league_id=lid, season_id=sid, limit=200), 0
    while j is not None and pages < 15:
        pages += 1; allev += items(j)
        nxt = j.get("next") if isinstance(j, dict) else None
        j = get(nxt) if nxt else None
    save("events_2026", allev)
    print(f"   partidos de la temporada: {len(allev)}")
    c = Counter((e.get("stage"), e.get("group_name")) for e in allev)
    for k, v in sorted(c.items(), key=lambda x: str(x[0])): print("   ", k, v)
    by = {}
    for e in allev:
        k = (e.get("stage"), e.get("round_name") or e.get("round_number"))
        d = str(e.get("event_date"))[:10]
        lo, hi = by.get(k, (d, d)); by[k] = (min(lo, d), max(hi, d))
    for k in sorted(by, key=lambda k: by[k][0])[:45]: print("    ", k, by[k])

    # 7) Forma real de eventos de gol / asistencia / stats de jugador
    print("\n[7] Forma de los datos de gol y asistencia (primer partido de la muestra)...")
    if muestra:
        eid = first(muestra[0], "id")
        det = json.loads((DUMP / f"event_{eid}.json").read_text())
        ps = json.loads((DUMP / f"event_{eid}_playerstats.json").read_text())
        print("   detalle del partido, claves:", paths(det, depth=2)[:50])
        print("   player-stats, claves:", paths(ps, depth=3)[:50])

    # 8) Resumen
    print("\n=== RESUMEN ===")
    print("Tabla actual:     ", "OK" if rows else "FALTA")
    print("Fixture/partidos: ", "OK" if ev else "FALTA (¿sin partidos en 14 días? ampliá el rango)")
    print("Goleadores:       ", "OK" if ok_gol else "NO CONFIRMADO")
    print("Asistidores:      ", "OK" if ok_asist else "NO CONFIRMADO")
    print("Temporadas 24/25: ", "revisar seasons.json")
    print(f"\nJSON crudo en {DUMP.resolve()} — pasámelo y ajusto el esquema/mapeo a los campos reales.")


if __name__ == "__main__":
    main()
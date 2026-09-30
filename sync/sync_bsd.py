"""
Sincroniza BSD (sports.bzzoiro.com) -> PostgreSQL para la Liga Profesional 2026.
Reglas verificadas con probe_bsd.py (ver comentarios al final de schema.sql).

Requisitos:
  pip install requests "psycopg[binary]"
  psql -f schema.sql  (una sola vez, sobre una base vacia)

Variables de entorno:
  BSD_TOKEN      token de BSD
  DATABASE_URL   ej. postgresql://usuario:clave@localhost:5432/futbol

Uso:
  python sync_bsd.py                  # equipos + partidos + stats de partidos nuevos
  python sync_bsd.py --historicos     # ademas carga puntos de 2024 y 2025 (una sola vez)
  python sync_bsd.py --max-matches 50 # procesa player-stats de a tandas (cuida la cuota)
  python sync_bsd.py --resync-days 3  # vuelve a bajar stats de partidos terminados en los ultimos 3 dias

Es idempotente: se puede correr las veces que haga falta sin duplicar datos.
"""
import argparse, logging, os, sys, time
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import psycopg
import requests

BASE = "https://sports.bzzoiro.com/api/v2"
LEAGUE_ID = 85
SEASON_2026 = 1635
HIST = {2024: [1638], 2025: [1637, 1636]}   # anio -> season_ids de BSD
CORTE_APERTURA = "2026-06-15"               # event_date < corte => Apertura, si no Clausura
PLAYOFF_STAGES = {"round-of-16", "quarterfinals", "semifinals", "final"}
ESTADOS = {"finished": "finalizado", "notstarted": "programado", "postponed": "postergado",
           "inprogress": "en_juego", "suspended": "suspendido", "abandoned": "suspendido"}
MAX_INTENTOS_STATS = 8   # con un sync cada 4 h son ~32 h de margen para que BSD cargue las stats
log = logging.getLogger("sync")
S = requests.Session()


# ---------------------------------------------------------------- BSD
def get(path, **params):
    """GET con reintentos. Devuelve JSON o None si falla."""
    url = path if path.startswith("http") else BASE + path
    for intento in range(4):
        time.sleep(0.2)
        try:
            r = S.get(url, params=params or None, timeout=30)
        except requests.RequestException as e:
            log.warning("red: %s (%s)", e, url)
            time.sleep(2 ** intento)
            continue
        if r.status_code in (401, 403):
            sys.exit("Token invalido o sin permiso (401/403). Revisa BSD_TOKEN.")
        if r.status_code == 429:
            espera = 5 * (intento + 1)
            log.warning("429 (limite de requests), espero %ss", espera)
            time.sleep(espera)
            continue
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            log.warning("HTTP %s en %s", r.status_code, url)
            return None
        return r.json()
    return None


def items(j):
    if j is None:
        return []
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for k in ("results", "data", "items"):
            if isinstance(j.get(k), list):
                return j[k]
    return []


def get_all(path, **params):
    out, j = [], get(path, **params)
    paginas = 0
    while j is not None and paginas < 50:
        paginas += 1
        out += items(j)
        nxt = j.get("next") if isinstance(j, dict) else None
        j = get(nxt) if nxt else None
    return out


# ---------------------------------------------------------------- mapeos
def tipo_torneo(ev):
    return "apertura" if ev["event_date"] < CORTE_APERTURA else "clausura"


def fase(ev):
    return "playoff" if ev.get("stage") in PLAYOFF_STAGES else "zona"


def estado(ev):
    e = ESTADOS.get(ev.get("status"))
    if e is None:
        log.warning("status desconocido %r en partido %s: lo dejo como 'programado'", ev.get("status"), ev.get("id"))
        e = "programado"
    return e


def marcar_reprogramados(events):
    """ids de partidos 'postponed' que tienen un gemelo (mismo cruce, fecha e instancia) con otro id."""
    por_clave = defaultdict(list)
    for e in events:
        por_clave[(e["stage"], e["round_number"], e["home_team_id"], e["away_team_id"])].append(e)
    rep = set()
    for grupo in por_clave.values():
        if len(grupo) > 1:
            rep |= {e["id"] for e in grupo if e["status"] == "postponed"}
    return rep


# ---------------------------------------------------------------- pasos
def asegurar_base(cur):
    for anio in (2024, 2025, 2026):
        cur.execute("INSERT INTO temporada (anio) VALUES (%s) ON CONFLICT (anio) DO NOTHING", (anio,))
    cur.execute("SELECT id FROM temporada WHERE anio = 2026")
    tid = cur.fetchone()[0]
    for tipo in ("apertura", "clausura"):
        cur.execute(
            """INSERT INTO torneo (temporada_id, tipo, ext_season_id) VALUES (%s, %s::tipo_torneo, %s)
               ON CONFLICT (temporada_id, tipo) DO UPDATE SET ext_season_id = EXCLUDED.ext_season_id""",
            (tid, tipo, SEASON_2026),
        )
    cur.execute("SELECT tipo::text, id FROM torneo WHERE temporada_id = %s", (tid,))
    return dict(cur.fetchall())


def sync_equipos_y_partidos(cur, torneos, events):
    # Equipos. No se pisa el nombre ni la abreviatura si ya existen (son nuestros); si se actualiza la zona.
    zonas = {}
    for e in events:
        for pref in ("home", "away"):
            tid = e[f"{pref}_team_id"]
            zonas.setdefault(tid, None)
            if e["stage"] == "group-stage" and e.get("group_name", "").endswith(("Group A", "Group B")):
                zonas[tid] = e["group_name"][-1]
    nombres = {}
    for e in events:
        nombres[e["home_team_id"]] = e["home_team"]
        nombres[e["away_team_id"]] = e["away_team"]
    for tid, nombre in nombres.items():
        cur.execute(
            """INSERT INTO equipo (ext_id, nombre, zona_2026) VALUES (%s, %s, %s)
               ON CONFLICT (ext_id) DO UPDATE SET zona_2026 = COALESCE(EXCLUDED.zona_2026, equipo.zona_2026)""",
            (tid, nombre, zonas.get(tid)),
        )
    cur.execute("SELECT ext_id, id FROM equipo")
    eq = dict(cur.fetchall())

    reprog = marcar_reprogramados(events)
    n = 0
    for e in events:
        cur.execute(
            """INSERT INTO partido (ext_id, torneo_id, fase, instancia, interzonal, fecha_nro, fecha_hora,
                                    local_id, visitante_id, goles_local, goles_visitante, estado, reprogramado, actualizado_en)
               VALUES (%s, %s, %s::fase_partido, %s, %s, %s, %s, %s, %s, %s, %s, %s::estado_partido, %s, now())
               ON CONFLICT (ext_id) DO UPDATE SET
                 torneo_id = EXCLUDED.torneo_id, fase = EXCLUDED.fase, instancia = EXCLUDED.instancia,
                 interzonal = EXCLUDED.interzonal, fecha_nro = EXCLUDED.fecha_nro, fecha_hora = EXCLUDED.fecha_hora,
                 local_id = EXCLUDED.local_id, visitante_id = EXCLUDED.visitante_id,
                 goles_local = EXCLUDED.goles_local, goles_visitante = EXCLUDED.goles_visitante,
                 estado = EXCLUDED.estado, reprogramado = EXCLUDED.reprogramado, actualizado_en = now()""",
            (
                e["id"], torneos[tipo_torneo(e)], fase(e), e["stage"], e["stage"] == "league-phase",
                e.get("round_number"), e["event_date"], eq[e["home_team_id"]], eq[e["away_team_id"]],
                e.get("home_score"), e.get("away_score"), estado(e), e["id"] in reprog,
            ),
        )
        n += 1
    log.info("equipos: %d | partidos: %d (reprogramados: %d)", len(eq), n, len(reprog))
    return eq


def partidos_pendientes_de_stats(cur, resync_days, max_matches):
    """Finalizados sin stats (con tope de intentos), mas los terminados en los ultimos N dias si se pidio resync."""
    desde = datetime.now(timezone.utc) - timedelta(days=resync_days)
    cur.execute(
        """SELECT p.id, p.ext_id, p.goles_local, p.goles_visitante, p.local_id, p.visitante_id
           FROM partido p
           WHERE p.estado = 'finalizado'
             AND ((NOT p.stats_ok AND p.stats_intentos < %s)
                  OR (%s > 0 AND p.fecha_hora >= %s))
           ORDER BY p.fecha_hora""",
        (MAX_INTENTOS_STATS, resync_days, desde),
    )
    filas = cur.fetchall()
    return filas[:max_matches] if max_matches else filas


def asegurar_jugador(cur, ext_id, eq, cache):
    if ext_id in cache:
        return cache[ext_id]
    cur.execute("SELECT id FROM jugador WHERE ext_id = %s", (ext_id,))
    fila = cur.fetchone()
    if fila:
        cache[ext_id] = fila[0]
        return fila[0]
    d = get(f"/players/{ext_id}/") or {}
    nombre = d.get("name") or f"Jugador {ext_id}"
    cur.execute(
        """INSERT INTO jugador (ext_id, nombre, nombre_corto, posicion, equipo_id)
           VALUES (%s, %s, %s, %s, %s) ON CONFLICT (ext_id) DO UPDATE SET nombre = EXCLUDED.nombre
           RETURNING id""",
        (ext_id, nombre, d.get("short_name"), d.get("position"), eq.get(d.get("current_team_id"))),
    )
    cache[ext_id] = cur.fetchone()[0]
    return cache[ext_id]


def sync_stats(conn, cur, eq, resync_days, max_matches):
    pend = partidos_pendientes_de_stats(cur, resync_days, max_matches)
    log.info("partidos con stats por bajar: %d", len(pend))
    cache, inv_eq = {}, {v: k for k, v in eq.items()}
    desajustes = 0
    en_contra = 0
    for i, (pid, pext, gl, gv, local_id, visit_id) in enumerate(pend, 1):
        ps = (get(f"/events/{pext}/player-stats/") or {}).get("player_stats")
        if not ps:      # None (error/404) o lista vacia: contar el intento y no tocar lo que ya hubiera
            cur.execute("UPDATE partido SET stats_intentos = stats_intentos + 1 WHERE id = %s", (pid,))
            cur.execute("UPDATE partido SET stats_ok = true WHERE id = %s", (pid,))
            conn.commit()
            log.warning("sin player-stats para partido %s", pext)
            continue
        goles = defaultdict(int)
        cur.execute("DELETE FROM estadistica_jugador WHERE partido_id = %s", (pid,))
        for p in ps:
            g, a = p.get("goals") or 0, p.get("goal_assist") or 0
            yc, rc = p.get("yellow_card") or 0, p.get("red_card") or 0
            mins = p.get("minutes_played") or 0
            goles[p["team_id"]] += g
            if not (mins or g or a or yc or rc):
                continue          # suplentes que no entraron
            equipo_id = eq.get(p["team_id"])
            if equipo_id is None:
                log.warning("team_id %s desconocido en partido %s", p["team_id"], pext)
                continue
            jid = asegurar_jugador(cur, p["player_id"], eq, cache)
            cur.execute(
                """INSERT INTO estadistica_jugador (partido_id, jugador_id, equipo_id, minutos, goles, asistencias, amarillas, rojas)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (partido_id, jugador_id) DO UPDATE SET
                     minutos = EXCLUDED.minutos, goles = EXCLUDED.goles, asistencias = EXCLUDED.asistencias,
                     amarillas = EXCLUDED.amarillas, rojas = EXCLUDED.rojas""",
                (pid, jid, equipo_id, mins, g, a, yc, rc),
            )
        # Control: goles por jugador vs marcador. No se corrige, solo se avisa (posibles goles en contra).
        gl_bsd, gv_bsd = goles.get(inv_eq[local_id], 0), goles.get(inv_eq[visit_id], 0)
        if gl_bsd > gl or gv_bsd > gv:
            # Anomalia real: los jugadores suman MAS goles que el marcador.
            desajustes += 1
            log.warning("DESAJUSTE partido %s: marcador %s-%s, goles por jugador %s-%s", pext, gl, gv, gl_bsd, gv_bsd)
        elif (gl_bsd, gv_bsd) != (gl, gv):
            # Faltan goles en los jugadores: son goles en contra (BSD no se los asigna a nadie).
            # Confirmado a mano en 2 partidos (Rio Cuarto 0-1 Ind. Rivadavia y River 0-1 Rosario Central).
            en_contra += (gl - gl_bsd) + (gv - gv_bsd)
            log.debug("partido %s: %d gol(es) en contra sin jugador", pext, (gl - gl_bsd) + (gv - gv_bsd))
        conn.commit()                       # guardar partido a partido: se ve el avance y un corte no pierde todo
        log.info("[%d/%d] partido %s listo", i, len(pend), pext)
    log.info("stats listas. anomalias de goles: %d | goles en contra sin jugador: %d", desajustes, en_contra)


def standings_rows(st):
    """Filas de equipo (team_id + pts) esten donde esten en la respuesta."""
    def rec(o, prof=0):
        if prof > 6:
            return []
        if isinstance(o, dict):
            if o.get("team_id") is not None and o.get("pts") is not None:
                return [o]
            return [r for v in o.values() for r in rec(v, prof + 1)]
        if isinstance(o, list):
            return [r for v in o for r in rec(v, prof + 1)]
        return []
    return rec(st or {})


def sync_historicos(cur, eq):
    for anio, seasons in HIST.items():
        pj, pts = defaultdict(int), defaultdict(int)
        for sid in seasons:
            for r in standings_rows(get(f"/leagues/{LEAGUE_ID}/standings/", season_id=sid)):
                pj[r["team_id"]] += r["played"]
                pts[r["team_id"]] += r["pts"]
        omitidos = [t for t in pj if t not in eq]
        for t in pj:
            if t in eq:
                cur.execute(
                    """INSERT INTO puntos_historicos (equipo_id, anio, pj, pts) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (equipo_id, anio) DO UPDATE SET pj = EXCLUDED.pj, pts = EXCLUDED.pts""",
                    (eq[t], anio, pj[t], pts[t]),
                )
        log.info("historicos %s: %d equipos cargados, %d fuera de la liga 2026 (omitidos)", anio, len(pj) - len(omitidos), len(omitidos))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--historicos", action="store_true", help="cargar puntos de 2024 y 2025")
    ap.add_argument("--max-matches", type=int, help="maximo de partidos a los que bajar player-stats en esta corrida")
    ap.add_argument("--resync-days", type=int, default=0, help="rebajar stats de partidos terminados en los ultimos N dias")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    token, dsn = os.environ.get("BSD_TOKEN"), os.environ.get("DATABASE_URL")
    if not token or not dsn:
        sys.exit("Faltan BSD_TOKEN y/o DATABASE_URL.")
    S.headers["Authorization"] = f"Token {token}"

    events = get_all("/events/", league_id=LEAGUE_ID, season_id=SEASON_2026, limit=200)
    if not events:
        sys.exit("BSD no devolvio partidos. No toco la base.")
    log.info("partidos bajados de BSD: %d", len(events))

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        torneos = asegurar_base(cur)
        eq = sync_equipos_y_partidos(cur, torneos, events)
        conn.commit()                       # partidos y equipos quedan guardados aunque falle lo siguiente
        if a.historicos:
            sync_historicos(cur, eq)
            conn.commit()
        sync_stats(conn, cur, eq, a.resync_days, a.max_matches)
        conn.commit()
    log.info("listo")


if __name__ == "__main__":
    main()
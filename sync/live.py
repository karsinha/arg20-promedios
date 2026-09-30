"""
Tick de partidos en vivo: 1 llamada a /events/live/ por ciclo, y solo si la base dice que hay un partido en ventana.
Actualiza marcador y estado. Las stats de jugadores las baja sync_bsd.py cuando el partido termina.

  python -m sync.live                # bucle, cada 30 s
  python -m sync.live --una-vez      # un solo tick (para probar)
"""
import argparse, logging, os, sys, time

import psycopg

from sync import sync_bsd as b

log = logging.getLogger("live")

# Compuerta local (sin API): hay algo en juego, o algo que deberia haber empezado en las ultimas 3 h.
VENTANA = """SELECT 1 FROM partido
             WHERE estado = 'en_juego'
                OR (estado = 'programado' AND NOT reprogramado
                    AND fecha_hora BETWEEN now() - interval '3 hours' AND now() + interval '10 minutes')
             LIMIT 1"""


def cerrar_terminados(cur, vivos_ids):
    """Partidos que estaban en_juego y ya no aparecen en /live/: pedir su detalle (1 llamada por partido, una vez)."""
    cur.execute("SELECT ext_id FROM partido WHERE estado = 'en_juego'")
    for (ext,) in cur.fetchall():
        if ext in vivos_ids:
            continue
        d = b.get(f"/events/{ext}/") or {}
        nuevo = b.ESTADOS.get(d.get("status"))
        if nuevo is None:
            log.warning("partido %s salio de /live/ con status desconocido %r: lo dejo como esta", ext, d.get("status"))
        elif nuevo == "en_juego":
            continue                      # el caché del detalle va atrasado: se reintenta en el proximo tick
        else:
            cur.execute("""UPDATE partido SET estado = %s::estado_partido, goles_local = COALESCE(%s, goles_local),
                           goles_visitante = COALESCE(%s, goles_visitante), actualizado_en = now() WHERE ext_id = %s""",
                        (nuevo, d.get("home_score"), d.get("away_score"), ext))
            log.info("partido %s -> %s (%s-%s)", ext, nuevo, d.get("home_score"), d.get("away_score"))


def tick(cur, primera=[True]):
    if not cur.execute(VENTANA).fetchone():
        return "fuera de ventana"
    j = b.get("/events/live/", league_id=b.LEAGUE_ID)
    if j is None:
        return "error de BSD: no toco nada"      # evita cerrar partidos por un fallo de red
    vivos = b.items(j)
    if vivos and primera[0]:
        log.info("forma de /events/live/: %s", sorted(vivos[0].keys()))
        primera[0] = False
    ids = set()
    for e in vivos:
        eid = e.get("id", e.get("event_id"))
        if eid is None:
            log.warning("item de /live/ sin id: %s", e)
            continue
        ids.add(eid)
        cur.execute("""UPDATE partido SET estado = 'en_juego', goles_local = %s, goles_visitante = %s,
                       actualizado_en = now() WHERE ext_id = %s""", (e.get("home_score"), e.get("away_score"), eid))
        if cur.rowcount == 0:
            log.warning("partido vivo %s no esta en la base (correr sync)", eid)
    cerrar_terminados(cur, ids)
    return f"{len(ids)} en vivo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cada", type=int, default=30, help="segundos entre ticks (el caché de BSD es de 10-30 s)")
    ap.add_argument("--una-vez", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token, dsn = os.environ.get("BSD_TOKEN"), os.environ.get("DATABASE_URL")
    if not token or not dsn:
        sys.exit("Faltan BSD_TOKEN y/o DATABASE_URL.")
    b.S.headers["Authorization"] = f"Token {token}"
    while True:
        try:
            with psycopg.connect(dsn) as conn, conn.cursor() as cur:   # conexion por tick: sobrevive a reinicios de la base
                res = tick(cur)
            log.debug("tick: %s", res)
        except Exception:
            log.exception("fallo en el tick")
        if a.una_vez:
            break
        time.sleep(a.cada)


if __name__ == "__main__":
    main()
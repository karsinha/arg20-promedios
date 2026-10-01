"""
Detecta cambios de calendario (postergado, cambio de horario) con 1 llamada a /fixtures/changes/.
Si hay alguno, refresca equipos y partidos completos: el reemplazo de un postergado llega con otro id
y el feed solo avisa del original.

  python -m sync.cambios                      # ventana de 75 min (para un timer cada 60 min)
  python -m sync.cambios --ventana-min 10080  # 7 dias (maximo del feed), para ver la forma de los datos
"""
import argparse, logging, os, sys
from datetime import datetime, timedelta, timezone

import psycopg

from sync import sync_bsd as b

log = logging.getLogger("cambios")


def cambios_de(j) -> list[dict]:
    return (j or {}).get("changes") or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ventana-min", type=int, default=75,
                    help="cuanto mirar hacia atras; debe superar el intervalo del timer (idempotente: repetir no daña)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token, dsn = os.environ.get("BSD_TOKEN"), os.environ.get("DATABASE_URL")
    if not token or not dsn:
        sys.exit("Faltan BSD_TOKEN y/o DATABASE_URL.")
    b.S.headers["Authorization"] = f"Token {token}"

    since = (datetime.now(timezone.utc) - timedelta(minutes=a.ventana_min)).strftime("%Y-%m-%dT%H:%M:%SZ")
    j = b.get("/fixtures/changes/", since=since, league_id=b.LEAGUE_ID, change="kickoff,status", limit=500)
    if j is None:
        log.warning("BSD no respondio: no toco nada")
        return
    cs = cambios_de(j)
    if not cs:
        log.info("sin cambios desde %s", since)
        return
    for c in cs:
        log.info("%s partido %s (%s - %s): %s -> %s", c.get("change"), c.get("event_id"),
                 c.get("home_team"), c.get("away_team"), c.get("old_value"), c.get("new_value"))

    # Si el feed vino truncado da igual: se refresca todo igual.
    events = b.get_all("/events/", league_id=b.LEAGUE_ID, season_id=b.SEASON_2026, limit=200)
    if not events:
        log.warning("BSD no devolvio partidos: no toco la base")
        return
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        torneos = b.asegurar_base(cur)
        b.sync_equipos_y_partidos(cur, torneos, events)
        conn.commit()
    log.info("partidos refrescados por %d cambio(s)", len(cs))


if __name__ == "__main__":
    main()
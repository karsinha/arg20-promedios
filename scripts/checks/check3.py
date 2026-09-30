import json, os, requests
from collections import Counter

ev = json.load(open("bsd_dump/events_2026.json"))
cl = [e for e in ev if e["stage"] in ("group-stage", "league-phase") and e["event_date"] >= "2026-06-15"]

# 1) partidos por equipo en el Clausura (deberían ser 16 cada uno)
c = Counter()
for e in cl:
    c[e["home_team"]] += 1
    c[e["away_team"]] += 1
print("equipos con != 16:", {t: n for t, n in c.items() if n != 16})

# 2) pares de equipos que se enfrentan más de una vez
par = lambda e: frozenset((e["home_team_id"], e["away_team_id"]))
pares = Counter(par(e) for e in cl)
for e in cl:
    if pares[par(e)] > 1:
        print(e["id"], e["home_team"], "-", e["away_team"], e["event_date"][:10],
              "fecha", e["round_number"], e["status"], e["group_name"])

# 3) qué trae la tabla de 2024
st = json.load(open("bsd_dump/standings_1638.json"))
print("claves:", list(st.keys()))
print("stages:", st["season"]["stages"])
rows = st.get("standings") or []
print("filas:", len(rows))
print(rows[0] if rows else None)

# 4) ¿el endpoint de jugador devuelve el nombre?
r = requests.get("https://sports.bzzoiro.com/api/v2/players/21911/",
                 headers={"Authorization": f"Token {os.environ['BSD_TOKEN']}"}, timeout=30)
print(r.status_code, r.text[:600])
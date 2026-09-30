import glob, json

# 1) el partido postergado
ev = json.load(open("bsd_dump/events_2026.json"))
for e in ev:
    if e["status"] == "postponed":
        print({k: e[k] for k in ("id", "home_team", "away_team", "event_date", "round_number", "stage", "replaced_by")})

# 2) goles por jugador vs marcador (usa los 5 partidos que ya bajó la sonda)
for f in glob.glob("bsd_dump/event_*_playerstats.json"):
    eid = f.split("event_")[1].split("_")[0]
    ps = json.load(open(f))["player_stats"]
    d = json.load(open(f"bsd_dump/event_{eid}.json"))
    g = {}
    for p in ps:
        g[p["team_id"]] = g.get(p["team_id"], 0) + (p["goals"] or 0)
    print(eid, d["home_team"], d["home_score"], "-", d["away_score"], d["away_team"],
          "| goles sumados:", g, "| asistencias:", sum(p["goal_assist"] or 0 for p in ps))
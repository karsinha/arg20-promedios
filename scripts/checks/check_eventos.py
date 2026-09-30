import json
from collections import Counter
ev = json.load(open("bsd_dump/events_2026.json"))
print("status:", Counter(e["status"] for e in ev))
reg = [e for e in ev if e["stage"] in ("group-stage", "league-phase")]
ap = [e for e in reg if e["event_date"] < "2026-06-15"]
print("zona Apertura:", len(ap), "| zona Clausura:", len(reg) - len(ap))
print("Apertura por stage:", Counter(e["stage"] for e in ap))
"""Resumen de un club a partir de sus partidos de la temporada (funciones puras)."""

INSTANCIAS = {"round-of-16": "Octavos", "quarterfinals": "Cuartos", "semifinals": "Semifinales", "final": "Final"}
CLAVE = {"G": "pg", "E": "pe", "P": "pp"}


def _equipo(p, lado):
    return {"equipo": p[lado], "abrev": p[f"{lado}_abrev"], "slug": p.get(f"{lado}_slug")}


def _marcador(p, hay):
    if hay:
        s = f"{p['goles_local']} - {p['goles_visitante']}"
        if p.get("pen_local") is not None and p.get("pen_visitante") is not None:
            s += f" ({p['pen_local']}-{p['pen_visitante']} p)"
        return s
    if p["estado"] == "postergado":
        return "Postergado"
    hora = p.get("hora_local")
    return hora.strftime("%d/%m %H:%M") if hora else "A definir"


def _etiqueta(p):
    if p["fase"] == "playoff":
        return INSTANCIAS.get(p.get("instancia"), "Playoffs")
    torneo = p["torneo"].capitalize()
    return f"{torneo} · Fecha {p['fecha_nro']}" if p.get("fecha_nro") else torneo


def vista(p, equipo_id):
    """El partido visto desde el club: izq/der en orden de partido, rival, marcador y resultado (G/E/P).
    Un empate de playoffs definido por penales cuenta como E (tiempo reglamentario)."""
    es_local = p["local_id"] == equipo_id
    gl, gv = p["goles_local"], p["goles_visitante"]
    hay = p["estado"] in ("finalizado", "en_juego") and gl is not None and gv is not None
    gf, gc = (gl, gv) if es_local else (gv, gl)
    resultado = None
    if p["estado"] == "finalizado" and hay:
        resultado = "E" if gf == gc else ("G" if gf > gc else "P")
    izq, der = _equipo(p, "local"), _equipo(p, "visitante")
    return {"id": p["id"], "fase": p["fase"], "estado": p["estado"], "etiqueta": _etiqueta(p),
            "es_local": es_local, "izq": izq, "der": der, "rival": der if es_local else izq,
            "gf": gf, "gc": gc, "marcador": _marcador(p, hay), "resultado": resultado,
            "hora_local": p.get("hora_local")}


def _registro(vistas):
    r = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "pts": 0}
    for v in vistas:
        r["pj"] += 1
        r["gf"] += v["gf"]
        r["gc"] += v["gc"]
        r[CLAVE[v["resultado"]]] += 1
    r["pts"] = 3 * r["pg"] + r["pe"]
    return r


def resumen(partidos: list[dict], equipo_id: int) -> dict:
    """partidos: ordenados por fecha. Devuelve fixture completo, proximo, ultimos 5 (el mas reciente primero),
    forma (ultimos 5, del mas viejo al mas nuevo) y el registro de zona como local y como visitante."""
    vistas = [vista(p, equipo_id) for p in partidos]
    jugados = [v for v in vistas if v["resultado"]]
    pendientes = [v for v in vistas if v["estado"] in ("en_juego", "programado")]
    en_vivo = [v for v in pendientes if v["estado"] == "en_juego"]
    zona = [v for v in jugados if v["fase"] == "zona"]
    return {"fixture": vistas,
            "proximo": (en_vivo or pendientes or [None])[0],
            "ultimos": list(reversed(jugados[-5:])),
            "forma": [v["resultado"] for v in jugados[-5:]],
            "condicion": {"local": _registro([v for v in zona if v["es_local"]]),
                          "visitante": _registro([v for v in zona if not v["es_local"]])}}

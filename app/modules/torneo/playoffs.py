"""Cuadro de playoffs (octavos a final) a partir de las posiciones por zona y los partidos jugados.

Pasan los 8 primeros de cada zona. Los octavos estan en orden de llave: cada par consecutivo alimenta un
cuarto, cada par de cuartos una semifinal, y las dos semifinales la final.
Validado con el Apertura 2026 (posiciones finales y los 15 partidos jugados).
"""
from collections import defaultdict

CLASIFICAN = 8

# (mejor ubicado, peor ubicado). ("A", 1) = primero de la zona A. El primero nombrado es el local.
OCTAVOS = [
    (("A", 1), ("B", 8)), (("B", 4), ("A", 5)),
    (("B", 2), ("A", 7)), (("A", 3), ("B", 6)),
    (("B", 1), ("A", 8)), (("A", 4), ("B", 5)),
    (("A", 2), ("B", 7)), (("B", 3), ("A", 6)),
]


def octavos(zonas: dict[str, list[dict]]) -> list[dict]:
    """zonas: {'A': [filas ordenadas], 'B': [...]} (cada fila con 'equipo' y 'abrev').
    Devuelve los 8 cruces en orden de llave; si una zona no llega a ese puesto, el casillero queda en None."""
    def equipo(zona, pos):
        filas = zonas.get(zona, [])
        return filas[pos - 1] if pos <= len(filas) else None

    return [{"local": equipo(*a), "local_pos": f"{a[1]}{a[0]}",
             "visitante": equipo(*b), "visitante_pos": f"{b[1]}{b[0]}"} for a, b in OCTAVOS]


def _ganador(p):
    """Equipo que avanza ({'equipo','abrev'}) o None si no se sabe (no termino, o empate sin penales cargados)."""
    if not p or p["estado"] != "finalizado" or p["goles_local"] is None:
        return None
    gl, gv = p["goles_local"], p["goles_visitante"]
    if gl == gv:
        gl, gv = p.get("pen_local"), p.get("pen_visitante")
        if gl is None or gv is None or gl == gv:
            return None
    if gl > gv:
        return {"equipo": p["local"], "abrev": p["local_abrev"]}
    return {"equipo": p["visitante"], "abrev": p["visitante_abrev"]}


def _marcador(p):
    if p is None:
        return "vs"
    if p["estado"] in ("finalizado", "en_juego") and p["goles_local"] is not None:
        s = f"{p['goles_local']} - {p['goles_visitante']}"
        if p.get("pen_local") is not None and p.get("pen_visitante") is not None:
            s += f" ({p['pen_local']}-{p['pen_visitante']} p)"
        return s
    hora = p.get("hora_local")
    return hora.strftime("%d/%m %H:%M") if hora else "A definir"


def _buscar(lista, a, b):
    if a is None or b is None:
        return None
    par = {a["equipo"], b["equipo"]}
    return next((p for p in lista if {p["local"], p["visitante"]} == par), None)


def _nodo(a, b, lista, pos=(None, None)):
    p = _buscar(lista, a, b)
    if p:   # con partido jugado/programado se muestran sus datos (local real)
        a = {"equipo": p["local"], "abrev": p["local_abrev"]}
        b = {"equipo": p["visitante"], "abrev": p["visitante_abrev"]}
    return {"local": a, "visitante": b, "local_pos": pos[0], "visitante_pos": pos[1],
            "marcador": _marcador(p), "ganador": _ganador(p)}


def cuadro(zonas: dict[str, list[dict]], jugados: list[dict]) -> list[list[dict]]:
    """[octavos (8), cuartos (4), semifinales (2), final (1)]. Sin partidos de playoff es la proyeccion
    con las posiciones actuales; a medida que se juegan, cada cruce toma su partido real."""
    por = defaultdict(list)
    for p in jugados:
        por[p["instancia"]].append(p)
    rondas = [[_nodo(c["local"], c["visitante"], por["round-of-16"], (c["local_pos"], c["visitante_pos"]))
               for c in octavos(zonas)]]
    for inst in ("quarterfinals", "semifinals", "final"):
        prev = rondas[-1]
        rondas.append([_nodo(prev[i]["ganador"], prev[i + 1]["ganador"], por[inst])
                       for i in range(0, len(prev), 2)])
    return rondas
"""Contextos de torneo (fixture, playoffs, tablas por zona). Los usan la portada y los fragmentos HTMX."""
from app.modules.torneo import modos, playoffs, queries


def contexto_fixture(ctx: modos.Contexto, fecha: int | None = None) -> dict:
    todas = queries.fechas(ctx.torneo_id)
    if not todas:
        return {"fecha": None, "prev": None, "next": None, "partidos": [], "hay_vivo": False}
    if fecha not in todas:
        fecha = queries.fecha_inicial(ctx.torneo_id)
    if fecha not in todas:
        fecha = todas[0]
    i = todas.index(fecha)
    partidos = queries.partidos(ctx.torneo_id, fecha)
    return {"fecha": fecha, "prev": todas[i - 1], "next": todas[(i + 1) % len(todas)],
            "partidos": partidos, "hay_vivo": any(p["estado"] == "en_juego" for p in partidos)}


def agrupar_por_zona(filas: list[dict]) -> list[tuple]:
    zonas: dict = {}
    for f in filas:
        zonas.setdefault(f["zona"], []).append(f)
    return sorted(zonas.items(), key=lambda kv: (kv[0] is None, kv[0] or ""))


def contexto_playoffs(torneo: str = "clausura") -> dict:
    if torneo not in ("apertura", "clausura"):
        torneo = "clausura"
    ctx = modos.resolver(torneo)
    zonas = dict(agrupar_por_zona(queries.tabla_torneo(ctx.torneo_id)))
    jugados = queries.playoffs(ctx.torneo_id)
    return {"torneo": torneo, "rondas": playoffs.cuadro(zonas, jugados),
            "proyectado": not any(p["instancia"] == "round-of-16" for p in jugados)}
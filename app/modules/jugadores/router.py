"""Contexto de goleadores y asistidores. Lo usan la portada y el fragmento HTMX."""
from app.modules.jugadores import queries
from app.modules.torneo import modos


def contexto_jugadores(ctx: modos.Contexto, tipo: str = "goles") -> dict:
    if tipo not in queries.COLUMNAS:
        tipo = "goles"
    if ctx.modo in ("anual", "promedios"):
        filas = queries.top_anual(ctx.temporada_id, tipo)
    else:
        filas = queries.top_torneo(ctx.torneo_id, tipo)
    return {"tipo": tipo, "filas_jugadores": filas}
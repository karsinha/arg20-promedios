from fastapi import APIRouter, Request

from app.core.templating import templates
from app.modules.jugadores import queries
from app.modules.torneo import modos

router = APIRouter(prefix="/jugadores")


def contexto_jugadores(ctx: modos.Contexto, tipo: str = "goles") -> dict:
    if tipo not in queries.COLUMNAS:
        tipo = "goles"
    if ctx.modo in ("anual", "promedios"):
        filas = queries.top_anual(ctx.temporada_id, tipo)
    else:
        filas = queries.top_torneo(ctx.torneo_id, tipo)
    return {"tipo": tipo, "filas_jugadores": filas}


@router.get("")
def jugadores(request: Request, modo: str = "clausura", tipo: str = "goles"):
    ctx = modos.resolver(modo)
    return templates.TemplateResponse(
        request, "partials/jugadores.html", {"modo": modo, **contexto_jugadores(ctx, tipo)})

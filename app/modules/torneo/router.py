from fastapi import APIRouter, Request

from app.core.templating import templates
from app.modules.torneo import modos, queries

router = APIRouter(prefix="/torneo")


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


@router.get("/fixture")
def fixture(request: Request, modo: str = "clausura", fecha: int | None = None):
    ctx = modos.resolver(modo)
    return templates.TemplateResponse(
        request, "partials/fixture.html", {"modo": modo, **contexto_fixture(ctx, fecha)})
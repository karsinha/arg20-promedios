"""Fragmentos HTMX. No son paginas indexables: viven bajo /parcial para no mezclarse con las URLs publicas."""
from fastapi import APIRouter, Request

from app.core.templating import templates
from app.modules.jugadores.router import contexto_jugadores
from app.modules.portada import contexto_main
from app.modules.torneo import modos
from app.modules.torneo.router import contexto_fixture, contexto_playoffs

router = APIRouter(prefix="/parcial", include_in_schema=False)


@router.get("/modo/{modo}")
def cambiar_modo(request: Request, modo: str):
    return templates.TemplateResponse(request, "partials/main.html", contexto_main(modo))


@router.get("/fixture")
def fixture(request: Request, modo: str = "clausura", fecha: int | None = None):
    ctx = modos.resolver(modo)
    return templates.TemplateResponse(
        request, "partials/fixture.html", {"modo": modo, **contexto_fixture(ctx, fecha)})


@router.get("/playoffs")
def cuadro_playoffs(request: Request, torneo: str = "clausura"):
    return templates.TemplateResponse(request, "partials/cuadro.html", contexto_playoffs(torneo))


@router.get("/jugadores")
def jugadores(request: Request, modo: str = "clausura", tipo: str = "goles"):
    ctx = modos.resolver(modo)
    return templates.TemplateResponse(
        request, "partials/jugadores.html", {"modo": modo, **contexto_jugadores(ctx, tipo)})
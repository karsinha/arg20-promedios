"""Portada: compone los 6 bloques (tabla + fixture + jugadores) usando los modulos de dominio."""
from fastapi import APIRouter, Request

from app.core.templating import templates
from app.modules.jugadores.router import contexto_jugadores
from app.modules.torneo import modos, queries
from app.modules.torneo.router import agrupar_por_zona, contexto_fixture

router = APIRouter()


def contexto_main(modo: str) -> dict:
    ctx = modos.resolver(modo)
    datos = {"modo": modo, "etiquetas": modos.ETIQUETAS, "etiqueta": modos.ETIQUETAS[modo]}
    if modo in ("clausura", "apertura"):
        datos["zonas"] = agrupar_por_zona(queries.tabla_torneo(ctx.torneo_id))
    elif modo == "anual":
        datos["filas"] = queries.tabla_anual(ctx.temporada_id)
    else:
        datos["filas"] = queries.tabla_promedios()
    datos.update(contexto_fixture(ctx))
    datos.update(contexto_jugadores(ctx))
    return datos


@router.get("/")
def portada(request: Request, modo: str = "clausura"):
    return templates.TemplateResponse(
        request, "home.html", {"anio": modos.ANIO, **contexto_main(modo)})


@router.get("/modo/{modo}")
def cambiar_modo(request: Request, modo: str):
    return templates.TemplateResponse(request, "partials/main.html", contexto_main(modo))

"""Portada y paginas de cada modo: compone los bloques (tabla + fixture + jugadores) con los modulos de dominio."""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.core.templating import templates
from app.modules.jugadores.router import contexto_jugadores
from app.modules.seo import datos_seo
from app.modules.torneo import descenso, modos, playoffs, queries
from app.modules.torneo.router import agrupar_por_zona, contexto_fixture, contexto_playoffs

router = APIRouter()


def contexto_main(modo: str) -> dict:
    ctx = modos.resolver(modo)
    datos = {"modo": modo, "etiquetas": modos.ETIQUETAS, "etiqueta": modos.ETIQUETAS[modo],
             "clasifican": playoffs.CLASIFICAN}
    if modo in ("clausura", "apertura"):
        datos["zonas"] = agrupar_por_zona(queries.tabla_torneo(ctx.torneo_id))
    elif modo == "anual":
        datos["filas"] = descenso.marcar(queries.tabla_anual(ctx.temporada_id), "pts")
    elif modo == "playoffs":
        datos.update(contexto_playoffs("clausura"))
    else:
        datos["filas"] = descenso.marcar(queries.tabla_promedios(), "promedio")
    if modo in ("anual", "promedios"):
        datos["hay_empate_descenso"] = any(f["empate_descenso"] for f in datos["filas"])
    datos.update(contexto_fixture(ctx))
    datos.update(contexto_jugadores(ctx))
    return datos


def pagina(request: Request, modo: str):
    contexto = contexto_main(modo)            # lanza 404 si el modo no existe
    return templates.TemplateResponse(
        request, "home.html",
        {"anio": modos.ANIO, "actualizado": queries.ultima_actualizacion(),
         "seo": datos_seo(modo), **contexto})


@router.get("/")
def portada(request: Request, modo: str | None = None):
    if modo is not None:                      # URL vieja: /?modo=anual
        if modo not in modos.ETIQUETAS:
            raise HTTPException(404, "Modo desconocido")
        return RedirectResponse(modos.url_modo(modo), status_code=301)
    return pagina(request, "clausura")


@router.get("/torneo/{modo}")
def torneo(request: Request, modo: str):
    if modo == "clausura":                    # una sola URL para el mismo contenido
        return RedirectResponse("/", status_code=301)
    return pagina(request, modo)
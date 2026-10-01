"""Pagina de club: /club/<slug>. Compone resumen, posiciones y goleadores del equipo."""
from fastapi import APIRouter, HTTPException, Request

from app.core.templating import templates
from app.modules.club import queries, resumen
from app.modules.seo import datos_seo_club
from app.modules.torneo import modos
from app.modules.torneo import queries as torneo
from app.modules.torneo.router import agrupar_por_zona

router = APIRouter()


def puesto(filas: list[dict], abrev: str) -> dict | None:
    """Posicion del equipo en una tabla ya ordenada (None si no esta)."""
    for i, f in enumerate(filas, 1):
        if f["abrev"] == abrev:
            return {"pos": i, "de": len(filas), "pts": f["pts"]}
    return None


def contexto_resumen(slug: str) -> dict:
    """Equipo, resumen y posiciones, sin goleadores. Lo usan la pagina de club y la tarjeta 'Mi club'."""
    equipo = queries.equipo_por_slug(slug)
    if equipo is None:
        raise HTTPException(404, "Club desconocido")
    ctx = modos.resolver("clausura")
    zonas = dict(agrupar_por_zona(torneo.tabla_torneo(ctx.torneo_id)))
    return {"equipo": equipo, "temporada_id": ctx.temporada_id,
            "resumen": resumen.resumen(queries.partidos_equipo(equipo["id"], modos.ANIO), equipo["id"]),
            "puesto_zona": puesto(zonas.get(equipo["zona"], []), equipo["abrev"]),
            "puesto_anual": puesto(torneo.tabla_anual(ctx.temporada_id), equipo["abrev"])}


def contexto_club(slug: str) -> dict:
    datos = contexto_resumen(slug)
    tid, eid = datos["temporada_id"], datos["equipo"]["id"]
    datos.update(goleadores=queries.top_equipo(tid, eid, "goles"),
                 asistidores=queries.top_equipo(tid, eid, "asistencias"))
    return datos


@router.get("/club/{slug}")
def club(request: Request, slug: str):
    contexto = contexto_club(slug)
    return templates.TemplateResponse(
        request, "club.html",
        {"anio": modos.ANIO, "actualizado": torneo.ultima_actualizacion(),
         "seo": datos_seo_club(contexto["equipo"]), **contexto})

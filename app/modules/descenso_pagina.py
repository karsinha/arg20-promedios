"""Pagina /descenso: Anual y Promedios con margen, partidos restantes y estado matematico de cada equipo."""
from fastapi import APIRouter, Request

from app.core.templating import templates
from app.modules.seo import datos_seo_descenso
from app.modules.torneo import descenso, modos
from app.modules.torneo import queries as torneo

router = APIRouter()

ZONA_VISIBLE = 6      # cuantos equipos del fondo de cada tabla se muestran


def _armar(filas: list[dict], clave: str, cotas, restantes: dict[str, int]) -> dict:
    minimos, maximos = cotas(filas, restantes)
    marcadas = descenso.marcar(filas, clave)
    ui = [{**f, "restantes": restantes.get(f["abrev"], 0), "matematico": e}
          for f, e in zip(marcadas, descenso.estados(minimos, maximos))]
    m = descenso.margen(filas, clave)
    texto = None if m is None else (f"{m} pts" if clave == "pts" else f"{float(m):.3f} de promedio")
    return {"filas": ui[-ZONA_VISIBLE:], "margen_txt": texto,
            "hay_empate": any(f["empate_descenso"] for f in marcadas)}


def contexto_descenso() -> dict:
    ctx = modos.resolver("anual")
    restantes = torneo.partidos_restantes(modos.ANIO)
    return {"anual": _armar(torneo.tabla_anual(ctx.temporada_id), "pts", descenso.cotas_pts, restantes),
            "promedios": _armar(torneo.tabla_promedios(), "promedio", descenso.cotas_promedio, restantes)}


@router.get("/descenso")
def pagina_descenso(request: Request):
    return templates.TemplateResponse(
        request, "descenso.html",
        {"anio": modos.ANIO, "actualizado": torneo.ultima_actualizacion(), "seo": datos_seo_descenso(),
         **contexto_descenso()})

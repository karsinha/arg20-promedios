"""Pagina /descenso: Anual y Promedios con margen, partidos restantes y estado matematico de cada equipo."""
from fastapi import APIRouter, Request

from app.core.templating import templates
from app.modules.seo import datos_seo_descenso
from app.modules.torneo import descenso, modos
from app.modules.torneo import queries as torneo

router = APIRouter()

ZONA_VISIBLE = 6      # cuantos equipos del fondo de cada tabla se muestran


def _ui(filas, clave, restantes, estados, excluidos=frozenset()) -> dict:
    marcadas = descenso.marcar(filas, clave, excluidos=excluidos)
    ui = [{**f, "restantes": restantes.get(f["abrev"], 0), "matematico": e} for f, e in zip(marcadas, estados)]
    m = descenso.margen(filas, clave, excluidos=excluidos)
    texto = None if m is None else (f"{m} pts" if clave == "pts" else f"{float(m):.3f} de promedio")
    return {"filas": ui[-ZONA_VISIBLE:], "margen_txt": texto,
            "hay_empate": any(f["empate_descenso"] for f in marcadas),
            "traspaso": descenso.traspaso(filas, clave, excluidos)}


def contexto_descenso() -> dict:
    ctx = modos.resolver("anual")
    restantes = torneo.partidos_restantes(modos.ANIO)
    anual, prom = torneo.tabla_anual(ctx.temporada_id), torneo.tabla_promedios()

    # Promedios se resuelve primero: su descendido sale del pool de la Anual.
    min_p, max_p = descenso.cotas_promedio(prom, restantes)
    est_p = descenso.estados(min_p, max_p)
    baja_prom = {f["abrev"] for f in descenso.marcar(prom, "promedio") if f["descenso"]}
    condenados = {f["abrev"] for f, e in zip(prom, est_p) if e == "condenado"}
    salvados = {f["abrev"] for f, e in zip(prom, est_p) if e == "salvado"}

    min_a, max_a = descenso.cotas_pts(anual, restantes)
    est_a = descenso.estados_anual([f["abrev"] for f in anual], min_a, max_a, condenados, salvados)
    return {"anual": _ui(anual, "pts", restantes, est_a, baja_prom),
            "promedios": _ui(prom, "promedio", restantes, est_p)}


@router.get("/descenso")
def pagina_descenso(request: Request):
    return templates.TemplateResponse(
        request, "descenso.html",
        {"anio": modos.ANIO, "actualizado": torneo.ultima_actualizacion(), "seo": datos_seo_descenso(),
         **contexto_descenso()})
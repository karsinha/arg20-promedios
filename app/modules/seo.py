"""SEO: title, description y URL canonica de cada pagina, mas sitemap.xml y robots.txt."""
from fastapi import APIRouter
from fastapi.responses import Response

from app.core.config import settings
from app.modules.torneo import modos

router = APIRouter(include_in_schema=False)

TITULOS = {"clausura": "Tabla del Clausura", "apertura": "Tabla del Apertura", "anual": "Tabla Anual",
           "promedios": "Tabla de Promedios", "playoffs": "Playoffs"}
DESCRIPCIONES = {
    "clausura": f"Tabla de posiciones por zona, fixture y goleadores del Clausura {modos.ANIO} de la Liga Profesional Argentina.",
    "apertura": f"Tabla de posiciones por zona, fixture y goleadores del Apertura {modos.ANIO} de la Liga Profesional Argentina.",
    "anual": f"Tabla anual {modos.ANIO} de la Liga Profesional: suma de los puntos del Apertura y el Clausura.",
    "promedios": f"Tabla de promedios del descenso: puntos y partidos de 2024, 2025 y {modos.ANIO}.",
    "playoffs": f"Cuadro de playoffs {modos.ANIO}: octavos, cuartos, semifinales y final, con resultados y penales.",
}


def url_absoluta(ruta: str) -> str:
    return settings.sitio_url.rstrip("/") + ruta


def datos_seo(modo: str) -> dict:
    return {"titulo": f"{TITULOS[modo]} {modos.ANIO} · Liga Profesional Argentina",
            "descripcion": DESCRIPCIONES[modo],
            "url": url_absoluta(modos.url_modo(modo))}


@router.get("/sitemap.xml")
def sitemap():
    urls = "".join(f"<url><loc>{url_absoluta(modos.url_modo(m))}</loc></url>" for m in modos.ETIQUETAS)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    return Response(xml, media_type="application/xml")


@router.get("/robots.txt")
def robots():
    texto = f"User-agent: *\nDisallow: /parcial/\nDisallow: /salud\nSitemap: {url_absoluta('/sitemap.xml')}\n"
    return Response(texto, media_type="text/plain")

def datos_seo_club(equipo: dict) -> dict:
    nombre = equipo["equipo"]
    return {"titulo": f"{nombre} {modos.ANIO} · Resultados, fixture y goleadores · Liga Profesional",
            "descripcion": (f"{nombre} en la Liga Profesional Argentina {modos.ANIO}: próximo partido, últimos "
                            "resultados, forma, fixture completo, posición y goleadores."),
            "url": url_absoluta(f"/club/{equipo['slug']}")}

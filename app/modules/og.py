"""Tarjetas Open Graph (PNG 1200x630) para compartir. El dibujo (`tarjeta`) es puro: recibe un dict."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.modules.club.router import contexto_resumen
from app.modules.torneo import modos
from app.modules.torneo import queries as torneo

router = APIRouter(include_in_schema=False)

RAIZ = Path(__file__).resolve().parent.parent          # app/
ANCHO, ALTO = 1200, 630
FONDO, CARD, CARD2, LINEA = (15, 23, 32), (23, 33, 45), (27, 39, 54), (42, 58, 77)
TX, MUT, VERDE, ROJO, GRIS = (232, 238, 245), (147, 164, 184), (61, 220, 151), (255, 122, 165), (111, 129, 151)
COLOR_FORMA = {"G": VERDE, "E": GRIS, "P": ROJO}

# Manrope si la copias a app/static/fonts/; si no, cae a fuentes del sistema.
FUENTES = {True: [RAIZ / "static" / "fonts" / "Manrope-Bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"],
           False: [RAIZ / "static" / "fonts" / "Manrope-Medium.ttf", "DejaVuSans.ttf", "arial.ttf"]}


@lru_cache(maxsize=64)
def fuente(tam: int, negrita: bool = True):
    for f in FUENTES[negrita]:
        try:
            return ImageFont.truetype(str(f), tam)
        except OSError:
            continue
    return ImageFont.load_default(tam)


def ajustar(d, texto: str, ancho: int, tam: int, negrita: bool = True, minimo: int = 24):
    """(texto, fuente) que entra en `ancho`: primero achica la letra, y si aun asi no entra, recorta con '…'."""
    while tam > minimo and d.textlength(texto, font=fuente(tam, negrita)) > ancho:
        tam -= 2
    f = fuente(tam, negrita)
    if d.textlength(texto, font=f) > ancho:
        while texto and d.textlength(texto + "…", font=f) > ancho:
            texto = texto[:-1]
        texto = texto.rstrip() + "…"
    return texto, f


def tarjeta(datos: dict) -> bytes:
    """datos: titulo (obligatorio); subtitulo, destacado, abrev, escudo (ruta), forma ['G','E','P'], lineas [..], pie."""
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((40, 40, ANCHO - 40, ALTO - 40), radius=28, fill=CARD, outline=LINEA, width=2)
    d.ellipse((84, 78, 98, 92), fill=VERDE)
    d.text((112, 72), "FÚTBOL ARGENTINA", font=fuente(24), fill=MUT)

    tiene_escudo = False
    ruta = datos.get("escudo")
    if ruta and Path(ruta).exists():
        c = Image.open(ruta).convert("RGBA").resize((220, 220), Image.LANCZOS)
        img.paste(c, (90, 140), c)
        tiene_escudo = True
    elif datos.get("abrev"):                                   # sin imagen: circulo con la abreviatura
        d.ellipse((90, 140, 310, 360), fill=CARD2, outline=LINEA, width=3)
        t, f = ajustar(d, datos["abrev"], 160, 72)
        d.text((200, 250), t, font=f, fill=MUT, anchor="mm")
        tiene_escudo = True

    x = 350 if tiene_escudo else 90
    ancho = ANCHO - 90 - x
    t, f = ajustar(d, datos["titulo"], ancho, 84)
    d.text((x, 130), t, font=f, fill=TX)
    if datos.get("subtitulo"):
        t, f = ajustar(d, datos["subtitulo"], ancho, 34, negrita=False)
        d.text((x, 245), t, font=f, fill=MUT)
    if datos.get("destacado"):
        t, f = ajustar(d, datos["destacado"], ancho, 40)
        d.text((x, 305), t, font=f, fill=VERDE)

    px = 90
    for r in datos.get("forma", []):
        d.rounded_rectangle((px, 385, px + 56, 441), radius=12, fill=COLOR_FORMA[r])
        d.text((px + 28, 413), r, font=fuente(30), fill=CARD, anchor="mm")
        px += 68

    y = 460
    for i, linea in enumerate(datos.get("lineas", [])[:2]):
        t, f = ajustar(d, linea, ANCHO - 180, 32, negrita=(i == 0))
        d.text((90, y), t, font=f, fill=TX if i == 0 else MUT)
        y += 48

    d.text((ANCHO - 90, ALTO - 66), datos.get("pie", ""), font=fuente(24, False), fill=MUT, anchor="rm")
    buf = BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------- datos de cada tarjeta
def _pie() -> str:
    return settings.sitio_url.split("//")[-1].rstrip("/")


def datos_club(ctx: dict) -> dict:
    """ctx: lo que devuelve club.router.contexto_resumen."""
    e, r, za, pa = ctx["equipo"], ctx["resumen"], ctx["puesto_zona"], ctx["puesto_anual"]
    partes = []
    if za:
        partes.append(f"Clausura: {za['pos']}.º (Zona {e['zona']})")
    if pa:
        partes.append(f"Anual: {pa['pos']}.º de {pa['de']} · {pa['pts']} pts")
    lineas, p = [], r["proximo"]
    if p and p["estado"] == "en_juego":
        lineas.append(f"En juego: {p['izq']['equipo']} {p['marcador']} {p['der']['equipo']}")
    elif p:
        lineas.append(f"Próximo: {p['rival']['equipo']} ({'local' if p['es_local'] else 'visitante'}) · {p['marcador']}")
    if r["ultimos"]:
        u = r["ultimos"][0]
        lineas.append(f"Último: {u['izq']['equipo']} {u['marcador']} {u['der']['equipo']}")
    return {"titulo": f"{e['equipo']} {modos.ANIO}",
            "subtitulo": f"Liga Profesional{' · Zona ' + e['zona'] if e.get('zona') else ''}",
            "destacado": " · ".join(partes), "abrev": e["abrev"], "forma": r["forma"], "lineas": lineas,
            "escudo": str(RAIZ / "static" / "crests" / f"{e['abrev'].lower()}.webp"), "pie": _pie()}


def datos_sitio() -> dict:
    return {"titulo": f"Liga Profesional {modos.ANIO}", "subtitulo": "Tablas, fixture, descenso y goleadores",
            "pie": _pie()}


# ---------------------------------------------------------------- rutas (cache en memoria, se invalida con cada sync)
_CACHE: dict[tuple, bytes] = {}


def _cacheado(clave: tuple, generar) -> Response:
    k = (clave, str(torneo.ultima_actualizacion()))
    if k not in _CACHE:
        if len(_CACHE) >= 100:
            _CACHE.clear()
        _CACHE[k] = generar()
    return Response(_CACHE[k], media_type="image/png", headers={"Cache-Control": "public, max-age=900"})


@router.get("/og/club/{slug}.png")
def og_club(slug: str):
    return _cacheado(("club", slug), lambda: tarjeta(datos_club(contexto_resumen(slug))))   # 404 si no existe


@router.get("/og/sitio.png")
def og_sitio():
    return _cacheado(("sitio",), lambda: tarjeta(datos_sitio()))
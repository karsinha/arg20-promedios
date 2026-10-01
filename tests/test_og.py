from io import BytesIO

from PIL import Image

from app.core.config import settings
from app.modules import og
from tests.test_club import cli  # noqa: F401  (fixture con base y club falsos)


def abrir(png):
    return Image.open(BytesIO(png))


def test_tarjeta_tiene_tamano_y_formato_de_og():
    im = abrir(og.tarjeta({
        "titulo": "River Plate 2026", "subtitulo": "Liga Profesional · Zona A", "abrev": "RIV",
        "destacado": "Clausura: 1.º (Zona A) · Anual: 1.º de 30 · 60 pts", "forma": ["G", "E", "P"],
        "lineas": ["Próximo: Lanús (local) · 07/10 20:00", "Último: Sarmiento 2 - 1 River Plate"], "pie": "ejemplo.com"}))
    assert im.format == "PNG" and im.size == (1200, 630)


def test_textos_largos_y_sin_escudo_no_rompen():
    assert abrir(og.tarjeta({"titulo": "X" * 200, "lineas": ["Y" * 300], "destacado": "Z" * 200})).size == (1200, 630)
    assert abrir(og.tarjeta({"titulo": "Liga Profesional 2026"})).size == (1200, 630)


def test_og_de_club(cli):
    r = cli.get("/og/club/river.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert "max-age" in r.headers["cache-control"] and abrir(r.content).size == (1200, 630)
    assert cli.get("/og/club/nadie.png").status_code == 404
    assert cli.get("/og/sitio.png").status_code == 200


def test_las_paginas_apuntan_a_su_tarjeta(cli, monkeypatch):
    monkeypatch.setattr(settings, "sitio_url", "https://ejemplo.com")
    club = cli.get("/club/river").text
    assert 'property="og:image" content="https://ejemplo.com/og/club/river.png"' in club
    assert 'content="summary_large_image"' in club
    assert 'property="og:image" content="https://ejemplo.com/og/sitio.png"' in cli.get("/torneo/anual").text
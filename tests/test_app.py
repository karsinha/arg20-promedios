"""Prueba las rutas y plantillas con una base falsa (sin PostgreSQL)."""
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.main import app
from app.core.config import settings
from app.modules.torneo import queries

fila = dict(pj=2, pg=1, pe=1, pp=0, gf=3, gc=1, dg=2, pts=4)


def falsa(sql, params=None):
    if "MAX(actualizado_en)" in sql:
        return [{"ultima": datetime(2026, 9, 30, 14, 5)}]
    if "FROM torneo t" in sql:
        return [{"id": 1, "tipo": "apertura", "temporada_id": 1}, {"id": 2, "tipo": "clausura", "temporada_id": 1}]
    if "v_tabla_torneo" in sql:
        return [{"zona": "A", "equipo": "River Plate", "abrev": "RIV", **fila},
                {"zona": "B", "equipo": "Boca Juniors", "abrev": "BOC", **fila}]
    if "v_tabla_anual" in sql:
        return [{"equipo": "Racing Club", "abrev": "RAC", **fila}]
    if "v_promedios" in sql:
        return [{"equipo": "Talleres", "abrev": "TAL", "pts_2024": 40, "pts_2025": 35, "pts_2026": 10,
                 "pj": 70, "promedio": Decimal("1.214")}]
    if "DISTINCT fecha_nro" in sql:
        return [{"fecha_nro": n} for n in (1, 2, 3)]
    if "MAX(fecha_nro)" in sql:
        return [{"fecha": 2}]
    if "fase = 'playoff'" in sql:
        return []
    if "FROM partido p" in sql:
        return [{"id": 1, "estado": "finalizado", "goles_local": 2, "goles_visitante": 1, "hora_local": None,
                 "local": "Lanús", "local_abrev": "LAN", "visitante": "Tigre", "visitante_abrev": "TIG"},
                {"id": 2, "estado": "programado", "goles_local": None, "goles_visitante": None,
                 "hora_local": datetime(2026, 10, 7, 20, 0), "local": "Sarmiento", "local_abrev": "SAR",
                 "visitante": "River Plate", "visitante_abrev": "RIV"}]
    if "v_stats_jugador" in sql:
        return [{"pos": 1, "jugador": "J. Candia", "equipo": "Lanús", "goles": 7, "asistencias": 2}]
    raise AssertionError(f"consulta no prevista: {sql[:60]}")


@pytest.fixture()
def cli(monkeypatch):
    monkeypatch.setattr(db, "consultar", falsa)
    return TestClient(app)


def test_portada_clausura(cli):
    r = cli.get("/")
    assert r.status_code == 200
    assert "Zona A" in r.text and "Zona B" in r.text and "River Plate" in r.text
    assert "Fecha 2" in r.text and "2 - 1" in r.text and "07/10 20:00" in r.text
    assert "J. Candia" in r.text
    assert "8.º puesto" in r.text
    assert "Última actualización: 30/09/2026 14:05" in r.text


def test_modos(cli):
    assert "Racing Club" in cli.get("/torneo/anual").text
    p = cli.get("/torneo/promedios").text
    assert "Talleres" in p and "1.214" in p
    assert 'hx-push-url="/torneo/anual"' in cli.get("/").text


def test_fragmentos(cli):
    anual = cli.get("/parcial/modo/anual").text
    assert "Racing Club" in anual and "<html" not in anual
    assert "Fecha 3" in cli.get("/parcial/fixture?modo=clausura&fecha=3").text
    assert "Asist." in cli.get("/parcial/jugadores?modo=clausura&tipo=asistencias").text


def test_modo_invalido(cli):
    assert cli.get("/torneo/xxx").status_code == 404
    assert cli.get("/parcial/modo/xxx").status_code == 404
    assert cli.get("/?modo=xxx").status_code == 404


def test_redirecciones_de_urls_viejas(cli):
    r = cli.get("/?modo=anual", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/torneo/anual"
    r = cli.get("/torneo/clausura", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/"


def test_playoffs_proyectado(cli):
    r = cli.get("/torneo/playoffs").text
    assert "Octavos" in r and "Semifinales" in r and "1A" in r and "8B" in r
    assert "Apertura" in cli.get("/parcial/playoffs?torneo=apertura").text


def test_tema(cli):
    t = cli.get("/").text
    assert "theme.css" in t and 'id="tema"' in t




def test_seo(cli, monkeypatch):
    monkeypatch.setattr(settings, "sitio_url", "https://ejemplo.com")
    t = cli.get("/torneo/anual").text
    assert "<title>Tabla Anual 2026 · Liga Profesional Argentina</title>" in t
    assert '<link rel="canonical" href="https://ejemplo.com/torneo/anual">' in t
    assert 'property="og:title"' in t and 'name="description"' in t
    assert '<link rel="canonical" href="https://ejemplo.com/">' in cli.get("/").text


def test_sitemap_y_robots(cli, monkeypatch):
    monkeypatch.setattr(settings, "sitio_url", "https://ejemplo.com/")
    s = cli.get("/sitemap.xml")
    assert s.headers["content-type"].startswith("application/xml")
    assert "<loc>https://ejemplo.com/</loc>" in s.text
    assert "<loc>https://ejemplo.com/torneo/playoffs</loc>" in s.text
    r = cli.get("/robots.txt").text
    assert "Disallow: /parcial/" in r and "Sitemap: https://ejemplo.com/sitemap.xml" in r




def test_anual_marca_el_descenso(cli, monkeypatch):
    f = dict(pj=2, pg=0, pe=0, pp=0, gf=0, gc=0, dg=0)
    monkeypatch.setattr(queries, "tabla_anual", lambda tid: [
        {"equipo": "Racing Club", "abrev": "RAC", "pts": 6, **f},
        {"equipo": "Tigre", "abrev": "TIG", "pts": 6, **f}])
    t = cli.get("/torneo/anual").text
    assert "descenso empate" in t and "partido de desempate" in t



def test_anual_con_campeon_y_zonas_de_copa(cli, monkeypatch):
    f = dict(pj=2, pg=0, pe=0, pp=0, gf=0, gc=0, dg=0)
    monkeypatch.setattr(queries, "tabla_anual", lambda tid: [
        {"equipo": "Racing Club", "abrev": "RAC", "pts": 9, **f},
        {"equipo": "Boca Juniors", "abrev": "BOC", "pts": 7, **f},
        {"equipo": "Tigre", "abrev": "TIG", "pts": 6, **f}])
    final = {"instancia": "final", "estado": "finalizado", "goles_local": 1, "goles_visitante": 0,
             "pen_local": None, "pen_visitante": None, "hora_local": None,
             "local": "Boca Juniors", "local_abrev": "BOC", "visitante": "Tigre", "visitante_abrev": "TIG"}
    monkeypatch.setattr(queries, "playoffs", lambda tid: [final])
    t = cli.get("/torneo/anual").text
    assert "★" in t and "Boca Juniors (Apertura y Clausura)" in t
    assert "Copa Libertadores" in t and "Copa Sudamericana" in t
    assert "Todavía sin campeón" not in t

import re

def test_la_clase_de_copa_queda_en_la_fila_con_celdas(cli, monkeypatch):
    f = dict(pj=2, pg=0, pe=0, pp=0, gf=0, gc=0, dg=0)
    monkeypatch.setattr(queries, "tabla_anual", lambda tid: [
        {"equipo": "Racing Club", "abrev": "RAC", "pts": 9, **f},
        {"equipo": "Tigre", "abrev": "TIG", "pts": 6, **f}])
    t = cli.get("/torneo/anual").text
    assert re.search(r'<tr class="[^"]*\blib\b[^"]*">\s*<td', t)


def test_anual_avisa_si_falta_el_campeon(cli):
    assert "Todavía sin campeón: Apertura y Clausura" in cli.get("/torneo/anual").text

def test_la_clase_de_copa_queda_en_la_fila_con_celdas(cli, monkeypatch):
    import re
    f = dict(pj=2, pg=0, pe=0, pp=0, gf=0, gc=0, dg=0)
    monkeypatch.setattr(queries, "tabla_anual", lambda tid: [
        {"equipo": "Racing Club", "abrev": "RAC", "pts": 9, **f},
        {"equipo": "Tigre", "abrev": "TIG", "pts": 6, **f}])
    t = cli.get("/torneo/anual").text
    assert re.search(r'<tr class="[^"]*\blib\b[^"]*">\s*<td', t)
    assert re.search(r'<tr class="[^"]*\bdescenso\b[^"]*">\s*<td', t)

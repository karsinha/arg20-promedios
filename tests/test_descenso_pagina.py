import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.main import app
from app.modules.torneo import queries
from tests.test_app import falsa


from decimal import Decimal


@pytest.fixture()
def cli(monkeypatch):
    monkeypatch.setattr(db, "consultar", falsa)
    f = dict(pj=30, pg=0, pe=0, pp=0, gf=0, gc=0, dg=0)
    monkeypatch.setattr(queries, "tabla_anual", lambda tid: [
        {"equipo": "Racing Club", "abrev": "RAC", "slug": "racing", "pts": 60, **f},
        {"equipo": "Boca Juniors", "abrev": "BOC", "slug": "boca", "pts": 30, **f},
        {"equipo": "Tigre", "abrev": "TIG", "slug": "tigre", "pts": 10, **f}])

    def prom(eq, ab, slug, p, pr):
        return {"equipo": eq, "abrev": ab, "slug": slug, "pts_2024": p, "pts_2025": p, "pts_2026": p,
                "pj": 100, "promedio": Decimal(pr)}
    monkeypatch.setattr(queries, "tabla_promedios", lambda: [
        prom("Racing Club", "RAC", "racing", 50, "1.600"), prom("Boca Juniors", "BOC", "boca", 30, "0.900"),
        prom("Tigre", "TIG", "tigre", 10, "0.300")])
    monkeypatch.setattr(queries, "partidos_restantes", lambda anio: {"RAC": 1, "BOC": 1, "TIG": 1})
    return TestClient(app)


def test_pagina_descenso(cli):
    t = cli.get("/descenso").text
    assert "Desciende" in t and "Salvado" in t and 'href="/club/tigre"' in t
    assert "Tigre ya desciende por promedio" in t and "pasa a Boca Juniors" in t
    assert "El primero que se salva le saca 30 pts" in t


def test_descenso_en_el_sitemap_y_enlazado(cli):
    assert "/descenso</loc>" in cli.get("/sitemap.xml").text
    assert 'href="/descenso"' in cli.get("/torneo/anual").text


def test_pagina_muestra_cuanto_necesita(cli, monkeypatch):
    def prom(eq, ab, p):
        return {"equipo": eq, "abrev": ab, "slug": ab.lower(), "pts_2024": p, "pts_2025": p, "pts_2026": p,
                "pj": 30, "promedio": Decimal(p * 3) / 30}
    monkeypatch.setattr(queries, "tabla_promedios", lambda: [
        prom("Racing Club", "RAC", 20), prom("Boca Juniors", "BOC", 10), prom("Tigre", "TIG", 9)])
    monkeypatch.setattr(queries, "partidos_restantes", lambda anio: {"RAC": 3, "BOC": 3, "TIG": 3})
    t = cli.get("/descenso").text
    assert "Necesita 7 de 9" in t and "Depende de otros" in t

def test_descenso_es_una_pestania(cli):
    home = cli.get("/").text
    assert 'hx-get="/parcial/modo/descenso"' in home and 'hx-push-url="/descenso"' in home
    frag = cli.get("/parcial/modo/descenso").text
    assert "Tabla Anual" in frag and "Tabla de Promedios" in frag and "<html" not in frag
    r = cli.get("/torneo/descenso", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/descenso"
    r = cli.get("/?modo=descenso", follow_redirects=False)
    assert r.status_code == 301 and r.headers["location"] == "/descenso"


def test_descenso_una_sola_vez_en_el_sitemap(cli):
    assert cli.get("/sitemap.xml").text.count("/descenso</loc>") == 1

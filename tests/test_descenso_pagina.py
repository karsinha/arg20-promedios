import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.main import app
from app.modules.torneo import queries
from tests.test_app import falsa


@pytest.fixture()
def cli(monkeypatch):
    monkeypatch.setattr(db, "consultar", falsa)
    f = dict(pj=30, pg=0, pe=0, pp=0, gf=0, gc=0, dg=0)
    monkeypatch.setattr(queries, "tabla_anual", lambda tid: [
        {"equipo": "Racing Club", "abrev": "RAC", "slug": "racing", "pts": 60, **f},
        {"equipo": "Tigre", "abrev": "TIG", "slug": "tigre", "pts": 10, **f}])
    monkeypatch.setattr(queries, "partidos_restantes", lambda anio: {"RAC": 1, "TIG": 1})
    return TestClient(app)


def test_pagina_descenso(cli):
    r = cli.get("/descenso")
    assert r.status_code == 200
    t = r.text
    assert "Descenso" in t and "Racing Club" in t and "Tigre" in t
    assert "Desciende" in t and "Salvado" in t and 'href="/club/tigre"' in t
    assert "Talleres" in t and "El primero que se salva le saca 50 pts" in t


def test_descenso_en_el_sitemap_y_enlazado(cli):
    assert "/descenso</loc>" in cli.get("/sitemap.xml").text
    assert 'href="/descenso"' in cli.get("/torneo/anual").text

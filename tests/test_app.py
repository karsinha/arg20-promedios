"""Prueba las rutas y plantillas con una base falsa (sin PostgreSQL)."""
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.main import app

fila = dict(pj=2, pg=1, pe=1, pp=0, gf=3, gc=1, dg=2, pts=4)


def falsa(sql, params=None):
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


def test_modos(cli):
    assert "Racing Club" in cli.get("/modo/anual").text
    p = cli.get("/modo/promedios").text
    assert "Talleres" in p and "1.214" in p


def test_fixture_y_jugadores(cli):
    assert "Fecha 3" in cli.get("/torneo/fixture?modo=clausura&fecha=3").text
    assert "Asist." in cli.get("/jugadores?modo=clausura&tipo=asistencias").text


def test_modo_invalido(cli):
    assert cli.get("/modo/xxx").status_code == 404

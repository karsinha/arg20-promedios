from datetime import datetime

from app.modules.club import resumen

RIVER, SARMIENTO, LANUS = 7, 8, 9
NOMBRES = {RIVER: ("River Plate", "RIV", "river"), SARMIENTO: ("Sarmiento", "SAR", "sarmiento"),
           LANUS: ("Lanús", "LAN", "lanus")}


def partido(pid, local_id, visit_id, estado, gl=None, gv=None, fase="zona", **kw):
    l, v = NOMBRES[local_id], NOMBRES[visit_id]
    base = dict(id=pid, fase=fase, instancia="group-stage", fecha_nro=pid, torneo="clausura", estado=estado,
                goles_local=gl, goles_visitante=gv, pen_local=None, pen_visitante=None, hora_local=None,
                local_id=local_id, visitante_id=visit_id, local=l[0], local_abrev=l[1], local_slug=l[2],
                visitante=v[0], visitante_abrev=v[1], visitante_slug=v[2])
    return {**base, **kw}


PARTIDOS = [
    partido(1, RIVER, SARMIENTO, "finalizado", 2, 0),       # G de local
    partido(2, LANUS, RIVER, "finalizado", 1, 1),           # E de visitante
    partido(3, SARMIENTO, RIVER, "finalizado", 2, 1),       # P de visitante
    partido(4, RIVER, LANUS, "programado", hora_local=datetime(2026, 10, 7, 20, 0)),
]


def test_forma_proximo_y_ultimos():
    r = resumen.resumen(PARTIDOS, RIVER)
    assert r["forma"] == ["G", "E", "P"]
    assert r["proximo"]["rival"]["equipo"] == "Lanús" and r["proximo"]["es_local"]
    assert [v["id"] for v in r["ultimos"]] == [3, 2, 1]
    assert r["ultimos"][0]["marcador"] == "2 - 1"            # en orden de partido, no del club


def test_local_y_visitante():
    c = resumen.resumen(PARTIDOS, RIVER)["condicion"]
    assert c["local"] == dict(pj=1, pg=1, pe=0, pp=0, gf=2, gc=0, pts=3)
    assert c["visitante"] == dict(pj=2, pg=0, pe=1, pp=1, gf=2, gc=3, pts=1)


def test_postergado_no_es_proximo():
    r = resumen.resumen(PARTIDOS[:1] + [partido(9, SARMIENTO, RIVER, "postergado")], RIVER)
    assert r["proximo"] is None and r["fixture"][1]["marcador"] == "Postergado"


def test_playoff_con_penales_y_etiqueta():
    p = partido(5, RIVER, LANUS, "finalizado", 1, 1, fase="playoff", instancia="round-of-16",
                pen_local=4, pen_visitante=3)
    v = resumen.vista(p, RIVER)
    assert v["marcador"] == "1 - 1 (4-3 p)" and v["etiqueta"] == "Octavos" and v["resultado"] == "E"


def test_sin_partidos():
    r = resumen.resumen([], RIVER)
    assert r["proximo"] is None and r["forma"] == [] and r["condicion"]["local"]["pj"] == 0


# ---------------------------------------------------------------- pagina
import pytest
from fastapi.testclient import TestClient

from app.core import db
from app.core.config import settings
from app.main import app
from app.modules.club import queries as club_q
from tests.test_app import falsa

EQUIPO = {"id": RIVER, "equipo": "River Plate", "abrev": "RIV", "zona": "A", "slug": "river"}


@pytest.fixture()
def cli(monkeypatch):
    monkeypatch.setattr(db, "consultar", falsa)
    monkeypatch.setattr(club_q, "equipo_por_slug", lambda s: EQUIPO if s == "river" else None)
    monkeypatch.setattr(club_q, "partidos_equipo", lambda eid, anio: PARTIDOS)
    monkeypatch.setattr(club_q, "top_equipo", lambda tid, eid, tipo, limite=5: [
        {"pos": 1, "jugador": "J. Candia", "goles": 7, "asistencias": 2}])
    return TestClient(app)


def test_pagina_de_club(cli, monkeypatch):
    monkeypatch.setattr(settings, "sitio_url", "https://ejemplo.com")
    r = cli.get("/club/river")
    assert r.status_code == 200
    t = r.text
    assert "River Plate" in t and "Próximo partido" in t and "07/10 20:00" in t
    assert "1.º de 1 en la Zona A" in t and "J. Candia" in t
    assert '<link rel="canonical" href="https://ejemplo.com/club/river">' in t
    assert "forma-g" in t and "res-p" in t


def test_club_inexistente(cli):
    assert cli.get("/club/nadie").status_code == 404


def test_sitemap_incluye_los_clubes(cli):
    assert "/club/river</loc>" in cli.get("/sitemap.xml").text


def test_el_escudo_linkea_al_club(cli, monkeypatch):
    from app.modules.torneo import queries as torneo_q
    f = dict(pj=2, pg=0, pe=0, pp=0, gf=0, gc=0, dg=0)
    monkeypatch.setattr(torneo_q, "tabla_anual", lambda tid: [
        {"equipo": "Racing Club", "abrev": "RAC", "slug": "racing", "pts": 6, **f}])
    assert 'href="/club/racing"' in cli.get("/torneo/anual").text
    assert 'href="/club/' not in cli.get("/torneo/playoffs").text    # sin slug en los datos falsos, no hay link roto


def test_tarjeta_mi_club(cli):
    t = cli.get("/parcial/club/river").text
    assert "MI CLUB" in t and "Próximo partido" in t and "07/10 20:00" in t
    assert "data-mi-club-quitar" in t and 'href="/club/river"' in t and "<html" not in t
    assert cli.get("/parcial/club/nadie").status_code == 404


def test_portada_y_club_tienen_los_ganchos_de_mi_club(cli):
    home = cli.get("/").text
    assert 'id="mi-club"' in home and "mi_club.js" in home
    assert 'data-mi-club="river"' in cli.get("/club/river").text

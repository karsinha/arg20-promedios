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

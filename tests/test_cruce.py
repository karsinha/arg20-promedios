import importlib.util
from pathlib import Path

ruta = Path(__file__).resolve().parent.parent / "scripts" / "checks" / "cruce_tabla.py"
spec = importlib.util.spec_from_file_location("cruce_tabla", ruta)
cruce = importlib.util.module_from_spec(spec); spec.loader.exec_module(cruce)


def fila(nombre, zona, pj, pts, gf, gc):
    return dict(nombre=nombre, zona=zona, pj=pj, pg=0, pe=0, pp=0, gf=gf, gc=gc, dg=gf - gc, pts=pts)


DB = {1: fila("A", "A", 5, 10, 8, 3), 2: fila("B", "A", 5, 10, 6, 3), 3: fila("C", "B", 5, 4, 2, 5)}


def test_todo_igual():
    ext = {k: {"pj": f["pj"], "pts": f["pts"], "gf": f["gf"]} for k, f in DB.items()}
    difs, solo_db, solo_ext, campos = cruce.comparar(DB, ext)
    assert not difs and not solo_db and not solo_ext and campos == {"pj", "pts", "gf"}


def test_detecta_diferencias_y_faltantes():
    ext = {1: {"pj": 5, "pts": 9}, 2: {"pj": 5, "pts": 10}, 9: {"pj": 1, "pts": 1}}
    difs, solo_db, solo_ext, _ = cruce.comparar(DB, ext)
    assert difs == [(1, "pts", 10, 9)] and solo_db == {3} and solo_ext == {9}


def test_orden_por_zona_y_desempate():
    # A y B empatan en puntos: nuestro criterio pone primero a A (mejor DG)
    assert cruce.comparar_orden(DB, {1: 1, 2: 2, 3: 1}) == ([], None)
    difs, _ = cruce.comparar_orden(DB, {1: 2, 2: 1, 3: 1})
    assert sorted(difs) == [(1, 1, 2), (2, 2, 1)]


def test_orden_global_se_omite():
    difs, motivo = cruce.comparar_orden(DB, {1: 1, 2: 2, 3: 30})
    assert difs == [] and "global" in motivo


def test_filas_bsd_en_distintas_formas():
    plana = [{"team_id": 7, "played": 3}]
    anidada = [{"team": {"id": 7, "name": "X"}, "stats": {"played": 3}}]
    por_zona = [{"group_name": "Group A", "teams": anidada}, {"group_name": "Group B", "teams": [{"team_id": 8}]}]
    assert [cruce.id_equipo(f) for f in cruce.aplanar_filas(plana)] == [7]
    assert [cruce.id_equipo(f) for f in cruce.aplanar_filas(anidada)] == [7]
    assert [cruce.id_equipo(f) for f in cruce.aplanar_filas(por_zona)] == [7, 8]
    assert cruce.primero(cruce.plano(anidada[0]), cruce.NOMBRES_BSD["pj"]) == 3


def test_buscar_filas_ignora_descriptores_y_encuentra_zonas():
    resp = {"season": {"id": 1}, "zones": [{"key": "playoff", "label": "Playoffs", "from": 1, "to": 8}],
            "standings": {"Group A": [{"team_id": 1, "pts": 5}, {"team": {"id": 2}, "stats": {"points": 4}}],
                          "Group B": [{"team_id": 3, "pts": 1}]}}
    halladas = cruce.buscar_filas(resp)
    assert sorted(cruce.id_equipo(f) for _, f in halladas) == [1, 2, 3]
    assert {r for r, _ in halladas} == {"standings.Group A[]", "standings.Group B[]"}
    assert cruce.buscar_filas({"zones": [{"key": "playoff"}]}) == []
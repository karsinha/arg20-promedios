from decimal import Decimal

from app.modules.torneo import descenso


def tabla(*pts):
    return [{"equipo": f"E{i}", "pts": p} for i, p in enumerate(pts)]


def test_baja_el_ultimo():
    r = descenso.marcar(tabla(30, 20, 10), "pts")
    assert [f["descenso"] for f in r] == [False, False, True]
    assert [f["pos"] for f in r] == [1, 2, 3]
    assert not any(f["empate_descenso"] for f in r)


def test_empate_en_el_corte_marca_a_los_empatados():
    r = descenso.marcar(tabla(30, 12, 12, 12), "pts")
    assert [f["descenso"] for f in r] == [False, False, False, True]
    assert [f["empate_descenso"] for f in r] == [False, True, True, True]


def test_empate_lejos_del_corte_no_cuenta():
    r = descenso.marcar(tabla(30, 30, 20, 10), "pts")
    assert not any(f["empate_descenso"] for f in r)


def test_margen():
    assert descenso.margen(tabla(30, 20, 14), "pts") == 6
    assert descenso.margen(tabla(5), "pts") is None


def test_promedios_con_decimal():
    filas = [{"promedio": Decimal("1.200")}, {"promedio": Decimal("1.100")}]
    assert descenso.margen(filas, "promedio") == Decimal("0.100")


def test_tabla_vacia_o_de_un_equipo():
    assert descenso.marcar([], "pts") == []
    assert not descenso.marcar(tabla(5), "pts")[0]["descenso"]
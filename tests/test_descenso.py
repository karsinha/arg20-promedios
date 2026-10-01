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

def test_estados_anual_con_partidos_restantes():
    filas = [{"abrev": a, "pts": p} for a, p in (("A", 60), ("B", 40), ("C", 10))]
    mins, maxs = descenso.cotas_pts(filas, {"A": 2, "B": 2, "C": 2})
    # C llega a 16 como mucho: ni A ni B pueden caer debajo; C no alcanza a nadie.
    assert descenso.estados(mins, maxs) == ["salvado", "salvado", "condenado"]


def test_estados_sin_nada_definido_y_empate_exacto():
    filas = [{"abrev": a, "pts": p} for a, p in (("A", 20), ("B", 19), ("C", 18))]
    mins, maxs = descenso.cotas_pts(filas, {"A": 10, "B": 10, "C": 10})
    assert descenso.estados(mins, maxs) == [None, None, None]
    # empatados en puntos y sin partidos por jugar: se define por desempate, no por la tabla
    filas = [{"abrev": "A", "pts": 30}, {"abrev": "B", "pts": 30}]
    mins, maxs = descenso.cotas_pts(filas, {})
    assert descenso.estados(mins, maxs) == [None, None]


def test_estados_promedios_con_fracciones_exactas():
    from fractions import Fraction

    def fila(a, p24, p25, p26, pj):
        return {"abrev": a, "pts_2024": p24, "pts_2025": p25, "pts_2026": p26, "pj": pj}

    filas = [fila("A", 50, 50, 20, 70), fila("B", 30, 30, 10, 70)]
    mins, maxs = descenso.cotas_promedio(filas, {"A": 1, "B": 1})
    assert mins[0] == Fraction(120, 71) and maxs[0] == Fraction(123, 71) and maxs[1] == Fraction(73, 71)
    assert descenso.estados(mins, maxs) == ["salvado", "condenado"]


def test_estados_sin_zona():
    assert descenso.estados([], []) == []
    assert descenso.estados([1], [4]) == [None]

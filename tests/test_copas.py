from app.modules.torneo import copas


def tabla(n):
    return [{"equipo": f"E{i}", "descenso": i == n} for i in range(1, n + 1)]


def zonas(filas):
    return [f["copa"] for f in filas]


def test_sin_campeones():
    r = copas.asignar(tabla(12), {})
    assert zonas(r) == ["libertadores"] * 3 + ["sudamericana"] * 6 + [None] * 3
    assert not any(f["titulo"] for f in r)


def test_campeon_entre_los_tres_pasa_el_cupo_al_siguiente():
    r = copas.asignar(tabla(12), {"E2": ["Apertura"]})
    assert zonas(r) == ["libertadores"] * 4 + ["sudamericana"] * 6 + [None] * 2
    assert r[1]["titulo"] == "Campeón Apertura"


def test_campeon_fuera_de_los_tres_entra_por_titulo():
    r = copas.asignar(tabla(12), {"E8": ["Clausura"]})
    assert r[7]["copa"] == "libertadores" and r[7]["titulo"] == "Campeón Clausura"
    assert zonas(r)[:3] == ["libertadores"] * 3
    assert sum(1 for f in r if f["copa"] == "sudamericana") == 6
    assert r[8]["copa"] == "sudamericana" and r[10]["copa"] is None


def test_campeon_de_los_dos_torneos():
    r = copas.asignar(tabla(12), {"E2": ["Apertura", "Clausura"]})
    assert r[1]["titulo"] == "Campeón Apertura y Clausura"


def test_el_descenso_no_recibe_copa():
    r = copas.asignar(tabla(5), {})
    assert zonas(r) == ["libertadores"] * 3 + ["sudamericana", None]
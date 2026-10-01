from app.modules.torneo import playoffs


def zona(*nombres):
    return [{"equipo": n, "abrev": n[:3].upper()} for n in nombres]


APERTURA_2026 = {
    "A": zona("Estudiantes (LP)", "Boca Juniors", "Vélez Sarsfield", "Talleres", "Independiente",
              "Lanús", "San Lorenzo", "Unión", "Instituto"),
    "B": zona("Independiente Rivadavia", "River Plate", "Argentinos Juniors", "Rosario Central", "Belgrano",
              "Gimnasia (LP)", "Huracán", "Racing Club", "Barracas Central"),
}


def test_octavos_reproducen_el_apertura_2026():
    cruces = [(c["local"]["equipo"], c["visitante"]["equipo"]) for c in playoffs.octavos(APERTURA_2026)]
    assert cruces == [
        ("Estudiantes (LP)", "Racing Club"), ("Rosario Central", "Independiente"),
        ("River Plate", "San Lorenzo"), ("Vélez Sarsfield", "Gimnasia (LP)"),
        ("Independiente Rivadavia", "Unión"), ("Talleres", "Belgrano"),
        ("Boca Juniors", "Huracán"), ("Argentinos Juniors", "Lanús"),
    ]


def test_zona_incompleta_deja_el_casillero_vacio():
    c = playoffs.octavos({"A": zona("X"), "B": []})
    assert c[0]["local"]["equipo"] == "X" and c[0]["visitante"] is None


def pj(inst, l, v, gl, gv, pl=None, pv=None):
    return {"instancia": inst, "estado": "finalizado", "local": l, "local_abrev": l[:3].upper(),
            "visitante": v, "visitante_abrev": v[:3].upper(), "goles_local": gl, "goles_visitante": gv,
            "pen_local": pl, "pen_visitante": pv, "hora_local": None}


def test_cuadro_real_del_apertura_2026():
    o, c = "round-of-16", "quarterfinals"
    jugados = [
        pj(o, "Talleres", "Belgrano", 0, 1), pj(o, "Boca Juniors", "Huracán", 2, 3),
        pj(o, "Independiente Rivadavia", "Unión", 1, 2), pj(o, "Argentinos Juniors", "Lanús", 2, 0),
        pj(o, "Rosario Central", "Independiente", 3, 1), pj(o, "Estudiantes (LP)", "Racing Club", 0, 1),
        pj(o, "River Plate", "San Lorenzo", 2, 2, 4, 3), pj(o, "Vélez Sarsfield", "Gimnasia (LP)", 0, 1),
        pj(c, "Belgrano", "Unión", 2, 0), pj(c, "Argentinos Juniors", "Huracán", 1, 0),
        pj(c, "Rosario Central", "Racing Club", 2, 1), pj(c, "River Plate", "Gimnasia (LP)", 2, 0),
        pj("semifinals", "River Plate", "Rosario Central", 1, 0),
        pj("semifinals", "Argentinos Juniors", "Belgrano", 1, 1, 3, 4),   # penales ilustrativos
        pj("final", "River Plate", "Belgrano", 2, 3),
    ]
    rondas = playoffs.cuadro(APERTURA_2026, jugados)
    assert [len(r) for r in rondas] == [8, 4, 2, 1]
    assert rondas[0][2]["marcador"] == "2 - 2 (4-3 p)" and rondas[0][2]["ganador"]["equipo"] == "River Plate"
    assert rondas[-1][0]["ganador"]["equipo"] == "Belgrano"


def test_empate_sin_penales_no_define_ganador():
    p = pj("round-of-16", "A", "B", 1, 1)
    assert playoffs._ganador(p) is None
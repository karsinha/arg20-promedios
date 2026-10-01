"""Cupos a copas desde la tabla Anual (funcion pura).

Esquema (a confirmar con el reglamento): los campeones del Apertura y del Clausura van a la Libertadores y,
ademas, los 3 mejores de la Anual que no sean campeones. Los 6 siguientes van a la Sudamericana.
"""

LIBERTADORES = 3
SUDAMERICANA = 6


def asignar(filas: list[dict], campeones: dict[str, list[str]],
            libertadores: int = LIBERTADORES, sudamericana: int = SUDAMERICANA) -> list[dict]:
    """filas: tabla Anual ordenada y ya marcada con `descenso`. campeones: {equipo: ["Apertura", ...]}.

    Devuelve copias con `copa` ('libertadores' | 'sudamericana' | None) y `titulo` ('Campeón Apertura' | None).
    Un campeon entra por titulo y no gasta un cupo de la tabla: ese cupo pasa al siguiente."""
    lib, sud, res = libertadores, sudamericana, []
    for f in filas:
        titulos = campeones.get(f["equipo"], [])
        copa = None
        if titulos:
            copa = "libertadores"
        elif f.get("descenso"):
            pass
        elif lib > 0:
            copa, lib = "libertadores", lib - 1
        elif sud > 0:
            copa, sud = "sudamericana", sud - 1
        res.append({**f, "copa": copa, "titulo": ("Campeón " + " y ".join(titulos)) if titulos else None})
    return res
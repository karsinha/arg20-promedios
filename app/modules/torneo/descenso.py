"""Zona de descenso: funciones puras sobre una tabla ya ordenada de mejor a peor.

Hay un descenso por tabla (Anual y Promedios). En la Anual, un empate de puntos en la zona se define
por partido de desempate (art. 26.2), no por diferencia de gol; en Promedios el criterio no esta confirmado.
"""

CUPOS = 1


def marcar(filas: list[dict], clave: str, cupos: int = CUPOS) -> list[dict]:
    """Copia de las filas con `pos`, `descenso` y `empate_descenso`.

    Descienden los ultimos `cupos`. Si el ultimo que se salva empata en `clave` con el primero que desciende,
    todos los que tienen ese valor quedan con empate_descenso=True."""
    n = len(filas)
    corte = n - cupos
    hay_zona = n > cupos
    res = [{**f, "pos": i + 1, "descenso": hay_zona and i >= corte, "empate_descenso": False}
           for i, f in enumerate(filas)]
    if hay_zona and corte >= 1 and filas[corte - 1][clave] == filas[corte][clave]:
        valor = filas[corte][clave]
        for r in res:
            r["empate_descenso"] = r[clave] == valor
    return res


def margen(filas: list[dict], clave: str, cupos: int = CUPOS):
    """Distancia entre el primero que se salva y el primero que desciende (None si no hay zona)."""
    n = len(filas)
    if n <= cupos:
        return None
    return filas[n - cupos - 1][clave] - filas[n - cupos][clave]
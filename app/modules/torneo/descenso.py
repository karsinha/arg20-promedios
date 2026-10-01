"""Zona de descenso: funciones puras sobre una tabla ya ordenada de mejor a peor.

Hay un descenso por tabla (Anual y Promedios). En la Anual, un empate de puntos en la zona se define
por partido de desempate (art. 26.2), no por diferencia de gol; en Promedios el criterio no esta confirmado.
"""

from fractions import Fraction

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

def cotas_pts(filas: list[dict], restantes: dict[str, int]):
    """(minimos, maximos) de los puntos finales de cada fila de la Anual.
    El minimo es lo que ya suma; el maximo, lo que suma si gana todo lo que le falta. restantes: {abrev: partidos}."""
    minimos = [Fraction(int(f["pts"])) for f in filas]
    maximos = [Fraction(int(f["pts"]) + 3 * restantes.get(f["abrev"], 0)) for f in filas]
    return minimos, maximos


def cotas_promedio(filas: list[dict], restantes: dict[str, int]):
    """(minimos, maximos) del promedio final: pierde todo lo que falta / gana todo lo que falta.
    Los partidos que faltan suman al denominador en los dos casos."""
    minimos, maximos = [], []
    for f in filas:
        pts = int(f["pts_2024"]) + int(f["pts_2025"]) + int(f["pts_2026"])
        r = restantes.get(f["abrev"], 0)
        den = int(f["pj"]) + r
        minimos.append(Fraction(pts, den) if den else Fraction(0))
        maximos.append(Fraction(pts + 3 * r, den) if den else Fraction(0))
    return minimos, maximos


def estados(minimos: list, maximos: list, cupos: int = CUPOS) -> list:
    """Por fila: 'salvado', 'condenado' o None (todavia no esta matematicamente definido).

    Salvado: aun perdiendo todo, queda estrictamente por encima de al menos `cupos` equipos que ganen todo.
    Condenado: aun ganando todo, queda estrictamente por debajo de todos salvo `cupos - 1`... es decir, de al menos
    n - cupos equipos que pierdan todo. Las desigualdades son estrictas: un empate se define por partido de desempate."""
    n = len(minimos)
    if n <= cupos:
        return [None] * n
    res = []
    for i in range(n):
        debajo = sum(1 for j in range(n) if j != i and maximos[j] < minimos[i])
        encima = sum(1 for j in range(n) if j != i and minimos[j] > maximos[i])
        res.append("salvado" if debajo >= cupos else "condenado" if encima >= n - cupos else None)
    return res

"""Zona de descenso: funciones puras sobre una tabla ya ordenada de mejor a peor.

Hay un descenso por tabla (Anual y Promedios). En la Anual, un empate de puntos en la zona se define
por partido de desempate (art. 26.2), no por diferencia de gol; en Promedios el criterio no esta confirmado.
"""

from fractions import Fraction

CUPOS = 1


def marcar(filas: list[dict], clave: str, cupos: int = CUPOS, excluidos=frozenset()) -> list[dict]:
    """Copia de las filas con `pos`, `descenso`, `descenso_promedio` y `empate_descenso`.

    `excluidos`: abreviaturas que ya descienden por otra tabla (en la Anual, el peor promedio). No ocupan lugar:
    descienden los ultimos `cupos` de los que quedan. Si el ultimo que se salva empata en `clave` con el primero
    que desciende, todos los que tienen ese valor quedan con empate_descenso=True."""
    pool = [i for i, f in enumerate(filas) if f.get("abrev") not in excluidos]
    n = len(pool)
    corte = n - cupos
    hay_zona = n > cupos
    bajan = set(pool[corte:]) if hay_zona else set()
    res = [{**f, "pos": i + 1, "descenso": i in bajan, "descenso_promedio": f.get("abrev") in excluidos,
            "empate_descenso": False} for i, f in enumerate(filas)]
    if hay_zona and corte >= 1 and filas[pool[corte - 1]][clave] == filas[pool[corte]][clave]:
        valor = filas[pool[corte]][clave]
        for r in res:
            r["empate_descenso"] = r[clave] == valor and not r["descenso_promedio"]
    return res


def margen(filas: list[dict], clave: str, cupos: int = CUPOS, excluidos=frozenset()):
    """Distancia entre el primero que se salva y el primero que desciende, sin contar a los excluidos."""
    pool = [f for f in filas if f.get("abrev") not in excluidos]
    n = len(pool)
    if n <= cupos:
        return None
    return pool[n - cupos - 1][clave] - pool[n - cupos][clave]


def traspaso(filas: list[dict], clave: str, excluidos=frozenset()):
    """Si el que baja por otra tabla era justo el que bajaba aca, devuelve {'sale', 'entra'} (nombres); si no, None."""
    if not excluidos:
        return None
    sale = next((f for f in marcar(filas, clave) if f["descenso"] and f["abrev"] in excluidos), None)
    entra = next((f for f in marcar(filas, clave, excluidos=excluidos) if f["descenso"]), None)
    return {"sale": sale["equipo"], "entra": entra["equipo"]} if sale and entra else None


def estados_anual(abrevs: list[str], minimos: list, maximos: list, prom_condenados: set, prom_salvados: set) -> list:
    """Estados de la Anual teniendo en cuenta que el que baja por promedio sale del pool. Un solo descenso por tabla.

    Condenado: baja por promedio, o es el ultimo del pool aun sin contar a los condenados por promedio.
    Salvado: tiene >= 2 equipos seguros por debajo (uno solo podria bajar por promedio y dejarlo ultimo),
    o 1 que ya esta salvado en Promedios (seguira en el pool)."""
    n = len(abrevs)
    res = []
    for i, a in enumerate(abrevs):
        if n <= 1:
            res.append(None)
            continue
        if a in prom_condenados:
            res.append("condenado")
            continue
        otros = [j for j in range(n) if j != i and abrevs[j] not in prom_condenados]
        debajo = [abrevs[j] for j in range(n) if j != i and maximos[j] < minimos[i]]
        if otros and all(minimos[j] > maximos[i] for j in otros):
            res.append("condenado")
        elif len(debajo) >= 2 or any(d in prom_salvados for d in debajo):
            res.append("salvado")
        else:
            res.append(None)
    return res

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

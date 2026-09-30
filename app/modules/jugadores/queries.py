from app.core import db

# Columna principal y de desempate segun el ranking. Lista blanca: estos nombres se interpolan en el SQL.
COLUMNAS = {"goles": ("goles", "asistencias"), "asistencias": ("asistencias", "goles")}


def _top(vista: str, clave: str, valor: int, tipo: str, limite: int) -> list[dict]:
    a, b = COLUMNAS[tipo]
    return db.consultar(
        f"""SELECT RANK() OVER (ORDER BY v.{a} DESC, v.{b} DESC) AS pos,
                   v.nombre AS jugador, COALESCE(e.nombre_corto, e.nombre) AS equipo,
                   v.goles, v.asistencias
            FROM {vista} v JOIN equipo e ON e.id = v.equipo_id
            WHERE v.{clave} = %s AND v.{a} > 0
            ORDER BY pos, v.nombre LIMIT %s""", (valor, limite))


def top_torneo(torneo_id: int, tipo: str, limite: int = 10) -> list[dict]:
    return _top("v_stats_jugador_torneo", "torneo_id", torneo_id, tipo, limite)


def top_anual(temporada_id: int, tipo: str, limite: int = 10) -> list[dict]:
    return _top("v_stats_jugador_anual", "temporada_id", temporada_id, tipo, limite)

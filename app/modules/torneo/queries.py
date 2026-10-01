from app.core import db

# Nombre y abreviatura para mostrar: los propios si existen (scripts/equipos_abreviaturas.py), si no un fallback.
_EQ = "COALESCE(e.nombre_corto, e.nombre) AS equipo, COALESCE(e.abreviatura, UPPER(LEFT(e.nombre, 3))) AS abrev"


def tabla_torneo(torneo_id: int) -> list[dict]:
    # Desempates: pts, dg, gf (verificar con el reglamento de la AFA).
    return db.consultar(
        f"""SELECT v.zona_2026 AS zona, v.pj, v.pg, v.pe, v.pp, v.gf, v.gc, v.dg, v.pts, {_EQ}
            FROM v_tabla_torneo v JOIN equipo e ON e.id = v.equipo_id
            WHERE v.torneo_id = %s
            ORDER BY v.zona_2026, v.pts DESC, v.dg DESC, v.gf DESC, e.nombre""", (torneo_id,))


def tabla_anual(temporada_id: int) -> list[dict]:
    return db.consultar(
        f"""SELECT v.pj, v.pg, v.pe, v.pp, v.gf, v.gc, v.dg, v.pts, {_EQ}
            FROM v_tabla_anual v JOIN equipo e ON e.id = v.equipo_id
            WHERE v.temporada_id = %s
            ORDER BY v.pts DESC, v.dg DESC, v.gf DESC, e.nombre""", (temporada_id,))


def tabla_promedios() -> list[dict]:
    return db.consultar(
        f"""SELECT v.pts_2024, v.pts_2025, v.pts_2026, v.pj, v.promedio, {_EQ}
            FROM v_promedios v JOIN equipo e ON e.id = v.equipo_id
            ORDER BY v.promedio DESC, v.pts_2026 DESC, e.nombre""")


def fechas(torneo_id: int) -> list[int]:
    filas = db.consultar(
        """SELECT DISTINCT fecha_nro FROM partido
           WHERE torneo_id = %s AND fase = 'zona' AND fecha_nro IS NOT NULL
           ORDER BY fecha_nro""", (torneo_id,))
    return [f["fecha_nro"] for f in filas]


def fecha_inicial(torneo_id: int) -> int | None:
    """Fecha del proximo partido programado; si no queda ninguno, la ultima."""
    filas = db.consultar(
        """SELECT COALESCE(
             (SELECT fecha_nro FROM partido
               WHERE torneo_id = %s AND fase = 'zona' AND estado = 'programado'
                 AND NOT reprogramado AND fecha_nro IS NOT NULL
               ORDER BY fecha_hora LIMIT 1),
             (SELECT MAX(fecha_nro) FROM partido WHERE torneo_id = %s AND fase = 'zona')) AS fecha""",
        (torneo_id, torneo_id))
    return filas[0]["fecha"] if filas else None


def partidos(torneo_id: int, fecha: int) -> list[dict]:
    # NOT reprogramado: oculta el original postergado cuando ya existe el reemplazo.
    return db.consultar(
        """SELECT p.id, p.estado::text AS estado, p.goles_local, p.goles_visitante,
                  p.fecha_hora AT TIME ZONE 'America/Argentina/Buenos_Aires' AS hora_local,
                  COALESCE(l.nombre_corto, l.nombre) AS local,
                  COALESCE(l.abreviatura, UPPER(LEFT(l.nombre, 3))) AS local_abrev,
                  COALESCE(v.nombre_corto, v.nombre) AS visitante,
                  COALESCE(v.abreviatura, UPPER(LEFT(v.nombre, 3))) AS visitante_abrev
           FROM partido p JOIN equipo l ON l.id = p.local_id JOIN equipo v ON v.id = p.visitante_id
           WHERE p.torneo_id = %s AND p.fase = 'zona' AND p.fecha_nro = %s AND NOT p.reprogramado
           ORDER BY p.fecha_hora, p.id""", (torneo_id, fecha))


def playoffs(torneo_id: int) -> list[dict]:
    return db.consultar(
        """SELECT p.instancia, p.estado::text AS estado, p.goles_local, p.goles_visitante,
                  p.pen_local, p.pen_visitante,
                  p.fecha_hora AT TIME ZONE 'America/Argentina/Buenos_Aires' AS hora_local,
                  COALESCE(l.nombre_corto, l.nombre) AS local,
                  COALESCE(l.abreviatura, UPPER(LEFT(l.nombre, 3))) AS local_abrev,
                  COALESCE(v.nombre_corto, v.nombre) AS visitante,
                  COALESCE(v.abreviatura, UPPER(LEFT(v.nombre, 3))) AS visitante_abrev
           FROM partido p JOIN equipo l ON l.id = p.local_id JOIN equipo v ON v.id = p.visitante_id
           WHERE p.torneo_id = %s AND p.fase = 'playoff' AND NOT p.reprogramado
           ORDER BY p.fecha_hora, p.id""", (torneo_id,))




def ultima_actualizacion():
    """Hora (Argentina) de la ultima vez que el sync toco un partido."""
    filas = db.consultar(
        """SELECT MAX(actualizado_en) AT TIME ZONE 'America/Argentina/Buenos_Aires' AS ultima FROM partido""")
    return filas[0]["ultima"] if filas else None
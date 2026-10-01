from app.core import db
from app.modules.jugadores.queries import COLUMNAS


def equipo_por_slug(slug: str) -> dict | None:
    filas = db.consultar(
        """SELECT e.id, COALESCE(e.nombre_corto, e.nombre) AS equipo,
                  COALESCE(e.abreviatura, UPPER(LEFT(e.nombre, 3))) AS abrev,
                  e.zona_2026 AS zona, e.slug
           FROM equipo e WHERE e.slug = %s""", (slug,))
    return filas[0] if filas else None


def partidos_equipo(equipo_id: int, anio: int) -> list[dict]:
    """Todos los partidos del equipo en la temporada (zona y playoffs), sin el original de un postergado ya reprogramado."""
    return db.consultar(
        """SELECT p.id, p.fase::text AS fase, p.instancia, p.fecha_nro, t.tipo::text AS torneo,
                  p.estado::text AS estado, p.goles_local, p.goles_visitante, p.pen_local, p.pen_visitante,
                  p.fecha_hora AT TIME ZONE 'America/Argentina/Buenos_Aires' AS hora_local,
                  p.local_id, p.visitante_id,
                  COALESCE(l.nombre_corto, l.nombre) AS local,
                  COALESCE(l.abreviatura, UPPER(LEFT(l.nombre, 3))) AS local_abrev, l.slug AS local_slug,
                  COALESCE(v.nombre_corto, v.nombre) AS visitante,
                  COALESCE(v.abreviatura, UPPER(LEFT(v.nombre, 3))) AS visitante_abrev, v.slug AS visitante_slug
           FROM partido p
           JOIN torneo t ON t.id = p.torneo_id JOIN temporada te ON te.id = t.temporada_id
           JOIN equipo l ON l.id = p.local_id JOIN equipo v ON v.id = p.visitante_id
           WHERE te.anio = %s AND NOT p.reprogramado AND (p.local_id = %s OR p.visitante_id = %s)
           ORDER BY p.fecha_hora, p.id""", (anio, equipo_id, equipo_id))


def top_equipo(temporada_id: int, equipo_id: int, tipo: str, limite: int = 5) -> list[dict]:
    a, b = COLUMNAS[tipo]       # lista blanca: se interpolan en el SQL
    return db.consultar(
        f"""SELECT RANK() OVER (ORDER BY v.{a} DESC, v.{b} DESC) AS pos,
                   v.nombre AS jugador, v.goles, v.asistencias
            FROM v_stats_jugador_anual v
            WHERE v.temporada_id = %s AND v.equipo_id = %s AND v.{a} > 0
            ORDER BY pos, v.nombre LIMIT %s""", (temporada_id, equipo_id, limite))

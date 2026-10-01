"""Que torneo/temporada corresponde a cada pestania del selector."""
from dataclasses import dataclass

from fastapi import HTTPException

from app.core import db

ANIO = 2026
ETIQUETAS = {"clausura": "Clausura", "apertura": "Apertura", "anual": "Anual", "promedios": "Promedios",
             "playoffs": "Playoffs"}

@dataclass(frozen=True)
class Contexto:
    modo: str
    torneo_id: int      # torneo que alimenta tabla por zonas, fixture y goleadores
    temporada_id: int   # temporada para Anual / Promedios


def resolver(modo: str) -> Contexto:
    if modo not in ETIQUETAS:
        raise HTTPException(404, "Modo desconocido")
    filas = db.consultar(
        """SELECT t.id, t.tipo::text AS tipo, t.temporada_id
           FROM torneo t JOIN temporada te ON te.id = t.temporada_id
           WHERE te.anio = %s""", (ANIO,))
    por_tipo = {f["tipo"]: f for f in filas}
    # Anual y Promedios muestran el fixture y los jugadores del torneo en curso (Clausura).
    base = por_tipo.get("apertura" if modo == "apertura" else "clausura")
    if base is None:
        raise HTTPException(503, "No hay torneos cargados. Correr: make sync")
    return Contexto(modo, base["id"], base["temporada_id"])



def url_modo(modo: str) -> str:
    """URL publica de cada pestania. Clausura es la portada."""
    return "/" if modo == "clausura" else f"/torneo/{modo}"
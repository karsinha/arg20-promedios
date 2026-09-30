"""Pool de conexiones y helpers de consulta. La web solo LEE de la base (escribe sync/)."""
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import settings

pool = ConnectionPool(settings.database_url, min_size=1, max_size=5, open=False,
                      kwargs={"row_factory": dict_row})


def consultar(sql: str, params=None) -> list[dict]:
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchall()

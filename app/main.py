from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core import db
from app.modules import portada
from app.modules.jugadores.router import router as jugadores_router
from app.modules.torneo.router import router as torneo_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.pool.open()
    yield
    db.pool.close()


app = FastAPI(title="Futbol Argentina", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(portada.router)
app.include_router(torneo_router)
app.include_router(jugadores_router)


@app.get("/salud", include_in_schema=False)
def salud():
    db.consultar("SELECT 1")
    return {"ok": True}

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core import db
from app.modules import descenso_pagina, parcial, portada, seo
from app.modules.club import router as club

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.pool.open()
    yield
    db.pool.close()


app = FastAPI(title="Futbol Argentina", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(portada.router)
app.include_router(parcial.router)
app.include_router(seo.router)
app.include_router(club.router)
app.include_router(descenso_pagina.router)


@app.get("/salud", include_in_schema=False)
def salud():
    db.consultar("SELECT 1")
    return {"ok": True}
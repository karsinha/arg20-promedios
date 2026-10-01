from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.modules.torneo import modos

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")
templates.env.globals["url_modo"] = modos.url_modo
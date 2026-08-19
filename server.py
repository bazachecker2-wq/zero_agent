from __future__ import annotations

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from api import app

web = Path(__file__).parent / "web"
app.mount("/", StaticFiles(directory=web, html=True), name="web")

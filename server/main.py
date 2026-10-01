from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .backups.routes import router as backup_router
from .movies.routes import router as movies_router
from .photos.gallery_routes import router as photos_router
from .photos.sidecar_routes import router as sidecar_router
from .photos.trash_routes import router as trash_photos_router
from .photos.upload_routes import router as upload_photos_router
from .trips.routes import router as trips_router
from .trips.trash_routes import router as trip_trash_router
from .fitness.routes import router as fitness_router
from .settings_routes import router as settings_router
from .config import DATA_DIR, MEDIA_DIR

APP_TITLE = "Diary Upload Server"
def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent.parent / relative_path
app = FastAPI(title=APP_TITLE)

# Read-only access to Diary/data for the gallery (served under /files).
# Starlette StaticFiles answers Range requests, which <video> needs in order to seek.
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(DATA_DIR)), name="files")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.include_router(backup_router)
app.include_router(movies_router)
app.include_router(photos_router)
app.include_router(sidecar_router)
app.include_router(trash_photos_router)
app.include_router(upload_photos_router)
app.include_router(trips_router)
app.include_router(trip_trash_router)
app.include_router(fitness_router)
app.include_router(settings_router)


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now().astimezone().isoformat(timespec="seconds")}

FRONTEND_DIR = resource_path("web-dist")

if FRONTEND_DIR.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(FRONTEND_DIR / "assets")),
        name="assets",
    )

    @app.get("/")
    def serve_frontend():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/{full_path:path}")
    def serve_frontend_routes(full_path: str):
        requested_file = FRONTEND_DIR / full_path

        if requested_file.exists() and requested_file.is_file():
            return FileResponse(requested_file)

        return FileResponse(FRONTEND_DIR / "index.html")
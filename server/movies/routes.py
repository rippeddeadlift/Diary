from __future__ import annotations

import mimetypes
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..local_requests import check_local_request
from ..thumbnails import generate_video_poster
from . import repository

router = APIRouter(prefix="/api/movies", tags=["movies"])

def _resolve_movie(movie_path: str) -> tuple[Path, Path]:
    root = repository.get_movie_folder()
    if root is None:
        raise HTTPException(status_code=404, detail="Choose a movie folder first")
    candidate = repository.resolve_movie_path(root, movie_path)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return root, candidate


@router.get("")
def list_movies():
    root = repository.get_movie_folder()
    if root is None:
        return {"folder": None, "count": 0, "items": []}

    items = []
    for movie in repository.list_movie_files(root):
        rel = movie.relative_to(root).as_posix()
        encoded = quote(rel, safe="/")
        items.append({
            "path": rel,
            "title": movie.stem,
            "url": f"/api/movies/stream/{encoded}",
            "posterUrl": f"/api/movies/poster/{encoded}",
        })
    items.sort(key=lambda item: item["title"].casefold())
    return {"folder": str(root), "count": len(items), "items": items}


@router.post("/folder")
def set_movie_folder(payload: dict[str, str], request: Request):
    check_local_request(request)
    folder = payload.get("path", "").strip()
    if not folder:
        raise HTTPException(status_code=400, detail="Folder path is required")
    if repository.save_movie_folder(folder) is None:
        raise HTTPException(status_code=400, detail="Folder does not exist")
    return list_movies()


@router.post("/pick-folder")
def pick_movie_folder(request: Request):
    check_local_request(request)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        raise HTTPException(status_code=501, detail="Native folder selection is unavailable; enter a path instead") from None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        current = repository.get_movie_folder()
        selected = filedialog.askdirectory(
            title="Choose your movie folder",
            initialdir=str(current) if current else None,
        )
    finally:
        root.destroy()
    if not selected:
        return {"cancelled": True, **list_movies()}
    if repository.save_movie_folder(selected) is None:
        raise HTTPException(status_code=400, detail="Folder does not exist")
    return list_movies()


@router.get("/poster/{movie_path:path}")
def movie_poster(movie_path: str):
    root, movie = _resolve_movie(movie_path)
    rel = movie.relative_to(root)
    poster = (repository.MOVIE_THUMBS_DIR / f"{rel.as_posix()}.jpg").resolve()
    try:
        poster.relative_to(repository.MOVIE_THUMBS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Poster not found") from None
    generate_video_poster(movie, poster)
    if not poster.is_file():
        raise HTTPException(status_code=404, detail="Could not create movie poster; install ffmpeg")
    return FileResponse(poster, media_type="image/jpeg")


@router.get("/stream/{movie_path:path}")
def stream_movie(movie_path: str):
    _, movie = _resolve_movie(movie_path)
    media_type = mimetypes.guess_type(movie.name)[0] or "application/octet-stream"
    return FileResponse(movie, media_type=media_type, filename=movie.name)


@router.post("/open")
def open_movie(payload: dict[str, str], request: Request):
    check_local_request(request)
    _, movie = _resolve_movie(payload.get("path", ""))
    try:
        if sys.platform == "win32":
            os.startfile(str(movie))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(movie)])
        else:
            subprocess.Popen(["xdg-open", str(movie)])
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not open movie player: {exc}") from exc
    return {"ok": True}

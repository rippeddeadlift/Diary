from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from . import config
from .folder_picker import pick_directory
from .local_requests import check_local_request

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _media_directory_state(selected: Path | None = None) -> dict[str, str | bool]:
    active = config.MEDIA_DIR.resolve()
    selected = selected or config.load_media_dir_setting() or active
    return {
        "path": str(selected),
        "activePath": str(active),
        "restartRequired": selected.resolve() != active,
    }


@router.get("/media-directory")
def get_media_directory(request: Request):
    check_local_request(request)
    return _media_directory_state()


@router.post("/media-directory")
def set_media_directory(payload: dict[str, str], request: Request):
    check_local_request(request)
    path = payload.get("path", "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="Media directory is required")
    try:
        selected = config.save_media_dir_setting(path)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Media directory must be an existing folder") from exc
    return _media_directory_state(selected)


@router.post("/media-directory/pick")
def pick_media_directory(request: Request):
    check_local_request(request)
    initial_dir = config.load_media_dir_setting() or config.MEDIA_DIR
    if not initial_dir.is_dir():
        initial_dir = Path.home()
    try:
        selected = pick_directory("Diary Medienordner auswählen", initial_dir)
    except ImportError as exc:
        raise HTTPException(status_code=501, detail="Native Ordnerauswahl ist nicht verfügbar") from exc
    if selected is None:
        return {"cancelled": True, **_media_directory_state()}
    try:
        saved = config.save_media_dir_setting(selected)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Media directory must be an existing folder") from exc
    return {"cancelled": False, **_media_directory_state(saved)}
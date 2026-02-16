from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, PHOTOS_INBOX_DIR, ROOT
from .models import GalleryItem, GalleryListResponse, UploadResponse, UploadSavedItem
from .photos_repo import (
    batch_folder_name,
    build_sidecar_for_image,
    list_inbox_images,
    load_sidecar,
    save_sidecar,
    sidecar_path_for,
    unique_filename,
)

APP_TITLE = "Diary Upload Server"

app = FastAPI(title=APP_TITLE)

# Read-only access to Diary/data for the gallery (served under /files)
DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(DATA_DIR)), name="files")


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now().astimezone().isoformat(timespec="seconds")}


@app.get("/api/photos/inbox/all", response_model=GalleryListResponse)
def list_inbox_all():
    items: list[GalleryItem] = []

    for img in list_inbox_images():
        rel = img.relative_to(DATA_DIR).as_posix()
        sc_path = sidecar_path_for(img)
        sc = load_sidecar(sc_path) if sc_path.exists() else {}

        created_at = sc.get("createdAt")
        created_src = sc.get("createdAtSource")
        location = sc.get("location")

        missing = not bool(created_at)

        items.append(
            GalleryItem(
                path=rel,
                url=f"/files/{rel}",
                hasSidecar=sc_path.exists(),
                sidecarPath=sc_path.relative_to(DATA_DIR).as_posix() if sc_path.exists() else None,
                createdAt=created_at,
                createdAtSource=created_src,
                location=location,
                missing=missing,
            )
        )

    # Sort: non-missing first, then by createdAt (desc). Missing is always last.
    local_tz = datetime.now().astimezone().tzinfo

    def parse_isoish(s: str):
        try:
            return datetime.fromisoformat(s)
        except Exception:
            return None

    def sort_key(it: GalleryItem):
        is_missing = 1 if it.missing else 0
        dt = parse_isoish(str(it.createdAt or ""))
        if dt is None:
            ts = float("-inf")
        else:
            if dt.tzinfo is None and local_tz is not None:
                dt = dt.replace(tzinfo=local_tz)
            ts = dt.timestamp()
        return (is_missing, -ts)

    items.sort(key=sort_key)

    return GalleryListResponse(count=len(items), items=items)


@app.post("/api/photos/upload", response_model=UploadResponse)
async def upload_photos(files: List[UploadFile] = File(...)):
    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)

    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    saved: list[UploadSavedItem] = []
    for f in files:
        out_name = unique_filename(prefix, f.filename or "upload")
        out_path = batch_dir / out_name

        with out_path.open("wb") as w:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                w.write(chunk)

        sidecar = build_sidecar_for_image(out_path)
        sc_path = sidecar_path_for(out_path)
        save_sidecar(sc_path, sidecar)

        saved.append(
            UploadSavedItem(
                file=str(out_path.relative_to(ROOT)).replace("\\", "/"),
                sidecar=str(sc_path.relative_to(ROOT)).replace("\\", "/"),
                originalName=f.filename,
            )
        )

    return UploadResponse(
        batch=str(batch_dir.relative_to(ROOT)).replace("\\", "/"),
        count=len(saved),
        saved=saved,
    )

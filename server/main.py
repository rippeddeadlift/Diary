from __future__ import annotations

import json
from datetime import datetime
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, PHOTOS_INBOX_DIR, ROOT
from .models import (
    GalleryItem,
    GalleryListResponse,
    SidecarGetResponse,
    SidecarModel,
    SidecarUpdateRequest,
    SidecarUpdateResponse,
    SidecarBulkUpdateRequest,
    SidecarBulkUpdateResponse,
    UploadResponse,
    UploadSavedItem,
)
from .photos_repo import (
    batch_folder_name,
    build_sidecar_for_image,
    list_inbox_images,
    load_or_init_sidecar_for_image,
    resolve_data_path,
    save_sidecar,
    sidecar_path_for,
    unique_filename,
    sort_gallery_items,
    update_sidecar_fields,
    bulk_toggle_sidecar_fields,
    load_sha256_index,
    save_sha256_index,
    sha256_file,
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

    errors: list[dict[str, Any]] = []

    for img in list_inbox_images():
        rel = img.relative_to(DATA_DIR).as_posix()
        sc_path = sidecar_path_for(img)
        sc = load_or_init_sidecar_for_image(img) if sc_path.exists() else {}

        people = sc.get("people") or []
        tags = sc.get("tags") or []
        created_at = sc.get("createdAt")
        created_src = sc.get("createdAtSource")
        location = sc.get("location")

        # Normalize types (defensive: avoid response_model validation 500)
        if not isinstance(people, list):
            people = []
        if not isinstance(tags, list):
            tags = []
        people = [str(x) for x in people if x is not None and str(x).strip()]
        tags = [str(x) for x in tags if x is not None and str(x).strip()]

        if created_at is not None and not isinstance(created_at, str):
            created_at = str(created_at)
        if created_src is not None and not isinstance(created_src, str):
            created_src = str(created_src)

        loc_obj: Any = None
        if isinstance(location, dict) and "lat" in location and "lon" in location:
            try:
                loc_obj = {
                    "lat": float(location["lat"]),
                    "lon": float(location["lon"]),
                    "source": str(location.get("source") or "exif_gps"),
                }
            except Exception:
                loc_obj = None

        missing = not bool(created_at)

        try:
            items.append(
                GalleryItem(
                    path=rel,
                    url=f"/files/{rel}",
                    hasSidecar=sc_path.exists(),
                    sidecarPath=sc_path.relative_to(DATA_DIR).as_posix() if sc_path.exists() else None,
                    people=people,
                    tags=tags,
                    createdAt=created_at,
                    createdAtSource=created_src,
                    location=loc_obj,
                    missing=missing,
                )
            )
        except Exception as e:
            errors.append({"path": rel, "error": str(e)})
            continue

    # Sort: non-missing first, then by createdAt (desc). Missing is always last.
    # Keep the sort logic in photos_repo.
    items_dicts = [it.model_dump() for it in items]
    sort_gallery_items(items_dicts)
    items = [GalleryItem(**d) for d in items_dicts]

    # We don't expose errors in the typed response model; keep count stable.
    # If you need diagnostics, check server logs.
    return GalleryListResponse(count=len(items), items=items)


@app.get("/api/photos/sidecar", response_model=SidecarGetResponse)
def get_sidecar(path: str):
    img = resolve_data_path(path)
    if not img.exists():
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)

    sc_path = sidecar_path_for(img)
    sidecar = load_or_init_sidecar_for_image(img)
    if not sc_path.exists():
        save_sidecar(sc_path, sidecar)

    return SidecarGetResponse(
        path=str(img.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecarPath=str(sc_path.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecar=SidecarModel(**sidecar),
    )


@app.post("/api/photos/sidecar", response_model=SidecarUpdateResponse)
def update_sidecar(req: SidecarUpdateRequest):
    img = resolve_data_path(req.path)
    if not img.exists():
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)

    sc_path = sidecar_path_for(img)
    sidecar = load_or_init_sidecar_for_image(img)
    sidecar = update_sidecar_fields(sidecar, req.people, req.tags, req.caption)
    save_sidecar(sc_path, sidecar)

    return SidecarUpdateResponse(
        path=str(img.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecarPath=str(sc_path.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecar=SidecarModel(**sidecar),
    )


@app.post("/api/photos/sidecar/bulk", response_model=SidecarBulkUpdateResponse)
def bulk_update_sidecars(req: SidecarBulkUpdateRequest):
    updated = 0
    for rel in req.paths:
        try:
            img = resolve_data_path(rel)
        except Exception:
            continue
        if not img.exists():
            continue

        sc_path = sidecar_path_for(img)
        sidecar = load_or_init_sidecar_for_image(img)
        sidecar = bulk_toggle_sidecar_fields(
            sidecar,
            add_people=req.addPeople,
            remove_people=req.removePeople,
            add_tags=req.addTags,
            remove_tags=req.removeTags,
        )
        save_sidecar(sc_path, sidecar)
        updated += 1

    return SidecarBulkUpdateResponse(updated=updated)


@app.post("/api/trips/import-gpx")
def import_gpx():
    """Run GPX import (downloads -> data/trips) and archive originals to data/import/gpx/_done."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "tools.import_gpx_inbox"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    m = re.search(r"Imported:\s*(\d+)\s*GPX", proc.stdout or "")
    imported = int(m.group(1)) if m else None

    if proc.returncode != 0:
        return JSONResponse(
            {"ok": False, "returncode": proc.returncode, "output": out, "imported": imported},
            status_code=500,
        )

    return {"ok": True, "imported": imported, "output": out}


@app.post("/api/photos/upload", response_model=UploadResponse)
async def upload_photos(files: List[UploadFile] = File(...)):
    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)

    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    sha_idx = load_sha256_index()

    saved: list[UploadSavedItem] = []
    for f in files:
        out_name = unique_filename(prefix, f.filename or "upload")
        out_path = batch_dir / out_name

        # 1) Write file to disk
        with out_path.open("wb") as w:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                w.write(chunk)

        # 2) Compute hash and dedupe
        try:
            h = sha256_file(out_path)
        except Exception:
            h = None

        if h and h in sha_idx:
            existing_rel = sha_idx.get(h)
            existing_path = (DATA_DIR / str(existing_rel)).resolve() if existing_rel else None
            if existing_path and existing_path.exists():
                # Duplicate: don't save (remove just-written file)
                try:
                    out_path.unlink(missing_ok=True)
                except Exception:
                    pass
                continue
            else:
                # stale index entry, treat as new
                sha_idx.pop(h, None)

        # 3) Sidecar + index update
        sidecar = build_sidecar_for_image(out_path)
        if h:
            sidecar["sha256"] = h
        sc_path = sidecar_path_for(out_path)
        save_sidecar(sc_path, sidecar)

        if h:
            rel = out_path.relative_to(DATA_DIR).as_posix()
            sha_idx[h] = rel

        saved.append(
            UploadSavedItem(
                file=str(out_path.relative_to(ROOT)).replace("\\", "/"),
                sidecar=str(sc_path.relative_to(ROOT)).replace("\\", "/"),
                originalName=f.filename,
            )
        )

    # Persist hash index
    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass

    return UploadResponse(
        batch=str(batch_dir.relative_to(ROOT)).replace("\\", "/"),
        count=len(saved),
        saved=saved,
    )

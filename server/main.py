from __future__ import annotations

import json
import os
from datetime import datetime
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, List
import zipfile
import tempfile
import shutil

from PIL import Image, ImageOps
import pillow_heif

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import photos_repo
from .backups.routes import router as backup_router
from .movies.routes import router as movies_router
from .photos.routes import router as photos_router
from .config import DATA_DIR, MEDIA_DIR, MEDIA_EXTS, PHOTOS_INBOX_DIR, ROOT
from .thumbnails import ensure_thumb, thumb_path_for

TRASH_DIR = MEDIA_DIR / "photos" / "_trash"
THUMBS_DIR = DATA_DIR / "photos" / "_thumbs"
THUMBS_TRASH_DIR = THUMBS_DIR / "_trash"

TRIPS_DIR = DATA_DIR / "trips"
TRIPS_INDEX = TRIPS_DIR / "index.json"
TRIPS_TRASH_DIR = TRIPS_DIR / "_trash"
TRIPS_MEDIA_DIR = MEDIA_DIR / "trips"
TRIPS_MEDIA_TRASH_DIR = TRIPS_MEDIA_DIR / "_trash"
from .models import (
    FitnessLogRequest,
    FitnessLogResponse,
    SidecarGetResponse,
    SidecarModel,
    SidecarUpdateRequest,
    SidecarUpdateResponse,
    SidecarBulkUpdateRequest,
    SidecarBulkUpdateResponse,
    TrashPhotosRequest,
    TrashPhotosResponse,
    TrashTripsRequest,
    TrashTripsResponse,
    TripMetaUpdateRequest,
    TripMetaUpdateResponse,
    UploadResponse,
    UploadSavedItem,
)
from .photos_repo import (
    batch_folder_name,
    build_sidecar_for_image,
    iter_inbox_images,
    is_live_photo_video_file,
    list_inbox_images,
    newest_inbox_images,
    load_or_init_sidecar_for_image,
    resolve_media_path,
    save_sidecar,
    sidecar_path_for,
    unique_filename,
    sort_gallery_items,
    update_sidecar_fields,
    bulk_toggle_sidecar_fields,
    load_sha256_index,
    save_sha256_index,
    sha256_file,
    GALLERY_ORDER_PATH,
    load_gallery_order,
    save_gallery_order,
    load_gallery_paths,
    save_gallery_paths,
    remember_gallery_items,
    forget_gallery_items,
    sync_missing_gallery_items_once,
    order_sort_key,
)

APP_TITLE = "Diary Upload Server"

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


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now().astimezone().isoformat(timespec="seconds")}


@app.get("/api/photos/sidecar", response_model=SidecarGetResponse)
def get_sidecar(path: str):
    img = resolve_media_path(path)
    if not img.exists():
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)

    sc_path = sidecar_path_for(img)
    sidecar = load_or_init_sidecar_for_image(img)
    if not sc_path.exists():
        save_sidecar(sc_path, sidecar)

    return SidecarGetResponse(
        path=str(img.relative_to(MEDIA_DIR)).replace("\\", "/"),
        sidecarPath=str(sc_path.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecar=SidecarModel(**sidecar),
    )


@app.post("/api/photos/sidecar", response_model=SidecarUpdateResponse)
def update_sidecar(req: SidecarUpdateRequest):
    img = resolve_media_path(req.path)
    if not img.exists():
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)

    sc_path = sidecar_path_for(img)
    sidecar = load_or_init_sidecar_for_image(img)
    sidecar = update_sidecar_fields(sidecar, req.people, req.tags, req.caption)
    save_sidecar(sc_path, sidecar)

    return SidecarUpdateResponse(
        path=str(img.relative_to(MEDIA_DIR)).replace("\\", "/"),
        sidecarPath=str(sc_path.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecar=SidecarModel(**sidecar),
    )


@app.post("/api/photos/sidecar/bulk", response_model=SidecarBulkUpdateResponse)
def bulk_update_sidecars(req: SidecarBulkUpdateRequest):
    updated = 0
    for rel in req.paths:
        try:
            img = resolve_media_path(rel)
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


@app.post("/api/photos/trash", response_model=TrashPhotosResponse)
def trash_photos(req: TrashPhotosRequest):
    dt = datetime.now().astimezone()
    batch = dt.strftime("%Y-%m-%d_%H%M%S")
    trash_batch_dir = TRASH_DIR / batch
    trash_batch_dir.mkdir(parents=True, exist_ok=True)

    sha_idx = load_sha256_index()

    trashed = 0
    trashed_rels: list[str] = []
    for rel in req.paths:
        try:
            img = resolve_media_path(rel)
        except Exception:
            continue
        if not img.exists():
            continue

        # Only allow trashing from inbox
        try:
            img.relative_to(PHOTOS_INBOX_DIR)
        except Exception:
            continue

        sc_path = sidecar_path_for(img)
        sc = load_or_init_sidecar_for_image(img) if sc_path.exists() else {}

        h = None
        try:
            h = sc.get("sha256") or sha256_file(img)
        except Exception:
            h = None

        # Move image
        dst_img = trash_batch_dir / img.name
        if dst_img.exists():
            dst_img = trash_batch_dir / f"{img.stem}_{int(img.stat().st_mtime)}{img.suffix}"
        try:
            dst_img.parent.mkdir(parents=True, exist_ok=True)
            img.rename(dst_img)
        except Exception:
            # fallback to shutil
            try:
                import shutil

                shutil.move(str(img), str(dst_img))
            except Exception:
                continue

        # Move sidecar if present
        if sc_path.exists():
            dst_rel = dst_img.relative_to(MEDIA_DIR).as_posix()
            dst_sc = DATA_DIR / f"{dst_rel}.json"
            dst_sc.parent.mkdir(parents=True, exist_ok=True)
            try:
                sc_path.rename(dst_sc)
            except Exception:
                try:
                    import shutil

                    shutil.move(str(sc_path), str(dst_sc))
                except Exception:
                    pass

        # Move thumbnail if present (keep restore possible)
        try:
            rel_under_data = img.relative_to(MEDIA_DIR).as_posix()
            thumb_abs = thumb_path_for(rel_under_data)
            if thumb_abs.exists():
                thumb_dst = (THUMBS_TRASH_DIR / batch / rel_under_data).resolve()
                thumb_dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    thumb_abs.rename(thumb_dst)
                except Exception:
                    import shutil

                    shutil.move(str(thumb_abs), str(thumb_dst))
        except Exception:
            pass

        if h and h in sha_idx:
            sha_idx.pop(h, None)

        trashed += 1
        trashed_rels.append(rel)

    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass
    try:
        forget_gallery_items(trashed_rels)
    except Exception:
        pass

    return TrashPhotosResponse(trashed=trashed, batch=str(trash_batch_dir.relative_to(MEDIA_DIR)).replace("\\", "/"))


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


@app.post("/api/trips/trash", response_model=TrashTripsResponse)
def trash_trips(req: TrashTripsRequest):
    dt = datetime.now().astimezone()
    batch = dt.strftime("%Y-%m-%d_%H%M%S")
    trash_batch_dir = TRIPS_TRASH_DIR / batch
    trash_batch_dir.mkdir(parents=True, exist_ok=True)

    if not TRIPS_INDEX.exists():
        return TrashTripsResponse(trashed=0, batch=str(trash_batch_dir.relative_to(DATA_DIR)).replace("\\", "/"))

    idx = json.loads(TRIPS_INDEX.read_text(encoding="utf-8"))
    trips = list(idx.get("trips") or [])

    by_id: dict[str, dict[str, Any]] = {}
    for t in trips:
        if isinstance(t, dict) and isinstance(t.get("id"), str):
            by_id[t["id"]] = t

    trashed = 0
    to_remove: set[str] = set()

    for trip_id in req.ids:
        t = by_id.get(trip_id)
        if not t:
            continue
        rel = t.get("path")
        if not isinstance(rel, str) or not rel.strip():
            continue

        src = (TRIPS_DIR / rel).resolve()
        src_media = (TRIPS_MEDIA_DIR / rel).resolve()
        try:
            src.relative_to(TRIPS_DIR)
            src_media.relative_to(TRIPS_MEDIA_DIR)
        except Exception:
            continue

        if not src.is_dir() or not src_media.is_dir():
            continue

        dst = (trash_batch_dir / rel).resolve()
        dst_media = (TRIPS_MEDIA_TRASH_DIR / batch / rel).resolve()
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        except Exception:
            try:
                import shutil

                shutil.move(str(src), str(dst))
            except Exception:
                continue

        try:
            dst_media.parent.mkdir(parents=True, exist_ok=True)
            src_media.rename(dst_media)
        except Exception:
            try:
                import shutil

                shutil.move(str(src_media), str(dst_media))
            except Exception:
                try:
                    dst.rename(src)
                except Exception:
                    pass
                continue

        to_remove.add(trip_id)
        trashed += 1

    if to_remove:
        idx["trips"] = [t for t in trips if not (isinstance(t, dict) and t.get("id") in to_remove)]
        TRIPS_INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return TrashTripsResponse(trashed=trashed, batch=str(trash_batch_dir.relative_to(DATA_DIR)).replace("\\", "/"))


@app.post("/api/trips/meta", response_model=TripMetaUpdateResponse)
def update_trip_meta(req: TripMetaUpdateRequest):
    if not TRIPS_INDEX.exists():
        return JSONResponse({"ok": False, "error": "Trips index not found"}, status_code=404)

    idx = json.loads(TRIPS_INDEX.read_text(encoding="utf-8"))
    trips = idx.get("trips", [])

    trip_entry = None
    for t in trips:
        if t.get("id") == req.id:
            trip_entry = t
            break

    if not trip_entry:
        return JSONResponse({"ok": False, "error": f"Trip {req.id} not found"}, status_code=404)

    trip_dir = TRIPS_DIR / trip_entry["path"]
    meta_path = trip_dir / "meta.json"

    if not meta_path.exists():
        return JSONResponse({"ok": False, "error": f"Meta file not found for trip {req.id}"}, status_code=404)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["title"] = req.title
    meta["tags"] = req.tags

    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return TripMetaUpdateResponse(ok=True)

@app.get("/api/trips/meta")
def get_all_trips_meta():
    if not TRIPS_INDEX.exists():
        return []

    # 1. Die Haupt-Index Datei lesen
    idx = json.loads(TRIPS_INDEX.read_text(encoding="utf-8"))
    trips_list = idx.get("trips", [])

    full_data = []
    
    # 2. Für jede Tour die zugehörige meta.json laden
    for t in trips_list:
        trip_id = t.get("id")
        trip_path = t.get("path")
        
        meta_file = TRIPS_DIR / trip_path / "meta.json"
        if meta_file.exists():
            meta_content = json.loads(meta_file.read_text(encoding="utf-8"))
            full_data.append({
                "id": trip_id,
                "path": trip_path,
                "meta": meta_content
            })
    
    return full_data

@app.post("/api/fitness/log", response_model=FitnessLogResponse)
def fitness_log(req: FitnessLogRequest):
    csv_dir = DATA_DIR / "fitness"
    csv_dir.mkdir(exist_ok=True)
    csv_path = csv_dir / f"{req.exercise}.csv"
    
    today = datetime.now().date().isoformat()
    
    lines = []
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()

    # Prüfen, ob der letzte Eintrag von heute ist
    if lines and lines[-1].startswith(today):
        # Bestehende Sets extrahieren und neue anhängen
        existing_sets = lines[-1].strip().split(',', 1)[1].strip('"')
        lines[-1] = f'{today},"{existing_sets},{req.sets}"\n'
        
        # Komplette Datei mit aktualisierter letzter Zeile überschreiben
        with csv_path.open("w", encoding="utf-8") as f:
            f.writelines(lines)
    else:
        # Neue Datei anlegen oder neue Zeile anhängen
        if not csv_path.exists():
            csv_path.write_text('date,sets\n', encoding="utf-8")
            
        with csv_path.open("a", encoding="utf-8") as f:
            f.write(f'{today},"{req.sets}"\n')

    return FitnessLogResponse()


@app.post("/api/photos/upload", response_model=UploadResponse)
async def upload_photos(files: List[UploadFile] = File(...)):

    pillow_heif.register_heif_opener()
    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)

    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    sha_idx = load_sha256_index()

    saved: list[UploadSavedItem] = []
    indexed: list[tuple[str, str | None]] = []
    duplicates_skipped = 0
    skipped_non_images = 0
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in MEDIA_EXTS and ext not in {".heif"}:
            skipped_non_images += 1
            continue
        out_name = unique_filename(prefix, f.filename or "upload")
        out_path = batch_dir / out_name

        # 1) Write file to disk
        with out_path.open("wb") as w:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                w.write(chunk)

# HEIC → JPG convert (share compat)
        ext = out_path.suffix.lower()
        if ext in [".heic", ".heif"]:
            with Image.open(out_path) as im:
                # 1. EXIF-Daten direkt beim Öffnen sichern
                exif_data = im.info.get("exif")

                im = ImageOps.exif_transpose(im)
                im = im.convert("RGB")

                jpg_filename = f"{out_path.stem}.jpg"
                jpg_name = unique_filename(prefix, jpg_filename)
                jpg_path = batch_dir / jpg_name

                # 2. EXIF-Daten beim Speichern wieder einfügen
                if exif_data:
                    im.save(jpg_path, 'JPEG', quality=92, optimize=True, progressive=True, exif=exif_data)
                else:
                    im.save(jpg_path, 'JPEG', quality=92, optimize=True, progressive=True)

            out_path.unlink()  # Remove HEIC
            out_path = jpg_path  # Use JPG

        if is_live_photo_video_file(out_path):
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
            skipped_non_images += 1
            continue

        # 2) Compute hash and dedupe
        try:
            h = sha256_file(out_path)
        except Exception:
            h = None

        if h and h in sha_idx:
            print(f"SKIPPED Duplicate: {f.filename} (Hash: {h[:8]}...)") # Neu
            existing_rel = sha_idx.get(h)
            existing_path = (MEDIA_DIR / str(existing_rel)).resolve() if existing_rel else None
            if existing_path and existing_path.exists():
                # Duplicate: don't save (remove just-written file)
                try:
                    out_path.unlink(missing_ok=True)
                except Exception:
                    pass
                duplicates_skipped += 1
                continue
            else:
                # stale index entry, treat as new
                sha_idx.pop(h, None)

        # 3) Thumbnail (best-effort)
        try:
            rel_under_data = out_path.relative_to(MEDIA_DIR).as_posix()
            ensure_thumb(out_path, rel_under_data)
        except Exception:
            pass

        # 4) Sidecar + index update
        sidecar = build_sidecar_for_image(out_path)
        if h:
            sidecar["sha256"] = h
        sc_path = sidecar_path_for(out_path)
        save_sidecar(sc_path, sidecar)

        rel = out_path.relative_to(MEDIA_DIR).as_posix()
        if h:
            sha_idx[h] = rel
        created = sidecar.get("createdAt")
        indexed.append((rel, str(created) if created else None))

        saved.append(
            UploadSavedItem(
                file=str(out_path.relative_to(MEDIA_DIR)).replace("\\", "/"),
                sidecar=str(sc_path.relative_to(DATA_DIR)).replace("\\", "/"),
                originalName=f.filename,
            )
        )

    # Persist hash index and make the new files visible to the paged gallery.
    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass
    try:
        remember_gallery_items(indexed)
    except Exception:
        pass

    return UploadResponse(
        batch=str(batch_dir.relative_to(MEDIA_DIR)).replace("\\", "/"),
        count=len(saved),
        saved=saved,
        duplicatesSkipped=duplicates_skipped,
        skippedNonImages=skipped_non_images,
    )


@app.post("/api/photos/upload-zip", response_model=UploadResponse)
async def upload_photos_zip(file: UploadFile = File(...)):
    # High but safe limits
    MAX_ZIP_BYTES = 3 * 1024 * 1024 * 1024  # 3 GB
    MAX_FILES = 50_000
    MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024 * 1024  # 100 GB

    # Basic file check
    name = (file.filename or "upload.zip").lower()
    if not name.endswith(".zip"):
        return JSONResponse({"ok": False, "error": "Expected .zip file"}, status_code=400)

    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)
    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    sha_idx = load_sha256_index()

    saved: list[UploadSavedItem] = []
    indexed: list[tuple[str, str | None]] = []
    duplicates_skipped = 0
    skipped_non_images = 0
    errors: list[str] = []

    # Store zip to a temp file (avoid holding huge payloads in memory)
    with tempfile.TemporaryDirectory(prefix="diary_zip_") as tmp:
        zip_path = Path(tmp) / "upload.zip"
        total = 0
        try:
            with zip_path.open("wb") as w:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_ZIP_BYTES:
                        return JSONResponse({"ok": False, "error": "ZIP too large (max 3GB)"}, status_code=413)
                    w.write(chunk)
        except Exception as e:
            return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

        # Process zip entries
        try:
            zf = zipfile.ZipFile(zip_path)
        except Exception:
            return JSONResponse({"ok": False, "error": "Invalid ZIP"}, status_code=400)

        with zf:
            infos = [i for i in zf.infolist() if not i.is_dir()]
            if len(infos) > MAX_FILES:
                return JSONResponse({"ok": False, "error": f"Too many files in ZIP (max {MAX_FILES})"}, status_code=413)

            uncompressed = sum(int(i.file_size or 0) for i in infos)
            if uncompressed > MAX_UNCOMPRESSED_BYTES:
                return JSONResponse({"ok": False, "error": "ZIP contents too large"}, status_code=413)

            allowed = MEDIA_EXTS | {".heif"}

            for info in infos:
                try:
                    base = Path(info.filename).name
                    ext = Path(base).suffix.lower()
                    if ext not in allowed:
                        skipped_non_images += 1
                        continue

                    out_name = unique_filename(prefix, base or "image")
                    out_path = batch_dir / out_name

                    # Extract file to out_path
                    with zf.open(info, "r") as src, out_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst, length=1024 * 1024)

                    if is_live_photo_video_file(out_path):
                        try:
                            out_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        skipped_non_images += 1
                        continue

                    # Hash + dedupe
                    try:
                        h = sha256_file(out_path)
                    except Exception:
                        h = None

                    if h and h in sha_idx:
                        existing_rel = sha_idx.get(h)
                        existing_path = (MEDIA_DIR / str(existing_rel)).resolve() if existing_rel else None
                        if existing_path and existing_path.exists():
                            try:
                                out_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                            duplicates_skipped += 1
                            continue
                        else:
                            sha_idx.pop(h, None)

                    # Thumb
                    try:
                        rel_under_data = out_path.relative_to(MEDIA_DIR).as_posix()
                        ensure_thumb(out_path, rel_under_data)
                    except Exception:
                        pass

                    # Sidecar + index
                    sidecar = build_sidecar_for_image(out_path)
                    if h:
                        sidecar["sha256"] = h
                    sc_path = sidecar_path_for(out_path)
                    save_sidecar(sc_path, sidecar)

                    rel = out_path.relative_to(MEDIA_DIR).as_posix()
                    if h:
                        sha_idx[h] = rel
                    created = sidecar.get("createdAt")
                    indexed.append((rel, str(created) if created else None))

                    saved.append(
                        UploadSavedItem(
                            file=str(out_path.relative_to(MEDIA_DIR)).replace("\\", "/"),
                            sidecar=str(sc_path.relative_to(DATA_DIR)).replace("\\", "/"),
                            originalName=base,
                        )
                    )
                except Exception as e:
                    errors.append(f"{info.filename}: {e}")
                    continue

    # Persist hash index and make the new files visible to the paged gallery.
    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass
    try:
        remember_gallery_items(indexed)
    except Exception:
        pass

    return UploadResponse(
        batch=str(batch_dir.relative_to(MEDIA_DIR)).replace("\\", "/"),
        count=len(saved),
        saved=saved,
        duplicatesSkipped=duplicates_skipped,
        skippedNonImages=skipped_non_images,
        errors=errors,
    )

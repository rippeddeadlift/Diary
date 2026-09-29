from __future__ import annotations

import json
import os
from datetime import datetime
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
from .trips.routes import router as trips_router
from .fitness.routes import router as fitness_router
from .config import DATA_DIR, MEDIA_DIR, MEDIA_EXTS, PHOTOS_INBOX_DIR
from .thumbnails import ensure_thumb, thumb_path_for

TRASH_DIR = MEDIA_DIR / "photos" / "_trash"
THUMBS_DIR = DATA_DIR / "photos" / "_thumbs"
THUMBS_TRASH_DIR = THUMBS_DIR / "_trash"

from .models import (
    SidecarGetResponse,
    SidecarModel,
    SidecarUpdateRequest,
    SidecarUpdateResponse,
    SidecarBulkUpdateRequest,
    SidecarBulkUpdateResponse,
    TrashPhotosRequest,
    TrashPhotosResponse,
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
app.include_router(trips_router)
app.include_router(fitness_router)


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

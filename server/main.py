from __future__ import annotations

import json
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

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import DATA_DIR, PHOTOS_INBOX_DIR, ROOT

TRASH_DIR = DATA_DIR / "photos" / "_trash"
THUMBS_DIR = DATA_DIR / "photos" / "_thumbs"
THUMBS_TRASH_DIR = THUMBS_DIR / "_trash"

TRIPS_DIR = DATA_DIR / "trips"
TRIPS_INDEX = TRIPS_DIR / "index.json"
TRIPS_TRASH_DIR = TRIPS_DIR / "_trash"


def thumb_path_for(rel_under_data: str) -> Path:
    # rel_under_data like: photos/inbox/.../x.jpg
    return (THUMBS_DIR / rel_under_data).resolve()


def ensure_thumb(img_abs: Path, rel_under_data: str, *, max_size: int = 512) -> None:
    """Best-effort thumbnail generation. Creates THUMBS_DIR/<rel_under_data>."""

    dst = thumb_path_for(rel_under_data)
    if dst.exists():
        return

    # Only generate thumbs for common raster formats.
    ext = img_abs.suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(img_abs) as im:
        im = ImageOps.exif_transpose(im)
        if ext in {".jpg", ".jpeg"}:
            im = im.convert("RGB")
        im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        if ext in {".jpg", ".jpeg"}:
            im.save(dst, format="JPEG", quality=82, optimize=True, progressive=True)
        elif ext == ".png":
            im.save(dst, format="PNG", optimize=True)
        else:  # .webp
            im = im.convert("RGB")
            im.save(dst, format="WEBP", quality=82, method=6)
from .models import (
    GalleryItem,
    GalleryListResponse,
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
    FitnessLogRequest,
    FitnessLogResponse,
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
        thumb_rel = f"photos/_thumbs/{rel}"
        thumb_abs = (DATA_DIR / thumb_rel).resolve()
        thumb_exists = thumb_abs.exists()
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
                    thumbUrl=f"/files/{thumb_rel}" if thumb_exists else None,
                    thumbExists=thumb_exists,
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


@app.get("/api/photos/suggest", response_model=GalleryListResponse)
def suggest_photos(date: str, bbox: str | None = None, limit: int = 200):
    """Suggest inbox photos for a given day (YYYY-MM-DD).

    Optional bbox: "minLat,minLon,maxLat,maxLon" to further filter by GPS.
    """

    # Basic date validation
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
        return JSONResponse({"ok": False, "error": "Invalid date"}, status_code=400)

    bbox_vals: tuple[float, float, float, float] | None = None
    if bbox:
        try:
            parts = [float(x) for x in bbox.split(",")]
            if len(parts) == 4:
                minLat, minLon, maxLat, maxLon = parts
                if minLat > maxLat:
                    minLat, maxLat = maxLat, minLat
                if minLon > maxLon:
                    minLon, maxLon = maxLon, minLon
                bbox_vals = (minLat, minLon, maxLat, maxLon)
        except Exception:
            bbox_vals = None

    items: list[GalleryItem] = []

    for img in list_inbox_images():
        if len(items) >= max(1, min(int(limit), 1000)):
            break

        rel = img.relative_to(DATA_DIR).as_posix()
        sc_path = sidecar_path_for(img)
        sc = load_or_init_sidecar_for_image(img) if sc_path.exists() else {}

        created_at = sc.get("createdAt")
        if not (isinstance(created_at, str) and created_at.startswith(date)):
            continue

        # Optional bbox filter (requires gps)
        if bbox_vals is not None:
            loc = sc.get("location")
            try:
                if not (isinstance(loc, dict) and "lat" in loc and "lon" in loc):
                    continue
                lat = float(loc["lat"])
                lon = float(loc["lon"])
                minLat, minLon, maxLat, maxLon = bbox_vals
                if not (minLat <= lat <= maxLat and minLon <= lon <= maxLon):
                    continue
            except Exception:
                continue

        thumb_rel = f"photos/_thumbs/{rel}"
        thumb_abs = (DATA_DIR / thumb_rel).resolve()
        thumb_exists = thumb_abs.exists()

        people = sc.get("people") or []
        tags = sc.get("tags") or []
        if not isinstance(people, list):
            people = []
        if not isinstance(tags, list):
            tags = []
        people = [str(x) for x in people if x is not None and str(x).strip()]
        tags = [str(x) for x in tags if x is not None and str(x).strip()]

        items.append(
            GalleryItem(
                path=rel,
                url=f"/files/{rel}",
                hasSidecar=sc_path.exists(),
                sidecarPath=sc_path.relative_to(DATA_DIR).as_posix() if sc_path.exists() else None,
                thumbUrl=f"/files/{thumb_rel}" if thumb_exists else None,
                thumbExists=thumb_exists,
                people=people,
                tags=tags,
                createdAt=str(created_at),
                createdAtSource=str(sc.get("createdAtSource") or "exif"),
                location=None,
                missing=False,
            )
        )

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


@app.post("/api/photos/trash", response_model=TrashPhotosResponse)
def trash_photos(req: TrashPhotosRequest):
    dt = datetime.now().astimezone()
    batch = dt.strftime("%Y-%m-%d_%H%M%S")
    trash_batch_dir = TRASH_DIR / batch
    trash_batch_dir.mkdir(parents=True, exist_ok=True)

    sha_idx = load_sha256_index()

    trashed = 0
    for rel in req.paths:
        try:
            img = resolve_data_path(rel)
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
            dst_sc = dst_img.with_suffix(dst_img.suffix + ".json")
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
            rel_under_data = img.relative_to(DATA_DIR).as_posix()
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

    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass

    return TrashPhotosResponse(trashed=trashed, batch=str(trash_batch_dir.relative_to(DATA_DIR)).replace("\\", "/"))


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
        # Prevent traversal / ensure under TRIPS_DIR
        try:
            src.relative_to(TRIPS_DIR)
        except Exception:
            continue

        if not src.exists() or not src.is_dir():
            # Still remove from index (stale)
            to_remove.add(trip_id)
            continue

        dst = (trash_batch_dir / rel).resolve()
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        except Exception:
            try:
                import shutil

                shutil.move(str(src), str(dst))
            except Exception:
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
    trips = list(idx.get("trips") or [])

    rel: str | None = None
    for t in trips:
        if isinstance(t, dict) and t.get("id") == req.id:
            p = t.get("path")
            if isinstance(p, str):
                rel = p
            break

    if not rel:
        return JSONResponse({"ok": False, "error": "Trip not found"}, status_code=404)

    trip_dir = (TRIPS_DIR / rel).resolve()
    try:
        trip_dir.relative_to(TRIPS_DIR)
    except Exception:
        return JSONResponse({"ok": False, "error": "Invalid path"}, status_code=400)

    meta_path = trip_dir / "meta.json"
    if not meta_path.exists():
        return JSONResponse({"ok": False, "error": "meta.json not found"}, status_code=404)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["title"] = str(req.title)
    meta["tags"] = [str(x) for x in (req.tags or []) if x is not None and str(x).strip()]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return TripMetaUpdateResponse()


@app.post("/api/fitness/log", response_model=FitnessLogResponse)
def fitness_log(req: FitnessLogRequest):
    csv_dir = DATA_DIR / "fitness"
    csv_dir.mkdir(exist_ok=True)
    csv_path = csv_dir / f"{req.exercise}.csv"
    today = datetime.now().date().isoformat()
    line = f'"{today}","{req.sets}"\n'
    if not csv_path.exists():
        csv_path.write_text('date,sets\n', encoding="utf-8")
    csv_path.write_text(line, mode="a", encoding="utf-8")
    return FitnessLogResponse(ok=True)


@app.post("/api/photos/upload", response_model=UploadResponse)
async def upload_photos(files: List[UploadFile] = File(...)):
    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)

    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    sha_idx = load_sha256_index()

    saved: list[UploadSavedItem] = []
    duplicates_skipped = 0
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
                duplicates_skipped += 1
                continue
            else:
                # stale index entry, treat as new
                sha_idx.pop(h, None)

        # 3) Thumbnail (best-effort)
        try:
            rel_under_data = out_path.relative_to(DATA_DIR).as_posix()
            ensure_thumb(out_path, rel_under_data)
        except Exception:
            pass

        # 4) Sidecar + index update
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
        duplicatesSkipped=duplicates_skipped,
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

            allowed = {".jpg", ".jpeg", ".png", ".webp"}

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

                    # Hash + dedupe
                    try:
                        h = sha256_file(out_path)
                    except Exception:
                        h = None

                    if h and h in sha_idx:
                        existing_rel = sha_idx.get(h)
                        existing_path = (DATA_DIR / str(existing_rel)).resolve() if existing_rel else None
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
                        rel_under_data = out_path.relative_to(DATA_DIR).as_posix()
                        ensure_thumb(out_path, rel_under_data)
                    except Exception:
                        pass

                    # Sidecar + index
                    sidecar = build_sidecar_for_image(out_path)
                    if h:
                        sidecar["sha256"] = h
                    sc_path = sidecar_path_for(out_path)
                    save_sidecar(sc_path, sidecar)

                    if h:
                        sha_idx[h] = out_path.relative_to(DATA_DIR).as_posix()

                    saved.append(
                        UploadSavedItem(
                            file=str(out_path.relative_to(ROOT)).replace("\\", "/"),
                            sidecar=str(sc_path.relative_to(ROOT)).replace("\\", "/"),
                            originalName=base,
                        )
                    )
                except Exception as e:
                    errors.append(f"{info.filename}: {e}")
                    continue

    # Persist hash index
    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass

    return UploadResponse(
        batch=str(batch_dir.relative_to(ROOT)).replace("\\", "/"),
        count=len(saved),
        saved=saved,
        duplicatesSkipped=duplicates_skipped,
        skippedNonImages=skipped_non_images,
        errors=errors,
    )

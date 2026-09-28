from __future__ import annotations

import json
import mimetypes
import ipaddress
import os
from datetime import datetime
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, List
from urllib.parse import quote
import zipfile
import tempfile
import shutil
import threading
import time
from uuid import uuid4

from PIL import Image, ImageOps, ImageStat
import pillow_heif

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import photos_repo
from .backups import create_backup_archive, latest_valid_backup, restore_backup_archive
from .config import DATA_DIR, MEDIA_DIR, MEDIA_EXTS, PHOTOS_INBOX_DIR, ROOT, VIDEO_EXTS

TRASH_DIR = MEDIA_DIR / "photos" / "_trash"
THUMBS_DIR = DATA_DIR / "photos" / "_thumbs"
THUMBS_TRASH_DIR = THUMBS_DIR / "_trash"

TRIPS_DIR = DATA_DIR / "trips"
TRIPS_INDEX = TRIPS_DIR / "index.json"
TRIPS_TRASH_DIR = TRIPS_DIR / "_trash"
TRIPS_MEDIA_DIR = MEDIA_DIR / "trips"
TRIPS_MEDIA_TRASH_DIR = TRIPS_MEDIA_DIR / "_trash"
MOVIES_CONFIG_PATH = DATA_DIR / "movies" / "library.json"
MOVIE_THUMBS_DIR = DATA_DIR / "movies" / "_thumbs"
MOVIE_EXTS = VIDEO_EXTS | {".avi", ".mkv", ".mpeg", ".mpg", ".wmv"}
BACKUP_EXPORTS: dict[str, dict[str, Any]] = {}
BACKUP_EXPORTS_LOCK = threading.Lock()


def thumb_path_for(rel_under_data: str) -> Path:
    # rel_under_data like: photos/inbox/.../x.jpg
    return (THUMBS_DIR / rel_under_data).resolve()


def ensure_video_poster(video_abs: Path, rel_under_data: str) -> None:
    """Grab one JPEG frame for the gallery tile. Needs ffmpeg on PATH."""
    dst = thumb_path_for(rel_under_data).with_suffix(".jpg")
    _generate_video_poster(video_abs, dst)


def _generate_video_poster(video_abs: Path, dst: Path) -> None:
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(video_abs),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        duration = float(probe.stdout.strip())
        sample_times = [duration * fraction for fraction in (0.1, 0.25, 0.5)]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        sample_times = [10.0, 30.0, 60.0]

    candidate = dst.with_name(f"{dst.stem}.candidate.jpg")
    best_brightness = -1.0
    try:
        for sample_time in sample_times:
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-ss", f"{sample_time:.3f}", "-i", str(video_abs),
                        "-frames:v", "1", "-vf",
                        "scale=512:512:force_original_aspect_ratio=increase,crop=512:512",
                        str(candidate),
                    ],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                with Image.open(candidate) as image:
                    brightness = ImageStat.Stat(image.convert("L")).mean[0]
                if brightness > best_brightness:
                    shutil.copyfile(candidate, dst)
                    best_brightness = brightness
                if brightness >= 12:
                    break
            except (OSError, subprocess.TimeoutExpired):
                continue
    finally:
        candidate.unlink(missing_ok=True)


def ensure_thumb(img_abs: Path, rel_under_data: str, *, max_size: int = 512) -> None:
    """Best-effort thumbnail generation. Creates THUMBS_DIR/<rel_under_data>."""

    if img_abs.suffix.lower() in VIDEO_EXTS:
        ensure_video_poster(img_abs, rel_under_data)
        return

    dst = thumb_path_for(rel_under_data)
    if dst.exists():
        return

    # Only generate thumbs for common raster formats.
    ext = img_abs.suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(img_abs) as im:
        im = ImageOps.exif_transpose(im)
        if ext in {".jpg", ".jpeg", ".heic"}:
            im = im.convert("RGB")
        im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        if ext in {".jpg", ".jpeg", ".heic"}:
            im.save(dst, format="JPEG", quality=82, optimize=True, progressive=True)
        elif ext == ".png":
            im.save(dst, format="PNG", optimize=True)
        else:  # .webp
            im = im.convert("RGB")
            im.save(dst, format="WEBP", quality=82, method=6)
from .models import (
    FitnessLogRequest,
    FitnessLogResponse,
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


@app.get("/api/health")
def health():
    return {"ok": True, "time": datetime.now().astimezone().isoformat(timespec="seconds")}


@app.get("/api/backup/status")
def backup_status(request: Request):
    _check_local_request(request)
    return latest_valid_backup(MEDIA_DIR)


def _run_backup_export(job_id: str) -> None:
    def update_progress(files_done: int, total_files: int) -> None:
        with BACKUP_EXPORTS_LOCK:
            job = BACKUP_EXPORTS.get(job_id)
            if job is not None:
                job["filesDone"] = files_done
                job["totalFiles"] = total_files

    try:
        archive = create_backup_archive(DATA_DIR, on_progress=update_progress)
    except Exception as exc:
        with BACKUP_EXPORTS_LOCK:
            job = BACKUP_EXPORTS.get(job_id)
            if job is not None:
                job.update(status="error", error=str(exc))
        return

    with BACKUP_EXPORTS_LOCK:
        job = BACKUP_EXPORTS.get(job_id)
        if job is not None:
            job.update(status="ready", archive=archive, filesDone=job["totalFiles"])
        else:
            archive.unlink(missing_ok=True)


def _cleanup_backup_export(job_id: str, archive: Path) -> None:
    archive.unlink(missing_ok=True)
    with BACKUP_EXPORTS_LOCK:
        BACKUP_EXPORTS.pop(job_id, None)


@app.post("/api/backup/export")
def start_data_backup(request: Request):
    _check_local_request(request)
    with BACKUP_EXPORTS_LOCK:
        for job_id, job in list(BACKUP_EXPORTS.items()):
            age = time.time() - job["createdAt"]
            if job["status"] == "running":
                raise HTTPException(status_code=409, detail="A backup export is already running or ready to download")
            if job["status"] == "ready" and age <= 3600:
                raise HTTPException(status_code=409, detail="A backup export is already running or ready to download")
            if age > 3600:
                archive = job.get("archive")
                if isinstance(archive, Path):
                    archive.unlink(missing_ok=True)
                BACKUP_EXPORTS.pop(job_id, None)

        job_id = uuid4().hex
        BACKUP_EXPORTS[job_id] = {
            "status": "running",
            "filesDone": 0,
            "totalFiles": 0,
            "createdAt": time.time(),
        }
    threading.Thread(target=_run_backup_export, args=(job_id,), daemon=True).start()
    return {"jobId": job_id, "status": "running"}


@app.get("/api/backup/export/{job_id}")
def get_data_backup_status(job_id: str, request: Request):
    _check_local_request(request)
    with BACKUP_EXPORTS_LOCK:
        job = BACKUP_EXPORTS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Backup export not found")
        return {
            "jobId": job_id,
            "status": job["status"],
            "filesDone": job["filesDone"],
            "totalFiles": job["totalFiles"],
            "error": job.get("error"),
        }


@app.get("/api/backup/export/{job_id}/download")
def download_data_backup(job_id: str, request: Request):
    _check_local_request(request)
    with BACKUP_EXPORTS_LOCK:
        job = BACKUP_EXPORTS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Backup export not found")
        if job["status"] != "ready":
            raise HTTPException(status_code=409, detail="Backup export is not ready")
        archive = job["archive"]
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=f"diary-data-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip",
        background=BackgroundTask(_cleanup_backup_export, job_id, archive),
    )


@app.post("/api/backup/export/{job_id}/save-to-media")
def save_data_backup_to_media(job_id: str, request: Request):
    _check_local_request(request)
    with BACKUP_EXPORTS_LOCK:
        job = BACKUP_EXPORTS.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Backup export not found")
        if job["status"] != "ready":
            raise HTTPException(status_code=409, detail="Backup export is not ready")
        job["status"] = "saving"
        archive = job["archive"]

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = MEDIA_DIR / f"diary-backup-{stamp}.zip"
    suffix = 2
    while destination.exists():
        destination = MEDIA_DIR / f"diary-backup-{stamp}-{suffix}.zip"
        suffix += 1
    try:
        shutil.move(str(archive), str(destination))
    except OSError as exc:
        with BACKUP_EXPORTS_LOCK:
            job = BACKUP_EXPORTS.get(job_id)
            if job is not None:
                job["status"] = "ready"
        raise HTTPException(status_code=500, detail=f"Could not save backup to media folder: {exc}") from exc

    with BACKUP_EXPORTS_LOCK:
        BACKUP_EXPORTS.pop(job_id, None)
    return {"ok": True, "path": str(destination)}


@app.post("/api/backup/import")
def import_data_backup(
    request: Request,
    file: UploadFile = File(...),
    confirm_replace: bool = Form(False),
):
    _check_local_request(request)
    if not confirm_replace:
        raise HTTPException(status_code=400, detail="Confirm replacing the current data directory")
    try:
        file.file.seek(0)
        file_count, unpacked_bytes = restore_backup_archive(DATA_DIR, file.file)
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise HTTPException(status_code=400, detail=f"Could not restore backup: {exc}") from exc

    photos_repo._gallery_disk_synced = False
    photos_repo._ranked_rels = None
    photos_repo._ranked_index = None
    return {"ok": True, "files": file_count, "unpackedBytes": unpacked_bytes}


def _movie_folder() -> Path | None:
    try:
        value = json.loads(MOVIES_CONFIG_PATH.read_text(encoding="utf-8")).get("folder")
        folder = Path(value).expanduser().resolve() if isinstance(value, str) else None
        return folder if folder is not None and folder.is_dir() else None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _check_local_request(request: Request) -> None:
    host = request.client.host if request.client else ""
    try:
        is_local = ipaddress.ip_address(host).is_loopback
    except ValueError:
        is_local = False
    if not is_local:
        raise HTTPException(status_code=403, detail="Movie library settings are local-only")


def _save_movie_folder(folder: str) -> Path:
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        raise HTTPException(status_code=400, detail="Folder does not exist")
    MOVIES_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    MOVIES_CONFIG_PATH.write_text(json.dumps({"folder": str(path)}, indent=2), encoding="utf-8")
    return path


def _resolve_movie(movie_path: str) -> tuple[Path, Path]:
    root = _movie_folder()
    if root is None:
        raise HTTPException(status_code=404, detail="Choose a movie folder first")
    candidate = (root / movie_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=404, detail="Movie not found") from None
    if not candidate.is_file() or candidate.suffix.lower() not in MOVIE_EXTS:
        raise HTTPException(status_code=404, detail="Movie not found")
    return root, candidate


@app.get("/api/movies")
def list_movies():
    root = _movie_folder()
    if root is None:
        return {"folder": None, "count": 0, "items": []}

    items = []
    for movie in root.rglob("*"):
        if not movie.is_file() or movie.suffix.lower() not in MOVIE_EXTS:
            continue
        try:
            movie.resolve().relative_to(root)
        except ValueError:
            continue
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


@app.post("/api/movies/folder")
def set_movie_folder(payload: dict[str, str], request: Request):
    _check_local_request(request)
    folder = payload.get("path", "").strip()
    if not folder:
        raise HTTPException(status_code=400, detail="Folder path is required")
    _save_movie_folder(folder)
    return list_movies()


@app.post("/api/movies/pick-folder")
def pick_movie_folder(request: Request):
    _check_local_request(request)
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        raise HTTPException(status_code=501, detail="Native folder selection is unavailable; enter a path instead") from None

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        current = _movie_folder()
        selected = filedialog.askdirectory(
            title="Choose your movie folder",
            initialdir=str(current) if current else None,
        )
    finally:
        root.destroy()
    if not selected:
        return {"cancelled": True, **list_movies()}
    _save_movie_folder(selected)
    return list_movies()


@app.get("/api/movies/poster/{movie_path:path}")
def movie_poster(movie_path: str):
    root, movie = _resolve_movie(movie_path)
    rel = movie.relative_to(root)
    poster = (MOVIE_THUMBS_DIR / f"{rel.as_posix()}.jpg").resolve()
    try:
        poster.relative_to(MOVIE_THUMBS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Poster not found") from None
    _generate_video_poster(movie, poster)
    if not poster.is_file():
        raise HTTPException(status_code=404, detail="Could not create movie poster; install ffmpeg")
    return FileResponse(poster, media_type="image/jpeg")


@app.get("/api/movies/stream/{movie_path:path}")
def stream_movie(movie_path: str):
    _, movie = _resolve_movie(movie_path)
    media_type = mimetypes.guess_type(movie.name)[0] or "application/octet-stream"
    return FileResponse(movie, media_type=media_type, filename=movie.name)


@app.post("/api/movies/open")
def open_movie(payload: dict[str, str], request: Request):
    _check_local_request(request)
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


def _gallery_item_for(img: Path) -> GalleryItem | None:
    rel = img.relative_to(MEDIA_DIR).as_posix()
    kind = "video" if img.suffix.lower() in VIDEO_EXTS else "image"
    thumb_rel = f"photos/_thumbs/{rel}"
    if kind == "video":
        thumb_rel = str(Path(thumb_rel).with_suffix(".jpg")).replace("\\", "/")
    thumb_abs = (DATA_DIR / thumb_rel).resolve()
    thumb_exists = thumb_abs.exists()
    sc_path = sidecar_path_for(img)
    sc = load_or_init_sidecar_for_image(img) if sc_path.exists() else {}

    people = sc.get("people") or []
    tags = sc.get("tags") or []
    created_at = sc.get("createdAt")
    created_src = sc.get("createdAtSource")
    location = sc.get("location")

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
        return GalleryItem(
            path=rel,
            url=f"/media/{rel}",
            kind=kind,
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
    except Exception:
        return None


@app.get("/api/photos/inbox/all", response_model=GalleryListResponse)
def list_inbox_all(offset: int = 0, limit: int | None = None, before: str | None = None):
    before_created_at = before
    """List inbox photos.

    Without limit, returns the full sorted list (existing callers).
    With limit, returns one page so the UI can paint before the rest is read.
    """
    offset = max(0, offset)
    order: dict[str, str | None] = {}
    cached_rels = load_gallery_paths() if limit is not None else []
    # Uploads update the cache themselves. Catch files dropped on disk only
    # once per process — a full inbox walk on every page made the first 48 slow.
    if limit is not None and (cached_rels or GALLERY_ORDER_PATH.exists()):
        try:
            added = sync_missing_gallery_items_once()
        except Exception:
            added = 0
        if added:
            cached_rels = load_gallery_paths()
    # A sorted page needs a date for every path. Use it only when the last full
    # pass already wrote one; otherwise scan newest folders only.
    if limit is not None and cached_rels and GALLERY_ORDER_PATH.exists():
        order = load_gallery_order()

    partial = False
    if limit is not None:
        images, partial = newest_inbox_images(max(1, min(limit, 500)), before)
        total = len(cached_rels) if cached_rels else None
        offset = 0
    else:
        images = list_inbox_images()
        total = len(images)
        try:
            save_gallery_paths([p.relative_to(MEDIA_DIR).as_posix() for p in images])
        except Exception:
            pass

    if limit is None:
        page = images
        has_more = False
    else:
        limit = max(1, min(limit, 500))
        page = images[:limit]
        has_more = partial

    items: list[GalleryItem] = []
    for img in page:
        item = _gallery_item_for(img)
        if item is not None:
            items.append(item)

    if limit is None:
        items_dicts = [it.model_dump() for it in items]
        sort_gallery_items(items_dicts)
        items = [GalleryItem(**d) for d in items_dicts]
        try:
            save_gallery_order({it.path: it.createdAt for it in items})
        except Exception:
            pass

    return GalleryListResponse(
        count=len(items),
        total=total,
        offset=offset,
        limit=limit,
        hasMore=has_more,
        items=items,
    )


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

        rel = img.relative_to(MEDIA_DIR).as_posix()
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

        # Location parsen, falls vorhanden und gültig
        loc_data = sc.get("location")
        location_val = None
        if isinstance(loc_data, dict) and "lat" in loc_data and "lon" in loc_data:
            try:
                location_val = {"lat": float(loc_data["lat"]), "lon": float(loc_data["lon"])}
            except (ValueError, TypeError):
                pass

        items.append(
            GalleryItem(
                path=rel,
                url=f"/media/{rel}",
                hasSidecar=sc_path.exists(),
                sidecarPath=sc_path.relative_to(DATA_DIR).as_posix() if sc_path.exists() else None,
                thumbUrl=f"/files/{thumb_rel}" if thumb_exists else None,
                thumbExists=thumb_exists,
                people=people,
                tags=tags,
                createdAt=str(created_at),
                createdAtSource=str(sc.get("createdAtSource") or "exif"),
                location=location_val, # <-- Hier den ermittelten Wert einsetzen
                missing=False,
            )
        )

    return GalleryListResponse(count=len(items), items=items)


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

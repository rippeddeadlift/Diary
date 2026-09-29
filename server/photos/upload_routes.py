from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps
import pillow_heif
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from ..config import DATA_DIR, MEDIA_DIR, MEDIA_EXTS, PHOTOS_INBOX_DIR
from ..models import UploadResponse, UploadSavedItem
from .repository import (
    batch_folder_name,
    build_sidecar_for_image,
    is_live_photo_video_file,
    load_sha256_index,
    remember_gallery_items,
    save_sha256_index,
    save_sidecar,
    sha256_file,
    sidecar_path_for,
    unique_filename,
)
from ..thumbnails import ensure_thumb

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.post("/upload", response_model=UploadResponse)
async def upload_photos(files: list[UploadFile] = File(...)):
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

    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in MEDIA_EXTS and ext not in {".heif"}:
            skipped_non_images += 1
            continue
        out_name = unique_filename(prefix, upload.filename or "upload")
        out_path = batch_dir / out_name

        with out_path.open("wb") as output:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)

        ext = out_path.suffix.lower()
        if ext in [".heic", ".heif"]:
            with Image.open(out_path) as image:
                exif_data = image.info.get("exif")
                image = ImageOps.exif_transpose(image).convert("RGB")
                jpg_filename = f"{out_path.stem}.jpg"
                jpg_name = unique_filename(prefix, jpg_filename)
                jpg_path = batch_dir / jpg_name
                if exif_data:
                    image.save(jpg_path, "JPEG", quality=92, optimize=True, progressive=True, exif=exif_data)
                else:
                    image.save(jpg_path, "JPEG", quality=92, optimize=True, progressive=True)
            out_path.unlink()
            out_path = jpg_path

        if is_live_photo_video_file(out_path):
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
            skipped_non_images += 1
            continue

        try:
            file_hash = sha256_file(out_path)
        except Exception:
            file_hash = None

        if file_hash and file_hash in sha_idx:
            print(f"SKIPPED Duplicate: {upload.filename} (Hash: {file_hash[:8]}...)")
            existing_rel = sha_idx.get(file_hash)
            existing_path = (MEDIA_DIR / str(existing_rel)).resolve() if existing_rel else None
            if existing_path and existing_path.exists():
                try:
                    out_path.unlink(missing_ok=True)
                except Exception:
                    pass
                duplicates_skipped += 1
                continue
            sha_idx.pop(file_hash, None)

        try:
            rel_under_data = out_path.relative_to(MEDIA_DIR).as_posix()
            ensure_thumb(out_path, rel_under_data)
        except Exception:
            pass

        sidecar = build_sidecar_for_image(out_path)
        if file_hash:
            sidecar["sha256"] = file_hash
        sidecar_file = sidecar_path_for(out_path)
        save_sidecar(sidecar_file, sidecar)

        rel = out_path.relative_to(MEDIA_DIR).as_posix()
        if file_hash:
            sha_idx[file_hash] = rel
        created = sidecar.get("createdAt")
        indexed.append((rel, str(created) if created else None))
        saved.append(
            UploadSavedItem(
                file=out_path.relative_to(MEDIA_DIR).as_posix(),
                sidecar=sidecar_file.relative_to(DATA_DIR).as_posix(),
                originalName=upload.filename,
            )
        )

    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass
    try:
        remember_gallery_items(indexed)
    except Exception:
        pass

    return UploadResponse(
        batch=batch_dir.relative_to(MEDIA_DIR).as_posix(),
        count=len(saved),
        saved=saved,
        duplicatesSkipped=duplicates_skipped,
        skippedNonImages=skipped_non_images,
    )


@router.post("/upload-zip", response_model=UploadResponse)
async def upload_photos_zip(file: UploadFile = File(...)):
    max_zip_bytes = 3 * 1024 * 1024 * 1024
    max_files = 50_000
    max_uncompressed_bytes = 100 * 1024 * 1024 * 1024

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

    with tempfile.TemporaryDirectory(prefix="diary_zip_") as tmp:
        zip_path = Path(tmp) / "upload.zip"
        total = 0
        try:
            with zip_path.open("wb") as output:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_zip_bytes:
                        return JSONResponse({"ok": False, "error": "ZIP too large (max 3GB)"}, status_code=413)
                    output.write(chunk)
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

        try:
            archive = zipfile.ZipFile(zip_path)
        except Exception:
            return JSONResponse({"ok": False, "error": "Invalid ZIP"}, status_code=400)

        with archive:
            infos = [item for item in archive.infolist() if not item.is_dir()]
            if len(infos) > max_files:
                return JSONResponse({"ok": False, "error": f"Too many files in ZIP (max {max_files})"}, status_code=413)

            uncompressed = sum(int(item.file_size or 0) for item in infos)
            if uncompressed > max_uncompressed_bytes:
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
                    with archive.open(info, "r") as source, out_path.open("wb") as destination:
                        shutil.copyfileobj(source, destination, length=1024 * 1024)

                    if is_live_photo_video_file(out_path):
                        try:
                            out_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        skipped_non_images += 1
                        continue

                    try:
                        file_hash = sha256_file(out_path)
                    except Exception:
                        file_hash = None

                    if file_hash and file_hash in sha_idx:
                        existing_rel = sha_idx.get(file_hash)
                        existing_path = (MEDIA_DIR / str(existing_rel)).resolve() if existing_rel else None
                        if existing_path and existing_path.exists():
                            try:
                                out_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                            duplicates_skipped += 1
                            continue
                        sha_idx.pop(file_hash, None)

                    try:
                        rel_under_data = out_path.relative_to(MEDIA_DIR).as_posix()
                        ensure_thumb(out_path, rel_under_data)
                    except Exception:
                        pass

                    sidecar = build_sidecar_for_image(out_path)
                    if file_hash:
                        sidecar["sha256"] = file_hash
                    sidecar_file = sidecar_path_for(out_path)
                    save_sidecar(sidecar_file, sidecar)

                    rel = out_path.relative_to(MEDIA_DIR).as_posix()
                    if file_hash:
                        sha_idx[file_hash] = rel
                    created = sidecar.get("createdAt")
                    indexed.append((rel, str(created) if created else None))
                    saved.append(
                        UploadSavedItem(
                            file=out_path.relative_to(MEDIA_DIR).as_posix(),
                            sidecar=sidecar_file.relative_to(DATA_DIR).as_posix(),
                            originalName=base,
                        )
                    )
                except Exception as exc:
                    errors.append(f"{info.filename}: {exc}")
                    continue

    try:
        save_sha256_index(sha_idx)
    except Exception:
        pass
    try:
        remember_gallery_items(indexed)
    except Exception:
        pass

    return UploadResponse(
        batch=batch_dir.relative_to(MEDIA_DIR).as_posix(),
        count=len(saved),
        saved=saved,
        duplicatesSkipped=duplicates_skipped,
        skippedNonImages=skipped_non_images,
        errors=errors,
    )

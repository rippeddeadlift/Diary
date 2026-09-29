from __future__ import annotations

import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps
import pillow_heif
from starlette.datastructures import UploadFile

from ..config import DATA_DIR, MEDIA_DIR, MEDIA_EXTS, PHOTOS_INBOX_DIR
from ..models import UploadResponse, UploadSavedItem
from . import repository
from ..thumbnails import ensure_thumb


class UploadServiceError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _persist_upload_index(
    sha_index: dict[str, str], indexed: list[tuple[str, str | None]]
) -> None:
    try:
        repository.save_sha256_index(sha_index)
    except Exception:
        pass
    try:
        repository.remember_gallery_items(indexed)
    except Exception:
        pass


async def upload_photo_files(files: list[UploadFile]) -> UploadResponse:
    pillow_heif.register_heif_opener()
    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / repository.batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)
    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    sha_index = repository.load_sha256_index()
    saved: list[UploadSavedItem] = []
    indexed: list[tuple[str, str | None]] = []
    duplicates_skipped = 0
    skipped_non_images = 0

    for upload in files:
        ext = Path(upload.filename or "").suffix.lower()
        if ext not in MEDIA_EXTS and ext not in {".heif"}:
            skipped_non_images += 1
            continue

        out_name = repository.unique_filename(prefix, upload.filename or "upload")
        out_path = batch_dir / out_name
        with out_path.open("wb") as output:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)

        ext = out_path.suffix.lower()
        if ext in {".heic", ".heif"}:
            with Image.open(out_path) as image:
                exif_data = image.info.get("exif")
                image = ImageOps.exif_transpose(image).convert("RGB")
                jpg_filename = f"{out_path.stem}.jpg"
                jpg_name = repository.unique_filename(prefix, jpg_filename)
                jpg_path = batch_dir / jpg_name
                if exif_data:
                    image.save(jpg_path, "JPEG", quality=92, optimize=True, progressive=True, exif=exif_data)
                else:
                    image.save(jpg_path, "JPEG", quality=92, optimize=True, progressive=True)
            out_path.unlink()
            out_path = jpg_path

        if repository.is_live_photo_video_file(out_path):
            try:
                out_path.unlink(missing_ok=True)
            except Exception:
                pass
            skipped_non_images += 1
            continue

        try:
            file_hash = repository.sha256_file(out_path)
        except Exception:
            file_hash = None

        if file_hash and file_hash in sha_index:
            existing_rel = sha_index.get(file_hash)
            existing_path = (MEDIA_DIR / str(existing_rel)).resolve() if existing_rel else None
            if existing_path and existing_path.exists():
                try:
                    out_path.unlink(missing_ok=True)
                except Exception:
                    pass
                duplicates_skipped += 1
                continue
            sha_index.pop(file_hash, None)

        try:
            rel_under_data = out_path.relative_to(MEDIA_DIR).as_posix()
            ensure_thumb(out_path, rel_under_data)
        except Exception:
            pass

        sidecar = repository.build_sidecar_for_image(out_path)
        if file_hash:
            sidecar["sha256"] = file_hash
        sidecar_file = repository.sidecar_path_for(out_path)
        repository.save_sidecar(sidecar_file, sidecar)

        rel = out_path.relative_to(MEDIA_DIR).as_posix()
        if file_hash:
            sha_index[file_hash] = rel
        created = sidecar.get("createdAt")
        indexed.append((rel, str(created) if created else None))
        saved.append(
            UploadSavedItem(
                file=rel,
                sidecar=sidecar_file.relative_to(DATA_DIR).as_posix(),
                originalName=upload.filename,
            )
        )

    _persist_upload_index(sha_index, indexed)
    return UploadResponse(
        batch=batch_dir.relative_to(MEDIA_DIR).as_posix(),
        count=len(saved),
        saved=saved,
        duplicatesSkipped=duplicates_skipped,
        skippedNonImages=skipped_non_images,
    )


async def upload_photo_zip(file: UploadFile) -> UploadResponse:
    max_zip_bytes = 3 * 1024 * 1024 * 1024
    max_files = 50_000
    max_uncompressed_bytes = 100 * 1024 * 1024 * 1024

    name = (file.filename or "upload.zip").lower()
    if not name.endswith(".zip"):
        raise UploadServiceError("Expected .zip file", 400)

    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / repository.batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)
    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    sha_index = repository.load_sha256_index()
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
                        raise UploadServiceError("ZIP too large (max 3GB)", 413)
                    output.write(chunk)
        except UploadServiceError:
            raise
        except Exception as exc:
            raise UploadServiceError(str(exc), 500) from exc

        try:
            archive = zipfile.ZipFile(zip_path)
        except Exception as exc:
            raise UploadServiceError("Invalid ZIP", 400) from exc

        with archive:
            infos = [item for item in archive.infolist() if not item.is_dir()]
            if len(infos) > max_files:
                raise UploadServiceError(f"Too many files in ZIP (max {max_files})", 413)

            uncompressed = sum(int(item.file_size or 0) for item in infos)
            if uncompressed > max_uncompressed_bytes:
                raise UploadServiceError("ZIP contents too large", 413)

            allowed = MEDIA_EXTS | {".heif"}
            for info in infos:
                try:
                    base = Path(info.filename).name
                    ext = Path(base).suffix.lower()
                    if ext not in allowed:
                        skipped_non_images += 1
                        continue

                    out_name = repository.unique_filename(prefix, base or "image")
                    out_path = batch_dir / out_name
                    with archive.open(info, "r") as source, out_path.open("wb") as destination:
                        shutil.copyfileobj(source, destination, length=1024 * 1024)

                    if repository.is_live_photo_video_file(out_path):
                        try:
                            out_path.unlink(missing_ok=True)
                        except Exception:
                            pass
                        skipped_non_images += 1
                        continue

                    try:
                        file_hash = repository.sha256_file(out_path)
                    except Exception:
                        file_hash = None

                    if file_hash and file_hash in sha_index:
                        existing_rel = sha_index.get(file_hash)
                        existing_path = (MEDIA_DIR / str(existing_rel)).resolve() if existing_rel else None
                        if existing_path and existing_path.exists():
                            try:
                                out_path.unlink(missing_ok=True)
                            except Exception:
                                pass
                            duplicates_skipped += 1
                            continue
                        sha_index.pop(file_hash, None)

                    try:
                        rel_under_data = out_path.relative_to(MEDIA_DIR).as_posix()
                        ensure_thumb(out_path, rel_under_data)
                    except Exception:
                        pass

                    sidecar = repository.build_sidecar_for_image(out_path)
                    if file_hash:
                        sidecar["sha256"] = file_hash
                    sidecar_file = repository.sidecar_path_for(out_path)
                    repository.save_sidecar(sidecar_file, sidecar)

                    rel = out_path.relative_to(MEDIA_DIR).as_posix()
                    if file_hash:
                        sha_index[file_hash] = rel
                    created = sidecar.get("createdAt")
                    indexed.append((rel, str(created) if created else None))
                    saved.append(
                        UploadSavedItem(
                            file=rel,
                            sidecar=sidecar_file.relative_to(DATA_DIR).as_posix(),
                            originalName=base,
                        )
                    )
                except Exception as exc:
                    errors.append(f"{info.filename}: {exc}")
                    continue

    _persist_upload_index(sha_index, indexed)
    return UploadResponse(
        batch=batch_dir.relative_to(MEDIA_DIR).as_posix(),
        count=len(saved),
        saved=saved,
        duplicatesSkipped=duplicates_skipped,
        skippedNonImages=skipped_non_images,
        errors=errors,
    )

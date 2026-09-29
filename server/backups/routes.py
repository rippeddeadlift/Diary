from __future__ import annotations

import shutil
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask

from ..photos import repository as photos_repo
from ..config import DATA_DIR, MEDIA_DIR
from ..local_requests import check_local_request
from .archive import create_backup_archive, latest_valid_backup, restore_backup_archive

router = APIRouter(prefix="/api/backup", tags=["backup"])

BACKUP_EXPORTS: dict[str, dict[str, Any]] = {}
BACKUP_EXPORTS_LOCK = threading.Lock()


@router.get("/status")
def backup_status(request: Request):
    check_local_request(request)
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


@router.post("/export")
def start_data_backup(request: Request):
    check_local_request(request)
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


@router.get("/export/{job_id}")
def get_data_backup_status(job_id: str, request: Request):
    check_local_request(request)
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


@router.get("/export/{job_id}/download")
def download_data_backup(job_id: str, request: Request):
    check_local_request(request)
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


@router.post("/export/{job_id}/save-to-media")
def save_data_backup_to_media(job_id: str, request: Request):
    check_local_request(request)
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


@router.post("/import")
def import_data_backup(
    request: Request,
    file: UploadFile = File(...),
    confirm_replace: bool = Form(False),
):
    check_local_request(request)
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

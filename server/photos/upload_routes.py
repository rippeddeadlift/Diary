from __future__ import annotations

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from ..models import UploadResponse
from .upload_service import UploadServiceError, upload_photo_files, upload_photo_zip

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.post("/upload", response_model=UploadResponse)
async def upload_photos(files: list[UploadFile] = File(...)):
    return await upload_photo_files(files)


@router.post("/upload-zip", response_model=UploadResponse)
async def upload_photos_zip(file: UploadFile = File(...)):
    try:
        return await upload_photo_zip(file)
    except UploadServiceError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=exc.status_code)

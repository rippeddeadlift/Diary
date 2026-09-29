from __future__ import annotations

from fastapi import APIRouter

from ..models import TrashPhotosRequest, TrashPhotosResponse
from .trash_service import trash_photo_items

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.post("/trash", response_model=TrashPhotosResponse)
def trash_photos(req: TrashPhotosRequest):
    trashed, batch = trash_photo_items(req.paths)
    return TrashPhotosResponse(trashed=trashed, batch=batch)

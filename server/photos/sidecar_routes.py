from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from .. import photos_repo
from ..config import DATA_DIR, MEDIA_DIR
from ..models import (
    SidecarBulkUpdateRequest,
    SidecarBulkUpdateResponse,
    SidecarGetResponse,
    SidecarModel,
    SidecarUpdateRequest,
    SidecarUpdateResponse,
)

router = APIRouter(prefix="/api/photos", tags=["photos"])


@router.get("/sidecar", response_model=SidecarGetResponse)
def get_sidecar(path: str):
    img = photos_repo.resolve_media_path(path)
    if not img.exists():
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)

    sidecar_path = photos_repo.sidecar_path_for(img)
    sidecar = photos_repo.load_or_init_sidecar_for_image(img)
    if not sidecar_path.exists():
        photos_repo.save_sidecar(sidecar_path, sidecar)

    return SidecarGetResponse(
        path=str(img.relative_to(MEDIA_DIR)).replace("\\", "/"),
        sidecarPath=str(sidecar_path.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecar=SidecarModel(**sidecar),
    )


@router.post("/sidecar", response_model=SidecarUpdateResponse)
def update_sidecar(req: SidecarUpdateRequest):
    img = photos_repo.resolve_media_path(req.path)
    if not img.exists():
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)

    sidecar_path = photos_repo.sidecar_path_for(img)
    sidecar = photos_repo.load_or_init_sidecar_for_image(img)
    sidecar = photos_repo.update_sidecar_fields(sidecar, req.people, req.tags, req.caption)
    photos_repo.save_sidecar(sidecar_path, sidecar)

    return SidecarUpdateResponse(
        path=str(img.relative_to(MEDIA_DIR)).replace("\\", "/"),
        sidecarPath=str(sidecar_path.relative_to(DATA_DIR)).replace("\\", "/"),
        sidecar=SidecarModel(**sidecar),
    )


@router.post("/sidecar/bulk", response_model=SidecarBulkUpdateResponse)
def bulk_update_sidecars(req: SidecarBulkUpdateRequest):
    updated = 0
    for rel in req.paths:
        try:
            img = photos_repo.resolve_media_path(rel)
        except Exception:
            continue
        if not img.exists():
            continue

        sidecar_path = photos_repo.sidecar_path_for(img)
        sidecar = photos_repo.load_or_init_sidecar_for_image(img)
        sidecar = photos_repo.bulk_toggle_sidecar_fields(
            sidecar,
            add_people=req.addPeople,
            remove_people=req.removePeople,
            add_tags=req.addTags,
            remove_tags=req.removeTags,
        )
        photos_repo.save_sidecar(sidecar_path, sidecar)
        updated += 1

    return SidecarBulkUpdateResponse(updated=updated)
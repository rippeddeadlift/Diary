from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from . import repository as photos_repo
from ..config import DATA_DIR, MEDIA_DIR, VIDEO_EXTS
from ..models import GalleryItem, GalleryListResponse

router = APIRouter(prefix="/api/photos", tags=["photos"])


def _gallery_item_for(img: Path) -> GalleryItem | None:
    rel = img.relative_to(MEDIA_DIR).as_posix()
    kind = "video" if img.suffix.lower() in VIDEO_EXTS else "image"
    thumb_rel = f"photos/_thumbs/{rel}"
    if kind == "video":
        thumb_rel = str(Path(thumb_rel).with_suffix(".jpg")).replace("\\", "/")
    thumb_abs = (DATA_DIR / thumb_rel).resolve()
    thumb_exists = thumb_abs.exists()
    sc_path = photos_repo.sidecar_path_for(img)
    sc = photos_repo.load_or_init_sidecar_for_image(img) if sc_path.exists() else {}

    people = sc.get("people") or []
    tags = sc.get("tags") or []
    created_at = sc.get("createdAt")
    created_src = sc.get("createdAtSource")
    added_at = sc.get("addedAt")
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
            addedAt=added_at,
            location=loc_obj,
            missing=missing,
        )
    except Exception:
        return None


@router.get("/inbox/all", response_model=GalleryListResponse)
def list_inbox_all(offset: int = 0, limit: int | None = None, before: str | None = None):
    """List inbox photos, optionally returning one page for progressive loading."""
    offset = max(0, offset)
    cached_rels = photos_repo.load_gallery_paths() if limit is not None else []
    if limit is not None and (cached_rels or photos_repo.GALLERY_ORDER_PATH.exists()):
        try:
            added = photos_repo.sync_missing_gallery_items_once()
        except Exception:
            added = 0
        if added:
            cached_rels = photos_repo.load_gallery_paths()

    if limit is not None and cached_rels and photos_repo.GALLERY_ORDER_PATH.exists():
        photos_repo.load_gallery_order()

    partial = False
    if limit is not None:
        images, partial = photos_repo.newest_inbox_images(max(1, min(limit, 500)), before)
        total = len(cached_rels) if cached_rels else None
        offset = 0
    else:
        images = photos_repo.list_inbox_images()
        total = len(images)
        try:
            photos_repo.save_gallery_paths([p.relative_to(MEDIA_DIR).as_posix() for p in images])
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
        items_dicts = [item.model_dump() for item in items]
        photos_repo.sort_gallery_items(items_dicts)
        items = [GalleryItem(**item) for item in items_dicts]
        try:
            photos_repo.save_gallery_order({item.path: item.createdAt for item in items})
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


@router.get("/suggest", response_model=GalleryListResponse)
def suggest_photos(date: str, bbox: str | None = None, limit: int = 200):
    """Suggest inbox photos for a date, optionally limited to a GPS bounding box."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date or ""):
        return JSONResponse({"ok": False, "error": "Invalid date"}, status_code=400)

    bbox_vals: tuple[float, float, float, float] | None = None
    if bbox:
        try:
            parts = [float(value) for value in bbox.split(",")]
            if len(parts) == 4:
                min_lat, min_lon, max_lat, max_lon = parts
                if min_lat > max_lat:
                    min_lat, max_lat = max_lat, min_lat
                if min_lon > max_lon:
                    min_lon, max_lon = max_lon, min_lon
                bbox_vals = (min_lat, min_lon, max_lat, max_lon)
        except Exception:
            bbox_vals = None

    items: list[GalleryItem] = []
    for img in photos_repo.list_inbox_images():
        if len(items) >= max(1, min(int(limit), 1000)):
            break

        rel = img.relative_to(MEDIA_DIR).as_posix()
        sc_path = photos_repo.sidecar_path_for(img)
        sc = photos_repo.load_or_init_sidecar_for_image(img) if sc_path.exists() else {}
        created_at = sc.get("createdAt")
        if not (isinstance(created_at, str) and created_at.startswith(date)):
            continue

        if bbox_vals is not None:
            location = sc.get("location")
            try:
                if not (isinstance(location, dict) and "lat" in location and "lon" in location):
                    continue
                lat = float(location["lat"])
                lon = float(location["lon"])
                min_lat, min_lon, max_lat, max_lon = bbox_vals
                if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
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
        people = [str(value) for value in people if value is not None and str(value).strip()]
        tags = [str(value) for value in tags if value is not None and str(value).strip()]

        raw_location = sc.get("location")
        location_val = None
        if isinstance(raw_location, dict) and "lat" in raw_location and "lon" in raw_location:
            try:
                location_val = {"lat": float(raw_location["lat"]), "lon": float(raw_location["lon"])}
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
                location=location_val,
                missing=False,
            )
        )

    return GalleryListResponse(count=len(items), items=items)

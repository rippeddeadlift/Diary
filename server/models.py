from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class Location(BaseModel):
    lat: float
    lon: float
    source: str = "exif_gps"


class GalleryItem(BaseModel):
    path: str  # relative to data/ (e.g. photos/inbox/.../x.jpg)
    url: str
    hasSidecar: bool
    sidecarPath: Optional[str] = None

    createdAt: Optional[str] = None
    createdAtSource: Optional[str] = None

    location: Optional[Location] = None
    missing: bool = False


class GalleryListResponse(BaseModel):
    ok: bool = True
    count: int
    items: list[GalleryItem]


class UploadSavedItem(BaseModel):
    file: str
    sidecar: str
    originalName: Optional[str] = None


class UploadResponse(BaseModel):
    ok: bool = True
    batch: str
    count: int
    saved: list[UploadSavedItem]

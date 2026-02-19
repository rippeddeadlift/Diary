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

    thumbUrl: Optional[str] = None
    thumbExists: bool = False

    people: list[str] = []
    tags: list[str] = []

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
    duplicatesSkipped: int = 0
    skippedNonImages: int = 0
    errors: list[str] = []


class SidecarModel(BaseModel):
    people: list[str] = []
    tags: list[str] = []
    caption: str = ""

    createdAt: Optional[str] = None
    createdAtSource: Optional[str] = None
    addedAt: Optional[str] = None

    location: Optional[Location] = None
    locationSource: Optional[str] = None

    sha256: Optional[str] = None


class SidecarGetResponse(BaseModel):
    ok: bool = True
    path: str
    sidecarPath: str
    sidecar: SidecarModel


class SidecarUpdateRequest(BaseModel):
    path: str
    people: list[str] = []
    tags: list[str] = []
    caption: str = ""


class SidecarUpdateResponse(BaseModel):
    ok: bool = True
    path: str
    sidecarPath: str
    sidecar: SidecarModel


class SidecarBulkUpdateRequest(BaseModel):
    paths: list[str]
    addPeople: list[str] = []
    removePeople: list[str] = []
    addTags: list[str] = []
    removeTags: list[str] = []


class SidecarBulkUpdateResponse(BaseModel):
    ok: bool = True
    updated: int


class TrashPhotosRequest(BaseModel):
    paths: list[str]


class TrashPhotosResponse(BaseModel):
    ok: bool = True
    trashed: int
    batch: str


class TrashTripsRequest(BaseModel):
    ids: list[str]


class TrashTripsResponse(BaseModel):
    ok: bool = True
    trashed: int
    batch: str


class TripMetaUpdateRequest(BaseModel):
    id: str
    title: str
    tags: list[str] = []


class TripMetaUpdateResponse(BaseModel):
    ok: bool = True

from __future__ import annotations

from fastapi import APIRouter

from ..models import TrashTripsRequest, TrashTripsResponse
from .service import trash_trip_items

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("/trash", response_model=TrashTripsResponse)
def trash_trips(req: TrashTripsRequest):
    trashed, batch = trash_trip_items(req.ids)
    return TrashTripsResponse(trashed=trashed, batch=batch)

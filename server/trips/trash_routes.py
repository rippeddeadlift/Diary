from __future__ import annotations

import json
import shutil
from datetime import datetime
from typing import Any

from fastapi import APIRouter

from ..models import TrashTripsRequest, TrashTripsResponse
from . import paths

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("/trash", response_model=TrashTripsResponse)
def trash_trips(req: TrashTripsRequest):
    dt = datetime.now().astimezone()
    batch = dt.strftime("%Y-%m-%d_%H%M%S")
    trash_batch_dir = paths.TRIPS_TRASH_DIR / batch
    trash_batch_dir.mkdir(parents=True, exist_ok=True)

    if not paths.TRIPS_INDEX.exists():
        return TrashTripsResponse(
            trashed=0,
            batch=str(trash_batch_dir.relative_to(paths.DATA_DIR)).replace("\\", "/"),
        )

    idx = json.loads(paths.TRIPS_INDEX.read_text(encoding="utf-8"))
    trips = list(idx.get("trips") or [])

    by_id: dict[str, dict[str, Any]] = {}
    for trip in trips:
        if isinstance(trip, dict) and isinstance(trip.get("id"), str):
            by_id[trip["id"]] = trip

    trashed = 0
    to_remove: set[str] = set()

    for trip_id in req.ids:
        trip = by_id.get(trip_id)
        if not trip:
            continue
        rel = trip.get("path")
        if not isinstance(rel, str) or not rel.strip():
            continue

        source = (paths.TRIPS_DIR / rel).resolve()
        source_media = (paths.TRIPS_MEDIA_DIR / rel).resolve()
        try:
            source.relative_to(paths.TRIPS_DIR)
            source_media.relative_to(paths.TRIPS_MEDIA_DIR)
        except Exception:
            continue

        if not source.is_dir() or not source_media.is_dir():
            continue

        destination = (trash_batch_dir / rel).resolve()
        destination_media = (paths.TRIPS_MEDIA_TRASH_DIR / batch / rel).resolve()
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
        except Exception:
            try:
                shutil.move(str(source), str(destination))
            except Exception:
                continue

        try:
            destination_media.parent.mkdir(parents=True, exist_ok=True)
            source_media.rename(destination_media)
        except Exception:
            try:
                shutil.move(str(source_media), str(destination_media))
            except Exception:
                try:
                    destination.rename(source)
                except Exception:
                    pass
                continue

        to_remove.add(trip_id)
        trashed += 1

    if to_remove:
        idx["trips"] = [trip for trip in trips if not (isinstance(trip, dict) and trip.get("id") in to_remove)]
        paths.TRIPS_INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return TrashTripsResponse(
        trashed=trashed,
        batch=str(trash_batch_dir.relative_to(paths.DATA_DIR)).replace("\\", "/"),
    )

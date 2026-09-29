from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import DATA_DIR, MEDIA_DIR, ROOT
from ..models import TrashTripsRequest, TrashTripsResponse, TripMetaUpdateRequest, TripMetaUpdateResponse

router = APIRouter(prefix="/api/trips", tags=["trips"])

TRIPS_DIR = DATA_DIR / "trips"
TRIPS_INDEX = TRIPS_DIR / "index.json"
TRIPS_TRASH_DIR = TRIPS_DIR / "_trash"
TRIPS_MEDIA_DIR = MEDIA_DIR / "trips"
TRIPS_MEDIA_TRASH_DIR = TRIPS_MEDIA_DIR / "_trash"


@router.post("/import-gpx")
def import_gpx():
    """Run GPX import (downloads -> data/trips) and archive originals to data/import/gpx/_done."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "tools.import_gpx_inbox"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)

    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    match = re.search(r"Imported:\s*(\d+)\s*GPX", proc.stdout or "")
    imported = int(match.group(1)) if match else None

    if proc.returncode != 0:
        return JSONResponse(
            {"ok": False, "returncode": proc.returncode, "output": output, "imported": imported},
            status_code=500,
        )

    return {"ok": True, "imported": imported, "output": output}


@router.post("/trash", response_model=TrashTripsResponse)
def trash_trips(req: TrashTripsRequest):
    dt = datetime.now().astimezone()
    batch = dt.strftime("%Y-%m-%d_%H%M%S")
    trash_batch_dir = TRIPS_TRASH_DIR / batch
    trash_batch_dir.mkdir(parents=True, exist_ok=True)

    if not TRIPS_INDEX.exists():
        return TrashTripsResponse(trashed=0, batch=str(trash_batch_dir.relative_to(DATA_DIR)).replace("\\", "/"))

    idx = json.loads(TRIPS_INDEX.read_text(encoding="utf-8"))
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

        source = (TRIPS_DIR / rel).resolve()
        source_media = (TRIPS_MEDIA_DIR / rel).resolve()
        try:
            source.relative_to(TRIPS_DIR)
            source_media.relative_to(TRIPS_MEDIA_DIR)
        except Exception:
            continue

        if not source.is_dir() or not source_media.is_dir():
            continue

        destination = (trash_batch_dir / rel).resolve()
        destination_media = (TRIPS_MEDIA_TRASH_DIR / batch / rel).resolve()
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
        except Exception:
            try:
                import shutil

                shutil.move(str(source), str(destination))
            except Exception:
                continue

        try:
            destination_media.parent.mkdir(parents=True, exist_ok=True)
            source_media.rename(destination_media)
        except Exception:
            try:
                import shutil

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
        TRIPS_INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return TrashTripsResponse(trashed=trashed, batch=str(trash_batch_dir.relative_to(DATA_DIR)).replace("\\", "/"))


@router.post("/meta", response_model=TripMetaUpdateResponse)
def update_trip_meta(req: TripMetaUpdateRequest):
    if not TRIPS_INDEX.exists():
        return JSONResponse({"ok": False, "error": "Trips index not found"}, status_code=404)

    idx = json.loads(TRIPS_INDEX.read_text(encoding="utf-8"))
    trips = idx.get("trips", [])

    trip_entry = None
    for trip in trips:
        if trip.get("id") == req.id:
            trip_entry = trip
            break

    if not trip_entry:
        return JSONResponse({"ok": False, "error": f"Trip {req.id} not found"}, status_code=404)

    trip_dir = TRIPS_DIR / trip_entry["path"]
    meta_path = trip_dir / "meta.json"
    if not meta_path.exists():
        return JSONResponse({"ok": False, "error": f"Meta file not found for trip {req.id}"}, status_code=404)

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["title"] = req.title
    meta["tags"] = req.tags
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return TripMetaUpdateResponse(ok=True)


@router.get("/meta")
def get_all_trips_meta():
    if not TRIPS_INDEX.exists():
        return []

    idx = json.loads(TRIPS_INDEX.read_text(encoding="utf-8"))
    trips_list = idx.get("trips", [])

    full_data = []
    for trip in trips_list:
        trip_id = trip.get("id")
        trip_path = trip.get("path")
        meta_file = TRIPS_DIR / trip_path / "meta.json"
        if meta_file.exists():
            meta_content = json.loads(meta_file.read_text(encoding="utf-8"))
            full_data.append({"id": trip_id, "path": trip_path, "meta": meta_content})

    return full_data

from __future__ import annotations

import json
import re
import subprocess
import sys

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..config import ROOT
from ..models import TripMetaUpdateRequest, TripMetaUpdateResponse
from . import paths

router = APIRouter(prefix="/api/trips", tags=["trips"])

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


@router.post("/meta", response_model=TripMetaUpdateResponse)
def update_trip_meta(req: TripMetaUpdateRequest):
    if not paths.TRIPS_INDEX.exists():
        return JSONResponse({"ok": False, "error": "Trips index not found"}, status_code=404)

    idx = json.loads(paths.TRIPS_INDEX.read_text(encoding="utf-8"))
    trips = idx.get("trips", [])

    trip_entry = None
    for trip in trips:
        if trip.get("id") == req.id:
            trip_entry = trip
            break

    if not trip_entry:
        return JSONResponse({"ok": False, "error": f"Trip {req.id} not found"}, status_code=404)

    trip_dir = paths.TRIPS_DIR / trip_entry["path"]
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
    if not paths.TRIPS_INDEX.exists():
        return []

    idx = json.loads(paths.TRIPS_INDEX.read_text(encoding="utf-8"))
    trips_list = idx.get("trips", [])

    full_data = []
    for trip in trips_list:
        trip_id = trip.get("id")
        trip_path = trip.get("path")
        meta_file = paths.TRIPS_DIR / trip_path / "meta.json"
        if meta_file.exists():
            meta_content = json.loads(meta_file.read_text(encoding="utf-8"))
            full_data.append({"id": trip_id, "path": trip_path, "meta": meta_content})

    return full_data

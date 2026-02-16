#!/usr/bin/env python3
"""Backfill photo sidecar JSON with createdAt + location from EXIF.

- Scans: data/photos/inbox/**
- For each image, finds sidecar: <image>.<ext>.json (our upload format)
- If sidecar missing: creates it.
- Fills ONLY missing fields by default (does not overwrite tags/people/caption).

Usage (Windows PowerShell, from repo root):
  python tools/backfill_photo_sidecars.py
  python tools/backfill_photo_sidecars.py --dry-run
  python tools/backfill_photo_sidecars.py --overwrite

Dependencies:
  pip install -r server/requirements.txt

This script is safe: it won't touch the image files.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

import exifread  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
INBOX = ROOT / "data" / "photos" / "inbox"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def safe_json_load(p: Path) -> dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def exif_get_str(tags: dict, *keys: str) -> Optional[str]:
    for k in keys:
        v = tags.get(k)
        if v is not None:
            return str(v)
    return None


def parse_exif_dt(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(s.strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def ratio_to_float(x) -> Optional[float]:
    try:
        num = getattr(x, "num", None)
        den = getattr(x, "den", None)
        if num is not None and den:
            return float(num) / float(den)
        return float(x)
    except Exception:
        return None


def dms_to_deg(dms) -> Optional[float]:
    try:
        parts = list(dms)
        if len(parts) != 3:
            return None
        d = ratio_to_float(parts[0])
        m = ratio_to_float(parts[1])
        s = ratio_to_float(parts[2])
        if d is None or m is None or s is None:
            return None
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def read_exif(path: Path) -> dict:
    with path.open("rb") as f:
        return exifread.process_file(f, details=False)


def extract_created_at_and_location(tags: dict) -> tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
    dt_s = exif_get_str(tags, "EXIF DateTimeOriginal", "Image DateTimeOriginal")
    if not dt_s:
        dt_s = exif_get_str(tags, "EXIF DateTime", "Image DateTime")
    dt = parse_exif_dt(dt_s) if dt_s else None

    offset = exif_get_str(tags, "EXIF OffsetTimeOriginal") or exif_get_str(tags, "EXIF OffsetTimeDigitized")

    created_at = None
    if dt:
        base = dt.strftime("%Y-%m-%dT%H:%M:%S")
        created_at = base + offset if offset else base

    lat = lon = None
    lat_ref = exif_get_str(tags, "GPS GPSLatitudeRef")
    lon_ref = exif_get_str(tags, "GPS GPSLongitudeRef")
    gps_lat = tags.get("GPS GPSLatitude")
    gps_lon = tags.get("GPS GPSLongitude")
    if gps_lat is not None and gps_lon is not None:
        lat = dms_to_deg(gps_lat.values if hasattr(gps_lat, "values") else gps_lat)
        lon = dms_to_deg(gps_lon.values if hasattr(gps_lon, "values") else gps_lon)
        if lat is not None and lat_ref and lat_ref.upper() == "S":
            lat = -lat
        if lon is not None and lon_ref and lon_ref.upper() == "W":
            lon = -lon

    return created_at, ("exif_original" if dt_s else None), lat, lon


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing createdAt/location")
    args = ap.parse_args()

    INBOX.mkdir(parents=True, exist_ok=True)

    images = [p for p in INBOX.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXTS]
    images.sort()

    changed = 0
    for img in images:
        sidecar = img.with_suffix(img.suffix + ".json")
        data: dict[str, Any] = safe_json_load(sidecar) if sidecar.exists() else {}

        # ensure base keys exist
        data.setdefault("people", [])
        data.setdefault("tags", [])
        data.setdefault("caption", "")
        data.setdefault("addedAt", data.get("addedAt") or now_iso())

        created_src = data.get("createdAtSource")
        loc_src = data.get("locationSource")

        # Only backfill if field is missing AND we didn't already mark it as missing
        need_created = args.overwrite or (not data.get("createdAt") and created_src != "missing")
        need_loc = args.overwrite or (not data.get("location") and loc_src != "missing")

        if not need_created and not need_loc:
            continue

        try:
            tags = read_exif(img)
        except Exception:
            tags = {}

        created_at, created_src, lat, lon = extract_created_at_and_location(tags)

        # createdAt
        if need_created:
            if created_at:
                data["createdAt"] = created_at
                data["createdAtSource"] = created_src or "exif"
            else:
                # Mark explicitly missing so repeated runs don't keep touching this file
                data["createdAt"] = None
                data["createdAtSource"] = "missing"

        # location
        if need_loc:
            if lat is not None and lon is not None:
                data["location"] = {"lat": lat, "lon": lon, "source": "exif_gps"}
            else:
                data["location"] = None
                data["locationSource"] = "missing"

        if not args.dry_run:
            sidecar.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        changed += 1

    print(f"Scanned: {len(images)} images")
    print(f"Updated sidecars: {changed}{' (dry-run)' if args.dry_run else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

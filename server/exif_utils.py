from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import exifread  # type: ignore


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
    # Prefer original timestamp
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

    src = "exif_original" if dt_s else None
    return created_at, src, lat, lon

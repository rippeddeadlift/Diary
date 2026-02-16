#!/usr/bin/env python3
"""Debug: inspect photo date + GPS + timezone-related EXIF vs filesystem.

Usage (Windows PowerShell, from repo root):
  python tools/debug_photo_dates.py
  python tools/debug_photo_dates.py --limit 50
  python tools/debug_photo_dates.py --path data/photos/inbox

Dependencies:
  pip install exifread

This script does not modify any files.

Notes:
- Many photos have NO explicit timezone in EXIF. In that case you can only treat
  DateTimeOriginal as a local-naive timestamp.
- Some messengers strip EXIF; then only filesystem timestamps remain.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def dt_iso_local(ts: float) -> str:
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


def parse_exif_dt(s: str) -> Optional[datetime]:
    # EXIF typically: 'YYYY:MM:DD HH:MM:SS'
    try:
        return datetime.strptime(s.strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def _ratio_to_float(x) -> Optional[float]:
    """Convert exifread Ratio or numeric to float."""
    if x is None:
        return None
    try:
        # exifread Ratio has num/den
        num = getattr(x, "num", None)
        den = getattr(x, "den", None)
        if num is not None and den:
            return float(num) / float(den)
        return float(x)
    except Exception:
        return None


def _dms_to_deg(dms) -> Optional[float]:
    try:
        parts = list(dms)
        if len(parts) != 3:
            return None
        d = _ratio_to_float(parts[0])
        m = _ratio_to_float(parts[1])
        s = _ratio_to_float(parts[2])
        if d is None or m is None or s is None:
            return None
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None


def read_exif_tags(path: Path) -> Optional[dict]:
    try:
        import exifread  # type: ignore
    except Exception:
        return None

    try:
        with path.open("rb") as f:
            # details=False keeps it faster/cleaner
            tags = exifread.process_file(f, details=False)
        return tags
    except Exception:
        return None


def get_str(tags: dict, *keys: str) -> Optional[str]:
    for k in keys:
        v = tags.get(k)
        if v is not None:
            return str(v)
    return None


def read_exif_dates_tz_gps(path: Path) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str], Optional[float], Optional[float]]:
    tags = read_exif_tags(path)
    if not tags:
        return (None, None, None, None, None, None, None)

    # Dates
    exif_original = get_str(tags, "EXIF DateTimeOriginal", "Image DateTimeOriginal")
    exif_create = get_str(tags, "EXIF DateTime", "Image DateTime")
    exif_digitized = get_str(tags, "EXIF DateTimeDigitized", "Image DateTimeDigitized")

    # Timezone offset tags (may not exist)
    offset_original = get_str(tags, "EXIF OffsetTimeOriginal")
    offset_digitized = get_str(tags, "EXIF OffsetTimeDigitized")

    # GPS
    lat = lon = None
    lat_ref = get_str(tags, "GPS GPSLatitudeRef")
    lon_ref = get_str(tags, "GPS GPSLongitudeRef")

    gps_lat = tags.get("GPS GPSLatitude")
    gps_lon = tags.get("GPS GPSLongitude")

    if gps_lat is not None and gps_lon is not None:
        lat = _dms_to_deg(gps_lat.values if hasattr(gps_lat, "values") else gps_lat)
        lon = _dms_to_deg(gps_lon.values if hasattr(gps_lon, "values") else gps_lon)
        if lat is not None and lat_ref in {"S", "s"}:
            lat = -lat
        if lon is not None and lon_ref in {"W", "w"}:
            lon = -lon

    # Prefer OffsetTimeOriginal, else digitized
    offset = offset_original or offset_digitized

    return (exif_original, exif_create, exif_digitized, offset, lat_ref + "/" + lon_ref if (lat_ref or lon_ref) else None, lat, lon)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="data/photos/inbox", help="Folder to scan")
    ap.add_argument("--limit", type=int, default=0, help="Max files to print (0 = all)")
    args = ap.parse_args()

    root = Path(args.path)
    if not root.exists():
        print(f"Not found: {root}")
        return 2

    files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXTS]
    files.sort()

    if args.limit and args.limit > 0:
        files = files[: args.limit]

    print(
        "file\texif_original\texif_create\texif_digitized\texif_offset\tgps_ref\tlat\tlon\tfs_mtime\tfs_ctime\tbest_guess\tsource"
    )

    had_any_exif = False
    had_any_offset = False
    had_any_gps = False

    for p in files:
        st = p.stat()
        fs_mtime = dt_iso_local(st.st_mtime)
        fs_ctime = dt_iso_local(st.st_ctime)

        exif_o, exif_c, exif_d, exif_off, gps_ref, lat, lon = read_exif_dates_tz_gps(p)

        if exif_o or exif_c or exif_d:
            had_any_exif = True
        if exif_off:
            had_any_offset = True
        if lat is not None and lon is not None:
            had_any_gps = True

        best = None
        source = None
        for label, val in (
            ("exif_original", exif_o),
            ("exif_create", exif_c),
            ("exif_digitized", exif_d),
        ):
            if val:
                dt = parse_exif_dt(val)
                if dt:
                    # NOTE: dt is timezone-naive; offset is usually missing.
                    best = dt.isoformat(timespec="seconds")
                    source = label
                    break

        if best is None:
            best = fs_mtime
            source = "fs_mtime"

        rel = p.as_posix()
        print(
            f"{rel}\t{exif_o or ''}\t{exif_c or ''}\t{exif_d or ''}\t{exif_off or ''}\t{gps_ref or ''}\t{'' if lat is None else f'{lat:.6f}'}\t{'' if lon is None else f'{lon:.6f}'}\t{fs_mtime}\t{fs_ctime}\t{best}\t{source}"
        )

    if files and not had_any_exif:
        print("\nNOTE: EXIF dates were empty for sampled files.")
        print("If these came via Messenger/Telegram, EXIF may have been stripped.")

    if files and had_any_exif and not had_any_offset:
        print("\nNOTE: No EXIF timezone offset tags found (OffsetTimeOriginal/OffsetTimeDigitized).")
        print("This is common; EXIF often stores local time without timezone.")

    if files and had_any_exif and not had_any_gps:
        print("\nNOTE: No GPS coordinates found in sampled files.")
        print("If you expected location, enable 'Save location' in camera settings and share as file (no EXIF stripping).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

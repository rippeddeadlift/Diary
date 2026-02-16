#!/usr/bin/env python3
"""Debug: print photo date sources (EXIF vs filesystem) for images in data/photos/inbox.

Usage (Windows PowerShell, from repo root):
  python tools/debug_photo_dates.py
  python tools/debug_photo_dates.py --limit 50
  python tools/debug_photo_dates.py --path data/photos/inbox

If you want EXIF support:
  pip install exifread

This script does not modify any files.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def dt_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts).astimezone().isoformat(timespec="seconds")


def parse_exif_dt(s: str) -> Optional[datetime]:
    # EXIF typically: 'YYYY:MM:DD HH:MM:SS'
    try:
        return datetime.strptime(s.strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


@dataclass
class Dates:
    exif_original: Optional[str]
    exif_create: Optional[str]
    exif_digitized: Optional[str]
    fs_mtime: str
    fs_ctime: str


def read_exif_dates(path: Path) -> tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        import exifread  # type: ignore
    except Exception:
        return (None, None, None)

    try:
        with path.open("rb") as f:
            tags = exifread.process_file(f, details=False, stop_tag="EXIF DateTimeOriginal")

        def get(*keys: str) -> Optional[str]:
            for k in keys:
                v = tags.get(k)
                if v is not None:
                    return str(v)
            return None

        return (
            get("EXIF DateTimeOriginal", "Image DateTimeOriginal"),
            get("EXIF DateTime", "Image DateTime"),
            get("EXIF DateTimeDigitized", "Image DateTimeDigitized"),
        )
    except Exception:
        return (None, None, None)


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

    # Header
    print(
        "file\texif_original\texif_create\texif_digitized\tfs_mtime\tfs_ctime\tbest_guess\tsource"
    )

    for p in files:
        st = p.stat()
        exif_o, exif_c, exif_d = read_exif_dates(p)
        fs_mtime = dt_iso(st.st_mtime)
        fs_ctime = dt_iso(st.st_ctime)

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
                    best = dt.replace(tzinfo=timezone.utc).astimezone().isoformat(timespec="seconds")
                    source = label
                    break

        if best is None:
            best = fs_mtime
            source = "fs_mtime"

        rel = p.as_posix()
        print(
            f"{rel}\t{exif_o or ''}\t{exif_c or ''}\t{exif_d or ''}\t{fs_mtime}\t{fs_ctime}\t{best}\t{source}"
        )

    if files and all(read_exif_dates(p) == (None, None, None) for p in files[: min(10, len(files))]):
        print("\nNOTE: EXIF dates are empty for sampled files.")
        print("If these came via Messenger/Telegram, EXIF may have been stripped.")
        print("Install EXIF parsing for this script: pip install exifread")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

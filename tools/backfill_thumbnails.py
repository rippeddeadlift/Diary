#!/usr/bin/env python3
"""Backfill thumbnails for images in data/photos/inbox.

Creates: data/photos/inbox/<batch>/thumbs/<stem>.jpg

Usage (Windows PowerShell, repo root):
  python tools/backfill_thumbnails.py
  python tools/backfill_thumbnails.py --overwrite

Requires:
  pip install -r server/requirements.txt

Does not modify original photos.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from server.config import PHOTOS_INBOX_DIR, IMG_EXTS
from server.thumbs import ensure_thumbnail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    imgs = [p for p in PHOTOS_INBOX_DIR.rglob("*") if p.is_file() and p.suffix.lower() in IMG_EXTS]
    imgs.sort()

    made = 0
    skipped = 0
    for p in imgs:
        out = ensure_thumbnail(p, overwrite=args.overwrite)
        if out is None:
            skipped += 1
        else:
            made += 1

    print(f"Scanned: {len(imgs)} images")
    print(f"Thumbnails ok/created: {made}")
    print(f"Skipped (unsupported/failed): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

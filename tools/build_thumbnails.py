#!/usr/bin/env python3
"""Build global thumbnails for photos.

Creates thumbnails under:
  data/photos/_thumbs/<relative-to-data>/<original-filename>.jpg

Example:
  data/photos/inbox/2026-02-18_0100/foo.jpg
  -> data/photos/_thumbs/photos/inbox/2026-02-18_0100/foo.jpg

Notes:
- Uses EXIF transpose for correct orientation.
- Does not overwrite existing thumbs unless --force.
- Safe for large libraries: iterates files, prints progress.

Usage (from repo root):
  python -m tools.build_thumbnails --max-size 512
  python -m tools.build_thumbnails --max-size 512 --force
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
INBOX_DIR = DATA_DIR / "photos" / "inbox"
THUMBS_ROOT = DATA_DIR / "photos" / "_thumbs"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def iter_images(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() not in IMG_EXTS:
            continue
        if "thumbs" in p.parts:
            continue
        yield p


def thumb_path_for(img: Path) -> Path:
    rel = img.relative_to(DATA_DIR)
    return THUMBS_ROOT / rel


def make_thumb(src: Path, dst: Path, *, max_size: int, quality: int) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        im.save(dst, format="JPEG", quality=quality, optimize=True, progressive=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-size", type=int, default=512)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    THUMBS_ROOT.mkdir(parents=True, exist_ok=True)

    n = 0
    made = 0
    skipped = 0
    errors = 0

    for img in sorted(iter_images(INBOX_DIR)):
        n += 1
        dst = thumb_path_for(img)
        if dst.exists() and not args.force:
            skipped += 1
            continue

        try:
            make_thumb(img, dst, max_size=args.max_size, quality=args.quality)
            made += 1
        except Exception as e:
            errors += 1
            print(f"ERR: {img} -> {dst}: {e}")

        if n % 200 == 0:
            print(f"Scanned: {n} | made: {made} | skipped: {skipped} | errors: {errors}")

    print(f"Done. Scanned: {n} | made: {made} | skipped: {skipped} | errors: {errors}")
    print(f"Thumbs root: {THUMBS_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

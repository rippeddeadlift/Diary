#!/usr/bin/env python3
"""Create a single thumbnail for quick quality testing.

Usage:
    python -m tools.debug_one_thumbnail "photos/inbox/.../file.jpg"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageOps
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.config import DATA_DIR, MEDIA_DIR

THUMBS_ROOT = DATA_DIR / "photos" / "_thumbs"


def thumb_path_for(img: Path) -> Path:
    rel = img.relative_to(MEDIA_DIR)
    return THUMBS_ROOT / rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--max-size", type=int, default=512)
    ap.add_argument("--quality", type=int, default=82)
    args = ap.parse_args()

    src = (MEDIA_DIR / args.path).resolve() if not Path(args.path).is_absolute() else Path(args.path)
    if not src.exists():
        raise SystemExit(f"Not found: {src}")

    dst = thumb_path_for(src)
    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im = im.convert("RGB")
        im.thumbnail((args.max_size, args.max_size), Image.Resampling.LANCZOS)
        im.save(dst, format="JPEG", quality=args.quality, optimize=True, progressive=True)

    print(f"Wrote: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

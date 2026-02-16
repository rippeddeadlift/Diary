from __future__ import annotations

from pathlib import Path
from typing import Optional

from PIL import Image

THUMB_MAX_PX = 256
THUMBS_DIRNAME = "thumbs"
THUMB_EXT = ".jpg"
THUMB_QUALITY = 80


def thumb_path_for_image(img_path: Path) -> Path:
    """Given .../photo.jpg -> .../thumbs/photo.jpg (same stem, jpg)."""
    thumbs_dir = img_path.parent / THUMBS_DIRNAME
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    return thumbs_dir / (img_path.stem + THUMB_EXT)


def ensure_thumbnail(img_path: Path, *, overwrite: bool = False) -> Optional[Path]:
    """Create thumbnail if missing. Returns thumb path or None if unsupported."""
    out = thumb_path_for_image(img_path)
    if out.exists() and not overwrite:
        return out

    # For MVP we try Pillow open; if it can't decode (e.g. HEIC), we skip.
    try:
        with Image.open(img_path) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB_MAX_PX, THUMB_MAX_PX))
            im.save(out, format="JPEG", quality=THUMB_QUALITY, optimize=True)
        return out
    except Exception:
        return None

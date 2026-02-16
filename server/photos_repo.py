from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .config import DATA_DIR, IMG_EXTS, PHOTOS_INBOX_DIR
from .exif_utils import extract_created_at_and_location, read_exif


def now_local_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def batch_folder_name(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d_%H%M")


def safe_name(s: str) -> str:
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._-]+", "", s)
    s = s.strip("._-")
    return s or "file"


def unique_filename(prefix: str, original: str) -> str:
    base = Path(original).name
    stem = safe_name(Path(base).stem)
    ext = Path(base).suffix.lower() or ".bin"
    suffix = f"{os.getpid()}"
    return f"{prefix}_{stem}_{suffix}{ext}"


def is_image_file(p: Path) -> bool:
    return p.suffix.lower() in IMG_EXTS


def sidecar_path_for(img: Path) -> Path:
    return img.with_suffix(img.suffix + ".json")


def resolve_data_path(rel: str) -> Path:
    """Resolve a path relative to DATA_DIR and prevent traversal."""
    rel = rel.lstrip("/\\")
    p = (DATA_DIR / rel).resolve()
    data_root = DATA_DIR.resolve()
    if not str(p).startswith(str(data_root)):
        raise ValueError("Path traversal")
    return p


def load_or_init_sidecar_for_image(img: Path) -> dict[str, Any]:
    sc_path = sidecar_path_for(img)
    if sc_path.exists():
        sc = load_sidecar(sc_path)
    else:
        sc = {}
    return ensure_sidecar_fields(sc)


def update_sidecar_fields(sc: dict[str, Any], people: list[str], tags: list[str], caption: str) -> dict[str, Any]:
    sc = ensure_sidecar_fields(sc)
    sc["people"] = people
    sc["tags"] = tags
    sc["caption"] = caption
    return sc


def load_sidecar(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_sidecar(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def list_inbox_images() -> list[Path]:
    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    for p in PHOTOS_INBOX_DIR.rglob("*"):
        if not p.is_file():
            continue
        if not is_image_file(p):
            continue
        # Ignore generated thumbnails directory
        if "thumbs" in p.parts:
            continue
        files.append(p)

    files.sort()
    return files


def parse_isoish(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def get_created_at_for_sort(sidecar: dict[str, Any], img: Path) -> tuple[bool, Optional[float], Optional[str]]:
    """Return (missing, timestampSeconds, createdAtStr)."""
    created_at = sidecar.get("createdAt")
    created_src = sidecar.get("createdAtSource")

    if not created_at:
        # if no createdAt, treat as missing and push to end.
        # only fallback to mtime for items without sidecar at all.
        if not sidecar:
            created_at = datetime.fromtimestamp(img.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            dt = parse_isoish(created_at)
            return (False, dt.timestamp() if dt else None, created_at)
        return (True, None, None)

    dt = parse_isoish(str(created_at))
    if dt is None:
        return (True, None, None)

    if dt.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        if local_tz is not None:
            dt = dt.replace(tzinfo=local_tz)

    return (False, dt.timestamp(), str(created_at))


def build_sidecar_for_image(img: Path) -> dict[str, Any]:
    created_at = None
    created_src = None
    lat = lon = None
    try:
        tags = read_exif(img)
        created_at, created_src, lat, lon = extract_created_at_and_location(tags)
    except Exception:
        pass

    sidecar: dict[str, Any] = {
        "people": [],
        "tags": [],
        "caption": "",
        "createdAt": created_at,
        "addedAt": now_local_iso(),
    }

    sidecar["createdAtSource"] = created_src or ("missing" if created_at is None else "exif")

    if lat is not None and lon is not None:
        sidecar["location"] = {"lat": lat, "lon": lon, "source": "exif_gps"}
    else:
        sidecar["location"] = None
        sidecar["locationSource"] = "missing"

    return sidecar


def ensure_sidecar_fields(sidecar: dict[str, Any]) -> dict[str, Any]:
    sidecar.setdefault("people", [])
    sidecar.setdefault("tags", [])
    sidecar.setdefault("caption", "")
    if not sidecar.get("addedAt"):
        sidecar["addedAt"] = now_local_iso()
    return sidecar


def sort_gallery_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort gallery items: non-missing first, then createdAt desc. Missing last."""

    local_tz = datetime.now().astimezone().tzinfo

    def sort_key(it: dict[str, Any]):
        is_missing = 1 if it.get("missing") else 0
        dt = parse_isoish(str(it.get("createdAt") or ""))
        if dt is None:
            ts = float("-inf")
        else:
            if dt.tzinfo is None and local_tz is not None:
                dt = dt.replace(tzinfo=local_tz)
            ts = dt.timestamp()
        return (is_missing, -ts)

    items.sort(key=sort_key)
    return items

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import hashlib

from .config import DATA_DIR, IMG_EXTS, PHOTOS_INBOX_DIR

SHA256_INDEX_PATH = DATA_DIR / "photos" / "_sha256_index.json"
GALLERY_ORDER_PATH = DATA_DIR / "photos" / "_gallery_order.json"
GALLERY_PATHS_PATH = DATA_DIR / "photos" / "_gallery_paths.json"
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


def bulk_toggle_sidecar_fields(
    sc: dict[str, Any],
    *,
    add_people: list[str],
    remove_people: list[str],
    add_tags: list[str],
    remove_tags: list[str],
) -> dict[str, Any]:
    sc = ensure_sidecar_fields(sc)

    people = [str(x) for x in (sc.get("people") or []) if x is not None and str(x).strip()]
    tags = [str(x) for x in (sc.get("tags") or []) if x is not None and str(x).strip()]

    def add_many(base: list[str], xs: list[str]) -> list[str]:
        out = list(base)
        for x in xs:
            if x not in out:
                out.append(x)
        return out

    def remove_many(base: list[str], xs: list[str]) -> list[str]:
        return [x for x in base if x not in xs]

    people = add_many(people, add_people)
    people = remove_many(people, remove_people)

    tags = add_many(tags, add_tags)
    tags = remove_many(tags, remove_tags)

    sc["people"] = people
    sc["tags"] = tags
    return sc


def load_sidecar(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_sidecar(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_sha256_index() -> dict[str, str]:
    """hash -> relative path (posix)"""
    try:
        if SHA256_INDEX_PATH.exists():
            data = json.loads(SHA256_INDEX_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_sha256_index(idx: dict[str, str]) -> None:
    SHA256_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHA256_INDEX_PATH.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def iter_inbox_images():
    """Yield inbox images as they are found. Does not sort or buffer the whole tree."""
    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    for p in PHOTOS_INBOX_DIR.rglob("*"):
        if not p.is_file():
            continue
        if not is_image_file(p):
            continue
        if "thumbs" in p.parts:
            continue
        yield p


def _sidecar_created_at(img: Path) -> str | None:
    sc_path = sidecar_path_for(img)
    if not sc_path.exists():
        return None
    try:
        data = json.loads(sc_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    created = data.get("createdAt")
    return str(created) if created else None


def _page_from_order(limit: int, before_path: str | None) -> tuple[list[Path], bool] | None:
    order = load_gallery_order()
    if not order:
        return None
    ranked = [rel for rel in sorted(order, key=lambda rel: order_sort_key(rel, order.get(rel))) if order.get(rel)]
    if before_path:
        try:
            start = ranked.index(before_path) + 1
        except ValueError:
            start = 0
    else:
        start = 0
    page: list[Path] = []
    for rel in ranked[start:]:
        try:
            img = resolve_data_path(rel)
        except ValueError:
            continue
        if img.is_file():
            page.append(img)
        if len(page) >= limit:
            break
    return page, start + len(page) < len(ranked)


def newest_inbox_images(limit: int, before_path: str | None = None) -> tuple[list[Path], bool]:
    """Return the next dated photos after ``before_path`` in newest-first order.

    Uses the date cache when it exists. Otherwise only batch folders old enough
    to contain the next page are opened.
    """
    limit = max(1, limit)
    cached = _page_from_order(limit, before_path)
    if cached is not None:
        return cached
    cursor_created = ""
    if before_path:
        try:
            cursor_created = _sidecar_created_at(resolve_data_path(before_path)) or ""
        except ValueError:
            cursor_created = ""
    cursor_day = cursor_created[:10]
    cursor_key = order_sort_key(before_path, cursor_created) if before_path else None

    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    folders = [p for p in PHOTOS_INBOX_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")]
    loose = [p for p in PHOTOS_INBOX_DIR.iterdir() if p.is_file() and is_image_file(p)]
    folders.sort(key=lambda p: p.name, reverse=True)
    # Loose files have no batch date, so read them before assuming the page is complete.
    folders.append(PHOTOS_INBOX_DIR)

    found: list[tuple[str, Path]] = []
    scanned_all = True
    for folder in folders:
        if cursor_day and folder != PHOTOS_INBOX_DIR and folder.name[:10] > cursor_day:
            continue
        children = loose if folder == PHOTOS_INBOX_DIR else folder.rglob("*")
        for img in children:
            if not img.is_file() or not is_image_file(img) or "thumbs" in img.parts:
                continue
            created = _sidecar_created_at(img)
            if not created:
                continue
            rel = img.relative_to(DATA_DIR).as_posix()
            if cursor_key is not None and order_sort_key(rel, created) <= cursor_key:
                continue
            found.append((created, img))
        if len(found) >= limit and folder != PHOTOS_INBOX_DIR and folder.name[:10] < cursor_day:
            scanned_all = False
            break

    found.sort(key=lambda pair: order_sort_key(pair[1].as_posix(), pair[0]))
    page = [img for _, img in found[:limit]]
    return page, not scanned_all or len(found) > limit


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


def load_gallery_paths() -> list[str]:
    try:
        if GALLERY_PATHS_PATH.exists():
            data = json.loads(GALLERY_PATHS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(x) for x in data]
    except Exception:
        pass
    return []


def save_gallery_paths(rels: list[str]) -> None:
    GALLERY_PATHS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GALLERY_PATHS_PATH.write_text(json.dumps(rels, ensure_ascii=False) + "\n", encoding="utf-8")


def load_gallery_order() -> dict[str, str | None]:
    """rel path -> createdAt from the last full gallery pass. None means missing."""
    try:
        if GALLERY_ORDER_PATH.exists():
            data = json.loads(GALLERY_ORDER_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): (None if v is None else str(v)) for k, v in data.items()}
    except Exception:
        pass
    return {}


def save_gallery_order(order: dict[str, str | None]) -> None:
    GALLERY_ORDER_PATH.parent.mkdir(parents=True, exist_ok=True)
    GALLERY_ORDER_PATH.write_text(json.dumps(order, ensure_ascii=False) + "\n", encoding="utf-8")


def order_sort_key(rel: str, created_at: str | None):
    """Same order as sort_gallery_items: dated photos first (newest), missing last."""
    if not created_at:
        return (1, 0.0, rel)
    dt = parse_isoish(created_at)
    if dt is None:
        return (1, 0.0, rel)
    if dt.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo
        if local_tz is not None:
            dt = dt.replace(tzinfo=local_tz)
    return (0, -dt.timestamp(), rel)


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

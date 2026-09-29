from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from ..config import DATA_DIR, MEDIA_DIR, PHOTOS_INBOX_DIR
from . import repository

GALLERY_ORDER_PATH = DATA_DIR / "photos" / "_gallery_order.json"
GALLERY_PATHS_PATH = DATA_DIR / "photos" / "_gallery_paths.json"
_BATCH_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{4}$")

_ranked_rels: list[str] | None = None
_ranked_index: dict[str, int] | None = None
_gallery_disk_synced = False


def reset_gallery_cache() -> None:
    global _gallery_disk_synced
    _gallery_disk_synced = False
    invalidate_gallery_rank()


def iter_inbox_images():
    """Yield eligible inbox media without sorting or buffering the tree."""
    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    for path in PHOTOS_INBOX_DIR.rglob("*"):
        if not path.is_file() or not repository.is_media_file(path):
            continue
        if "thumbs" in path.parts or repository.is_live_photo_video_file(path):
            continue
        yield path


def _sidecar_created_at(img: Path) -> str | None:
    sidecar_path = repository.sidecar_path_for(img)
    if not sidecar_path.exists():
        return None
    try:
        data = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    created = data.get("createdAt")
    return str(created) if created else None


def invalidate_gallery_rank() -> None:
    global _ranked_rels, _ranked_index
    _ranked_rels = None
    _ranked_index = None


def ranked_gallery_rels() -> list[str]:
    """Return cached gallery paths ordered newest-first by capture date."""
    global _ranked_rels, _ranked_index
    if _ranked_rels is None:
        order = load_gallery_order()
        _ranked_rels = sorted(order, key=lambda rel: order_sort_key(rel, order.get(rel)))
        _ranked_index = {rel: index for index, rel in enumerate(_ranked_rels)}
    return _ranked_rels


def _page_from_order(limit: int, before_path: str | None) -> tuple[list[Path], bool] | None:
    ranked = ranked_gallery_rels()
    if not ranked:
        return None
    if before_path:
        start = (_ranked_index or {}).get(before_path)
        start = 0 if start is None else start + 1
    else:
        start = 0

    page: list[Path] = []
    for rel in ranked[start:]:
        try:
            img = repository.resolve_media_path(rel)
        except ValueError:
            continue
        if img.is_file():
            page.append(img)
        if len(page) >= limit:
            break
    return page, start + len(page) < len(ranked)


def newest_inbox_images(limit: int, before_path: str | None = None) -> tuple[list[Path], bool]:
    """Return a page of inbox images in newest-first capture-date order."""
    limit = max(1, limit)
    cached = _page_from_order(limit, before_path)
    if cached is not None:
        return cached

    cursor_created = ""
    if before_path:
        try:
            cursor_created = _sidecar_created_at(repository.resolve_media_path(before_path)) or ""
        except ValueError:
            cursor_created = ""
    cursor_day = cursor_created[:10]
    cursor_key = order_sort_key(before_path, cursor_created) if before_path else None

    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    folders = [path for path in PHOTOS_INBOX_DIR.iterdir() if path.is_dir() and not path.name.startswith("_")]
    loose = [path for path in PHOTOS_INBOX_DIR.iterdir() if path.is_file() and repository.is_media_file(path)]
    folders.sort(key=lambda path: path.name, reverse=True)
    folders.append(PHOTOS_INBOX_DIR)

    found: list[tuple[str, Path]] = []
    scanned_all = True
    for folder in folders:
        if cursor_day and folder != PHOTOS_INBOX_DIR and folder.name[:10] > cursor_day:
            continue
        children = loose if folder == PHOTOS_INBOX_DIR else folder.rglob("*")
        for img in children:
            if not img.is_file() or not repository.is_media_file(img) or "thumbs" in img.parts:
                continue
            created = _sidecar_created_at(img)
            rel = img.relative_to(MEDIA_DIR).as_posix()
            if cursor_key is not None and order_sort_key(rel, created) <= cursor_key:
                continue
            found.append((created or "", img))
        if len(found) >= limit and folder != PHOTOS_INBOX_DIR and folder.name[:10] < cursor_day:
            scanned_all = False
            break

    found.sort(key=lambda pair: order_sort_key(pair[1].as_posix(), pair[0]))
    page = [img for _, img in found[:limit]]
    return page, not scanned_all or len(found) > limit


def list_inbox_images() -> list[Path]:
    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        path
        for path in PHOTOS_INBOX_DIR.rglob("*")
        if path.is_file()
        and repository.is_media_file(path)
        and "thumbs" not in path.parts
        and not repository.is_live_photo_video_file(path)
    ]
    files.sort()
    return files


def load_gallery_paths() -> list[str]:
    try:
        if GALLERY_PATHS_PATH.exists():
            data = json.loads(GALLERY_PATHS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [str(value) for value in data]
    except Exception:
        pass
    return []


def save_gallery_paths(rels: list[str]) -> None:
    GALLERY_PATHS_PATH.parent.mkdir(parents=True, exist_ok=True)
    GALLERY_PATHS_PATH.write_text(json.dumps(rels, ensure_ascii=False) + "\n", encoding="utf-8")


def load_gallery_order() -> dict[str, str | None]:
    """Load the cached mapping from media path to capture date."""
    try:
        if GALLERY_ORDER_PATH.exists():
            data = json.loads(GALLERY_ORDER_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(key): (None if value is None else str(value)) for key, value in data.items()}
    except Exception:
        pass
    return {}


def save_gallery_order(order: dict[str, str | None]) -> None:
    GALLERY_ORDER_PATH.parent.mkdir(parents=True, exist_ok=True)
    GALLERY_ORDER_PATH.write_text(json.dumps(order, ensure_ascii=False) + "\n", encoding="utf-8")
    invalidate_gallery_rank()


def remember_gallery_items(rels_with_created: list[tuple[str, str | None]]) -> None:
    """Add newly uploaded media to gallery path and date caches."""
    if not rels_with_created:
        return
    order = load_gallery_order()
    paths = load_gallery_paths()
    known = set(paths)
    changed = False
    for rel, created in rels_with_created:
        rel = rel.replace("\\", "/")
        if rel not in order or order.get(rel) != created:
            order[rel] = created
            changed = True
        if rel not in known:
            paths.append(rel)
            known.add(rel)
            changed = True
    if not changed:
        return
    save_gallery_order(order)
    save_gallery_paths(paths)


def forget_gallery_items(rels: list[str]) -> None:
    """Remove trashed media from the gallery path and date caches."""
    if not rels:
        return
    drop = {rel.replace("\\", "/") for rel in rels}
    order = load_gallery_order()
    paths = load_gallery_paths()
    new_order = {rel: created for rel, created in order.items() if rel not in drop}
    new_paths = [rel for rel in paths if rel not in drop]
    if len(new_order) != len(order):
        save_gallery_order(new_order)
    if len(new_paths) != len(paths):
        save_gallery_paths(new_paths)


def gallery_cache_watermark() -> str:
    """Return the newest batch-folder name already present in the gallery cache."""
    mark = ""
    for rel in load_gallery_paths():
        parts = rel.replace("\\", "/").split("/")
        if "inbox" not in parts:
            continue
        index = parts.index("inbox") + 1
        if index >= len(parts) - 1:
            continue
        folder = parts[index]
        if _BATCH_FOLDER.match(folder) and folder > mark:
            mark = folder
    return mark


def sync_missing_gallery_items() -> int:
    """Add inbox media dropped on disk since the last gallery cache update."""
    order = load_gallery_order()
    if not order and not GALLERY_PATHS_PATH.exists():
        return 0
    known = set(order) | set(load_gallery_paths())
    watermark = gallery_cache_watermark()
    missing: list[tuple[str, str | None]] = []

    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)
    folders = [path for path in PHOTOS_INBOX_DIR.iterdir() if path.is_dir() and not path.name.startswith("_")]
    for folder in folders:
        if watermark and folder.name < watermark:
            continue
        for img in folder.rglob("*"):
            if not img.is_file() or not repository.is_media_file(img) or "thumbs" in img.parts:
                continue
            if repository.is_live_photo_video_file(img):
                continue
            rel = img.relative_to(MEDIA_DIR).as_posix()
            if rel in known:
                continue
            missing.append((rel, _sidecar_created_at(img)))

    for img in PHOTOS_INBOX_DIR.iterdir():
        if not img.is_file() or not repository.is_media_file(img) or repository.is_live_photo_video_file(img):
            continue
        rel = img.relative_to(MEDIA_DIR).as_posix()
        if rel not in known:
            missing.append((rel, _sidecar_created_at(img)))

    if missing:
        remember_gallery_items(missing)
    return len(missing)


def sync_missing_gallery_items_once() -> int:
    """Catch up the disk-backed gallery cache at most once per process."""
    global _gallery_disk_synced
    if _gallery_disk_synced:
        return 0
    ranked_gallery_rels()
    added = sync_missing_gallery_items()
    if added:
        invalidate_gallery_rank()
    _gallery_disk_synced = True
    return added


def order_sort_key(rel: str, created_at: str | None):
    """Sort dated photos newest-first, followed by items without a date."""
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


def parse_isoish(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def get_created_at_for_sort(sidecar: dict[str, Any], img: Path) -> tuple[bool, Optional[float], Optional[str]]:
    """Return (missing, timestamp, createdAt), falling back to mtime without sidecar."""
    created_at = sidecar.get("createdAt")
    if not created_at:
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


def sort_gallery_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort gallery items by capture date, leaving undated items last."""
    local_tz = datetime.now().astimezone().tzinfo

    def sort_key(item: dict[str, Any]):
        is_missing = 1 if item.get("missing") else 0
        dt = parse_isoish(str(item.get("createdAt") or ""))
        if dt is None:
            timestamp = float("-inf")
        else:
            if dt.tzinfo is None and local_tz is not None:
                dt = dt.replace(tzinfo=local_tz)
            timestamp = dt.timestamp()
        return (is_missing, -timestamp)

    items.sort(key=sort_key)
    return items

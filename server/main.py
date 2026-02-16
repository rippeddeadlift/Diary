from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import exifread  # type: ignore

APP_TITLE = "Diary Upload Server"

# Diary/ (repo root) is parent of this file's directory
ROOT = Path(__file__).resolve().parents[1]
PHOTOS_INBOX_DIR = ROOT / "data" / "photos" / "inbox"


def now_local_iso() -> str:
    # naive local time is fine for our use case; include offset if available
    return datetime.now().astimezone().isoformat(timespec="seconds")


def batch_folder_name(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d_%H%M")


def safe_name(s: str) -> str:
    # Keep ascii-ish, avoid weird filesystem chars.
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._-]+", "", s)
    s = s.strip("._-")
    return s or "file"


def unique_filename(prefix: str, original: str) -> str:
    # Prefix: 2026-02-16T173512
    base = Path(original).name
    stem = safe_name(Path(base).stem)
    ext = Path(base).suffix.lower()
    if not ext:
        ext = ".bin"

    # Add a small random-ish suffix to reduce collisions
    # (no need for crypto randomness here)
    suffix = f"{os.getpid()}"
    return f"{prefix}_{stem}_{suffix}{ext}"


app = FastAPI(title=APP_TITLE)

# Read-only access to Diary/data for the gallery (served under /files)
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(DATA_DIR)), name="files")


@app.get("/api/health")
def health():
    return {"ok": True, "time": now_local_iso()}


def is_image_file(p: Path) -> bool:
    return p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def _exif_get_str(tags: dict, *keys: str) -> Optional[str]:
    for k in keys:
        v = tags.get(k)
        if v is not None:
            return str(v)
    return None


def _parse_exif_dt(s: str) -> Optional[datetime]:
    try:
        return datetime.strptime(s.strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def _ratio_to_float(x) -> Optional[float]:
    try:
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


def read_exif(path: Path) -> dict:
    with path.open("rb") as f:
        return exifread.process_file(f, details=False)


def extract_created_at_and_location(tags: dict) -> tuple[Optional[str], Optional[str], Optional[float], Optional[float]]:
    # Prefer original timestamp
    dt_s = _exif_get_str(tags, "EXIF DateTimeOriginal", "Image DateTimeOriginal")
    if not dt_s:
        dt_s = _exif_get_str(tags, "EXIF DateTime", "Image DateTime")

    dt = _parse_exif_dt(dt_s) if dt_s else None

    offset = _exif_get_str(tags, "EXIF OffsetTimeOriginal") or _exif_get_str(tags, "EXIF OffsetTimeDigitized")

    created_at = None
    if dt:
        base = dt.strftime("%Y-%m-%dT%H:%M:%S")
        created_at = base + offset if offset else base

    lat = lon = None
    lat_ref = _exif_get_str(tags, "GPS GPSLatitudeRef")
    lon_ref = _exif_get_str(tags, "GPS GPSLongitudeRef")
    gps_lat = tags.get("GPS GPSLatitude")
    gps_lon = tags.get("GPS GPSLongitude")

    if gps_lat is not None and gps_lon is not None:
        lat = _dms_to_deg(gps_lat.values if hasattr(gps_lat, "values") else gps_lat)
        lon = _dms_to_deg(gps_lon.values if hasattr(gps_lon, "values") else gps_lon)
        if lat is not None and lat_ref and lat_ref.upper() == "S":
            lat = -lat
        if lon is not None and lon_ref and lon_ref.upper() == "W":
            lon = -lon

    src = "exif_original" if dt_s else None
    return created_at, src, lat, lon


def _parse_isoish(s: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


@app.get("/api/photos/inbox/all")
def list_inbox_all():
    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    items: list[dict[str, Any]] = []
    for p in sorted(PHOTOS_INBOX_DIR.rglob("*")):
        if not p.is_file():
            continue
        if not is_image_file(p):
            continue

        rel = p.relative_to(DATA_DIR).as_posix()  # e.g. photos/inbox/.../x.jpg
        sidecar_path = p.with_suffix(p.suffix + ".json")

        created_at = None
        location = None

        if sidecar_path.exists():
            try:
                sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                created_at = sidecar.get("createdAt")
                location = sidecar.get("location")
            except Exception:
                pass

        # Fallback: if createdAt missing, use filesystem mtime (still useful for ordering)
        if not created_at:
            created_at = datetime.fromtimestamp(p.stat().st_mtime).astimezone().isoformat(timespec="seconds")

        items.append(
            {
                "path": rel,
                "url": f"/files/{rel}",
                "hasSidecar": sidecar_path.exists(),
                "sidecarPath": sidecar_path.relative_to(DATA_DIR).as_posix() if sidecar_path.exists() else None,
                "createdAt": created_at,
                "location": location,
            }
        )

    def sort_key(it: dict[str, Any]):
        dt = _parse_isoish(str(it.get("createdAt") or ""))
        return dt or datetime.min

    # newest first
    items.sort(key=sort_key, reverse=True)

    return {"ok": True, "count": len(items), "items": items}


@app.post("/api/photos/upload")
async def upload_photos(files: List[UploadFile] = File(...)):
    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)

    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    saved = []
    for f in files:
        out_name = unique_filename(prefix, f.filename or "upload")
        out_path = batch_dir / out_name

        # Save file
        with out_path.open("wb") as w:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                w.write(chunk)

        # Extract EXIF (createdAt + GPS) without modifying the image
        created_at = None
        created_src = None
        lat = lon = None
        try:
            tags = read_exif(out_path)
            created_at, created_src, lat, lon = extract_created_at_and_location(tags)
        except Exception:
            pass

        # Sidecar JSON next to image
        sidecar_path = out_path.with_suffix(out_path.suffix + ".json")
        sidecar: dict[str, Any] = {
            "people": [],
            "tags": [],
            "caption": "",
            "createdAt": created_at,
            "addedAt": now_local_iso(),
        }
        if created_src:
            sidecar["createdAtSource"] = created_src
        if lat is not None and lon is not None:
            sidecar["location"] = {"lat": lat, "lon": lon, "source": "exif_gps"}

        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        saved.append(
            {
                "file": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "sidecar": str(sidecar_path.relative_to(ROOT)).replace("\\", "/"),
                "originalName": f.filename,
            }
        )

    return JSONResponse(
        {
            "ok": True,
            "batch": str(batch_dir.relative_to(ROOT)).replace("\\", "/"),
            "count": len(saved),
            "saved": saved,
        }
    )

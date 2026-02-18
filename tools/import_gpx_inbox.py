#!/usr/bin/env python3
"""Import GPX files into Diary data/trips.

Phase 1 MVP:
- Scan a source folder (default: Windows Downloads) for *.gpx
- Import each GPX directly into Diary/data/trips/<YYYY-MM-DD>-<slug>/
- After successful import, move the original GPX into Diary/data/import/gpx/_done/

Usage (PowerShell, from repo root):
  python tools/import_gpx_inbox.py
  python tools/import_gpx_inbox.py --source "C:\\Users\\ivank\\Downloads"
  python tools/import_gpx_inbox.py --dry-run

This script does NOT upload anything. It only moves/creates local files.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

# Optional: auto-fill computed fields after import
from tools.update_trip_meta_from_gpx import gpx_distance_km, gpx_duration_minutes, gpx_preview, gpx_max_kmh

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
IMPORT_DIR = DATA_DIR / "import" / "gpx"
DONE_DIR = IMPORT_DIR / "_done"
TRIPS_DIR = DATA_DIR / "trips"
INDEX_PATH = TRIPS_DIR / "index.json"


def slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9-]+", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "tour"


def guess_title_from_filename(name: str) -> str:
    """Derive a human title from a Komoot-ish filename.

    Examples:
      2026-02-15_2786323503_Fahrradtour.gpx -> Fahrradtour
      2025-11-03_2666929067_Gravel-Fahrt.gpx -> Gravel Fahrt
      something (1).gpx -> something
    """

    base = Path(name).stem

    # Remove duplicate suffix like " (1)"
    base = re.sub(r"\s*\(\d+\)\s*$", "", base)

    # Split by underscores first (Komoot uses _ between date/id/title)
    parts = [p for p in base.split("_") if p]

    # Drop leading date part if present
    if parts and re.fullmatch(r"\d{4}-\d{2}-\d{2}", parts[0]):
        parts = parts[1:]

    # Drop leading numeric id part if present
    if parts and re.fullmatch(r"\d{6,}", parts[0]):
        parts = parts[1:]

    base = "_".join(parts) if parts else base

    # Replace separators with spaces and collapse whitespace
    base = re.sub(r"[_-]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()

    return base or "Tour"


def infer_tags_from_title(title: str) -> list[str]:
    t = title.lower()
    tags: list[str] = []

    def has(*words: str) -> bool:
        return any(w in t for w in words)

    if has("fahrrad", "radtour", "rad ", "radfahren", "cycling", "bike", "gravel", "rennrad"):
        tags.append("cycling")

    if has("wandern", "wanderung", "hike", "hiking", "spaziergang"):
        tags.append("hiking")

    # Avoid false positive: "Langlauf" is skiing, not running.
    if "langlauf" not in t and has("laufen", "jog", "jogging", " run", "running", "trailrun", "trail-running"):
        tags.append("running")

    if has(
        "ski",
        "skifahren",
        "langlauf",
        "loipe",
        "skitour",
        "ski tour",
        "cross-country",
        "xc-ski",
    ):
        tags.append("skiing")

    # de-dup, stable order
    out: list[str] = []
    for x in tags:
        if x not in out:
            out.append(x)
    return out


def parse_gpx_date(gpx_path: Path) -> Optional[str]:
    """Return YYYY-MM-DD if we can find a timestamp in the GPX."""
    try:
        tree = ET.parse(gpx_path)
        root = tree.getroot()

        # GPX namespace handling: match by local-name
        def iter_times():
            for el in root.iter():
                if el.tag.endswith("time") and el.text:
                    yield el.text.strip()

        for t in iter_times():
            # Examples: 2026-02-15T10:11:12Z or 2026-02-15T10:11:12+01:00
            try:
                dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                return dt.date().isoformat()
            except Exception:
                continue
        return None
    except Exception:
        return None


def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {"version": 1, "trips": []}


def save_index(idx: dict, *, dry_run: bool) -> None:
    if dry_run:
        return
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_unique_trip_id(base_id: str, idx: dict) -> str:
    existing = {t.get("id") for t in idx.get("trips", [])}
    if base_id not in existing:
        return base_id
    i = 2
    while f"{base_id}-{i}" in existing:
        i += 1
    return f"{base_id}-{i}"


def move_file(src: Path, dst: Path, *, dry_run: bool) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        return
    shutil.move(str(src), str(dst))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source",
        default=str(Path.home() / "Downloads"),
        help="Folder to scan for newly downloaded .gpx files (default: ~/Downloads)",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    source_dir = Path(args.source)
    dry = bool(args.dry_run)

    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    DONE_DIR.mkdir(parents=True, exist_ok=True)
    TRIPS_DIR.mkdir(parents=True, exist_ok=True)

    idx = load_index()
    trips = idx.get("trips", [])

    imported = 0

    # Import directly from Downloads
    if source_dir.exists():
        for gpx in sorted(source_dir.glob("*.gpx")):
            if gpx.name.endswith(".crdownload"):
                continue
            date = parse_gpx_date(gpx)
            if not date:
                # fallback: file mtime
                date = datetime.fromtimestamp(gpx.stat().st_mtime).date().isoformat()

            title = guess_title_from_filename(gpx.name)
            base_id = f"{date}-{slugify(title)[:40]}"
            trip_id = ensure_unique_trip_id(base_id, idx)
            trip_path = TRIPS_DIR / trip_id

            # Create folder
            if not dry:
                trip_path.mkdir(parents=True, exist_ok=True)

            # Choose destination name
            dst_gpx = trip_path / gpx.name
            if dst_gpx.exists():
                dst_gpx = trip_path / f"route{gpx.suffix}"

            # Copy into trip folder first (so we only archive/delete source after success)
            dst_gpx.parent.mkdir(parents=True, exist_ok=True)
            if not dry:
                shutil.copy2(str(gpx), str(dst_gpx))

            # meta.json
            # Compute distance/duration/preview (best-effort)
            distance_km = None
            duration_min = None
            preview = None
            try:
                distance_km = round(gpx_distance_km(dst_gpx), 2)
            except Exception:
                distance_km = None
            try:
                dur = gpx_duration_minutes(dst_gpx)
                duration_min = int(round(dur)) if dur is not None else None
            except Exception:
                duration_min = None
            try:
                preview = gpx_preview(dst_gpx)
            except Exception:
                preview = None
            try:
                mk = gpx_max_kmh(dst_gpx)
                max_kmh = round(float(mk), 1) if mk is not None else None
            except Exception:
                max_kmh = None

            meta = {
                "id": trip_id,
                "title": title,
                "date": date,
                "tags": infer_tags_from_title(title),
                "gpx": dst_gpx.name,
            }
            if distance_km is not None:
                meta["distanceKm"] = distance_km
            if duration_min is not None:
                meta["durationMin"] = duration_min
            if distance_km is not None and duration_min is not None and duration_min > 0:
                meta["avgKmh"] = round(float(distance_km) / (float(duration_min) / 60.0), 1)
            if max_kmh is not None:
                meta["maxKmh"] = max_kmh
            if preview is not None:
                meta["preview"] = preview
            meta_path = trip_path / "meta.json"
            if not dry:
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            # index.json update (prepend newest)
            if not any(t.get("id") == trip_id for t in trips):
                trips.insert(0, {"id": trip_id, "path": trip_id})

            # Archive original GPX into _done
            done_target = DONE_DIR / gpx.name
            if done_target.exists():
                done_target = DONE_DIR / f"{gpx.stem}_{int(gpx.stat().st_mtime)}{gpx.suffix}"
            if not dry:
                shutil.move(str(gpx), str(done_target))

            imported += 1

    idx["trips"] = trips
    save_index(idx, dry_run=dry)

    print(f"Imported: {imported} GPX")
    print(f"Trips index: {INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

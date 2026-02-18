#!/usr/bin/env python3
"""Update trip meta.json with distanceKm computed from GPX tracks.

- Reads ../trips/index.json
- For each trip: loads meta.json and GPX (meta.gpx)
- Computes track distance (Haversine) and writes meta.distanceKm if missing

Usage (from tools dir or anywhere):
  python tools/update_trip_meta_from_gpx.py

Notes:
- Keeps date format in meta.json as ISO (YYYY-MM-DD)
- distanceKm stored with 2 decimals
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TRIPS_DIR = ROOT / "data" / "trips"
INDEX = TRIPS_DIR / "index.json"

NS = {"g": "http://www.topografix.com/GPX/1/1"}


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def gpx_points_latlon(path: Path) -> list[tuple[float, float]]:
    root = ET.parse(path).getroot()
    pts: list[tuple[float, float]] = []
    for trkpt in root.findall(".//g:trkpt", NS):
        try:
            lat = float(trkpt.attrib["lat"])
            lon = float(trkpt.attrib["lon"])
            pts.append((lat, lon))
        except Exception:
            continue
    return pts


def gpx_distance_km(path: Path) -> float:
    pts = gpx_points_latlon(path)

    if len(pts) < 2:
        return 0.0

    dist = 0.0
    for (a, b), (c, d) in zip(pts, pts[1:]):
        dist += haversine_m(a, b, c, d)

    return dist / 1000.0


def gpx_preview(path: Path, *, max_points: int = 200) -> dict | None:
    pts = gpx_points_latlon(path)
    if len(pts) < 2:
        return None

    # sample evenly down to max_points
    if len(pts) > max_points:
        step = max(1, len(pts) // max_points)
        pts = pts[::step]
        if len(pts) > max_points:
            pts = pts[:max_points]

    lats = [p[0] for p in pts]
    lons = [p[1] for p in pts]
    bbox = [min(lats), min(lons), max(lats), max(lons)]

    return {"bbox": bbox, "points": [[a, b] for (a, b) in pts]}


def gpx_duration_minutes(path: Path) -> float | None:
    """Return duration in minutes based on first/last <time> in trkpt (if present)."""
    try:
        root = ET.parse(path).getroot()
        times: list[str] = []
        for trkpt in root.findall(".//g:trkpt", NS):
            t_el = trkpt.find("g:time", NS)
            if t_el is not None and t_el.text:
                times.append(t_el.text.strip())

        if len(times) < 2:
            return None

        from datetime import datetime

        def parse(t: str) -> datetime | None:
            try:
                return datetime.fromisoformat(t.replace("Z", "+00:00"))
            except Exception:
                return None

        start = parse(times[0])
        end = parse(times[-1])
        if not start or not end:
            return None

        sec = (end - start).total_seconds()
        if sec <= 0:
            return None
        return sec / 60.0
    except Exception:
        return None


def main() -> None:
    idx = json.loads(INDEX.read_text(encoding="utf-8"))
    trips = idx.get("trips", [])

    changed = 0
    for t in trips:
        rel = t.get("path")
        if not rel:
            continue

        trip_dir = TRIPS_DIR / rel
        meta_path = trip_dir / "meta.json"
        if not meta_path.exists():
            continue

        meta = json.loads(meta_path.read_text(encoding="utf-8"))

        gpx_name = meta.get("gpx")
        if not gpx_name:
            continue

        gpx_path = trip_dir / gpx_name
        if not gpx_path.exists():
            continue

        did_change = False

        # distance
        if meta.get("distanceKm") is None:
            km = round(gpx_distance_km(gpx_path), 2)
            meta["distanceKm"] = km
            did_change = True

        # duration
        if meta.get("durationMin") is None:
            dur = gpx_duration_minutes(gpx_path)
            if dur is not None:
                meta["durationMin"] = int(round(dur))
                did_change = True

        # avg speed (km/h)
        if meta.get("avgKmh") is None:
            try:
                km = meta.get("distanceKm")
                mins = meta.get("durationMin")
                if isinstance(km, (int, float)) and isinstance(mins, (int, float)) and mins > 0:
                    meta["avgKmh"] = round(float(km) / (float(mins) / 60.0), 1)
                    did_change = True
            except Exception:
                pass

        # preview polyline
        if meta.get("preview") is None:
            prev = gpx_preview(gpx_path)
            if prev is not None:
                meta["preview"] = prev
                did_change = True

        if did_change:
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed += 1
            print(
                f"Updated {rel}:"
                + (f" distanceKm={meta.get('distanceKm')}" if meta.get('distanceKm') is not None else "")
                + (f" durationMin={meta.get('durationMin')}" if meta.get('durationMin') is not None else "")
            )

    print(f"Done. Updated {changed} trip(s).")


if __name__ == "__main__":
    main()

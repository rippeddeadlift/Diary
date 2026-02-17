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


def gpx_distance_km(path: Path) -> float:
    root = ET.parse(path).getroot()
    pts = []
    for trkpt in root.findall(".//g:trkpt", NS):
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        pts.append((lat, lon))

    if len(pts) < 2:
        return 0.0

    dist = 0.0
    for (a, b), (c, d) in zip(pts, pts[1:]):
        dist += haversine_m(a, b, c, d)

    return dist / 1000.0


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
        if meta.get("distanceKm") is not None:
            continue

        gpx_name = meta.get("gpx")
        if not gpx_name:
            continue

        gpx_path = trip_dir / gpx_name
        if not gpx_path.exists():
            continue

        km = round(gpx_distance_km(gpx_path), 2)
        meta["distanceKm"] = km
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed += 1
        print(f"Updated {rel}: distanceKm={km}")

    print(f"Done. Updated {changed} trip(s).")


if __name__ == "__main__":
    main()

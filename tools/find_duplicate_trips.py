#!/usr/bin/env python3
"""Find potential duplicate trips in data/trips.

Heuristic grouping:
- same date
- distance within +/-0.2 km
- duration within +/-2 min

This script is READ-ONLY: it does not modify or delete anything.

Usage:
  python tools/find_duplicate_trips.py
  python tools/find_duplicate_trips.py --dist-km 0.2 --dur-min 2

Output:
- prints groups with 2+ candidates and their trip ids/paths.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRIPS_DIR = ROOT / "data" / "trips"
INDEX_PATH = TRIPS_DIR / "index.json"


@dataclass
class TripRow:
    trip_id: str
    path: str
    date: str | None
    distance_km: float | None
    duration_min: int | None


def load_index() -> list[dict[str, Any]]:
    if not INDEX_PATH.exists():
        return []
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return list(idx.get("trips") or [])


def parse_trip(t: dict[str, Any]) -> TripRow | None:
    trip_id = t.get("id")
    rel = t.get("path")
    if not isinstance(trip_id, str) or not isinstance(rel, str):
        return None
    meta_path = TRIPS_DIR / rel / "meta.json"
    if not meta_path.exists():
        return TripRow(trip_id=trip_id, path=rel, date=None, distance_km=None, duration_min=None)

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return TripRow(trip_id=trip_id, path=rel, date=None, distance_km=None, duration_min=None)

    date = meta.get("date") if isinstance(meta.get("date"), str) else None

    dist = meta.get("distanceKm")
    distance_km = float(dist) if isinstance(dist, (int, float)) else None

    dur = meta.get("durationMin")
    duration_min = int(dur) if isinstance(dur, (int, float)) else None

    return TripRow(trip_id=trip_id, path=rel, date=date, distance_km=distance_km, duration_min=duration_min)


def is_close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist-km", type=float, default=0.2)
    ap.add_argument("--dur-min", type=int, default=2)
    args = ap.parse_args()

    trips_raw = load_index()
    rows: list[TripRow] = []
    for t in trips_raw:
        if not isinstance(t, dict):
            continue
        r = parse_trip(t)
        if r:
            rows.append(r)

    # only consider rows with enough data
    candidates = [r for r in rows if r.date and r.distance_km is not None and r.duration_min is not None]
    candidates.sort(key=lambda r: (r.date or "", r.distance_km or 0.0, r.duration_min or 0))

    used: set[str] = set()
    groups: list[list[TripRow]] = []

    for i, r in enumerate(candidates):
        if r.trip_id in used:
            continue
        grp = [r]
        used.add(r.trip_id)

        for j in range(i + 1, len(candidates)):
            o = candidates[j]
            if o.trip_id in used:
                continue
            if o.date != r.date:
                # because of sorting by date, once date changes we can break
                break
            if not is_close(o.distance_km or 0.0, r.distance_km or 0.0, args.dist_km):
                continue
            if not is_close(float(o.duration_min or 0), float(r.duration_min or 0), float(args.dur_min)):
                continue
            grp.append(o)
            used.add(o.trip_id)

        if len(grp) >= 2:
            groups.append(grp)

    print(f"Potential duplicate groups: {len(groups)} (dist±{args.dist_km}km, dur±{args.dur_min}min)")
    for k, grp in enumerate(groups, start=1):
        d = grp[0].date
        print(f"\nGroup #{k} — {d} — ~{grp[0].distance_km:.2f}km, ~{grp[0].duration_min}min")
        for r in grp:
            print(f"  - {r.trip_id}  ({r.path})  dist={r.distance_km:.2f}km dur={r.duration_min}min")

    if not groups:
        print("No potential duplicates found.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Convert Garmin .fit activities to .gpx (for Diary import).

Designed for Garmin Takeout folders like:
  Downloads/fit/UploadedFiles_0-_Part1
  Downloads/fit/UploadedFiles_0-_Part2

Features:
- Scans one or more input directories recursively for *.fit
- Converts to GPX 1.1 track with timestamps (trkpt/time)
- Skips activities with duration < --min-duration-min (default: 20)
- Skips files without usable GPS trackpoints

Dependencies:
- fitdecode (pure python)

Install:
  pip install fitdecode

Usage examples:
  python tools/convert_fit_to_gpx.py \
    --in "C:\\Users\\ivank\\Downloads\\fit\\UploadedFiles_0-_Part1" \
    --in "C:\\Users\\ivank\\Downloads\\fit\\UploadedFiles_0-_Part2" \
    --out "C:\\Users\\ivank\\Downloads" \
    --min-duration-min 20

Notes:
- FIT positions are stored in semicircles. We convert to degrees.
- We only write points that have lat+lon.
"""

from __future__ import annotations

import argparse
import html
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def _need_fitdecode() -> None:
    raise SystemExit(
        "Missing dependency: fitdecode\n"
        "Install with: pip install fitdecode\n"
    )


try:
    import fitdecode  # type: ignore
except Exception:  # pragma: no cover
    _need_fitdecode()


SEMICIRCLES_TO_DEG = 180.0 / 2**31


def semicircles_to_deg(v: int | float | None) -> float | None:
    if v is None:
        return None
    try:
        return float(v) * SEMICIRCLES_TO_DEG
    except Exception:
        return None


def to_iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@dataclass
class FitPoint:
    lat: float
    lon: float
    time: datetime | None
    ele_m: float | None = None


def iter_fit_points(path: Path) -> list[FitPoint]:
    pts: list[FitPoint] = []

    # We use a lenient reader: ignore CRC errors, etc.
    try:
        with fitdecode.FitReader(str(path), check_crc=False) as fit:
            for frame in fit:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name != "record":
                    continue

                fields = {f.name: f.value for f in frame.fields}
                lat = semicircles_to_deg(fields.get("position_lat"))
                lon = semicircles_to_deg(fields.get("position_long"))
                if lat is None or lon is None:
                    continue

                ts = fields.get("timestamp")
                t = ts if isinstance(ts, datetime) else None

                ele = fields.get("altitude")
                ele_m = float(ele) if isinstance(ele, (int, float)) else None

                pts.append(FitPoint(lat=float(lat), lon=float(lon), time=t, ele_m=ele_m))
    except Exception:
        return []

    return pts


def estimate_duration_minutes(pts: list[FitPoint]) -> float | None:
    times = [p.time for p in pts if p.time is not None]
    if len(times) < 2:
        return None
    start = times[0]
    end = times[-1]
    sec = (end - start).total_seconds()
    if sec <= 0:
        return None
    return sec / 60.0


def detect_start_time_and_sport(path: Path, pts: list[FitPoint]) -> tuple[datetime | None, str]:
    """Try to read start_time + sport from FIT metadata (session/activity messages).

    Returns (start_time_utc, sport_tag).
    sport_tag is one of: cycling|running|hiking|skiing|unknown
    """

    start: datetime | None = None
    sport: str = "unknown"

    def normalize_sport(v: object) -> str:
        s = str(v).lower()
        # common FIT sport enums
        if "cycling" in s or "bike" in s or "biking" in s:
            return "cycling"
        if "running" in s or s == "run":
            return "running"
        if "hiking" in s or "walking" in s or "walk" in s:
            return "hiking"
        if "cross_country_skiing" in s or "ski" in s:
            return "skiing"
        return "unknown"

    try:
        with fitdecode.FitReader(str(path), check_crc=False) as fit:
            for frame in fit:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name not in {"session", "activity", "sport"}:
                    continue
                fields = {f.name: f.value for f in frame.fields}

                # Prefer explicit session start_time
                st = fields.get("start_time") or fields.get("timestamp")
                if start is None and isinstance(st, datetime):
                    start = st

                sp = fields.get("sport")
                if sp is not None:
                    sport = normalize_sport(sp)

                # If we already have both, we can stop early.
                if start is not None and sport != "unknown":
                    break
    except Exception:
        pass

    if start is None:
        start = next((p.time for p in pts if p.time is not None), None)

    return start, sport


def gpx_from_points(pts: list[FitPoint], *, name: str) -> str:
    name_xml = html.escape(name)

    out: list[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append('<gpx version="1.1" creator="Diary FIT converter" xmlns="http://www.topografix.com/GPX/1/1">')
    out.append(f"  <trk><name>{name_xml}</name><trkseg>")

    for p in pts:
        lat = f"{p.lat:.7f}"
        lon = f"{p.lon:.7f}"
        out.append(f"    <trkpt lat=\"{lat}\" lon=\"{lon}\">")
        if p.ele_m is not None:
            out.append(f"      <ele>{p.ele_m:.1f}</ele>")
        if p.time is not None:
            out.append(f"      <time>{to_iso_z(p.time)}</time>")
        out.append("    </trkpt>")

    out.append("  </trkseg></trk>")
    out.append("</gpx>")
    return "\n".join(out) + "\n"


def find_fit_files(roots: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    for r in roots:
        if r.is_file() and r.suffix.lower() == ".fit":
            out.append(r)
        elif r.is_dir():
            out.extend([p for p in r.rglob("*.fit") if p.is_file()])
    out.sort()
    return out


def safe_out_name(base: str) -> str:
    # Keep it windows-friendly
    keep = []
    for ch in base:
        if ch.isalnum() or ch in "._- ":
            keep.append(ch)
        else:
            keep.append("_")
    s = "".join(keep).strip().strip(".")
    return s or "activity"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inputs", action="append", required=True, help="Input folder (or file). Repeatable.")
    ap.add_argument("--out", dest="out_dir", required=True, help="Output folder for GPX files")
    ap.add_argument("--min-duration-min", type=float, default=20.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    in_roots = [Path(x) for x in args.inputs]
    out_dir = Path(args.out_dir)

    fits = find_fit_files(in_roots)
    if not fits:
        print("No .fit files found.")
        return 0

    converted = 0
    skipped_short = 0
    skipped_no_gps = 0
    failed = 0

    for f in fits:
        pts = iter_fit_points(f)
        if len(pts) < 2:
            skipped_no_gps += 1
            continue

        dur = estimate_duration_minutes(pts)
        if dur is not None and dur < float(args.min_duration_min):
            skipped_short += 1
            continue

        start_time, sport = detect_start_time_and_sport(f, pts)
        date_prefix = start_time.date().isoformat() if start_time else "unknown-date"
        time_prefix = start_time.strftime("%H%M") if start_time else "0000"

        # Make the GPX <name> useful for our importer/tag inference
        title = {
            "cycling": "Cycling",
            "running": "Running",
            "hiking": "Hiking",
            "skiing": "Skiing",
            "unknown": "Activity",
        }.get(sport, "Activity")

        name = f"{date_prefix} {title}"
        gpx = gpx_from_points(pts, name=name)

        # File name: no email/id leakage from Garmin stems
        out_name = safe_out_name(f"{date_prefix}_{time_prefix}_{sport}.gpx")
        dst = out_dir / out_name
        if dst.exists():
            dst = out_dir / safe_out_name(f"{date_prefix}_{time_prefix}_{sport}_{int(f.stat().st_mtime)}.gpx")

        try:
            if not args.dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_text(gpx, encoding="utf-8")
            converted += 1
        except Exception as e:
            failed += 1
            print(f"FAILED {f}: {e}")

    print(f"FIT files scanned: {len(fits)}")
    print(f"Converted to GPX: {converted}")
    print(f"Skipped (no GPS track): {skipped_no_gps}")
    print(f"Skipped (duration < {args.min_duration_min} min): {skipped_short}")
    print(f"Failed: {failed}")
    print(f"Output dir: {out_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

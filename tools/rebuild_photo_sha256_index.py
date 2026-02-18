#!/usr/bin/env python3
"""Rebuild photos SHA-256 index.

This scans Diary/data/photos/inbox/** for images (ignores thumbs/) and creates/overwrites:
  data/photos/_sha256_index.json

The index maps sha256 -> relative path (posix) under data/.

Usage (from repo root):
  python -m tools.rebuild_photo_sha256_index

Notes:
- Exact duplicates (bit-identical) will keep only the first path encountered.
- This tool does not delete any files.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.config import DATA_DIR, PHOTOS_INBOX_DIR
from server.photos_repo import IMG_EXTS, sha256_file, save_sha256_index


def is_image(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMG_EXTS


def main() -> int:
    PHOTOS_INBOX_DIR.mkdir(parents=True, exist_ok=True)

    idx: dict[str, str] = {}

    files: list[Path] = []
    for p in PHOTOS_INBOX_DIR.rglob("*"):
        if not is_image(p):
            continue
        if "thumbs" in p.parts:
            continue
        files.append(p)

    files.sort()

    dupes = 0
    for p in files:
        try:
            h = sha256_file(p)
        except Exception as e:
            print(f"WARN: cannot hash {p}: {e}")
            continue

        rel = p.relative_to(DATA_DIR).as_posix()
        if h in idx:
            dupes += 1
            # keep first occurrence
            continue
        idx[h] = rel

    save_sha256_index(idx)

    print(f"Hashed: {len(files)} file(s)")
    print(f"Index entries: {len(idx)}")
    print(f"Exact duplicates (ignored): {dupes}")
    print(f"Wrote: {(DATA_DIR / 'photos' / '_sha256_index.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

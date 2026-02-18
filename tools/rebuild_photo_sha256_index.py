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

import hashlib

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PHOTOS_INBOX_DIR = DATA_DIR / "photos" / "inbox"
SHA256_INDEX_PATH = DATA_DIR / "photos" / "_sha256_index.json"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}


def is_image(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in IMG_EXTS


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_sha256_index(idx: dict[str, str]) -> None:
    SHA256_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    SHA256_INDEX_PATH.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    print(f"Wrote: {SHA256_INDEX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path

# Diary/ (repo root) is parent of this file's directory
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

PHOTOS_INBOX_DIR = DATA_DIR / "photos" / "inbox"

# Image extensions we treat as photos
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

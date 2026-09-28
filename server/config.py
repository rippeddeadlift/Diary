from __future__ import annotations

import os
from pathlib import Path

# Diary/ (repo root) is parent of this file's directory
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DEFAULT_MEDIA_DIR = Path(r"E:\Diary\data") if os.name == "nt" else DATA_DIR
MEDIA_DIR = Path(os.environ.get("DIARY_MEDIA_DIR", DEFAULT_MEDIA_DIR))

PHOTOS_INBOX_DIR = MEDIA_DIR / "photos" / "inbox"

# Image extensions we treat as photos
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

# Videos that browsers can play, or that phones commonly export.
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
MEDIA_EXTS = IMG_EXTS | VIDEO_EXTS

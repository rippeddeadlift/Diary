from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Diary/ (repo root) is parent of this file's directory
ROOT = Path(__file__).resolve().parents[1]
if os.name == "nt":
	APP_CONFIG_DIR = (
		Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Diary"
	)
elif sys.platform == "darwin":
	APP_CONFIG_DIR = Path.home() / "Library" / "Application Support" / "Diary"
else:
	APP_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "diary"

DATA_DIR = (
	Path(os.environ.get("DIARY_DATA_DIR", APP_CONFIG_DIR / "data"))
	if getattr(sys, "frozen", False)
	else ROOT / "data"
)
MEDIA_DIR_SETTINGS_PATH = APP_CONFIG_DIR / "settings.json"
DEFAULT_MEDIA_DIR = Path(r"E:\Diary\data") if os.name == "nt" else DATA_DIR


def load_media_dir_setting() -> Path | None:
	try:
		settings = json.loads(MEDIA_DIR_SETTINGS_PATH.read_text(encoding="utf-8"))
		value = settings.get("media_dir") if isinstance(settings, dict) else None
		return Path(value).expanduser().resolve() if isinstance(value, str) and value.strip() else None
	except (OSError, ValueError, TypeError, json.JSONDecodeError):
		return None


def save_media_dir_setting(path: str | Path) -> Path:
	resolved = Path(path).expanduser().resolve()
	if not resolved.is_dir():
		raise ValueError("Media directory does not exist")
	MEDIA_DIR_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
	temporary_path = MEDIA_DIR_SETTINGS_PATH.with_suffix(".tmp")
	temporary_path.write_text(json.dumps({"media_dir": str(resolved)}, indent=2) + "\n", encoding="utf-8")
	temporary_path.replace(MEDIA_DIR_SETTINGS_PATH)
	return resolved


MEDIA_DIR = (
	Path(os.environ["DIARY_MEDIA_DIR"]).expanduser()
	if os.environ.get("DIARY_MEDIA_DIR")
	else load_media_dir_setting() or DEFAULT_MEDIA_DIR
)

PHOTOS_INBOX_DIR = MEDIA_DIR / "photos" / "inbox"

# Image extensions we treat as photos
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

# Videos that browsers can play, or that phones commonly export.
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm"}
MEDIA_EXTS = IMG_EXTS | VIDEO_EXTS

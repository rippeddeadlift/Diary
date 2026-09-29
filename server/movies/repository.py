from __future__ import annotations

import json
from pathlib import Path

from ..config import DATA_DIR, VIDEO_EXTS

MOVIES_CONFIG_PATH = DATA_DIR / "movies" / "library.json"
MOVIE_THUMBS_DIR = DATA_DIR / "movies" / "_thumbs"
MOVIE_EXTS = VIDEO_EXTS | {".avi", ".mkv", ".mpeg", ".mpg", ".wmv"}


def get_movie_folder() -> Path | None:
    try:
        value = json.loads(MOVIES_CONFIG_PATH.read_text(encoding="utf-8")).get("folder")
        folder = Path(value).expanduser().resolve() if isinstance(value, str) else None
        return folder if folder is not None and folder.is_dir() else None
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def save_movie_folder(folder: str) -> Path | None:
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        return None
    MOVIES_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    MOVIES_CONFIG_PATH.write_text(json.dumps({"folder": str(path)}, indent=2), encoding="utf-8")
    return path


def list_movie_files(folder: Path) -> list[Path]:
    movies = []
    for movie in folder.rglob("*"):
        if not movie.is_file() or movie.suffix.lower() not in MOVIE_EXTS:
            continue
        try:
            movie.resolve().relative_to(folder)
        except ValueError:
            continue
        movies.append(movie)
    return movies


def resolve_movie_path(folder: Path, movie_path: str) -> Path | None:
    candidate = (folder / movie_path).resolve()
    try:
        candidate.relative_to(folder)
    except ValueError:
        return None
    if not candidate.is_file() or candidate.suffix.lower() not in MOVIE_EXTS:
        return None
    return candidate

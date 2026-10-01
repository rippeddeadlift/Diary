import os
import sys
from pathlib import Path

import uvicorn

from server import config


def configure_packaged_media_directory() -> bool:
    if not getattr(sys, "frozen", False):
        return True

    selected = config.load_media_dir_setting()
    if selected is None or not selected.is_dir():
        initial_dir = config.MEDIA_DIR if config.MEDIA_DIR.is_dir() else Path.home()
        try:
            from server.folder_picker import pick_directory

            selected = pick_directory("Diary Medienordner auswählen", initial_dir)
        except ImportError:
            selected = None
        if selected is None:
            print("Kein Medienordner ausgewählt. Diary wird beendet.")
            return False
        config.save_media_dir_setting(selected)

    os.environ["DIARY_MEDIA_DIR"] = str(selected)
    config.MEDIA_DIR = selected
    config.PHOTOS_INBOX_DIR = selected / "photos" / "inbox"
    return True


def main() -> None:
    if not configure_packaged_media_directory():
        return

    from server.main import app

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )


if __name__ == "__main__":
    main()
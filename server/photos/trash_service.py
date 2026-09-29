from __future__ import annotations

import shutil
from datetime import datetime

from . import repository as photos_repo
from ..config import DATA_DIR, MEDIA_DIR, PHOTOS_INBOX_DIR
from ..thumbnails import thumb_path_for

TRASH_DIR = MEDIA_DIR / "photos" / "_trash"
THUMBS_TRASH_DIR = DATA_DIR / "photos" / "_thumbs" / "_trash"


def trash_photo_items(paths: list[str]) -> tuple[int, str]:
    dt = datetime.now().astimezone()
    batch = dt.strftime("%Y-%m-%d_%H%M%S")
    trash_batch_dir = TRASH_DIR / batch
    trash_batch_dir.mkdir(parents=True, exist_ok=True)

    sha_idx = photos_repo.load_sha256_index()
    trashed = 0
    trashed_rels: list[str] = []

    for rel in paths:
        try:
            img = photos_repo.resolve_media_path(rel)
        except Exception:
            continue
        if not img.exists():
            continue

        try:
            img.relative_to(PHOTOS_INBOX_DIR)
        except Exception:
            continue

        sidecar_path = photos_repo.sidecar_path_for(img)
        sidecar = photos_repo.load_or_init_sidecar_for_image(img) if sidecar_path.exists() else {}
        try:
            file_hash = sidecar.get("sha256") or photos_repo.sha256_file(img)
        except Exception:
            file_hash = None

        destination_image = trash_batch_dir / img.name
        if destination_image.exists():
            destination_image = trash_batch_dir / f"{img.stem}_{int(img.stat().st_mtime)}{img.suffix}"
        try:
            destination_image.parent.mkdir(parents=True, exist_ok=True)
            img.rename(destination_image)
        except Exception:
            try:
                shutil.move(str(img), str(destination_image))
            except Exception:
                continue

        if sidecar_path.exists():
            destination_rel = destination_image.relative_to(MEDIA_DIR).as_posix()
            destination_sidecar = DATA_DIR / f"{destination_rel}.json"
            destination_sidecar.parent.mkdir(parents=True, exist_ok=True)
            try:
                sidecar_path.rename(destination_sidecar)
            except Exception:
                try:
                    shutil.move(str(sidecar_path), str(destination_sidecar))
                except Exception:
                    pass

        try:
            rel_under_data = img.relative_to(MEDIA_DIR).as_posix()
            thumbnail = thumb_path_for(rel_under_data)
            if thumbnail.exists():
                thumbnail_destination = (THUMBS_TRASH_DIR / batch / rel_under_data).resolve()
                thumbnail_destination.parent.mkdir(parents=True, exist_ok=True)
                try:
                    thumbnail.rename(thumbnail_destination)
                except Exception:
                    shutil.move(str(thumbnail), str(thumbnail_destination))
        except Exception:
            pass

        if file_hash and file_hash in sha_idx:
            sha_idx.pop(file_hash, None)
        trashed += 1
        trashed_rels.append(rel)

    try:
        photos_repo.save_sha256_index(sha_idx)
    except Exception:
        pass
    try:
        photos_repo.forget_gallery_items(trashed_rels)
    except Exception:
        pass

    batch_path = str(trash_batch_dir.relative_to(MEDIA_DIR)).replace("\\", "/")
    return trashed, batch_path

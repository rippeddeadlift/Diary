from __future__ import annotations

import os
import json
import shutil
import stat
import tempfile
from datetime import datetime
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import BinaryIO, Callable

MAX_BACKUP_ENTRIES = 100_000
MAX_BACKUP_UNPACKED_BYTES = 10 * 1024 * 1024 * 1024
BACKUP_MANIFEST_NAME = "__diary_backup__.json"
PRECOMPRESSED_EXTENSIONS = {
    ".7z", ".avif", ".avi", ".flac", ".gif", ".heic", ".jpeg", ".jpg",
    ".m4a", ".m4v", ".mkv", ".mov", ".mp3", ".mp4", ".pdf", ".png",
    ".rar", ".webm", ".webp", ".zip",
}


def create_backup_archive(
    data_dir: Path,
    on_progress: Callable[[int, int], None] | None = None,
) -> Path:
    descriptor, archive_name = tempfile.mkstemp(prefix="diary-data-", suffix=".zip")
    os.close(descriptor)
    archive_path = Path(archive_name)
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        entries = sorted(data_dir.rglob("*"))
        for source in entries:
            if source.is_symlink():
                raise ValueError(f"Backup contains an unsupported symbolic link: {source}")
        files = [source for source in entries if source.is_file()]
        if on_progress:
            on_progress(0, len(files))
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for source in entries:
                relative = source.relative_to(data_dir).as_posix()
                if source.is_dir():
                    archive.writestr(f"{relative}/", b"")
            for index, source in enumerate(files, start=1):
                compression = (
                    zipfile.ZIP_STORED
                    if source.suffix.lower() in PRECOMPRESSED_EXTENSIONS
                    else zipfile.ZIP_DEFLATED
                )
                archive.write(source, source.relative_to(data_dir).as_posix(), compress_type=compression)
                if on_progress:
                    on_progress(index, len(files))
            archive.writestr(
                BACKUP_MANIFEST_NAME,
                json.dumps({
                    "format": "diary-data-backup",
                    "version": 1,
                    "createdAt": created_at,
                    "files": len(files),
                }),
            )
        return archive_path
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise


def restore_backup_archive(data_dir: Path, source: BinaryIO) -> tuple[int, int]:
    data_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".diary-restore-", dir=data_dir.parent) as temp_dir:
        temporary_root = Path(temp_dir)
        staged_data = temporary_root / "restored-data"
        staged_data.mkdir()
        seen: set[str] = set()
        file_count = 0
        unpacked_bytes = 0

        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if not entries:
                raise ValueError("The backup archive is empty")
            if len(entries) > MAX_BACKUP_ENTRIES:
                raise ValueError("The backup archive contains too many entries")

            for entry in entries:
                normalized = entry.filename.replace("\\", "/")
                relative = PurePosixPath(normalized)
                windows_path = PureWindowsPath(entry.filename)
                parts = relative.parts
                if (
                    not normalized
                    or "\x00" in normalized
                    or relative.is_absolute()
                    or windows_path.is_absolute()
                    or windows_path.drive
                    or any(part in {"", ".", ".."} for part in parts)
                ):
                    raise ValueError("The backup contains an unsafe path")

                normalized_name = "/".join(parts)
                if normalized_name in seen:
                    raise ValueError("The backup contains duplicate paths")
                seen.add(normalized_name)
                if normalized_name == BACKUP_MANIFEST_NAME:
                    continue

                mode = (entry.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(mode)
                if stat.S_ISLNK(mode) or file_type not in {0, stat.S_IFREG, stat.S_IFDIR}:
                    raise ValueError("The backup contains an unsupported file type")

                target = staged_data.joinpath(*parts)
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                unpacked_bytes += entry.file_size
                if unpacked_bytes > MAX_BACKUP_UNPACKED_BYTES:
                    raise ValueError("The uncompressed backup is larger than 10 GiB")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as archived_file, target.open("wb") as restored_file:
                    shutil.copyfileobj(archived_file, restored_file, length=1024 * 1024)
                file_count += 1

        if file_count == 0:
            raise ValueError("The backup archive contains no files")

        previous_data = temporary_root / "previous-data"
        moved_previous = False
        try:
            if data_dir.exists():
                os.replace(data_dir, previous_data)
                moved_previous = True
            os.replace(staged_data, data_dir)
        except OSError:
            if moved_previous and not data_dir.exists():
                os.replace(previous_data, data_dir)
            raise

        if moved_previous:
            shutil.rmtree(previous_data, ignore_errors=True)

    return file_count, unpacked_bytes


def latest_valid_backup(media_dir: Path) -> dict[str, str | bool | None]:
    candidates = sorted(
        media_dir.glob("diary-backup-*.zip"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if media_dir.is_dir() else []

    for candidate in candidates:
        try:
            with zipfile.ZipFile(candidate) as archive:
                entries = archive.infolist()
                if not entries:
                    continue
                manifest_entry = next((entry for entry in entries if entry.filename == BACKUP_MANIFEST_NAME), None)
                if manifest_entry is not None:
                    manifest = json.loads(archive.read(manifest_entry))
                    if manifest.get("format") != "diary-data-backup" or manifest.get("version") != 1:
                        continue
                    created_at = manifest.get("createdAt")
                    if not isinstance(created_at, str):
                        continue
                    datetime.fromisoformat(created_at)
                else:
                    created_at = datetime.fromtimestamp(candidate.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            return {"valid": True, "createdAt": created_at, "filename": candidate.name}
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError, zipfile.BadZipFile):
            continue

    return {"valid": False, "createdAt": None, "filename": None}

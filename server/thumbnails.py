from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

from .config import DATA_DIR, VIDEO_EXTS

THUMBS_DIR = DATA_DIR / "photos" / "_thumbs"


def thumb_path_for(rel_under_data: str) -> Path:
    return (THUMBS_DIR / rel_under_data).resolve()


def generate_video_poster(video_abs: Path, dst: Path) -> None:
    """Create a best-effort JPEG poster using ffmpeg when available."""
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", str(video_abs),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        duration = float(probe.stdout.strip())
        sample_times = [duration * fraction for fraction in (0.1, 0.25, 0.5)]
    except (OSError, ValueError, subprocess.TimeoutExpired):
        sample_times = [10.0, 30.0, 60.0]

    candidate = dst.with_name(f"{dst.stem}.candidate.jpg")
    best_brightness = -1.0
    try:
        for sample_time in sample_times:
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-ss", f"{sample_time:.3f}", "-i", str(video_abs),
                        "-frames:v", "1", "-vf",
                        "scale=512:512:force_original_aspect_ratio=increase,crop=512:512",
                        str(candidate),
                    ],
                    capture_output=True,
                    timeout=30,
                    check=False,
                )
                with Image.open(candidate) as image:
                    brightness = ImageStat.Stat(image.convert("L")).mean[0]
                if brightness > best_brightness:
                    shutil.copyfile(candidate, dst)
                    best_brightness = brightness
                if brightness >= 12:
                    break
            except (OSError, subprocess.TimeoutExpired):
                continue
    finally:
        candidate.unlink(missing_ok=True)


def ensure_video_poster(video_abs: Path, rel_under_data: str) -> None:
    """Create the gallery poster at the photo thumbnail path."""
    generate_video_poster(video_abs, thumb_path_for(rel_under_data).with_suffix(".jpg"))


def ensure_thumb(img_abs: Path, rel_under_data: str, *, max_size: int = 512) -> None:
    """Best-effort thumbnail generation. Creates THUMBS_DIR/<rel_under_data>."""
    if img_abs.suffix.lower() in VIDEO_EXTS:
        ensure_video_poster(img_abs, rel_under_data)
        return

    dst = thumb_path_for(rel_under_data)
    if dst.exists():
        return

    ext = img_abs.suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(img_abs) as image:
        image = ImageOps.exif_transpose(image)
        if ext in {".jpg", ".jpeg", ".heic"}:
            image = image.convert("RGB")
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        if ext in {".jpg", ".jpeg", ".heic"}:
            image.save(dst, format="JPEG", quality=82, optimize=True, progressive=True)
        elif ext == ".png":
            image.save(dst, format="PNG", optimize=True)
        else:
            image = image.convert("RGB")
            image.save(dst, format="WEBP", quality=82, method=6)

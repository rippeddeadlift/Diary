from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse

APP_TITLE = "Diary Upload Server"

# Diary/ (repo root) is parent of this file's directory
ROOT = Path(__file__).resolve().parents[1]
PHOTOS_INBOX_DIR = ROOT / "data" / "photos" / "inbox"


def now_local_iso() -> str:
    # naive local time is fine for our use case; include offset if available
    return datetime.now().astimezone().isoformat(timespec="seconds")


def batch_folder_name(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d_%H%M")


def safe_name(s: str) -> str:
    # Keep ascii-ish, avoid weird filesystem chars.
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9._-]+", "", s)
    s = s.strip("._-")
    return s or "file"


def unique_filename(prefix: str, original: str) -> str:
    # Prefix: 2026-02-16T173512
    base = Path(original).name
    stem = safe_name(Path(base).stem)
    ext = Path(base).suffix.lower()
    if not ext:
        ext = ".bin"

    # Add a small random-ish suffix to reduce collisions
    # (no need for crypto randomness here)
    suffix = f"{os.getpid()}"
    return f"{prefix}_{stem}_{suffix}{ext}"


app = FastAPI(title=APP_TITLE)


@app.get("/api/health")
def health():
    return {"ok": True, "time": now_local_iso()}


@app.post("/api/photos/upload")
async def upload_photos(files: List[UploadFile] = File(...)):
    dt = datetime.now().astimezone()
    batch_dir = PHOTOS_INBOX_DIR / batch_folder_name(dt)
    batch_dir.mkdir(parents=True, exist_ok=True)

    prefix = dt.strftime("%Y-%m-%dT%H%M%S")

    saved = []
    for f in files:
        out_name = unique_filename(prefix, f.filename or "upload")
        out_path = batch_dir / out_name

        # Save file
        with out_path.open("wb") as w:
            while True:
                chunk = await f.read(1024 * 1024)
                if not chunk:
                    break
                w.write(chunk)

        # Sidecar JSON next to image
        sidecar_path = out_path.with_suffix(out_path.suffix + ".json")
        sidecar = {
            "people": [],
            "tags": [],
            "caption": "",
            "createdAt": None,
            "addedAt": now_local_iso(),
        }
        sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        saved.append(
            {
                "file": str(out_path.relative_to(ROOT)).replace("\\", "/"),
                "sidecar": str(sidecar_path.relative_to(ROOT)).replace("\\", "/"),
                "originalName": f.filename,
            }
        )

    return JSONResponse(
        {
            "ok": True,
            "batch": str(batch_dir.relative_to(ROOT)).replace("\\", "/"),
            "count": len(saved),
            "saved": saved,
        }
    )

"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_data_dir(monkeypatch) -> Generator[Path, None, None]:
    """Create a temporary data directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        
        # Create directory structure
        (tmp_path / "photos" / "inbox").mkdir(parents=True)
        (tmp_path / "photos" / "_thumbs").mkdir(parents=True)
        (tmp_path / "photos" / "_trash").mkdir(parents=True)
        (tmp_path / "trips").mkdir(parents=True)
        
        # Patch config to use temp directory
        monkeypatch.setattr("server.config.DATA_DIR", tmp_path)
        monkeypatch.setattr("server.config.PHOTOS_INBOX_DIR", tmp_path / "photos" / "inbox")
        monkeypatch.setattr("server.photos_repo.DATA_DIR", tmp_path)
        monkeypatch.setattr("server.photos_repo.PHOTOS_INBOX_DIR", tmp_path / "photos" / "inbox")
        monkeypatch.setattr("server.photos_repo.SHA256_INDEX_PATH", tmp_path / "photos" / "_sha256_index.json")

        # Patch server.main module-level paths (computed at import time)
        monkeypatch.setattr("server.main.DATA_DIR", tmp_path)
        monkeypatch.setattr("server.main.PHOTOS_INBOX_DIR", tmp_path / "photos" / "inbox")
        monkeypatch.setattr("server.main.TRASH_DIR", tmp_path / "photos" / "_trash")
        monkeypatch.setattr("server.main.THUMBS_DIR", tmp_path / "photos" / "_thumbs")
        monkeypatch.setattr("server.main.THUMBS_TRASH_DIR", tmp_path / "photos" / "_thumbs" / "_trash")
        monkeypatch.setattr("server.main.TRIPS_DIR", tmp_path / "trips")
        monkeypatch.setattr("server.main.TRIPS_INDEX", tmp_path / "trips" / "index.json")
        monkeypatch.setattr("server.main.TRIPS_TRASH_DIR", tmp_path / "trips" / "_trash")
        
        yield tmp_path


@pytest.fixture
def sample_image(tmp_path: Path) -> Path:
    """Create a minimal valid image file for testing."""
    from PIL import Image
    
    img_path = tmp_path / "test.jpg"
    # Create a 1x1 pixel image
    img = Image.new("RGB", (1, 1), color="red")
    img.save(img_path, "JPEG")
    return img_path


@pytest.fixture
def sample_sidecar_data() -> dict:
    """Sample sidecar JSON data."""
    return {
        "people": ["Alice", "Bob"],
        "tags": ["vacation", "beach"],
        "caption": "Test photo",
        "createdAt": "2024-01-15T10:30:00+00:00",
        "createdAtSource": "exif",
        "addedAt": "2024-01-15T10:35:00+00:00",
    }

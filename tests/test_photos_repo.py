"""Tests for server.photos_repo module."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from server.photos_repo import (
    batch_folder_name,
    bulk_toggle_sidecar_fields,
    ensure_sidecar_fields,
    is_image_file,
    load_sidecar,
    parse_isoish,
    resolve_data_path,
    safe_name,
    save_sidecar,
    sha256_file,
    sidecar_path_for,
    unique_filename,
    update_sidecar_fields,
)


class TestSafeName:
    """Tests for safe_name function."""

    def test_normal_name(self):
        assert safe_name("photo.jpg") == "photo.jpg"

    def test_spaces_to_underscores(self):
        assert safe_name("my photo.jpg") == "my_photo.jpg"

    def test_special_chars_removed(self):
        assert safe_name("photo@#$%test.jpg") == "phototest.jpg"

    def test_multiple_spaces(self):
        assert safe_name("my   photo.jpg") == "my_photo.jpg"

    def test_leading_trailing_dots(self):
        assert safe_name("...photo...") == "photo"

    def test_empty_string(self):
        assert safe_name("") == "file"

    def test_only_special_chars(self):
        assert safe_name("@#$%") == "file"


class TestUniqueFilename:
    """Tests for unique_filename function."""

    def test_basic(self):
        result = unique_filename("2024-01-15T103000", "photo.jpg")
        assert result.startswith("2024-01-15T103000_photo_")
        assert result.endswith(".jpg")
        assert "photo" in result

    def test_special_chars_sanitized(self):
        result = unique_filename("2024-01-15T103000", "photo@test.jpg")
        assert "@" not in result
        assert result.endswith(".jpg")

    def test_no_extension(self):
        result = unique_filename("2024-01-15T103000", "photo")
        assert result.endswith(".bin")


class TestIsImageFile:
    """Tests for is_image_file function."""

    def test_jpg(self):
        assert is_image_file(Path("test.jpg")) is True
        assert is_image_file(Path("test.JPG")) is True
        assert is_image_file(Path("test.jpeg")) is True

    def test_png(self):
        assert is_image_file(Path("test.png")) is True

    def test_webp(self):
        assert is_image_file(Path("test.webp")) is True

    def test_non_image(self):
        assert is_image_file(Path("test.txt")) is False
        assert is_image_file(Path("test")) is False


class TestSidecarPath:
    """Tests for sidecar_path_for function."""

    def test_jpg_sidecar(self):
        img = Path("photo.jpg")
        assert sidecar_path_for(img) == Path("photo.jpg.json")

    def test_png_sidecar(self):
        img = Path("photo.png")
        assert sidecar_path_for(img) == Path("photo.png.json")


class TestResolveDataPath:
    """Tests for resolve_data_path function."""

    def test_normal_path(self, temp_data_dir):
        rel = "photos/inbox/test.jpg"
        result = resolve_data_path(rel)
        assert result == temp_data_dir / rel
        assert result.exists() is False  # File doesn't exist, but path is valid

    def test_path_with_leading_slash(self, temp_data_dir):
        rel = "/photos/inbox/test.jpg"
        result = resolve_data_path(rel)
        assert result == temp_data_dir / "photos/inbox/test.jpg"

    def test_path_traversal_prevention(self, temp_data_dir):
        """Test that path traversal attacks are prevented."""
        with pytest.raises(ValueError, match="Path traversal"):
            resolve_data_path("../../etc/passwd")

    def test_path_traversal_with_slashes(self, temp_data_dir):
        """Test various path traversal attempts."""
        with pytest.raises(ValueError, match="Path traversal"):
            resolve_data_path("../data/photos/inbox/test.jpg")

    def test_absolute_path_inside_data_dir(self, temp_data_dir):
        """Test that paths inside data dir work."""
        rel = "photos/inbox/test.jpg"
        result = resolve_data_path(rel)
        assert str(result).startswith(str(temp_data_dir))


class TestSidecarOperations:
    """Tests for sidecar file operations."""

    def test_save_and_load_sidecar(self, temp_data_dir, sample_sidecar_data):
        sidecar_path = temp_data_dir / "test.json"
        save_sidecar(sidecar_path, sample_sidecar_data)
        
        assert sidecar_path.exists()
        loaded = load_sidecar(sidecar_path)
        assert loaded == sample_sidecar_data

    def test_load_nonexistent_sidecar(self, temp_data_dir):
        sidecar_path = temp_data_dir / "nonexistent.json"
        result = load_sidecar(sidecar_path)
        assert result == {}

    def test_load_invalid_json(self, temp_data_dir):
        sidecar_path = temp_data_dir / "invalid.json"
        sidecar_path.write_text("invalid json{")
        result = load_sidecar(sidecar_path)
        assert result == {}

    def test_ensure_sidecar_fields(self):
        empty = {}
        result = ensure_sidecar_fields(empty)
        assert "people" in result
        assert "tags" in result
        assert "caption" in result
        assert "addedAt" in result
        assert result["people"] == []
        assert result["tags"] == []
        assert result["caption"] == ""

    def test_ensure_sidecar_fields_preserves_existing(self):
        existing = {
            "people": ["Alice"],
            "tags": ["test"],
            "caption": "Existing",
        }
        result = ensure_sidecar_fields(existing)
        assert result["people"] == ["Alice"]
        assert result["tags"] == ["test"]
        assert result["caption"] == "Existing"

    def test_update_sidecar_fields(self):
        sidecar = {}
        result = update_sidecar_fields(
            sidecar,
            people=["Alice", "Bob"],
            tags=["vacation"],
            caption="New caption",
        )
        assert result["people"] == ["Alice", "Bob"]
        assert result["tags"] == ["vacation"]
        assert result["caption"] == "New caption"

    def test_bulk_toggle_add_people(self):
        sidecar = {"people": ["Alice"], "tags": []}
        result = bulk_toggle_sidecar_fields(
            sidecar,
            add_people=["Bob", "Charlie"],
            remove_people=[],
            add_tags=[],
            remove_tags=[],
        )
        assert set(result["people"]) == {"Alice", "Bob", "Charlie"}

    def test_bulk_toggle_remove_people(self):
        sidecar = {"people": ["Alice", "Bob", "Charlie"], "tags": []}
        result = bulk_toggle_sidecar_fields(
            sidecar,
            add_people=[],
            remove_people=["Bob"],
            add_tags=[],
            remove_tags=[],
        )
        assert set(result["people"]) == {"Alice", "Charlie"}

    def test_bulk_toggle_add_and_remove(self):
        sidecar = {"people": ["Alice"], "tags": ["old"]}
        result = bulk_toggle_sidecar_fields(
            sidecar,
            add_people=["Bob"],
            remove_people=["Alice"],
            add_tags=["new"],
            remove_tags=["old"],
        )
        assert result["people"] == ["Bob"]
        assert result["tags"] == ["new"]

    def test_bulk_toggle_no_duplicates(self):
        sidecar = {"people": ["Alice"], "tags": []}
        result = bulk_toggle_sidecar_fields(
            sidecar,
            add_people=["Alice", "Bob"],  # Alice already exists
            remove_people=[],
            add_tags=[],
            remove_tags=[],
        )
        assert result["people"].count("Alice") == 1
        assert set(result["people"]) == {"Alice", "Bob"}


class TestSha256File:
    """Tests for sha256_file function."""

    def test_sha256_hash(self, temp_data_dir):
        test_file = temp_data_dir / "test.txt"
        test_file.write_text("test content")
        
        hash1 = sha256_file(test_file)
        hash2 = sha256_file(test_file)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex string length

    def test_different_files_different_hashes(self, temp_data_dir):
        file1 = temp_data_dir / "test1.txt"
        file2 = temp_data_dir / "test2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")
        
        hash1 = sha256_file(file1)
        hash2 = sha256_file(file2)
        
        assert hash1 != hash2


class TestParseIsoish:
    """Tests for parse_isoish function."""

    def test_valid_iso_format(self):
        result = parse_isoish("2024-01-15T10:30:00+00:00")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_valid_iso_no_timezone(self):
        result = parse_isoish("2024-01-15T10:30:00")
        assert result is not None

    def test_invalid_format(self):
        result = parse_isoish("not a date")
        assert result is None

    def test_empty_string(self):
        result = parse_isoish("")
        assert result is None


class TestBatchFolderName:
    """Tests for batch_folder_name function."""

    def test_basic_format(self):
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = batch_folder_name(dt)
        assert result == "2024-01-15_1030"

    def test_different_dates(self):
        dt1 = datetime(2024, 1, 15, 10, 30)
        dt2 = datetime(2024, 12, 31, 23, 59)
        result1 = batch_folder_name(dt1)
        result2 = batch_folder_name(dt2)
        assert result1 != result2
        assert result1 == "2024-01-15_1030"
        assert result2 == "2024-12-31_2359"

"""Tests for FastAPI endpoints."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.main import app


@pytest.fixture
def client(temp_data_dir) -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "time" in data


class TestPhotosEndpoints:
    """Tests for photo-related endpoints."""

    def test_list_inbox_empty(self, client, temp_data_dir):
        """Test listing empty inbox."""
        response = client.get("/api/photos/inbox/all")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["count"] == 0
        assert data["items"] == []
        assert data["hasMore"] is False

    def test_list_inbox_page_does_not_require_full_scan(self, client, temp_data_dir):
        """A limited page returns before every sidecar is needed."""
        inbox = temp_data_dir / "photos" / "inbox"
        for name, created in (
            ("a.jpg", "2024-01-01T12:00:00"),
            ("b.jpg", "2024-03-01T12:00:00"),
            ("c.jpg", "2024-02-01T12:00:00"),
        ):
            (inbox / name).write_bytes(b"not-a-real-image")
            (inbox / f"{name}.json").write_text(
                '{"people":[],"tags":[],"createdAt":"%s"}' % created,
                encoding="utf-8",
            )

        response = client.get("/api/photos/inbox/all?offset=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["hasMore"] is True
        assert data["total"] in (None, 3)
        assert [it["path"].rsplit("/", 1)[-1] for it in data["items"]] == ["b.jpg", "c.jpg"]

    def test_list_inbox_page_appends_undated_after_dated(self, client, temp_data_dir):
        """Photos with no date still load, after every dated photo."""
        inbox = temp_data_dir / "photos" / "inbox"
        (inbox / "new.jpg").write_bytes(b"not-a-real-image")
        (inbox / "new.jpg.json").write_text('{"createdAt":"2024-06-01T12:00:00"}', encoding="utf-8")
        (inbox / "nodate.jpg").write_bytes(b"not-a-real-image")
        (inbox / "nodate.jpg.json").write_text('{"people":[],"tags":[]}', encoding="utf-8")

        client.get("/api/photos/inbox/all")
        first = client.get("/api/photos/inbox/all?limit=1").json()
        assert first["items"][0]["path"].endswith("new.jpg")
        assert first["hasMore"] is True

        rest = client.get("/api/photos/inbox/all", params={"before": first["items"][0]["path"], "limit": 5}).json()
        assert [it["path"].rsplit("/", 1)[-1] for it in rest["items"]] == ["nodate.jpg"]
        assert rest["hasMore"] is False

    def test_paged_gallery_includes_photos_added_after_cache(self, client, temp_data_dir):
        """Folder/file uploads must show up even when the date cache already exists."""
        inbox = temp_data_dir / "photos" / "inbox"
        (inbox / "old.jpg").write_bytes(b"not-a-real-image")
        (inbox / "old.jpg.json").write_text('{"createdAt":"2020-01-01T12:00:00"}', encoding="utf-8")
        client.get("/api/photos/inbox/all")

        batch = inbox / "2026-09-28_0010"
        batch.mkdir()
        (batch / "uploaded.jpg").write_bytes(b"not-a-real-image")
        (batch / "uploaded.jpg.json").write_text(
            '{"createdAt":"2021-08-11T14:09:17+02:00"}',
            encoding="utf-8",
        )

        page = client.get("/api/photos/inbox/all?limit=10").json()
        names = [it["path"].rsplit("/", 1)[-1] for it in page["items"]]
        assert names[0] == "uploaded.jpg"
        assert "old.jpg" in names
        assert page["total"] == 2

    def test_live_photo_mov_is_rejected(self, client, temp_data_dir):
        payload = b"\x00\x00\x00\x00ftypqt  com.apple.quicktime.content.identifier"
        up = client.post(
            "/api/photos/upload",
            files=[("files", ("IMG_8834.mov", payload, "video/quicktime"))],
        )
        assert up.status_code == 200, up.text
        assert up.json()["count"] == 0, up.text

        page = client.get("/api/photos/inbox/all").json()
        assert page["items"] == []
        assert list((temp_data_dir / "photos" / "inbox").rglob("IMG_8834.mov")) == []

    def test_video_upload_is_listed_and_playable(self, client, temp_data_dir, monkeypatch):
        monkeypatch.setattr("server.main.subprocess.run", lambda *a, **k: None)
        payload = b"\x00\x00\x00\x18ftypmp42"
        up = client.post(
            "/api/photos/upload",
            files=[("files", ("clip.mp4", payload, "video/mp4"))],
        )
        assert up.status_code == 200, up.text
        assert up.json()["count"] == 1, up.text

        page = client.get("/api/photos/inbox/all").json()
        item = next(it for it in page["items"] if it["path"].endswith(".mp4"))
        assert item["kind"] == "video"
        assert item["url"] == f"/files/{item['path']}"
        assert (temp_data_dir / item["path"]).read_bytes() == payload

    def test_suggest_photos_invalid_date(self, client):
        """Test photo suggestion with invalid date."""
        response = client.get("/api/photos/suggest?date=invalid")
        assert response.status_code == 400

    def test_suggest_photos_valid_date(self, client, temp_data_dir):
        """Test photo suggestion with valid date."""
        response = client.get("/api/photos/suggest?date=2024-01-15")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "items" in data

    def test_get_sidecar_nonexistent(self, client):
        """Test getting sidecar for nonexistent image."""
        response = client.get("/api/photos/sidecar?path=photos/inbox/nonexistent.jpg")
        assert response.status_code == 404

    def test_update_sidecar_nonexistent(self, client):
        """Test updating sidecar for nonexistent image."""
        response = client.post(
            "/api/photos/sidecar",
            json={
                "path": "photos/inbox/nonexistent.jpg",
                "people": [],
                "tags": [],
                "caption": "",
            },
        )
        assert response.status_code == 404


class TestTripsEndpoints:
    """Tests for trip-related endpoints."""

    def test_update_trip_meta_no_index(self, client, temp_data_dir):
        """Return not found when the trips index is missing."""
        response = client.post(
            "/api/trips/meta",
            json={
                "id": "test-trip",
                "title": "Test Trip",
                "tags": [],
            },
        )
        assert response.status_code == 404
        data = response.json()
        assert data["ok"] is False
        assert data["error"] == "Trips index not found"

    def test_trash_trips_no_index(self, client, temp_data_dir):
        """Test trashing trips when index doesn't exist."""
        response = client.post(
            "/api/trips/trash",
            json={"ids": ["test-trip"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["trashed"] == 0

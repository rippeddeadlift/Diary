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
        assert item["url"] == f"/media/{item['path']}"
        assert (temp_data_dir / item["path"]).read_bytes() == payload

    def test_upload_separates_media_from_app_data(self, client, temp_data_dir, tmp_path, monkeypatch, sample_image):
        media_dir = tmp_path / "archive"
        inbox_dir = media_dir / "photos" / "inbox"
        inbox_dir.mkdir(parents=True)
        monkeypatch.setattr("server.main.MEDIA_DIR", media_dir)
        monkeypatch.setattr("server.main.PHOTOS_INBOX_DIR", inbox_dir)
        monkeypatch.setattr("server.photos_repo.MEDIA_DIR", media_dir)
        monkeypatch.setattr("server.photos_repo.PHOTOS_INBOX_DIR", inbox_dir)

        response = client.post(
            "/api/photos/upload",
            files=[("files", ("photo.jpg", sample_image.read_bytes(), "image/jpeg"))],
        )

        assert response.status_code == 200, response.text
        saved = response.json()["saved"][0]
        assert (media_dir / saved["file"]).is_file()
        assert (temp_data_dir / saved["sidecar"]).is_file()
        assert not (media_dir / f"{saved['file']}.json").exists()
        assert (temp_data_dir / "photos" / "_sha256_index.json").exists()

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

    def test_gpx_import_separates_route_from_trip_metadata(self, tmp_path, monkeypatch):
        from tools import import_gpx_inbox

        app_data = tmp_path / "app-data"
        media_data = tmp_path / "media-data"
        source_dir = tmp_path / "downloads"
        source_dir.mkdir()
        source_gpx = source_dir / "2024-01-01_123456_Cycling.gpx"
        source_gpx.write_text(
            '<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>'
            '<trkpt lat="50.0" lon="6.0"><time>2024-01-01T10:00:00Z</time></trkpt>'
            '<trkpt lat="50.1" lon="6.1"><time>2024-01-01T10:10:00Z</time></trkpt>'
            '</trkseg></trk></gpx>',
            encoding="utf-8",
        )

        trips_dir = app_data / "trips"
        media_trips_dir = media_data / "trips"
        import_dir = media_data / "import" / "gpx"
        monkeypatch.setattr(import_gpx_inbox, "DATA_DIR", app_data)
        monkeypatch.setattr(import_gpx_inbox, "MEDIA_DIR", media_data)
        monkeypatch.setattr(import_gpx_inbox, "IMPORT_DIR", import_dir)
        monkeypatch.setattr(import_gpx_inbox, "DONE_DIR", import_dir / "_done")
        monkeypatch.setattr(import_gpx_inbox, "TRIPS_DIR", trips_dir)
        monkeypatch.setattr(import_gpx_inbox, "TRIPS_MEDIA_DIR", media_trips_dir)
        monkeypatch.setattr(import_gpx_inbox, "INDEX_PATH", trips_dir / "index.json")
        monkeypatch.setattr(
            "sys.argv",
            ["import_gpx_inbox", "--source", str(source_dir)],
        )

        assert import_gpx_inbox.main() == 0

        index = json.loads((trips_dir / "index.json").read_text(encoding="utf-8"))
        entry = index["trips"][0]
        meta_path = trips_dir / entry["path"] / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        route_path = media_trips_dir / entry["path"] / meta["gpx"]

        assert route_path.is_file()
        assert meta_path.is_file()
        assert not (trips_dir / entry["path"] / meta["gpx"]).exists()
        assert (import_dir / "_done" / source_gpx.name).is_file()

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

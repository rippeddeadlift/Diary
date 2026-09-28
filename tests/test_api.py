"""Tests for FastAPI endpoints."""
from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import time

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageStat

from server.main import app


@pytest.fixture
def client(temp_data_dir) -> TestClient:
    """Create a test client."""
    return TestClient(app, client=("127.0.0.1", 50000))


class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_check(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "time" in data


class TestBackupEndpoints:
    def test_export_and_restore_data_zip(self, client, temp_data_dir, tmp_path, monkeypatch):
        (temp_data_dir / "settings.json").write_text('{"private": true}', encoding="utf-8")
        media_dir = tmp_path / "external-media"
        media_dir.mkdir()
        (media_dir / "original.jpg").write_bytes(b"media stays outside the data backup")
        monkeypatch.setattr("server.main.MEDIA_DIR", media_dir)

        started = client.post("/api/backup/export")
        assert started.status_code == 200
        job_id = started.json()["jobId"]
        for _ in range(200):
            status = client.get(f"/api/backup/export/{job_id}")
            assert status.status_code == 200
            if status.json()["status"] != "running":
                break
            time.sleep(0.01)
        assert status.json()["status"] == "ready"
        saved = client.post(f"/api/backup/export/{job_id}/save-to-media")
        assert saved.status_code == 200, saved.text
        backup_path = Path(saved.json()["path"])
        assert backup_path.parent == media_dir
        with zipfile.ZipFile(backup_path) as archive:
            assert archive.read("settings.json") == b'{"private": true}'
            assert "original.jpg" not in archive.namelist()

        backup = BytesIO()
        with zipfile.ZipFile(backup, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("photos/custom.json", '{"tags":["saved"]}')
        backup.seek(0)
        restored = client.post(
            "/api/backup/import",
            files={"file": ("diary-data.zip", backup.getvalue(), "application/zip")},
            data={"confirm_replace": "true"},
        )
        assert restored.status_code == 200, restored.text
        assert restored.json()["files"] == 1
        assert not (temp_data_dir / "settings.json").exists()
        assert json.loads((temp_data_dir / "photos" / "custom.json").read_text(encoding="utf-8")) == {
            "tags": ["saved"]
        }
        assert (media_dir / "original.jpg").read_bytes() == b"media stays outside the data backup"
        assert backup_path.is_file()

    def test_import_rejects_unsafe_zip_without_replacing_data(self, client, temp_data_dir):
        marker = temp_data_dir / "keep.json"
        marker.write_text("keep", encoding="utf-8")
        unsafe_zip = BytesIO()
        with zipfile.ZipFile(unsafe_zip, "w") as archive:
            archive.writestr("../outside.json", "unsafe")

        response = client.post(
            "/api/backup/import",
            files={"file": ("bad.zip", unsafe_zip.getvalue(), "application/zip")},
            data={"confirm_replace": "true"},
        )
        assert response.status_code == 400
        assert marker.read_text(encoding="utf-8") == "keep"


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


class TestMoviesEndpoints:
    def test_movie_folder_lists_posters_and_range_playback(self, client, temp_data_dir, monkeypatch):
        movie_root = temp_data_dir / "movie-library"
        nested = movie_root / "Sci-Fi"
        nested.mkdir(parents=True)
        payload = b"0123456789"
        (nested / "Arrival.mp4").write_bytes(payload)

        sample_times = []

        def create_poster(args, **kwargs):
            if args[0] == "ffprobe":
                return SimpleNamespace(stdout="100\n")
            sample_times.append(args[args.index("-ss") + 1])
            color = "black" if len(sample_times) == 1 else "white"
            Image.new("RGB", (16, 16), color=color).save(args[-1], format="JPEG")
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr("server.main.subprocess.run", create_poster)
        selected = client.post("/api/movies/folder", json={"path": str(movie_root)})
        assert selected.status_code == 200, selected.text
        data = selected.json()
        assert data["folder"] == str(movie_root)
        assert data["count"] == 1
        item = data["items"][0]
        assert item["title"] == "Arrival"
        assert item["path"] == "Sci-Fi/Arrival.mp4"

        opened_paths = []
        monkeypatch.setattr("server.main.sys.platform", "win32")
        monkeypatch.setattr("server.main.os.startfile", opened_paths.append, raising=False)
        opened = client.post("/api/movies/open", json={"path": item["path"]})
        assert opened.status_code == 200, opened.text
        assert opened_paths == [str(nested / "Arrival.mp4")]

        poster = client.get(item["posterUrl"])
        assert poster.status_code == 200
        assert sample_times == ["10.000", "25.000"]
        with Image.open(BytesIO(poster.content)) as poster_image:
            assert ImageStat.Stat(poster_image.convert("L")).mean[0] >= 12

        stream = client.get(item["url"], headers={"Range": "bytes=2-5"})
        assert stream.status_code == 206
        assert stream.content == b"2345"
        assert stream.headers["content-range"] == "bytes 2-5/10"

        traversal = client.get("/api/movies/stream/%2E%2E%2Foutside.mp4")
        assert traversal.status_code == 404

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

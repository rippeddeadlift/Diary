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
        """Trip meta update currently always returns ok=True (no-op backend)."""
        response = client.post(
            "/api/trips/meta",
            json={
                "id": "test-trip",
                "title": "Test Trip",
                "tags": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("ok") is True

    def test_trash_trips_no_index(self, client, temp_data_dir):
        """Test trashing trips when index doesn't exist."""
        response = client.post(
            "/api/trips/trash",
            json={"ids": ["test-trip"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["trashed"] == 0

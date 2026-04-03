from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_raw_smoke_graceful_failure(sample_raw_path: Path) -> None:
    with TestClient(app) as client:
        recipe = client.post("/v1/recipe/reset").json()["recipe"]
        response = client.post(
            "/v1/recipe/apply",
            json={"image_path": str(sample_raw_path), "recipe": recipe, "prefer_raw": True},
        )
        assert response.status_code in {200, 400}
        if response.status_code == 400:
            assert "RAW" in response.text or "raw" in response.text


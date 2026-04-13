from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_e2e_jpeg_path(sample_jpeg: Path, test_workspace: Path) -> None:
    with TestClient(app) as client:
        import_res = client.post("/v1/images/import", json={"path": str(sample_jpeg)})
        assert import_res.status_code == 200
        assert import_res.json()["exists"] is True

        recipe_res = client.post("/v1/recipe/reset")
        assert recipe_res.status_code == 200
        recipe = recipe_res.json()["recipe"]

        apply_res = client.post(
            "/v1/recipe/apply",
            json={"image_path": str(sample_jpeg), "recipe": recipe, "prefer_raw": False},
        )
        assert apply_res.status_code == 200
        preview_path = Path(apply_res.json()["preview_path"])
        assert preview_path.exists()

        export_target = test_workspace / "out.jpg"
        export_res = client.post(
            "/v1/export",
            json={
                "image_path": str(sample_jpeg),
                "recipe": recipe,
                "output_path": str(export_target),
                "format": "jpeg",
                "quality": 90,
                "prefer_raw": False,
            },
        )
        assert export_res.status_code == 200
        assert export_target.exists()

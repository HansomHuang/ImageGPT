from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import default_recipe
from app.services import python_pipeline


class _FakeRawReader:
    def __init__(self) -> None:
        self.sizes = SimpleNamespace(width=512, height=341, raw_width=6048, raw_height=4024)

    def __enter__(self) -> "_FakeRawReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        return False

    def postprocess(self, **_kwargs):  # type: ignore[no-untyped-def]
        import numpy as np

        h, w = self.sizes.height, self.sizes.width
        y, x = np.mgrid[0:h, 0:w]
        r = (x / max(w - 1, 1) * 65535).astype(np.uint16)
        g = (y / max(h - 1, 1) * 65535).astype(np.uint16)
        b = np.full((h, w), 28000, dtype=np.uint16)
        return np.stack([r, g, b], axis=-1)


class _FakeRawPy:
    class ColorSpace:
        sRGB = "sRGB"

    @staticmethod
    def imread(_path: str) -> _FakeRawReader:
        return _FakeRawReader()


class _NeutralAIService:
    def analyze(self, **_kwargs):  # type: ignore[no-untyped-def]
        recipe = default_recipe().model_dump(mode="json")
        recipe["style_tag"] = "raw-test"
        return recipe, [], False


def test_raw_smoke_graceful_failure(sample_raw_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(python_pipeline, "rawpy", None)
    with TestClient(app) as client:
        recipe = client.post("/v1/recipe/reset").json()["recipe"]
        response = client.post(
            "/v1/recipe/apply",
            json={"image_path": str(sample_raw_path), "recipe": recipe, "prefer_raw": True},
        )
        assert response.status_code in {200, 400}
        if response.status_code == 400:
            assert "RAW" in response.text or "raw" in response.text


def test_raw_pipeline_with_python_fallback(
    sample_raw_path: Path, test_workspace: Path, monkeypatch  # type: ignore[no-untyped-def]
) -> None:
    monkeypatch.setattr(python_pipeline, "rawpy", _FakeRawPy)
    monkeypatch.setattr(python_pipeline, "_RAWPY_IMPORT_ERROR", None)

    with TestClient(app) as client:
        import_res = client.post("/v1/images/import", json={"path": str(sample_raw_path)})
        assert import_res.status_code == 200
        metadata = import_res.json()["metadata"]
        assert metadata["is_raw"] is True
        assert metadata["decoder"] == "rawpy"
        assert metadata["width"] == 512
        assert metadata["height"] == 341

        recipe = client.post("/v1/recipe/reset").json()["recipe"]

        apply_res = client.post(
            "/v1/recipe/apply",
            json={"image_path": str(sample_raw_path), "recipe": recipe, "prefer_raw": True},
        )
        assert apply_res.status_code == 200
        assert Path(apply_res.json()["preview_path"]).exists()

        export_target = test_workspace / "raw-out.jpg"
        export_res = client.post(
            "/v1/export",
            json={
                "image_path": str(sample_raw_path),
                "recipe": recipe,
                "output_path": str(export_target),
                "format": "jpeg",
                "quality": 90,
                "prefer_raw": True,
            },
        )
        assert export_res.status_code == 200
        assert export_target.exists()


def test_raw_analyze_with_python_fallback(sample_raw_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(python_pipeline, "rawpy", _FakeRawPy)
    monkeypatch.setattr(python_pipeline, "_RAWPY_IMPORT_ERROR", None)

    with TestClient(app) as client:
        original_ai = app.state.ai_service
        app.state.ai_service = _NeutralAIService()
        try:
            response = client.post(
                "/v1/ai/analyze",
                json={
                    "image_path": str(sample_raw_path),
                    "style_intent": "cool dramatic raw",
                    "metadata": {},
                },
            )
        finally:
            app.state.ai_service = original_ai

        assert response.status_code == 200
        body = response.json()
        assert not any("preview generation failed" in msg.lower() for msg in body["messages"])
        assert body["recipe"]["style_tag"] in {"raw-test", "cool dramatic raw"}

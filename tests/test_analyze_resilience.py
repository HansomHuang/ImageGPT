from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class _FailingAIService:
    def analyze(self, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated analyze crash")


class _NeutralAIService:
    def analyze(self, **_kwargs):  # type: ignore[no-untyped-def]
        return {"notes": ["cinematic"], "warnings": ["test"]}, [], False


class _ListAIService:
    def analyze(self, **_kwargs):  # type: ignore[no-untyped-def]
        return ["not", "an", "object"], [], False


def test_analyze_endpoint_handles_internal_ai_failure(sample_jpeg: Path) -> None:
    with TestClient(app) as client:
        original = app.state.ai_service
        app.state.ai_service = _FailingAIService()
        try:
            response = client.post(
                "/v1/ai/analyze",
                json={"image_path": str(sample_jpeg), "style_intent": "test", "metadata": {}},
            )
        finally:
            app.state.ai_service = original

        assert response.status_code == 200
        body = response.json()
        assert body["fallback_used"] is True
        assert any("before validation" in msg for msg in body["messages"])


def test_analyze_endpoint_applies_style_preset_when_recipe_is_neutral(sample_jpeg: Path) -> None:
    with TestClient(app) as client:
        original = app.state.ai_service
        app.state.ai_service = _NeutralAIService()
        try:
            response = client.post(
                "/v1/ai/analyze",
                json={
                    "image_path": str(sample_jpeg),
                    "style_intent": "restrained cinematic",
                    "metadata": {},
                },
            )
        finally:
            app.state.ai_service = original

        assert response.status_code == 200
        body = response.json()
        assert any("style-matched preset" in msg for msg in body["messages"])
        tone = body["recipe"]["global_adjustments"]["tone"]
        assert tone["contrast"] != 0 or tone["highlights"] != 0


def test_analyze_endpoint_handles_non_object_ai_payload(sample_jpeg: Path) -> None:
    with TestClient(app) as client:
        original = app.state.ai_service
        app.state.ai_service = _ListAIService()
        try:
            response = client.post(
                "/v1/ai/analyze",
                json={"image_path": str(sample_jpeg), "style_intent": "energetic and exposed", "metadata": {}},
            )
        finally:
            app.state.ai_service = original

        assert response.status_code == 200
        body = response.json()
        assert any("not a recipe object" in msg for msg in body["messages"])

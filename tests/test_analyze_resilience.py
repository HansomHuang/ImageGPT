from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


class _FailingAIService:
    def analyze(self, **_kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated analyze crash")


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


from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import RecipeModel


def test_tone_curve_monotonic_valid() -> None:
    model = RecipeModel.model_validate(
        {
            "version": "1.0",
            "style_tag": "curve-ok",
            "confidence": 0.7,
            "tone_curve": [
                {"x": 0.0, "y": 0.0},
                {"x": 0.25, "y": 0.2},
                {"x": 0.5, "y": 0.5},
                {"x": 1.0, "y": 1.0},
            ],
        }
    )
    assert model.tone_curve[2].x == 0.5


def test_tone_curve_monotonic_invalid() -> None:
    with pytest.raises(ValidationError):
        RecipeModel.model_validate(
            {
                "version": "1.0",
                "style_tag": "curve-bad",
                "confidence": 0.7,
                "tone_curve": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 0.5, "y": 0.6},
                    {"x": 0.4, "y": 0.7},
                    {"x": 1.0, "y": 1.0},
                ],
            }
        )


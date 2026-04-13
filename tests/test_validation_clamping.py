from __future__ import annotations

from app.schemas import default_recipe
from app.utils.validation import clamp_recipe_dict


def test_parameter_clamping() -> None:
    payload = {
        "style_tag": "x" * 200,
        "confidence": 3,
        "global_adjustments": {
            "white_balance": {"temperature": 999, "tint": -999},
            "tone": {
                "exposure": 100,
                "contrast": -200,
                "highlights": 101,
                "shadows": -222,
                "whites": 999,
                "blacks": -999,
            },
            "vibrance": 1000,
            "saturation": -1000,
            "finishing": {"clarity": 250, "dehaze": -250, "vignette": 1000},
        },
    }
    clamped = clamp_recipe_dict(payload)
    assert clamped["confidence"] == 1.0
    wb = clamped["global_adjustments"]["white_balance"]
    assert wb["temperature"] == 100
    assert wb["tint"] == -100
    tone = clamped["global_adjustments"]["tone"]
    assert tone["exposure"] == 5
    assert tone["contrast"] == -100
    assert tone["highlights"] == 100
    assert tone["shadows"] == -100
    assert tone["whites"] == 100
    assert tone["blacks"] == -100
    assert len(clamped["style_tag"]) <= 64


def test_default_recipe_schema_shape() -> None:
    recipe = default_recipe().model_dump(mode="json")
    assert recipe["version"] == "1.0"
    assert "global_adjustments" in recipe
    assert "hsl_bands" in recipe
    assert set(recipe["hsl_bands"].keys()) == {
        "red",
        "orange",
        "yellow",
        "green",
        "aqua",
        "blue",
        "purple",
        "magenta",
    }


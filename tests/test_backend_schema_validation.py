from __future__ import annotations

from app.config import get_settings
from app.utils.validation import load_recipe_schema, validate_recipe_or_fallback


def test_schema_validation_and_repair() -> None:
    schema = load_recipe_schema(get_settings().schema_path)
    candidate = {
        "version": "1.0",
        "style_tag": "test",
        "confidence": 2.0,
        "global_adjustments": {"tone": {"exposure": 99}},
        "tone_curve": [{"x": 0.8, "y": 0.2}, {"x": 0.2, "y": 0.8}],
    }
    model, messages, fallback = validate_recipe_or_fallback(candidate, schema)
    assert model.version == "1.0"
    assert messages
    assert fallback is False


def test_schema_validation_accepts_wrapped_color_recipe() -> None:
    schema = load_recipe_schema(get_settings().schema_path)
    candidate = {
        "color_recipe": {
            "version": "1.0",
            "style_tag": "wrapped",
            "confidence": 0.8,
            "global_adjustments": {
                "white_balance": {"temperature": 1, "tint": 0},
                "tone": {
                    "exposure": 0.1,
                    "contrast": 0,
                    "highlights": 0,
                    "shadows": 0,
                    "whites": 0,
                    "blacks": 0,
                },
                "vibrance": 0,
                "saturation": 0,
                "finishing": {"clarity": 0, "dehaze": 0, "vignette": 0},
            },
            "tone_curve": [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}],
            "hsl_bands": {
                "red": {"hue": 0, "saturation": 0, "luminance": 0},
                "orange": {"hue": 0, "saturation": 0, "luminance": 0},
                "yellow": {"hue": 0, "saturation": 0, "luminance": 0},
                "green": {"hue": 0, "saturation": 0, "luminance": 0},
                "aqua": {"hue": 0, "saturation": 0, "luminance": 0},
                "blue": {"hue": 0, "saturation": 0, "luminance": 0},
                "purple": {"hue": 0, "saturation": 0, "luminance": 0},
                "magenta": {"hue": 0, "saturation": 0, "luminance": 0},
            },
            "color_grading": {
                "shadows": {"hue": 0, "sat": 0},
                "midtones": {"hue": 0, "sat": 0},
                "highlights": {"hue": 0, "sat": 0},
                "balance": 0,
                "blend": 50,
            },
            "notes": "",
            "warnings": [],
        }
    }
    model, messages, fallback = validate_recipe_or_fallback(candidate, schema)
    assert model.style_tag == "wrapped"
    assert fallback is False
    assert messages == []

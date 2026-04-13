from __future__ import annotations

import pytest

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


def test_schema_validation_handles_non_object_payload() -> None:
    schema = load_recipe_schema(get_settings().schema_path)
    model, messages, fallback = validate_recipe_or_fallback(["bad", "shape"], schema)
    assert model.version == "1.0"
    assert fallback is False
    assert any("not a recipe object" in msg for msg in messages)


def test_schema_validation_adapts_flat_provider_recipe() -> None:
    schema = load_recipe_schema(get_settings().schema_path)
    candidate = {
        "exposure": 0.35,
        "contrast": 0.28,
        "highlights": -0.12,
        "shadows": 0.18,
        "whites": 0.22,
        "blacks": -0.08,
        "clarity": 0.24,
        "vibrance": 0.31,
        "saturation": 0.19,
        "temperature": 0.07,
        "tint": 0.03,
        "highlight_hue_shift": 0.0,
        "shadow_hue_shift": 0.0,
        "skin_tone_protection": True,
        "highlight_rolloff": "natural",
        "notes": "Provider returned a flat adjustment object.",
        "warnings": ["Watch specular highlights."],
    }
    model, messages, fallback = validate_recipe_or_fallback(candidate, schema)
    assert fallback is False
    assert messages == []
    assert model.global_adjustments.tone.exposure == pytest.approx(0.35)
    assert model.global_adjustments.tone.contrast == pytest.approx(28.0)
    assert model.global_adjustments.vibrance == pytest.approx(31.0)
    assert model.global_adjustments.white_balance.temperature == pytest.approx(7.0)
    assert "Highlight rolloff" in model.notes


def test_schema_validation_repairs_malformed_nested_types() -> None:
    schema = load_recipe_schema(get_settings().schema_path)
    candidate = {
        "style_tag": "bad-types",
        "global_adjustments": "unexpected",
        "tone_curve": ["bad-point", {"x": 1.0, "y": 1.0}],
        "hsl_bands": {"red": "invalid-band"},
        "color_grading": {"shadows": "bad-zone"},
    }
    model, messages, fallback = validate_recipe_or_fallback(candidate, schema)
    assert fallback is False
    assert messages
    assert model.style_tag == "bad-types"
    assert len(model.tone_curve) >= 2
    assert model.hsl_bands.red.hue == 0
    assert model.color_grading.shadows.hue == 0

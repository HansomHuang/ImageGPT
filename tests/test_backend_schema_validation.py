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


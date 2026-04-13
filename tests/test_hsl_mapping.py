from __future__ import annotations

from app.schemas import RecipeModel


def test_hsl_mapping_has_eight_bands() -> None:
    recipe = RecipeModel().model_dump(mode="json")
    bands = recipe["hsl_bands"]
    assert len(bands) == 8
    for band_name, payload in bands.items():
        assert set(payload.keys()) == {"hue", "saturation", "luminance"}, band_name


from __future__ import annotations

import numpy as np

from app.schemas import default_recipe
from app.services.python_pipeline import apply_recipe


def test_pipeline_deterministic() -> None:
    rng = np.random.default_rng(42)
    image = rng.random((80, 96, 3), dtype=np.float32)
    recipe = default_recipe().model_dump(mode="json")
    out_a = apply_recipe(image, recipe)
    out_b = apply_recipe(image, recipe)
    assert np.array_equal(out_a, out_b)


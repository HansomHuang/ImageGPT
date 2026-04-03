from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import jsonschema
from pydantic import ValidationError

from app.schemas import RecipeModel, default_recipe


def load_recipe_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in patch.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _sanitize_curve(curve: list[dict[str, Any]]) -> list[dict[str, float]]:
    cleaned: list[dict[str, float]] = []
    for point in curve:
        x = clamp(float(point.get("x", 0.0)), 0.0, 1.0)
        y = clamp(float(point.get("y", 0.0)), 0.0, 1.0)
        cleaned.append({"x": x, "y": y})

    if len(cleaned) < 2:
        cleaned = [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}]

    cleaned.sort(key=lambda p: p["x"])
    last_y = 0.0
    for point in cleaned:
        point["y"] = max(last_y, point["y"])
        last_y = point["y"]
    cleaned[0]["x"] = 0.0 if cleaned[0]["x"] > 0.1 else cleaned[0]["x"]
    cleaned[-1]["x"] = 1.0 if cleaned[-1]["x"] < 0.9 else cleaned[-1]["x"]
    return cleaned[:12]


def clamp_recipe_dict(candidate: dict[str, Any]) -> dict[str, Any]:
    recipe = _deep_merge(default_recipe().model_dump(mode="json"), candidate)
    recipe["version"] = "1.0"
    recipe["style_tag"] = str(recipe.get("style_tag", "default"))[:64] or "default"
    recipe["confidence"] = clamp(float(recipe.get("confidence", 0.5)), 0.0, 1.0)

    global_adj = recipe["global_adjustments"]
    wb = global_adj["white_balance"]
    wb["temperature"] = clamp(float(wb.get("temperature", 0)), -100, 100)
    wb["tint"] = clamp(float(wb.get("tint", 0)), -100, 100)

    tone = global_adj["tone"]
    tone["exposure"] = clamp(float(tone.get("exposure", 0)), -5, 5)
    for key in ("contrast", "highlights", "shadows", "whites", "blacks"):
        tone[key] = clamp(float(tone.get(key, 0)), -100, 100)

    global_adj["vibrance"] = clamp(float(global_adj.get("vibrance", 0)), -100, 100)
    global_adj["saturation"] = clamp(float(global_adj.get("saturation", 0)), -100, 100)

    finishing = global_adj["finishing"]
    for key in ("clarity", "dehaze", "vignette"):
        finishing[key] = clamp(float(finishing.get(key, 0)), -100, 100)

    recipe["tone_curve"] = _sanitize_curve(recipe.get("tone_curve", []))

    for band in ("red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"):
        values = recipe["hsl_bands"][band]
        values["hue"] = clamp(float(values.get("hue", 0)), -100, 100)
        values["saturation"] = clamp(float(values.get("saturation", 0)), -100, 100)
        values["luminance"] = clamp(float(values.get("luminance", 0)), -100, 100)

    grading = recipe["color_grading"]
    for key in ("shadows", "midtones", "highlights"):
        tone_item = grading[key]
        tone_item["hue"] = clamp(float(tone_item.get("hue", 0)), 0, 360)
        tone_item["sat"] = clamp(float(tone_item.get("sat", 0)), 0, 100)
    grading["balance"] = clamp(float(grading.get("balance", 0)), -100, 100)
    grading["blend"] = clamp(float(grading.get("blend", 50)), 0, 100)

    recipe["notes"] = str(recipe.get("notes", ""))[:256]
    warnings = [str(item)[:140] for item in recipe.get("warnings", [])][:8]
    recipe["warnings"] = warnings
    return recipe


def validate_recipe_or_fallback(
    candidate: dict[str, Any], schema: dict[str, Any]
) -> tuple[RecipeModel, list[str], bool]:
    messages: list[str] = []
    fallback_used = False

    try:
        jsonschema.validate(instance=candidate, schema=schema)
        model = RecipeModel.model_validate(candidate)
        return model, messages, fallback_used
    except Exception as first_error:
        messages.append(f"AI recipe validation failed, attempting safe repair: {first_error}")

    repaired = clamp_recipe_dict(candidate)
    try:
        jsonschema.validate(instance=repaired, schema=schema)
        model = RecipeModel.model_validate(repaired)
        messages.append("Recipe auto-repair succeeded with clamped values.")
        return model, messages, fallback_used
    except (ValidationError, jsonschema.ValidationError, ValueError) as second_error:
        messages.append(f"Recipe repair failed. Falling back to conservative defaults: {second_error}")
        fallback_used = True
        return default_recipe(), messages, fallback_used


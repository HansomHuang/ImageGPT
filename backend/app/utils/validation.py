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


def _looks_like_recipe(payload: dict[str, Any]) -> bool:
    anchors = {"version", "style_tag", "global_adjustments", "tone_curve", "hsl_bands", "color_grading"}
    return len(anchors.intersection(payload.keys())) >= 2


def _provider_flat_recipe_to_imagegpt(candidate: dict[str, Any]) -> dict[str, Any]:
    provider_keys = {
        "exposure",
        "contrast",
        "highlights",
        "shadows",
        "whites",
        "blacks",
        "clarity",
        "dehaze",
        "vibrance",
        "saturation",
        "temperature",
        "tint",
        "highlight_hue_shift",
        "shadow_hue_shift",
        "skin_tone_protection",
        "highlight_rolloff",
        "notes",
        "warnings",
    }
    if len(provider_keys.intersection(candidate.keys())) < 4:
        return candidate
    if _looks_like_recipe(candidate):
        return candidate

    recipe = default_recipe().model_dump(mode="json")
    recipe["style_tag"] = str(candidate.get("style_tag", "provider-adapted"))[:64] or "provider-adapted"
    recipe["confidence"] = clamp(float(candidate.get("confidence", 0.7)), 0.0, 1.0)

    def scaled(name: str, scale: float = 100.0, lo: float = -100.0, hi: float = 100.0) -> float:
        raw = candidate.get(name, 0.0)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 0.0
        if abs(value) <= 1.5:
            value *= scale
        return clamp(value, lo, hi)

    tone = recipe["global_adjustments"]["tone"]
    tone["exposure"] = clamp(float(candidate.get("exposure", 0.0)), -5.0, 5.0)
    tone["contrast"] = scaled("contrast")
    tone["highlights"] = scaled("highlights")
    tone["shadows"] = scaled("shadows")
    tone["whites"] = scaled("whites")
    tone["blacks"] = scaled("blacks")

    wb = recipe["global_adjustments"]["white_balance"]
    wb["temperature"] = scaled("temperature")
    wb["tint"] = scaled("tint")

    recipe["global_adjustments"]["vibrance"] = scaled("vibrance")
    recipe["global_adjustments"]["saturation"] = scaled("saturation")

    finishing = recipe["global_adjustments"]["finishing"]
    finishing["clarity"] = scaled("clarity")
    finishing["dehaze"] = scaled("dehaze")

    highlight_hue_shift = candidate.get("highlight_hue_shift")
    shadow_hue_shift = candidate.get("shadow_hue_shift")
    if isinstance(highlight_hue_shift, (int, float)):
        recipe["color_grading"]["highlights"]["hue"] = clamp(40.0 + float(highlight_hue_shift) * 120.0, 0.0, 360.0)
        recipe["color_grading"]["highlights"]["sat"] = 8.0
    if isinstance(shadow_hue_shift, (int, float)):
        recipe["color_grading"]["shadows"]["hue"] = clamp(220.0 + float(shadow_hue_shift) * 120.0, 0.0, 360.0)
        recipe["color_grading"]["shadows"]["sat"] = 8.0

    note_parts: list[str] = []
    if candidate.get("notes"):
        note_parts.append(str(candidate["notes"]))
    if isinstance(candidate.get("highlight_rolloff"), str):
        note_parts.append(f"Highlight rolloff: {candidate['highlight_rolloff']}.")
    if isinstance(candidate.get("skin_tone_protection"), bool):
        note_parts.append(
            "Skin tone protection requested."
            if candidate["skin_tone_protection"]
            else "Skin tone protection not requested."
        )
    recipe["notes"] = " ".join(part.strip() for part in note_parts if part).strip()[:256]

    raw_warnings = candidate.get("warnings", [])
    if isinstance(raw_warnings, str):
        raw_warnings = [raw_warnings]
    recipe["warnings"] = [str(item)[:140] for item in raw_warnings[:8]]
    return recipe


def _extract_recipe_payload(candidate: Any, depth: int = 0) -> dict[str, Any]:
    if depth > 4:
        return {}
    if isinstance(candidate, list):
        for item in candidate:
            extracted = _extract_recipe_payload(item, depth + 1)
            if _looks_like_recipe(extracted):
                return extracted
        return {}
    if not isinstance(candidate, dict):
        return {}
    if _looks_like_recipe(candidate):
        return candidate

    preferred_keys = ("color_recipe", "recipe", "result", "data", "payload", "output", "response")
    for key in preferred_keys:
        nested = candidate.get(key)
        if isinstance(nested, dict):
            extracted = _extract_recipe_payload(nested, depth + 1)
            return extracted
    return _provider_flat_recipe_to_imagegpt(candidate)


def _brief_error(exc: Exception) -> str:
    text = str(exc).strip().replace("\r", "")
    if not text:
        return exc.__class__.__name__
    first_line = text.split("\n")[0]
    return first_line[:220]


def _sanitize_curve(curve: list[dict[str, Any]]) -> list[dict[str, float]]:
    cleaned: list[dict[str, float]] = []
    for point in curve:
        if not isinstance(point, dict):
            continue
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


def clamp_recipe_dict(candidate: Any) -> dict[str, Any]:
    candidate = _extract_recipe_payload(candidate)
    top_level_allowed = {
        "version",
        "style_tag",
        "confidence",
        "global_adjustments",
        "tone_curve",
        "hsl_bands",
        "color_grading",
        "notes",
        "warnings",
    }
    candidate = {k: v for k, v in candidate.items() if k in top_level_allowed}

    recipe = _deep_merge(default_recipe().model_dump(mode="json"), candidate)
    defaults = default_recipe().model_dump(mode="json")
    recipe["version"] = "1.0"
    recipe["style_tag"] = str(recipe.get("style_tag", "default"))[:64] or "default"
    recipe["confidence"] = clamp(float(recipe.get("confidence", 0.5)), 0.0, 1.0)

    if not isinstance(recipe.get("global_adjustments"), dict):
        recipe["global_adjustments"] = copy.deepcopy(defaults["global_adjustments"])
    if not isinstance(recipe["global_adjustments"].get("white_balance"), dict):
        recipe["global_adjustments"]["white_balance"] = copy.deepcopy(
            defaults["global_adjustments"]["white_balance"]
        )
    if not isinstance(recipe["global_adjustments"].get("tone"), dict):
        recipe["global_adjustments"]["tone"] = copy.deepcopy(defaults["global_adjustments"]["tone"])
    if not isinstance(recipe["global_adjustments"].get("finishing"), dict):
        recipe["global_adjustments"]["finishing"] = copy.deepcopy(
            defaults["global_adjustments"]["finishing"]
        )

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

    if not isinstance(recipe.get("tone_curve"), list):
        recipe["tone_curve"] = copy.deepcopy(defaults["tone_curve"])
    recipe["tone_curve"] = _sanitize_curve(recipe.get("tone_curve", []))

    if not isinstance(recipe.get("hsl_bands"), dict):
        recipe["hsl_bands"] = copy.deepcopy(defaults["hsl_bands"])
    for band in ("red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"):
        if not isinstance(recipe["hsl_bands"].get(band), dict):
            recipe["hsl_bands"][band] = copy.deepcopy(defaults["hsl_bands"][band])
        values = recipe["hsl_bands"][band]
        values["hue"] = clamp(float(values.get("hue", 0)), -100, 100)
        values["saturation"] = clamp(float(values.get("saturation", 0)), -100, 100)
        values["luminance"] = clamp(float(values.get("luminance", 0)), -100, 100)

    if not isinstance(recipe.get("color_grading"), dict):
        recipe["color_grading"] = copy.deepcopy(defaults["color_grading"])
    grading = recipe["color_grading"]
    for key in ("shadows", "midtones", "highlights"):
        if not isinstance(grading.get(key), dict):
            grading[key] = copy.deepcopy(defaults["color_grading"][key])
        tone_item = grading[key]
        tone_item["hue"] = clamp(float(tone_item.get("hue", 0)), 0, 360)
        tone_item["sat"] = clamp(float(tone_item.get("sat", 0)), 0, 100)
    grading["balance"] = clamp(float(grading.get("balance", 0)), -100, 100)
    grading["blend"] = clamp(float(grading.get("blend", 50)), 0, 100)

    notes_value = recipe.get("notes", "")
    if isinstance(notes_value, list):
        notes_value = " ".join(str(item) for item in notes_value)
    elif notes_value is None:
        notes_value = ""
    recipe["notes"] = str(notes_value)[:256]

    raw_warnings = recipe.get("warnings", [])
    if isinstance(raw_warnings, str):
        raw_warnings = [raw_warnings]
    warnings = [str(item)[:140] for item in raw_warnings][:8]
    recipe["warnings"] = warnings
    return recipe


def validate_recipe_or_fallback(
    candidate: Any, schema: dict[str, Any]
) -> tuple[RecipeModel, list[str], bool]:
    messages: list[str] = []
    fallback_used = False
    candidate = _extract_recipe_payload(candidate)
    if not candidate:
        messages.append("AI output was not a recipe object. Attempting safe repair from defaults.")

    try:
        jsonschema.validate(instance=candidate, schema=schema)
        model = RecipeModel.model_validate(candidate)
        return model, messages, fallback_used
    except Exception as first_error:
        messages.append(
            "AI recipe validation failed, attempting safe repair: " f"{_brief_error(first_error)}"
        )

    repaired = clamp_recipe_dict(candidate)
    try:
        jsonschema.validate(instance=repaired, schema=schema)
        model = RecipeModel.model_validate(repaired)
        messages.append("Recipe auto-repair succeeded with clamped values.")
        return model, messages, fallback_used
    except (ValidationError, jsonschema.ValidationError, ValueError) as second_error:
        messages.append(
            "Recipe repair failed. Falling back to conservative defaults: "
            f"{_brief_error(second_error)}"
        )
        fallback_used = True
        return default_recipe(), messages, fallback_used

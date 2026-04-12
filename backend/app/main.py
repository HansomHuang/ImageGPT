from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import history_insert, history_recent, init_db
from app.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ApplyRequest,
    ApplyResponse,
    ExportRequest,
    ExportResponse,
    ImportImageRequest,
    ImportImageResponse,
    PresetLoadResponse,
    PresetSaveRequest,
    PresetSummary,
    RecipeModel,
    default_recipe,
    recipe_to_dict,
)
from app.services.ai_service import AIService
from app.services.core_adapter import CoreAdapter
from app.services.image_service import ImageService
from app.services.preset_service import PresetService
from app.utils.validation import load_recipe_schema, validate_recipe_or_fallback


settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
LOGGER = logging.getLogger("imagegpt.backend")

app = FastAPI(title="ImageGPT Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def resolve_existing_path(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Image not found: {path}")
    return path


def _recipe_is_identity(recipe: RecipeModel) -> bool:
    g = recipe.global_adjustments
    tone = g.tone
    wb = g.white_balance
    fin = g.finishing
    if any(
        abs(v) > 1e-3
        for v in (
            wb.temperature,
            wb.tint,
            tone.exposure,
            tone.contrast,
            tone.highlights,
            tone.shadows,
            tone.whites,
            tone.blacks,
            g.vibrance,
            g.saturation,
            fin.clarity,
            fin.dehaze,
            fin.vignette,
        )
    ):
        return False

    for point in recipe.tone_curve:
        if abs(point.x - point.y) > 1e-3:
            return False

    for band in recipe.hsl_bands.model_dump().values():
        if any(abs(float(band[key])) > 1e-3 for key in ("hue", "saturation", "luminance")):
            return False

    c = recipe.color_grading
    if any(
        abs(v) > 1e-3
        for v in (
            c.shadows.sat,
            c.midtones.sat,
            c.highlights.sat,
            c.balance,
            c.blend - 50.0,
        )
    ):
        return False
    return True


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _synthesize_recipe_from_style_intent(style_intent: str) -> RecipeModel:
    text = style_intent.lower().strip()
    recipe = default_recipe().model_dump(mode="json")
    recipe["style_tag"] = text[:64] or "intent-fallback"
    recipe["confidence"] = 0.62

    strong_words = {"very", "extremely", "intense", "dramatic", "strong", "bold"}
    mild_words = {"slight", "slightly", "gentle", "subtle", "light", "softly"}
    tokens = re.findall(r"[a-zA-Z]+", text)
    intensity = 1.0 + 0.35 * sum(t in strong_words for t in tokens) - 0.22 * sum(
        t in mild_words for t in tokens
    )
    intensity = _clamp(float(intensity), 0.6, 1.8)

    def add(path: str, delta: float) -> None:
        keys = path.split(".")
        node: dict[str, Any] = recipe
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = float(node[keys[-1]]) + delta

    matched = 0
    effect_profiles: list[tuple[tuple[str, ...], dict[str, float]]] = [
        (
            ("energetic", "vivid", "punchy", "dynamic"),
            {
                "global_adjustments.tone.contrast": 22,
                "global_adjustments.vibrance": 26,
                "global_adjustments.saturation": 10,
                "global_adjustments.finishing.clarity": 16,
                "global_adjustments.finishing.dehaze": 8,
            },
        ),
        (
            ("exposed", "bright", "airy", "highkey", "high-key"),
            {
                "global_adjustments.tone.exposure": 0.35,
                "global_adjustments.tone.whites": 16,
                "global_adjustments.tone.shadows": 8,
                "global_adjustments.tone.highlights": -8,
            },
        ),
        (
            ("moody", "dark", "lowkey", "low-key"),
            {
                "global_adjustments.tone.exposure": -0.35,
                "global_adjustments.tone.blacks": -16,
                "global_adjustments.tone.highlights": -12,
                "global_adjustments.tone.contrast": 10,
                "global_adjustments.saturation": -8,
            },
        ),
        (
            ("cinematic", "filmic", "movie"),
            {
                "global_adjustments.tone.contrast": 14,
                "global_adjustments.tone.highlights": -26,
                "global_adjustments.tone.shadows": 20,
                "global_adjustments.tone.blacks": -10,
                "global_adjustments.saturation": -10,
                "global_adjustments.finishing.vignette": -16,
                "color_grading.shadows.hue": 210,
                "color_grading.shadows.sat": 12,
                "color_grading.highlights.hue": 45,
                "color_grading.highlights.sat": 8,
                "color_grading.balance": -8,
                "color_grading.blend": 12,
            },
        ),
        (
            ("warm", "golden", "sunset"),
            {
                "global_adjustments.white_balance.temperature": 18,
                "global_adjustments.white_balance.tint": 4,
                "global_adjustments.saturation": 4,
            },
        ),
        (
            ("cool", "blue", "icy"),
            {
                "global_adjustments.white_balance.temperature": -18,
                "global_adjustments.white_balance.tint": -2,
                "global_adjustments.saturation": -3,
            },
        ),
        (
            ("muted", "vintage", "historical", "retro"),
            {
                "global_adjustments.vibrance": -18,
                "global_adjustments.saturation": -20,
                "global_adjustments.tone.contrast": -6,
                "global_adjustments.finishing.vignette": -14,
                "global_adjustments.white_balance.temperature": 8,
            },
        ),
        (
            ("portrait", "skin", "face"),
            {
                "hsl_bands.orange.saturation": 8,
                "hsl_bands.orange.luminance": 6,
                "hsl_bands.red.saturation": 5,
                "global_adjustments.white_balance.temperature": 6,
                "global_adjustments.tone.highlights": -8,
            },
        ),
        (
            ("natural", "clean", "neutral"),
            {
                "global_adjustments.tone.contrast": 6,
                "global_adjustments.tone.highlights": -10,
                "global_adjustments.tone.shadows": 8,
                "global_adjustments.vibrance": 6,
            },
        ),
    ]

    for keywords, effects in effect_profiles:
        if any(word in text for word in keywords):
            matched += 1
            for field, value in effects.items():
                add(field, value * intensity)

    if matched == 0:
        # Deterministic free-form fallback for arbitrary prompts.
        digest = hashlib.sha1(text.encode("utf-8")).digest()
        n1 = digest[0] / 255.0
        n2 = digest[1] / 255.0
        n3 = digest[2] / 255.0
        n4 = digest[3] / 255.0
        add("global_adjustments.tone.exposure", (n1 - 0.5) * 0.6)
        add("global_adjustments.tone.contrast", (n2 - 0.5) * 30.0)
        add("global_adjustments.vibrance", (n3 - 0.5) * 30.0)
        add("global_adjustments.white_balance.temperature", (n4 - 0.5) * 24.0)
        add("global_adjustments.finishing.clarity", (n1 - 0.5) * 18.0)
        add("hsl_bands.blue.saturation", (n2 - 0.5) * 18.0)
        add("hsl_bands.orange.saturation", (0.5 - n3) * 16.0)
        add("global_adjustments.finishing.vignette", -8.0)
        add("color_grading.shadows.hue", 210.0)
        add("color_grading.shadows.sat", 8.0)
        add("color_grading.blend", 8.0)

    contrast = recipe["global_adjustments"]["tone"]["contrast"]
    s_curve_strength = _clamp(abs(float(contrast)) / 100.0, 0.12, 0.32)
    recipe["tone_curve"] = [
        {"x": 0.0, "y": 0.0 + s_curve_strength * 0.18},
        {"x": 0.25, "y": 0.25 - s_curve_strength * 0.14},
        {"x": 0.5, "y": 0.5},
        {"x": 0.75, "y": 0.75 + s_curve_strength * 0.14},
        {"x": 1.0, "y": 1.0 - s_curve_strength * 0.18},
    ]

    # Clamp ranges.
    g = recipe["global_adjustments"]
    wb = g["white_balance"]
    tone = g["tone"]
    fin = g["finishing"]
    wb["temperature"] = _clamp(float(wb["temperature"]), -100, 100)
    wb["tint"] = _clamp(float(wb["tint"]), -100, 100)
    tone["exposure"] = _clamp(float(tone["exposure"]), -5, 5)
    for key in ("contrast", "highlights", "shadows", "whites", "blacks"):
        tone[key] = _clamp(float(tone[key]), -100, 100)
    g["vibrance"] = _clamp(float(g["vibrance"]), -100, 100)
    g["saturation"] = _clamp(float(g["saturation"]), -100, 100)
    for key in ("clarity", "dehaze", "vignette"):
        fin[key] = _clamp(float(fin[key]), -100, 100)

    for band in ("red", "orange", "yellow", "green", "aqua", "blue", "purple", "magenta"):
        hsl = recipe["hsl_bands"][band]
        hsl["hue"] = _clamp(float(hsl["hue"]), -100, 100)
        hsl["saturation"] = _clamp(float(hsl["saturation"]), -100, 100)
        hsl["luminance"] = _clamp(float(hsl["luminance"]), -100, 100)

    grading = recipe["color_grading"]
    for zone in ("shadows", "midtones", "highlights"):
        grading[zone]["hue"] = _clamp(float(grading[zone]["hue"]), 0, 360)
        grading[zone]["sat"] = _clamp(float(grading[zone]["sat"]), 0, 100)
    grading["balance"] = _clamp(float(grading["balance"]), -100, 100)
    grading["blend"] = _clamp(float(grading["blend"]), 0, 100)

    recipe["notes"] = (
        f"Prompt-driven fallback recipe generated from style intent: '{style_intent[:96]}'. "
        "AI analysis result was near-neutral, so adjustments were synthesized."
    )[:256]
    recipe["warnings"] = []
    return RecipeModel.model_validate(recipe)


@app.on_event("startup")
def startup() -> None:
    init_db(settings.db_path)
    app.state.schema = load_recipe_schema(settings.schema_path)
    app.state.core = CoreAdapter()
    app.state.image_service = ImageService(settings, app.state.core)
    app.state.ai_service = AIService(settings)
    app.state.preset_service = PresetService(settings)
    LOGGER.info("ImageGPT backend started.")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True}


@app.get("/v1/capabilities")
def capabilities() -> dict[str, Any]:
    core_caps = app.state.core.capabilities()
    return {
        "backend": "fastapi",
        "native": core_caps.get("native", False),
        "core": core_caps,
    }


@app.post("/v1/images/import", response_model=ImportImageResponse)
def import_image(payload: ImportImageRequest) -> ImportImageResponse:
    path = Path(payload.path).expanduser().resolve()
    try:
        metadata = app.state.image_service.import_metadata(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Import failed: {exc}") from exc
    preview_path: str | None = None
    preview_width: int | None = None
    preview_height: int | None = None
    try:
        rendered_preview, preview_width, preview_height = app.state.image_service.render_preview(
            image_path=path,
            recipe=default_recipe().model_dump(mode="json"),
            prefer_raw=payload.prefer_raw,
            variant="before",
        )
        preview_path = str(rendered_preview)
    except Exception as exc:
        LOGGER.warning("Import preview generation failed for %s: %s", path, exc)
    return ImportImageResponse(
        path=str(path),
        exists=path.exists(),
        metadata=metadata,
        preview_path=preview_path,
        preview_width=preview_width,
        preview_height=preview_height,
    )


@app.post("/v1/ai/analyze", response_model=AnalyzeResponse)
def analyze_with_ai(payload: AnalyzeRequest) -> AnalyzeResponse:
    image_path = resolve_existing_path(payload.image_path)
    image_metadata = payload.metadata or app.state.image_service.import_metadata(image_path)
    analysis_image_path = image_path
    preview_error: Exception | None = None
    try:
        preview_path, _, _ = app.state.image_service.render_preview(
            image_path=image_path,
            recipe=default_recipe().model_dump(mode="json"),
            prefer_raw=True,
            variant="analysis",
        )
        analysis_image_path = preview_path
    except Exception as exc:
        preview_error = exc
        LOGGER.warning("Analyze preview generation failed, using original image: %s", exc)

    raw_exts = {".arw", ".cr2", ".cr3", ".nef", ".nrw", ".dng"}
    if preview_error is not None and image_path.suffix.lower() in raw_exts:
        raw_recipe = default_recipe().model_dump(mode="json")
        ai_messages = [
            "RAW analysis preview generation failed. Build native core (LibRaw/OpenImageIO) "
            f"to enable RAW analyze. Original error: {preview_error}"
        ]
        ai_fallback = True
    else:
        try:
            raw_recipe, ai_messages, ai_fallback = app.state.ai_service.analyze(
                image_path=analysis_image_path,
                style_intent=payload.style_intent,
                metadata=image_metadata,
                schema=app.state.schema,
            )
        except Exception as exc:
            LOGGER.exception("Unhandled analyze failure: %s", exc)
            raw_recipe = default_recipe().model_dump(mode="json")
            ai_messages = [f"AI analyze failed before validation: {exc}"]
            ai_fallback = True

    try:
        model, validation_messages, validation_fallback = validate_recipe_or_fallback(
            raw_recipe, app.state.schema
        )
    except Exception as exc:
        LOGGER.exception("Unexpected validation failure during analyze: %s", exc)
        model = default_recipe()
        validation_messages = [f"Unexpected validation failure. Using defaults: {exc}"]
        validation_fallback = True
    synthesized_fallback = False
    if payload.style_intent.strip() and _recipe_is_identity(model):
        try:
            model = _synthesize_recipe_from_style_intent(payload.style_intent)
            synthesized_fallback = True
            validation_messages.append(
                "AI recipe was near-neutral; generated prompt-driven fallback adjustments."
            )
        except Exception as exc:
            validation_messages.append(
                f"AI recipe was near-neutral; prompt-driven fallback synthesis failed: {exc}"
            )

    fallback_used = ai_fallback or validation_fallback or synthesized_fallback
    messages = [*ai_messages, *validation_messages]
    history_insert(
        settings.db_path,
        input_path=str(image_path),
        style_intent=payload.style_intent,
        status="fallback" if fallback_used else "ok",
        message=" | ".join(messages) if messages else "AI analysis completed",
        recipe=model.model_dump(mode="json"),
    )
    return AnalyzeResponse(recipe=model, fallback_used=fallback_used, messages=messages)


@app.post("/v1/recipe/apply", response_model=ApplyResponse)
def apply_recipe(payload: ApplyRequest) -> ApplyResponse:
    image_path = resolve_existing_path(payload.image_path)
    model, messages, fallback = validate_recipe_or_fallback(
        recipe_to_dict(payload.recipe), app.state.schema
    )
    try:
        preview_path, width, height = app.state.image_service.render_preview(
            image_path=image_path,
            recipe=model.model_dump(mode="json"),
            prefer_raw=payload.prefer_raw,
            variant="after",
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Apply failed: {exc}") from exc
    app.state.preset_service.save_recipe_sidecar(image_path, model.model_dump(mode="json"))
    history_insert(
        settings.db_path,
        input_path=str(image_path),
        style_intent=None,
        status="fallback" if fallback else "ok",
        message="; ".join(messages) if messages else "Apply succeeded",
        recipe=model.model_dump(mode="json"),
    )
    return ApplyResponse(preview_path=str(preview_path), width=width, height=height)


@app.post("/v1/export", response_model=ExportResponse)
def export(payload: ExportRequest) -> ExportResponse:
    image_path = resolve_existing_path(payload.image_path)
    model, messages, fallback = validate_recipe_or_fallback(
        recipe_to_dict(payload.recipe), app.state.schema
    )
    try:
        output_path = app.state.image_service.export_image(
            image_path=image_path,
            recipe=model.model_dump(mode="json"),
            output_path=Path(payload.output_path).expanduser().resolve() if payload.output_path else None,
            image_format=payload.format,
            quality=payload.quality,
            prefer_raw=payload.prefer_raw,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Export failed: {exc}") from exc
    history_insert(
        settings.db_path,
        input_path=str(image_path),
        style_intent=None,
        status="fallback" if fallback else "ok",
        message="; ".join(messages) if messages else f"Exported {payload.format}",
        recipe=model.model_dump(mode="json"),
    )
    return ExportResponse(output_path=str(output_path), format=payload.format)


@app.get("/v1/presets", response_model=list[PresetSummary])
def presets_list() -> list[PresetSummary]:
    return [PresetSummary(**item) for item in app.state.preset_service.list_presets()]


@app.get("/v1/presets/{name}", response_model=PresetLoadResponse)
def presets_load(name: str) -> PresetLoadResponse:
    try:
        payload = app.state.preset_service.load_preset(name)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    model, _, _ = validate_recipe_or_fallback(payload, app.state.schema)
    return PresetLoadResponse(name=name, recipe=model)


@app.post("/v1/presets/save", response_model=PresetSummary)
def presets_save(payload: PresetSaveRequest) -> PresetSummary:
    saved = app.state.preset_service.save_preset(payload.name, recipe_to_dict(payload.recipe))
    return PresetSummary(name=saved.stem, path=str(saved.resolve()))


@app.post("/v1/recipe/reset")
def recipe_reset() -> dict[str, Any]:
    return {"recipe": default_recipe().model_dump(mode="json")}


@app.get("/v1/history")
def history(limit: int = 30) -> list[dict[str, Any]]:
    rows = history_recent(settings.db_path, limit=max(1, min(limit, 200)))
    parsed: list[dict[str, Any]] = []
    for row in rows:
        row_copy = dict(row)
        if row_copy.get("recipe_json"):
            try:
                row_copy["recipe_json"] = json.loads(row_copy["recipe_json"])
            except Exception:
                pass
        parsed.append(row_copy)
    return parsed

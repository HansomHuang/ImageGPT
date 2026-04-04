from __future__ import annotations

import json
import logging
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
    return ImportImageResponse(path=str(path), exists=path.exists(), metadata=metadata)


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

    model, validation_messages, validation_fallback = validate_recipe_or_fallback(
        raw_recipe, app.state.schema
    )
    fallback_used = ai_fallback or validation_fallback
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

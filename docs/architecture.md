# ImageGPT Architecture

## Stack

- Core: C++17 (`core/`) with OpenImageIO, LibRaw, LittleCMS2, pybind11.
- Backend: Python 3.11 FastAPI (`backend/`), OpenAI Responses API, Pydantic + JSON Schema validation.
- Desktop: Electron + TypeScript (`desktop/`), localhost communication to backend.
- Storage: SQLite (`backend/data/imagegpt.db`) + JSON presets/recipes.

## Data Flow

1. Desktop imports image path.
2. Backend probes metadata via native core (or Python fallback).
3. Backend generates analysis preview and calls OpenAI Responses API.
4. AI output is schema-validated, clamped, or conservatively replaced.
5. Backend applies recipe through native core (preferred) or fallback pipeline.
6. Desktop displays before/after and can export JPEG/TIFF.
7. Recipes are saved as JSON sidecars and presets in preset library.

## Native Core Notes

- JPEG path: implemented via OpenImageIO I/O.
- RAW path: implemented via LibRaw decode hooks.
- ICC transform: LittleCMS2 (sRGB->sRGB transform scaffold for output consistency).
- pybind11 module name: `imagegpt_core`.

## Failure Behavior

- If OpenAI fails, app continues with manual/preset editing and fallback recipe.
- If native core unavailable, backend switches to deterministic Python JPEG pipeline.
- RAW without native core returns graceful error instead of crashing.


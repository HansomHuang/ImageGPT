# ImageGPT

[English](./README.md) | [简体中文](./README.zh-CN.md)

This project was built with Codex (GPT-5.3-Codex and GPT-5.4).
Standalone AI-driven photo color editor (local-first) with a C++ imaging core, FastAPI backend, and Electron desktop UI.

## Monorepo Layout

- `core/` C++ imaging engine (LibRaw + LittleCMS2 + OpenImageIO + pybind11)
- `backend/` FastAPI orchestration, OpenAI Responses integration, validation, SQLite, presets
- `desktop/` Electron + TypeScript desktop app
- `schemas/` strict JSON schema for AI recipe output
- `samples/` sample presets and sample metadata only
- `docs/` architecture and setup docs
- `scripts/` local development scripts
- `tests/` cross-layer tests

## Quick Start (Windows PowerShell)

1. Create Python environment and install backend deps:
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   cd ..
   ```
2. Configure environment:
   ```powershell
   Copy-Item .env.example .env
   # then edit OPENAI_API_KEY or DASHSCOPE_API_KEY and optional settings
   ```
   > When using models such as Qwen, populate `DASHSCOPE_API_KEY`.
3. Optional: build C++ core module (recommended for performance):
   ```powershell
   cd core
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --config Release
   cd ..
   ```
4. Install desktop deps:
   ```powershell
   cd desktop
   npm.cmd install
   cd ..
   ```
5. Run backend + desktop together:
   ```powershell
   python scripts/dev.py
   ```
6. Run tests:
   ```powershell
   python scripts/test.py
   ```

If desktop shows `Analyze failed: Error: Failed to fetch`, the backend is unreachable on `http://127.0.0.1:8000`. Start backend first with `cd backend && python run_server.py`, then retry.

## Notes

- JPEG path is fully implemented with a Python fallback pipeline if the native core module is unavailable.
- RAW decode path is implemented in native core via LibRaw and also via a Python `rawpy` fallback for `.NEF`, `.ARW`, `.CR2`, `.CR3`, `.NRW`, and `.DNG` when the native module is unavailable.
- AI recipe output is strict schema-validated and clamped before pipeline use.

## Limitations

- Camera-matching color science is intentionally conservative in v1.
- `rawpy` fallback gives working RAW ingest/render/export, but full native-core builds remain the preferred path for production performance and deeper metadata handling.
- Desktop UI is utilitarian and optimized for correctness over advanced UX.
- In this environment, native build verification requires installing `cmake`.

## Development Tracking

See `TASKS.md` for completed and remaining work.

## CI

GitHub Actions workflows are included:
- `.github/workflows/backend-ci.yml`
- `.github/workflows/desktop-ci.yml`
- `.github/workflows/native-core-ci.yml`

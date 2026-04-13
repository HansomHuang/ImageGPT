# ImageGPT

[简体中文](#zh-cn) | [English](#en-us)

---

## English {#en-us}

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
   > When using models such as Qwen, please populate the DASHSCOPE_API_KEY.
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

If desktop shows `Analyze failed: Error: Failed to fetch`, it means backend is unreachable on `http://127.0.0.1:8000`. Start backend first (`cd backend && python run_server.py`) and retry.

## Notes

- JPEG path is fully implemented with a Python fallback pipeline if the native core module is unavailable.
- RAW decode path is implemented in native core via LibRaw and also via a Python `rawpy` fallback for `.NEF`, `.ARW`, `.CR2`, `.CR3`, `.NRW`, and `.DNG` when the native module is unavailable.
- AI recipe output is strict schema-validated and clamped before pipeline use.

## Limitations (Current)

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

---

## 简体中文/Simplified Chinese {#zh-cn}

本项目使用Codex（GPT-5.3-Codex 和 GPT-5.4）构建。
ImageGPT 是一个本地优先的独立 AI 照片调色工具，包含 C++ 图像核心、FastAPI 后端和 Electron 桌面界面。

## 项目结构

- `core/`：C++ 图像引擎（LibRaw + LittleCMS2 + OpenImageIO + pybind11）
- `backend/`：FastAPI 编排层、OpenAI Responses 集成、参数校验、SQLite、预设
- `desktop/`：Electron + TypeScript 桌面应用
- `schemas/`：AI 调色配方的严格 JSON Schema
- `samples/`：示例预设和示例元数据
- `docs/`：架构与开发文档
- `scripts/`：本地开发脚本
- `tests/`：跨层测试

## 快速开始（Windows PowerShell）

1. 创建 Python 虚拟环境并安装后端依赖：
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   cd ..
   ```
2. 配置环境变量：
   ```powershell
   Copy-Item .env.example .env
   # 然后填写 OPENAI_API_KEY 或 DASHSCOPE_API_KEY，以及其他可选配置
   ```
   > 若使用如千问的大模型，请将千问的 API_KEY 填入 DASHSCOPE_API_KEY.
3. 可选：编译 C++ 核心模块（推荐，性能更好）：
   ```powershell
   cd core
   cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
   cmake --build build --config Release
   cd ..
   ```
4. 安装桌面端依赖：
   ```powershell
   cd desktop
   npm.cmd install
   cd ..
   ```
5. 同时启动后端和桌面端：
   ```powershell
   python scripts/dev.py
   ```
6. 运行测试：
   ```powershell
   python scripts/test.py
   ```

如果桌面端提示 `Analyze failed: Error: Failed to fetch`，说明本地后端 `http://127.0.0.1:8000` 不可达。请先启动后端（`cd backend && python run_server.py`）再重试。

## 当前能力

- JPEG 路径已完整实现，在原生核心不可用时可以走 Python 回退管线。
- RAW 路径优先使用原生 LibRaw 核心；如果原生模块不可用，也支持基于 `rawpy` 的 `.NEF`、`.ARW`、`.CR2`、`.CR3`、`.NRW`、`.DNG` 回退解码。
- AI 输出会先经过严格 schema 校验和参数钳制，再进入调色管线。

## 当前限制

- v1 的相机色彩科学实现偏保守，优先稳定性。
- `rawpy` 回退路径已经可用于 RAW 导入、预览和导出，但生产环境仍建议优先使用原生核心以获得更好的性能和更完整的元数据支持。
- 桌面界面以正确性和可用性为主，视觉层面保持简洁。
- 当前环境里，验证原生 C++ 构建仍需要安装 `cmake`。

## 开发跟踪

完成项和剩余任务见 `TASKS.md`。

## 持续集成

仓库已包含以下 GitHub Actions：
- `.github/workflows/backend-ci.yml`
- `.github/workflows/desktop-ci.yml`
- `.github/workflows/native-core-ci.yml`

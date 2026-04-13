# ImageGPT

[English](./README.md) | [简体中文](./README.zh-CN.md)

本项目使用 Codex（GPT-5.3-Codex 和 GPT-5.4）构建。
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
   > 如果使用千问等模型，请填写 `DASHSCOPE_API_KEY`。
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

如果桌面端提示 `Analyze failed: Error: Failed to fetch`，说明本地后端 `http://127.0.0.1:8000` 不可达。请先启动后端：`cd backend && python run_server.py`，然后再重试。

## 当前能力

- JPEG 路径已完整实现，在原生核心不可用时可走 Python 回退管线。
- RAW 路径优先使用原生 LibRaw 核心；如果原生模块不可用，也支持基于 `rawpy` 的 `.NEF`、`.ARW`、`.CR2`、`.CR3`、`.NRW`、`.DNG` 回退解码。
- AI 输出会先经过严格 schema 校验和参数钳制，再进入调色管线。

## 当前限制

- v1 的相机色彩科学实现偏保守，优先稳定性。
- `rawpy` 回退路径已经可用于 RAW 导入、预览和导出，但生产环境仍建议优先使用原生核心，以获得更好的性能和更完整的元数据支持。
- 桌面界面以正确性和可用性为主，视觉层面保持简洁。
- 当前环境里，验证原生 C++ 构建仍需要安装 `cmake`。

## 开发跟踪

完成项和剩余任务见 `TASKS.md`。

## 持续集成

仓库已包含以下 GitHub Actions：
- `.github/workflows/backend-ci.yml`
- `.github/workflows/desktop-ci.yml`
- `.github/workflows/native-core-ci.yml`

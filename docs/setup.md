# Developer Setup

## Prerequisites

- Python 3.11+
- Node.js 20+
- CMake 3.18+
- Native libs for full core: OpenImageIO, LibRaw, LittleCMS2, pybind11

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..
```

## Desktop

```powershell
cd desktop
npm install
cd ..
```

## Optional Native Core Build

```powershell
cd core
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release
cd ..
```

## Environment

```powershell
Copy-Item .env.example .env
```

Set at least:

- `OPENAI_API_KEY`

## Run

```powershell
python scripts/dev.py
```


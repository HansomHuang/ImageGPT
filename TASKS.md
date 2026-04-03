# ImageGPT Task Board

## Completed
- [x] Initialize git repository
- [x] Create monorepo folder structure
- [x] Add root README and environment template
- [x] Add strict AI recipe JSON schema
- [x] Add sample preset library (5 presets)
- [x] Implement C++ core scaffold with JPEG pipeline, RAW hooks, ICC hooks, and pybind11 module
- [x] Implement FastAPI backend endpoints, schema validation/repair, SQLite history, and OpenAI integration
- [x] Implement Electron + TypeScript desktop app (import, analyze, apply, reset, export, presets, logs)
- [x] Implement developer scripts for combined run (`scripts/dev.py`) and tests (`scripts/test.py`)
- [x] Implement required unit/integration/smoke tests and run suite successfully (9 passed)
- [x] Add CI workflows for backend tests, desktop build, and native core smoke build

## In Progress
- [ ] Verify native C++ build in this environment (blocked locally: `cmake` missing; CI workflow added)
- [ ] Validate full desktop runtime launch in this environment (desktop build is verified)

## Remaining
- [x] Validate end-to-end run with local JPEG API path
- [x] Document native dependency installation and architecture
- [ ] Expand RAW test fixtures when sample RAW is available

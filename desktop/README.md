# Desktop

Electron + TypeScript desktop UI.

## Run

```powershell
npm install
npm run build
npm run dev
```

Assumes backend is available at `http://127.0.0.1:8000`.

Notes:
- `npm run dev` now starts Electron without forcing a rebuild first.
- Use `npm run dev:build` when you want an explicit rebuild before launch.
- Main/preload builds mark `electron` as external to avoid bundling Electron runtime stubs into `dist/main/main.js`.

## Step-by-Step Local Usage

1. Configure environment (repo root):
```powershell
Copy-Item .env.example .env
```
Set `OPENAI_API_KEY` in `.env`.

2. Install backend dependencies:
```powershell
cd ..\backend
python -m pip install -r requirements.txt
```

3. Start backend:
```powershell
python run_server.py
```
Keep this terminal open. Health check:
```powershell
curl http://127.0.0.1:8000/health
```

4. In a second terminal, start desktop:
```powershell
cd ..\desktop
npm install
npm run build
npm run dev
```

5. In app:
- Click `Import Image`
- Click `Analyze with AI`
- Click `Apply`
- Click `Export`

If you see `Failed to fetch`, backend is not reachable from desktop. Confirm backend is running on port `8000`, or set:
```powershell
$env:IMGGPT_BACKEND_URL='http://127.0.0.1:8000'
npm run dev
```

## Electron Install Troubleshooting

If `npm run dev` reports:
`Electron failed to install correctly, please delete node_modules/electron and try installing again`

Run:

```powershell
npm.cmd run doctor:electron
npm.cmd rebuild electron
```

If your network blocks GitHub release downloads, use mirror/proxy:

```powershell
$env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
npm.cmd rebuild electron
```

Then verify again:

```powershell
npm.cmd run doctor:electron
```

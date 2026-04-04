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

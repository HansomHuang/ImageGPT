# Desktop

Electron + TypeScript desktop UI.

## Run

```powershell
npm install
npm run dev
```

Assumes backend is available at `http://127.0.0.1:8000`.

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

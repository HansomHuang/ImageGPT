import { app, BrowserWindow, dialog, ipcMain } from "electron";
import path from "node:path";

const createWindow = () => {
  const window = new BrowserWindow({
    width: 1440,
    height: 920,
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  window.loadFile(path.join(__dirname, "../renderer/index.html"));
};

app.whenReady().then(() => {
  ipcMain.handle("dialog:openImage", async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openFile"],
      filters: [
        {
          name: "Images",
          extensions: ["jpg", "jpeg", "png", "tif", "tiff", "arw", "cr2", "cr3", "nef", "nrw", "dng"],
        },
      ],
    });
    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }
    return result.filePaths[0];
  });

  ipcMain.handle("dialog:saveExport", async (_, defaultPath: string) => {
    const result = await dialog.showSaveDialog({
      defaultPath,
      filters: [
        { name: "JPEG", extensions: ["jpg"] },
        { name: "TIFF", extensions: ["tiff"] },
      ],
    });
    if (result.canceled || !result.filePath) {
      return null;
    }
    return result.filePath;
  });

  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});


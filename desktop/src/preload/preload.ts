import { contextBridge, ipcRenderer } from "electron";

const BACKEND_BASE = process.env.IMGGPT_BACKEND_URL ?? "http://127.0.0.1:8000";

async function apiRequest<T>(
  path: string,
  method: "GET" | "POST" = "GET",
  body?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_BASE}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (error) {
    throw new Error(
      `Cannot reach backend at ${BACKEND_BASE}. Start backend first and confirm /health is reachable. Original error: ${error}`,
    );
  }

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${text}`);
  }
  return (await response.json()) as T;
}

const api = {
  pickImage: () => ipcRenderer.invoke("dialog:openImage") as Promise<string | null>,
  pickExportPath: (defaultPath: string) =>
    ipcRenderer.invoke("dialog:saveExport", defaultPath) as Promise<string | null>,
  health: () => apiRequest<{ ok: boolean }>("/health"),
  capabilities: () => apiRequest<Record<string, unknown>>("/v1/capabilities"),
  importImage: (path: string) => apiRequest("/v1/images/import", "POST", { path }),
  analyze: (imagePath: string, styleIntent: string, metadata: Record<string, unknown>) =>
    apiRequest("/v1/ai/analyze", "POST", {
      image_path: imagePath,
      style_intent: styleIntent,
      metadata,
    }),
  apply: (imagePath: string, recipe: unknown) =>
    apiRequest("/v1/recipe/apply", "POST", {
      image_path: imagePath,
      recipe,
      prefer_raw: true,
    }),
  exportImage: (
    imagePath: string,
    recipe: unknown,
    outputPath: string | null,
    format: "jpeg" | "tiff",
    quality: number,
  ) =>
    apiRequest("/v1/export", "POST", {
      image_path: imagePath,
      recipe,
      output_path: outputPath,
      format,
      quality,
      prefer_raw: true,
    }),
  listPresets: () => apiRequest<Array<{ name: string; path: string }>>("/v1/presets"),
  loadPreset: (name: string) => apiRequest<{ name: string; recipe: unknown }>(`/v1/presets/${name}`),
  savePreset: (name: string, recipe: unknown) =>
    apiRequest("/v1/presets/save", "POST", { name, recipe }),
  resetRecipe: () => apiRequest<{ recipe: unknown }>("/v1/recipe/reset", "POST"),
  history: () => apiRequest<Array<Record<string, unknown>>>("/v1/history"),
};

contextBridge.exposeInMainWorld("imagegpt", api);

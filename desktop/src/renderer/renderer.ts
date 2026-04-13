type Recipe = Record<string, unknown>;

const elements = {
  backendStatus: document.getElementById("backendStatus") as HTMLSpanElement,
  coreStatus: document.getElementById("coreStatus") as HTMLSpanElement,
  importBtn: document.getElementById("importBtn") as HTMLButtonElement,
  analyzeBtn: document.getElementById("analyzeBtn") as HTMLButtonElement,
  applyBtn: document.getElementById("applyBtn") as HTMLButtonElement,
  resetBtn: document.getElementById("resetBtn") as HTMLButtonElement,
  exportBtn: document.getElementById("exportBtn") as HTMLButtonElement,
  styleIntent: document.getElementById("styleIntent") as HTMLInputElement,
  exportFormat: document.getElementById("exportFormat") as HTMLSelectElement,
  jpegQuality: document.getElementById("jpegQuality") as HTMLInputElement,
  presetSelect: document.getElementById("presetSelect") as HTMLSelectElement,
  loadPresetBtn: document.getElementById("loadPresetBtn") as HTMLButtonElement,
  savePresetBtn: document.getElementById("savePresetBtn") as HTMLButtonElement,
  presetName: document.getElementById("presetName") as HTMLInputElement,
  beforeImage: document.getElementById("beforeImage") as HTMLImageElement,
  afterImage: document.getElementById("afterImage") as HTMLImageElement,
  recipeBox: document.getElementById("recipeBox") as HTMLTextAreaElement,
  metadataBox: document.getElementById("metadataBox") as HTMLPreElement,
  logBox: document.getElementById("logBox") as HTMLPreElement,
};

let currentImagePath: string | null = null;
let currentMetadata: Record<string, unknown> = {};

function log(message: string): void {
  const timestamp = new Date().toLocaleTimeString();
  elements.logBox.textContent = `[${timestamp}] ${message}\n${elements.logBox.textContent}`;
}

function fileUrl(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  return `file:///${normalized}`;
}

function currentRecipe(): Recipe {
  try {
    return JSON.parse(elements.recipeBox.value) as Recipe;
  } catch (error) {
    throw new Error(`Recipe JSON is invalid: ${error}`);
  }
}

async function refreshPresets(): Promise<void> {
  const presets = await window.imagegpt.listPresets();
  elements.presetSelect.innerHTML = "";
  for (const preset of presets) {
    const option = document.createElement("option");
    option.value = preset.name;
    option.textContent = preset.name;
    elements.presetSelect.appendChild(option);
  }
}

async function checkBackend(): Promise<void> {
  try {
    await window.imagegpt.health();
    const caps = await window.imagegpt.capabilities();
    elements.backendStatus.textContent = "Backend: online";
    elements.coreStatus.textContent = `Core: ${caps.native ? "native" : "python fallback"}`;
  } catch (error) {
    elements.backendStatus.textContent = "Backend: offline";
    elements.coreStatus.textContent = "Core: unavailable";
    log(`Backend not reachable: ${error}`);
  }
}

async function initialize(): Promise<void> {
  const reset = await window.imagegpt.resetRecipe();
  elements.recipeBox.value = JSON.stringify(reset.recipe, null, 2);
  await checkBackend();
  await refreshPresets();
}

elements.importBtn.addEventListener("click", async () => {
  try {
    const path = await window.imagegpt.pickImage();
    if (!path) {
      return;
    }
    currentImagePath = path;
    const imported = await window.imagegpt.importImage(path);
    const beforePreview = imported.preview_path ? fileUrl(imported.preview_path) : fileUrl(path);
    elements.beforeImage.src = `${beforePreview}?t=${Date.now()}`;
    elements.afterImage.removeAttribute("src");
    currentMetadata = imported.metadata;
    elements.metadataBox.textContent = JSON.stringify(imported.metadata, null, 2);
    log(`Imported image: ${path}`);
  } catch (error) {
    log(`Import failed: ${error}`);
  }
});

elements.analyzeBtn.addEventListener("click", async () => {
  if (!currentImagePath) {
    log("No image loaded.");
    return;
  }
  try {
    const response = await window.imagegpt.analyze(
      currentImagePath,
      elements.styleIntent.value.trim(),
      currentMetadata,
    );
    elements.recipeBox.value = JSON.stringify(response.recipe, null, 2);
    for (const msg of response.messages) {
      log(msg);
    }
    log(response.fallback_used ? "Analyze completed with fallback." : "Analyze completed.");
  } catch (error) {
    log(`Analyze failed: ${error}`);
  }
});

elements.applyBtn.addEventListener("click", async () => {
  if (!currentImagePath) {
    log("No image loaded.");
    return;
  }
  try {
    const response = await window.imagegpt.apply(currentImagePath, currentRecipe());
    elements.afterImage.src = `${fileUrl(response.preview_path)}?t=${Date.now()}`;
    log(`Applied recipe. Preview: ${response.width}x${response.height}`);
  } catch (error) {
    log(`Apply failed: ${error}`);
  }
});

elements.resetBtn.addEventListener("click", async () => {
  try {
    const reset = await window.imagegpt.resetRecipe();
    elements.recipeBox.value = JSON.stringify(reset.recipe, null, 2);
    log("Recipe reset to defaults.");
  } catch (error) {
    log(`Reset failed: ${error}`);
  }
});

elements.exportBtn.addEventListener("click", async () => {
  if (!currentImagePath) {
    log("No image loaded.");
    return;
  }
  try {
    const format = elements.exportFormat.value as "jpeg" | "tiff";
    const defaultPath = currentImagePath.replace(/\.[^.]+$/, format === "jpeg" ? "_edited.jpg" : "_edited.tiff");
    const outputPath = await window.imagegpt.pickExportPath(defaultPath);
    if (!outputPath) {
      return;
    }
    const response = await window.imagegpt.exportImage(
      currentImagePath,
      currentRecipe(),
      outputPath,
      format,
      Number(elements.jpegQuality.value || 92),
    );
    log(`Exported ${response.format.toUpperCase()}: ${response.output_path}`);
  } catch (error) {
    log(`Export failed: ${error}`);
  }
});

elements.loadPresetBtn.addEventListener("click", async () => {
  const selected = elements.presetSelect.value;
  if (!selected) {
    return;
  }
  try {
    const preset = await window.imagegpt.loadPreset(selected);
    elements.recipeBox.value = JSON.stringify(preset.recipe, null, 2);
    log(`Preset loaded: ${selected}`);
  } catch (error) {
    log(`Preset load failed: ${error}`);
  }
});

elements.savePresetBtn.addEventListener("click", async () => {
  const name = elements.presetName.value.trim();
  if (!name) {
    log("Preset name is required.");
    return;
  }
  try {
    const saved = await window.imagegpt.savePreset(name, currentRecipe());
    await refreshPresets();
    elements.presetSelect.value = saved.name;
    log(`Preset saved: ${saved.name}`);
  } catch (error) {
    log(`Preset save failed: ${error}`);
  }
});

initialize().catch((error) => log(`Initialization failed: ${error}`));

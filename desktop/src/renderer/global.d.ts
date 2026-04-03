export {};

declare global {
  interface Window {
    imagegpt: {
      pickImage(): Promise<string | null>;
      pickExportPath(defaultPath: string): Promise<string | null>;
      health(): Promise<{ ok: boolean }>;
      capabilities(): Promise<Record<string, unknown>>;
      importImage(path: string): Promise<{ metadata: Record<string, unknown> }>;
      analyze(
        imagePath: string,
        styleIntent: string,
        metadata: Record<string, unknown>,
      ): Promise<{ recipe: Record<string, unknown>; messages: string[]; fallback_used: boolean }>;
      apply(
        imagePath: string,
        recipe: Record<string, unknown>,
      ): Promise<{ preview_path: string; width: number; height: number }>;
      exportImage(
        imagePath: string,
        recipe: Record<string, unknown>,
        outputPath: string | null,
        format: "jpeg" | "tiff",
        quality: number,
      ): Promise<{ output_path: string; format: string }>;
      listPresets(): Promise<Array<{ name: string; path: string }>>;
      loadPreset(name: string): Promise<{ name: string; recipe: Record<string, unknown> }>;
      savePreset(name: string, recipe: Record<string, unknown>): Promise<{ name: string; path: string }>;
      resetRecipe(): Promise<{ recipe: Record<string, unknown> }>;
      history(): Promise<Array<Record<string, unknown>>>;
    };
  }
}


import { copyFile, mkdir } from "node:fs/promises";
import { build } from "esbuild";

await mkdir("dist/main", { recursive: true });
await mkdir("dist/preload", { recursive: true });
await mkdir("dist/renderer", { recursive: true });
await mkdir("dist/renderer/styles", { recursive: true });

await build({
  entryPoints: ["src/main/main.ts"],
  outfile: "dist/main/main.js",
  bundle: true,
  platform: "node",
  target: "node20",
});

await build({
  entryPoints: ["src/preload/preload.ts"],
  outfile: "dist/preload/preload.js",
  bundle: true,
  platform: "node",
  target: "node20",
});

await build({
  entryPoints: ["src/renderer/renderer.ts"],
  outfile: "dist/renderer/renderer.js",
  bundle: true,
  platform: "browser",
  target: "chrome120",
});

await copyFile("src/renderer/index.html", "dist/renderer/index.html");
await copyFile("src/renderer/styles/main.css", "dist/renderer/styles/main.css");

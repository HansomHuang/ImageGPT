import fs from "node:fs";
import path from "node:path";
import process from "node:process";

const root = process.cwd();
const electronDir = path.join(root, "node_modules", "electron");
const pathTxt = path.join(electronDir, "path.txt");

function readIfExists(file) {
  try {
    return fs.readFileSync(file, "utf8").trim();
  } catch {
    return "";
  }
}

function printDiagnostics() {
  const envKeys = [
    "ELECTRON_OVERRIDE_DIST_PATH",
    "ELECTRON_MIRROR",
    "ELECTRON_SKIP_BINARY_DOWNLOAD",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
  ];

  console.error("Electron runtime binary check failed.");
  console.error(`- electron package dir: ${electronDir}`);
  console.error(`- path.txt exists: ${fs.existsSync(pathTxt)}`);
  console.error(`- dist exists: ${fs.existsSync(path.join(electronDir, "dist"))}`);
  for (const key of envKeys) {
    console.error(`- ${key}=${process.env[key] ?? ""}`);
  }
  console.error("");
  console.error("Recovery commands (PowerShell):");
  console.error("1) Try rebuilding Electron:");
  console.error("   npm.cmd rebuild electron");
  console.error("");
  console.error("2) If your network blocks GitHub release downloads, use proxy or mirror:");
  console.error("   $env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'");
  console.error("   npm.cmd rebuild electron");
  console.error("");
  console.error("3) Then verify:");
  console.error("   npm.cmd run doctor:electron");
}

function checkElectronInstall() {
  if (!fs.existsSync(electronDir)) {
    return { ok: false, reason: "node_modules/electron is missing" };
  }

  const exeName = readIfExists(pathTxt);
  if (!exeName) {
    return { ok: false, reason: "node_modules/electron/path.txt is missing or empty" };
  }

  const exePath = path.join(electronDir, "dist", exeName);
  if (!fs.existsSync(exePath)) {
    return { ok: false, reason: `electron executable missing: ${exePath}` };
  }

  return { ok: true, exePath };
}

const doctorMode = process.argv.includes("--doctor");
const result = checkElectronInstall();
if (!result.ok) {
  console.error(result.reason);
  printDiagnostics();
  process.exit(1);
}

if (doctorMode) {
  console.log("Electron install looks healthy.");
  console.log(`Executable: ${result.exePath}`);
} else {
  console.log(`Electron binary found: ${result.exePath}`);
}


#!/usr/bin/env node
/**
 * Build trading-engine sidecar (runs as prebuild before vite build).
 * Uses venv Python when available (pandas_ta needs 3.12; system may be 3.14).
 */
import { execSync } from "child_process";
import { existsSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const isWin = process.platform === "win32";
const venvPy = isWin
  ? join(root, "trading-engine", ".venv", "Scripts", "python.exe")
  : join(root, "trading-engine", ".venv", "bin", "python");
const buildPy = join(root, "trading-engine", "build.py");
const py = existsSync(venvPy) ? venvPy : isWin ? "python" : "python3";

execSync(`"${py}" "${buildPy}"`, { stdio: "inherit", cwd: root });

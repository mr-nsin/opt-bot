#!/usr/bin/env node
/**
 * Build trading-engine sidecar for BOTH aarch64 and x86_64, then merge with lipo.
 * Used by build-mac-universal.sh. Produces:
 *   trading-engine-universal-apple-darwin (via lipo merge)
 * Tauri universal build expects trading-engine-universal-apple-darwin (see tauri#9422).
 *
 * x86_64 requires a DEDICATED venv with x86_64-only packages (arch -x86_64).
 * Shared site-packages have arm64 .so files that break PyInstaller.
 */
import { execSync, spawnSync } from "child_process";
import { existsSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const buildPy = join(root, "trading-engine", "build.py");
const binariesDir = join(root, "src-tauri", "binaries");
const venvX64 = join(root, "trading-engine", ".venv_x64");

const aarch64Bin = join(binariesDir, "trading-engine-aarch64-apple-darwin");
const x64Bin = join(binariesDir, "trading-engine-x86_64-apple-darwin");
const universalBin = join(binariesDir, "trading-engine-universal-apple-darwin");

// x86_64: Python 3.12 required (pandas_ta has no 3.13 x86_64 wheel). Use arch -x86_64 with universal installer.
const x64PythonCandidates = [
  "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
  "/usr/local/bin/python3.12",
  "/usr/local/bin/python3.11",
  "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
  "/usr/local/bin/python3",
];

function findX64Python() {
  for (const p of x64PythonCandidates) {
    if (!existsSync(p)) continue;
    try {
      const r = spawnSync("arch", ["-x86_64", p, "-c", "import sys; sys.exit(0)"], {
        encoding: "utf8",
        timeout: 5000,
      });
      if (r.status === 0) return p;
    } catch {
      /* skip */
    }
  }
  return null;
}

function run(cmd, opts = {}) {
  execSync(cmd, { stdio: "inherit", cwd: root, ...opts });
}

// aarch64: use venv (Apple Silicon native)
const venvPy = join(root, "trading-engine", ".venv", "bin", "python");

// 1. Build aarch64 (native)
console.log("\n==> Building trading-engine for aarch64 (Apple Silicon)");
const py = existsSync(venvPy) ? venvPy : "python3";
run(`"${py}" "${buildPy}"`);

// 2. Build x86_64 — requires dedicated venv with x86_64-only packages
// ALWAYS use arch -x86_64 to force x86_64 process (PyInstaller detects arch from running Python)
const x64Py = findX64Python();
const x64Arch = "arch -x86_64 ";
let hasX64 = false;
if (x64Py) {
  const venvPy64 = join(venvX64, "bin", "python");
  const reqFile = join(root, "trading-engine", "requirements.txt");
  if (existsSync(venvPy64)) {
    const versionCheck = spawnSync("arch", ["-x86_64", venvPy64, "-c", "import sys; sys.exit(0 if sys.version_info < (3, 13) else 1)"], {
      encoding: "utf8",
      timeout: 3000,
    });
    if (versionCheck.status !== 0) {
      console.warn("\nRemoving .venv_x64 (Python 3.13 unsupported for pandas_ta on x86_64)...");
      run(`rm -rf "${venvX64}"`);
    }
  }
  if (!existsSync(venvPy64)) {
    console.log("\n==> Creating x86_64 venv (one-time)...");
    mkdirSync(join(root, "trading-engine"), { recursive: true });
    // Use --system-site-packages for python.org 3.12 (inherits x86_64 packages from global install)
    const useSysPkgs = x64Py.includes("Library/Frameworks");
    run(`${x64Arch}"${x64Py}" -m venv ${useSysPkgs ? "--system-site-packages" : ""} "${venvX64}"`);
    if (useSysPkgs) {
      // Install deps into base Python for x86_64 (venv will inherit via system-site-packages)
      try {
        run(`${x64Arch}"${x64Py}" -m pip install -q -r "${reqFile}"`);
      } catch (e) {
        console.warn("pip install failed. Run: arch -x86_64 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pip install -r trading-engine/requirements.txt");
        throw e;
      }
    } else {
      try {
        run(`${x64Arch}"${venvPy64}" -m pip install -q -r "${reqFile}"`);
      } catch (e) {
        console.warn("pip install failed. Run: arch -x86_64 /Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m pip install -r trading-engine/requirements.txt");
        throw e;
      }
    }
  }
  console.log("\n==> Building trading-engine for x86_64 (Intel Mac)");
  try {
    run(`${x64Arch}"${venvPy64}" "${buildPy}"`, {
      env: { ...process.env, TARGET_TRIPLE: "x86_64-apple-darwin" },
    });
    hasX64 = existsSync(x64Bin);
  } catch (e) {
    console.warn("x86_64 build failed:", e.message);
  }
}

// 3. Merge with lipo (Tauri expects trading-engine-universal-apple-darwin)
if (hasX64) {
  console.log("\n==> Merging into universal binary (lipo)");
  run(`lipo -create "${aarch64Bin}" "${x64Bin}" -output "${universalBin}"`);
  console.log(`   Created: trading-engine-universal-apple-darwin`);
} else {
  console.warn("\nWARNING: No x86_64 binary. Tauri universal build will fail.");
  console.warn("  Install x86_64 Python 3.12 with: arch -x86_64 brew install python@3.12");
  console.warn("  Or use build-mac.sh for aarch64-only.");
  process.exit(1);
}

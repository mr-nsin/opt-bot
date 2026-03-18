# QuantDrift - Build Instructions

This document describes how to build a **standalone executable** with all dependencies embedded.

## Architecture

- **Tauri app**: Rust + React frontend → produces `QuantDrift.exe` (Windows) or `QuantDrift.app` (macOS)
- **Trading engine sidecar**: Python (PyInstaller) → produces `trading-engine-{target}.exe` (Windows) or `trading-engine-{target}` (macOS)
- Both are bundled together; the Tauri app spawns the Python engine as a subprocess.

## Prerequisites

### 1. Node.js (v18+)
- Install from https://nodejs.org
- Verify: `node -v` and `npm -v`

### 2. Rust
- Install from https://rustup.rs
- Verify: `rustc -v`

### 3. Python 3.11 or 3.12
- Install from https://python.org (add to PATH)
- Verify: `python -v` or `py -3.11 -V`

### 4. Python Dependencies (for trading-engine)

```powershell
cd c:\Temp\opt\opt-bot
pip install -r requirements.txt
```

Or with a specific Python:
```powershell
py -3.11 -m pip install -r requirements.txt
```

**Required packages** (from `requirements.txt`):
- `ibapi` (Interactive Brokers API)
- `pandas`, `numpy`, `yfinance`, `pandas_ta`, `pytz`
- `pyinstaller` (for building the sidecar exe)

## Build Steps

### Option A: One-command build (recommended)

```powershell
cd c:\Temp\opt\opt-bot
npm install
npm run tauri:build
```

This will:
1. Run `prebuild` → build trading-engine sidecar with PyInstaller
2. Run `build` → compile frontend (TypeScript + Vite)
3. Run Tauri build → produce final exe + installer

### Option B: Step-by-step

```powershell
cd c:\Temp\opt\opt-bot

# 1. Install Node dependencies
npm install

# 2. Build Python trading-engine sidecar (embeds all Python deps into exe)
python trading-engine\build.py

# 3. Build Tauri app (includes frontend + sidecar)
npm run tauri:build
```

### Option C: Using build-windows.bat

```powershell
cd c:\Temp\opt\opt-bot
.\build-windows.bat
```

## Output Location

After a successful build:

```
opt-bot\src-tauri\target\release\bundle\
├── nsis\QuantDrift_1.0.0_x64-setup.exe   # NSIS installer
├── msi\QuantDrift_1.0.0_x64_en-US.msi    # MSI installer
└── QuantDrift.exe                         # Standalone exe (in release folder)
```

The trading-engine binary is embedded in the bundle:
- `src-tauri\binaries\trading-engine-x86_64-pc-windows-msvc.exe`

## Embedded Dependencies (Trading Engine)

The PyInstaller build embeds these into the trading-engine exe:

| Category | Packages |
|----------|----------|
| **IB API** | ibapi (client, wrapper, contract, order, execution, ticktype, utils) |
| **Data** | pandas, numpy, yfinance, pandas_ta, pytz |
| **Stdlib** | logging, sqlite3, multiprocessing, queue, threading, json, shutil, etc. |
| **Project** | BOT.py, common.py, tws_api_client.py, order_manager.py, data_access.py, Indicators.py, logger.py |

## Build Script Notes

- **Frontend build**: Uses `vite build` (TypeScript check `tsc` is skipped due to existing type errors in the codebase; fix those and add `tsc &&` before `vite build` for strict builds)
- **prebuild**: Automatically runs `python trading-engine/build.py` before each `npm run build`, so the trading-engine sidecar is always rebuilt when you run `npm run tauri:build`

## Log File Location

When running the **packaged exe**, trading engine logs are written to:

| Platform | Path |
|----------|------|
| **Windows** | `%APPDATA%\QuantDrift\logs\bot_YYYY-MM-DD.log` |
| **Dev (not frozen)** | `./logs/bot_YYYY-MM-DD.log` (relative to working directory) |

Example: `C:\Users\<you>\AppData\Roaming\QuantDrift\logs\bot_2026-03-03.log`

Logs rotate at 50 MB and retain 2 files. The in-app Logs tab shows the same content in real time via the sidecar protocol.

## Troubleshooting

### "trading-engine not found"
- Ensure `python trading-engine\build.py` completed successfully
- Check that `src-tauri\binaries\trading-engine-x86_64-pc-windows-msvc.exe` exists

### "No module named 'ibapi'"
- Run `pip install -r requirements.txt` (or `py -3.11 -m pip install -r requirements.txt`)
- Use the same Python for both `pip install` and `python trading-engine\build.py`

### PyInstaller build fails
- Add any missing modules to `trading-engine/build.py` → `hidden_imports`
- Add any missing data files to `data_additions`

### Tauri build fails
- Ensure WebView2 is installed (Windows 10/11 usually has it)
- Run `rustup update` if Rust errors occur

---

## macOS Build (Runnable .app — equivalent to exe on Windows)

### Prerequisites
- Xcode Command Line Tools: `xcode-select --install`
- Node.js (v18+), Rust (`rustup.rs`), Python 3.12
- Create venv: `cd trading-engine && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt`

### One-command build
```bash
cd /path/to/OPT_BOT
npm install
npm run build:mac
```

### Output
```
src-tauri/target/release/bundle/macos/
└── QuantDrift.app        # Double-click to run, or: open QuantDrift.app
```

### Run with license registry env vars
```bash
./run-built-mac.sh         # Uses built .app with REGISTRY_URL and REGISTRY_LICENSE_PUBLIC_KEY_HEX
```

### Dev mode (with registry)
```bash
./run-with-registry.sh    # npm run tauri:dev with env vars set
```

### Notes
- Prebuild uses `trading-engine/.venv` Python when available (pandas_ta needs 3.12)
- Trading-engine binary: `src-tauri/binaries/trading-engine-aarch64-apple-darwin` (Apple Silicon) or `trading-engine-x86_64-apple-darwin` (Intel)

### Universal build (Intel + Apple Silicon)
```bash
npm run build:mac:universal
```
- Produces one app that runs on both Intel and Apple Silicon
- Requires x86_64 Python (python.org universal or Intel Homebrew). Creates `trading-engine/.venv_x64` with x86_64 packages on first run.
- Output: `src-tauri/target/universal-apple-darwin/release/bundle/macos/QuantDrift.app`

# Technical Context: QuantDrift Options Trading Bot

## Tech Stack Overview
QuantDrift leverages a multi-language architecture to blend a high-performance native desktop shell with an established Python trading ecosystem:
* **Frontend UI:** TypeScript, React 19, Zustand 5, Tailwind CSS 3, Recharts, React Router 7.
* **App Shell & IPC:** Rust, Tauri 2.0 (JSON-RPC over stdio for Python interop).
* **Licensing Module:** Compiled Rust using AES-256-GCM + HMAC-SHA256 hardware fingerprinting.
* **Trading Engine Sidecar:** Python 3.12+, `ibapi` (Interactive Brokers), `pandas`, `numpy`, `yfinance`, PyInstaller.
* **Database:** SQLite (managed via Python `data_access.py`).

## Development Setup & Prerequisites
1. **Node.js:** v18+ with `npm` v9+
2. **Rust & Cargo:** v1.70+ installed via `rustup.rs`
3. **Python:** v3.10+ (recommend 3.11/3.12) with a local `.venv` inside the project root containing the installed `requirements.txt`.
4. **Interactive Brokers:** TWS or IB Gateway must be running locally with ActiveX/Socket Clients enabled (Ports 7497/7496 for TWS, 4002/4001 for Gateway).

## Run Commands (Execution Paths)

### 1. Full Desktop Application (Development Mode)
Recommended for local UI and Rust development. It spawns the Vite dev server with hot-reload, builds the Rust Tauri shell, and runs the Python engine.
```bash
npm install
npm run tauri:dev
```
*(Note: A placeholder binary for the sidecar must exist in `src-tauri/binaries/` named for your target platform, e.g., `trading-engine-x86_64-pc-windows-msvc.exe` for Windows).*

### 2. Frontend Only (Browser Mode)
Useful for rapid UI prototyping without the Tauri shell or Rust compilation.
```bash
npm run dev
```
*(Access at `http://localhost:1420`. IPC `invoke()` calls to Rust/Python will fail).*

### 3. Python Sidecar Standalone (Testing)
Run the trading engine without the UI to test JSON-RPC pipes or IB API connections directly.
```bash
cd trading-engine
python main.py
```
*(Accepts standard JSON-RPC payloads via stdin, e.g., `{"id": "test", "method": "ping", "params": {}}`).*

### 4. Legacy PyQt5 App
The original application is preserved for backward compatibility.
```bash
# macOS/Linux
python GUI.py

# Windows
.\RUN_GUI.bat
```

## Build Commands (Production)

### Windows (Standalone .exe + MSI/NSIS)
A build script is provided to automate bundling the Python engine via PyInstaller and packaging the Tauri app.
```cmd
# 1. Automatic one-click build
.\build-windows.bat

# OR Step-by-Step
npm install
cd trading-engine
python build.py      # Outputs sidecar to src-tauri/binaries/trading-engine-x86_64-pc-windows-msvc.exe
cd ..
npm run tauri:build  # Outputs final exe to src-tauri/target/release/bundle/
```
*Outputs: `nsis/QuantDrift_1.0.0_x64-setup.exe` and `QuantDrift.exe`.*

### macOS / Linux
```bash
npm install
cd trading-engine && python3 build.py && cd ..
npm run tauri:build
```
*Outputs: macOS `.dmg` and Linux `.deb` / `.AppImage` in `src-tauri/target/release/bundle/`.*

## Configuration & Logs
* **`config.json`:** The central trading configuration file residing at the project root. When built for production, Tauri reads and persists updates to the user's AppData directory (Windows: `%APPDATA%\quantdrift\optbot\config.json`, macOS: `~/Library/Application Support/com.quantdrift.optbot/config.json`).
* **Log Files:** 
  * In Dev: Written to `./logs/bot_YYYY-MM-DD.log`.
  * In Production (Windows): Written to `%APPDATA%\QuantDrift\logs\bot_YYYY-MM-DD.log`. Logs rotate automatically at 50 MB.

## Troubleshooting
* **"trading-engine not found" during Tauri build:** Ensure the PyInstaller step (`python trading-engine/build.py`) ran successfully and generated the correct target triple name in `src-tauri/binaries/`.
* **"TWS not connected":** Check if TWS/Gateway is running, API is enabled, the port matches `config.json` (7497 for paper), and `127.0.0.1` is added to Trusted IPs in IB API Settings.
* **Rust/Link Errors on Windows:** Ensure Visual Studio Build Tools ("Desktop development with C++") is installed.

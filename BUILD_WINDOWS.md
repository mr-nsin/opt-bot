# Building QuantDrift for Windows (installable .exe)

This guide explains how to build an installable Windows executable (.exe and optional setup installer) on a **Windows** machine.

## Prerequisites (Windows)

1. **Node.js** (LTS) – [nodejs.org](https://nodejs.org)
2. **Rust** – [rustup.rs](https://rustup.rs) (use default `x86_64-pc-windows-msvc`)
3. **Python 3.9–3.11** – [python.org](https://www.python.org/downloads/) (add to PATH)
4. **Visual Studio Build Tools** (for Rust) – Install “Desktop development with C++” when prompted by Rust
5. **WebView2** – Usually already present on Windows 10/11; installer can download it if missing

### Python dependencies for the trading-engine sidecar

```cmd
cd trading-engine
python -m venv .venv
.venv\Scripts\activate
pip install pyinstaller ibapi pandas numpy
```

(Install any other packages your `trading-engine` code uses, e.g. from a `requirements.txt` if present.)

## Build steps (on Windows)

### 1. Build the trading-engine sidecar (.exe)

The Tauri app runs the trading engine as a sidecar. It must be built first and placed in `src-tauri/binaries/` with the name Tauri expects.

```cmd
cd trading-engine
python build.py
```

This produces:

- `src-tauri\binaries\trading-engine-x86_64-pc-windows-msvc.exe`

If the script fails, ensure all project root files used by the engine exist (`BOT.py`, `common.py`, `tws_api_client.py`, `order_manager.py`, `data_access.py`, `Indicators.py`, `logger.py`) and that you ran the Python commands from the repo root or `trading-engine` as above.

### 2. Install frontend dependencies

From the **project root**:

```cmd
npm install
```

### 3. Build the Tauri app (exe + installer)

From the **project root**:

```cmd
npm run tauri build
```

Outputs (in `src-tauri/target/release/bundle/`):

- **NSIS installer**: `nsis/QuantDrift_1.0.0_x64-setup.exe` – run this to install on Windows
- **Standalone .exe**: `msi/` or same folder – `QuantDrift.exe` (or similar) for a portable run

Installer behavior (configurable in `src-tauri/tauri.conf.json`):

- **NSIS**: `QuantDrift_1.0.0_x64-setup.exe` – installs for current user, allows elevation if needed
- **WebView2**: Installer will download/install WebView2 if the machine doesn’t have it (requires internet on first run)

## Quick script (Windows)

From the project root you can run:

```cmd
build-windows.bat
```

This will:

1. Build the trading-engine sidecar with Python/PyInstaller
2. Run `npm run tauri build`

Ensure Node, Rust, Python, and the trading-engine venv (and deps) are installed and on PATH before running.

## Troubleshooting

- **“trading-engine not found”**  
  Make sure `src-tauri/binaries/trading-engine-x86_64-pc-windows-msvc.exe` exists. Run `trading-engine/build.py` on Windows to generate it.

- **PyInstaller / import errors**  
  Install all packages the trading engine and BOT use (`ibapi`, `pandas`, etc.) in the same venv you use to run `build.py`. Add any missing modules to `trading-engine/build.py`’s `hidden_imports` or data files.

- **Rust / link errors**  
  Install Visual Studio Build Tools with the “Desktop development with C++” workload and retry `npm run tauri build`.

- **WebView2**  
  If the app fails to start on a clean Windows install, run the NSIS setup again (it will try to install WebView2) or install [WebView2](https://developer.microsoft.com/en-us/microsoft-edge/webview2/) manually.

## Building on macOS/Linux for Windows (cross-compile)

Cross-compiling the Tauri app for Windows from macOS or Linux is possible using NSIS and a Windows Rust target (e.g. `x86_64-pc-windows-msvc`) with tools like `cargo-xwin`. The **trading-engine sidecar** must still be built on Windows (PyInstaller produces a Windows .exe only on Windows). So for a full Windows build you need either:

- A Windows machine or VM, or  
- A Windows build agent (e.g. GitHub Actions) that runs the steps above.

See [Tauri docs – Build Windows apps on Linux and macOS](https://v2.tauri.app/distribute/windows-installer/#build-windows-apps-on-linux-and-macos) for the Rust/Tauri side.

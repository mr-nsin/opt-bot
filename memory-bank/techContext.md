# Technical Context: QuantDrift Options Trading Bot

## Tech Stack Overview
QuantDrift is built on a multi-language framework optimized for safety, performance, and cross-platform desktop integration:

| Layer | Language / Tech | Description |
|---|---|---|
| **Frontend UI** | TypeScript, React 19, Zustand 5, Tailwind CSS 3, Recharts | Interactive charts, configuration panels, real-time data binding. |
| **App Shell** | Rust, Tauri 2.0 | Desktop window manager, file system API, config persistence, event emitter. |
| **Licensing** | Rust | AES-256-GCM + HMAC-SHA256 validation of hardware-fingerprinted keys. |
| **Trading Engine** | Python 3.12+, `ibapi`, `pandas`, `numpy` | Execution logic, broker client, SQLite database access. |
| **Broker API** | Interactive Brokers API | Connection via local TWS (port 7496/7497) or Gateway (port 4001/4002). |

## Development Setup
### 1. Host Dependencies
* **Rust & Cargo:** (1.70+) Installed via `rustup.rs`.
* **NodeJS:** (18+) and `npm` (9+).
* **Python:** (3.10+) with active virtual environment `.venv` at project root.

### 2. Configuration (`config.json`)
The application relies on `config.json` situated in the project root for local run settings. In production, this config is parsed/saved in the system's App Data directory:
* macOS: `~/Library/Application Support/com.quantdrift.optbot/`
* Windows: `%APPDATA%\quantdrift\optbot\`

### 3. Tauri Sidecar Executable
Tauri relies on a sidecar binary for packaging. For local development:
* A script wrapper or dummy binary pointing to `trading-engine/main.py` is copied inside `src-tauri/binaries/` with the host's target triple suffix.

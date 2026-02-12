# QuantDrift - Options Trading Bot

A professional automated options trading bot built with **Tauri 2.0 + React + TypeScript** (frontend), **Rust** (backend/licensing), and a **Python sidecar** (trading engine). Connects to Interactive Brokers TWS/Gateway for real-time market data and order execution.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Building for Production](#building-for-production)
- [Features](#features)
- [Licensing System](#licensing-system)
- [Troubleshooting](#troubleshooting)

---

## Overview

QuantDrift is a desktop application that automates options trading on US equity markets via Interactive Brokers. It detects trading signals using technical indicators (SuperTrend, engulfing patterns, ATR), places options orders, and manages positions with configurable take-profit, stop-loss, and trailing profit logic.

**Key capabilities:**
- Real-time connection to IB TWS/Gateway
- Automated signal detection (SuperTrend, engulfing + ATR)
- Options order placement with delta-based strike selection
- Position management with trailing profit and stop-loss
- Daily P&L limits and trade caps
- Multi-symbol watchlist (SPY, QQQ, TSLA, AAPL, etc.)
- Demo and Live trading modes
- Dark/Light theme support
- Tamper-proof licensing system (Rust-compiled)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Tauri 2.0 Desktop Shell                    │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │          React + TypeScript Frontend                   │ │
│  │  Dashboard | Analytics | Positions | Logs | Settings   │ │
│  │  ┌──────────────────────────────────────────────────┐  │ │
│  │  │          Zustand State Management                │  │ │
│  │  └──────────────────────┬───────────────────────────┘  │ │
│  └─────────────────────────┼──────────────────────────────┘ │
│                            │ Tauri invoke() / listen()       │
│  ┌─────────────────────────┴──────────────────────────────┐ │
│  │              Rust Backend (src-tauri/)                  │ │
│  │  License Manager | Config | IPC Bridge | Event Router  │ │
│  └─────────────────────────┬──────────────────────────────┘ │
│                            │ JSON-RPC over stdio             │
│  ┌─────────────────────────┴──────────────────────────────┐ │
│  │          Python Sidecar (trading-engine/)               │ │
│  │  Trading Engine | TWS Client | Order Manager | Signals │ │
│  └─────────────────────────┬──────────────────────────────┘ │
└─────────────────────────────┼───────────────────────────────┘
                              │ TCP Socket
                    ┌─────────┴─────────┐
                    │  IB TWS / Gateway  │
                    └───────────────────┘
```

**Data flow:** IB TWS → Python sidecar (ibapi) → JSON events over stdout → Rust IPC bridge → Tauri events → React stores → UI components

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Desktop shell** | Tauri 2.0 | Cross-platform native wrapper, ~2MB overhead |
| **Frontend** | React 19 + TypeScript | Modern reactive UI |
| **Styling** | Tailwind CSS 3 + shadcn/ui patterns | Themeable component system |
| **Charts** | Recharts | Win/loss donut, P&L bar chart, equity curve |
| **State** | Zustand 5 | Lightweight TypeScript-first state management |
| **Routing** | React Router 7 | Client-side page navigation |
| **Backend** | Rust | Licensing, encryption, IPC bridge, config |
| **Trading engine** | Python 3.12+ | Proven ibapi/pandas/numpy trading logic |
| **IPC** | JSON-RPC over stdio | Language-agnostic, debuggable |
| **Broker API** | ibapi (Python) | Interactive Brokers TWS API |
| **Licensing** | AES-256-GCM + HMAC-SHA256 | Hardware-bound, tamper-proof |

---

## Prerequisites

Before running the project locally, ensure you have the following installed:

### Required

| Tool | Minimum Version | Install |
|------|----------------|---------|
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **npm** | 9+ | Comes with Node.js |
| **Rust** | 1.70+ | [rustup.rs](https://rustup.rs/) |
| **Python** | 3.10+ | [python.org](https://python.org/) |
| **IB TWS or Gateway** | Latest | [interactivebrokers.com](https://www.interactivebrokers.com/en/trading/tws.php) |

### Platform-specific

**macOS:**
```bash
xcode-select --install
```

**Windows:**
- Microsoft Visual Studio C++ Build Tools
- WebView2 (usually pre-installed on Windows 10/11)

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file \
  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

### Verify installations

```bash
node --version       # v18+ required
npm --version        # 9+ required
rustc --version      # 1.70+ required
cargo --version      # comes with Rust
python3 --version    # 3.10+ required
```

---

## Local Development Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd OPT_BOT
```

### 2. Install Node.js dependencies

```bash
npm install
```

### 3. Install Python dependencies (for the trading engine sidecar)

```bash
cd trading-engine
pip install -r requirements.txt
cd ..
```

### 4. Create placeholder sidecar binary (required for dev mode)

The Tauri build system expects a sidecar binary. For development, create a placeholder:

**macOS / Linux:**
```bash
mkdir -p src-tauri/binaries

# Detect your platform triple
TARGET=$(rustc -vV | grep host | awk '{print $2}')

# Create placeholder
cp trading-engine/main.py src-tauri/binaries/trading-engine-${TARGET}
chmod +x src-tauri/binaries/trading-engine-${TARGET}
```

**Windows (PowerShell):**
```powershell
mkdir -Force src-tauri\binaries
$target = (rustc -vV | Select-String "host:" | ForEach-Object { $_.Line.Split(": ")[1].Trim() })
Copy-Item trading-engine\main.py "src-tauri\binaries\trading-engine-$target.exe"
```

### 5. Configure IB TWS / Gateway

1. Open IB TWS or IB Gateway
2. Go to **Edit > Global Configuration > API > Settings**
3. Enable **"Enable ActiveX and Socket Clients"**
4. Set the Socket port (default: `7497` for TWS paper, `4002` for Gateway paper)
5. Add `127.0.0.1` to Trusted IPs
6. Disable **"Read-Only API"** if you want to place real orders

### 6. Edit trading configuration

The trading config is in `config.json` at the project root:

```json
{
  "IP": "127.0.0.1",
  "PORT": 7497,
  "CLIENTID": 0,
  "ACCOUNT_ID": "YOUR_ACCOUNT_ID",
  "QUANTITY": 2,
  "candleTime": "5 mins",
  "CALL_DELTA_CHECK": 0.35,
  "PUT_DELTA_CHECK": -0.35,
  "profit_amount_day": 200,
  "loss_amount_day": 200,
  "perDayTrades": 3
}
```

Key settings:
| Setting | Description | Default |
|---------|-------------|---------|
| `IP` | TWS/Gateway IP address | `127.0.0.1` |
| `PORT` | TWS socket port (7497=TWS paper, 7496=TWS live, 4002=GW paper, 4001=GW live) | `7497` |
| `CLIENTID` | Unique client ID for this connection | `0` |
| `ACCOUNT_ID` | Your IB account ID | - |
| `QUANTITY` | Number of contracts per trade | `2` |
| `candleTime` | Candle timeframe for signal detection | `5 mins` |
| `CALL_DELTA_CHECK` | Delta threshold for call options | `0.35` |
| `PUT_DELTA_CHECK` | Delta threshold for put options | `-0.35` |
| `profit_amount_day` | Daily profit target ($) - stops trading when hit | `200` |
| `loss_amount_day` | Daily loss limit ($) - stops trading when hit | `200` |
| `perDayTrades` | Maximum trades per day | `3` |
| `distance_between_trade` | Cooldown between trades (seconds) | `610` |
| `ORDER_TRANSMIT` | `true` = orders go to market, `false` = preview only | `true` |

---

## Running the Application

### Development mode (recommended for local work)

This starts both the Vite dev server (hot-reload) and the Tauri native window:

```bash
npm run tauri:dev
```

This will:
1. Start Vite dev server on `http://localhost:1420`
2. Compile the Rust backend
3. Launch the Tauri desktop window
4. Enable hot module replacement (HMR) for instant UI updates

### Frontend only (no native window)

If you only want to work on the React UI without the Tauri shell:

```bash
npm run dev
```

Then open `http://localhost:1420` in your browser. Note: Tauri commands (`invoke()`) will fail in browser mode, but the UI layout is fully visible.

### Run the Python trading engine standalone (for testing)

```bash
cd trading-engine
python3 main.py
```

The engine reads JSON commands from stdin and writes events to stdout. You can test it by typing JSON:

```json
{"id": "test-1", "method": "ping", "params": {}}
```

### Run the legacy PyQt5 GUI (original app)

The original PyQt5 GUI is still available:

```bash
python3 GUI.py
```

Or on Windows:
```
RUN_GUI.bat
```

---

## Building for Production

### 1. Build the Python sidecar

First, package the Python trading engine as a standalone executable:

```bash
cd trading-engine
python3 build.py
cd ..
```

This uses PyInstaller to create a binary at `src-tauri/binaries/trading-engine-{target-triple}`.

### 2. Build the full application

```bash
npm run tauri:build
```

This produces platform-specific installers:
- **macOS:** `.dmg` in `src-tauri/target/release/bundle/dmg/`
- **Windows:** `.msi` and `.exe` in `src-tauri/target/release/bundle/msi/` and `nsis/`
- **Linux:** `.deb` and `.AppImage` in `src-tauri/target/release/bundle/deb/` and `appimage/`

### Build frontend only

```bash
npm run build
```

Output goes to `dist/`.

### Check individual builds

```bash
# TypeScript type checking (no output = no errors)
npx tsc --noEmit

# Vite production build
npx vite build

# Rust compilation check
cd src-tauri && cargo check
```

---

## Project Structure

```
OPT_BOT/
│
├── src/                          # React + TypeScript frontend
│   ├── main.tsx                  # App entry point
│   ├── App.tsx                   # Root component with routing
│   ├── index.css                 # Global styles + Tailwind + theme vars
│   ├── components/
│   │   ├── layout/               # AppShell, Header, Sidebar
│   │   ├── dashboard/            # Main trading dashboard (8 components)
│   │   ├── analytics/            # Charts and performance metrics (5 components)
│   │   ├── positions/            # Active/closed positions table (3 components)
│   │   ├── logs/                 # System log viewer with filters (2 components)
│   │   ├── settings/             # App settings page
│   │   ├── license/              # License gate, input, status (3 components)
│   │   ├── common/               # StatCard, StatusBadge, ThemeToggle, etc.
│   │   └── ui/                   # Base UI components (Button, Card, Input, etc.)
│   ├── hooks/                    # Custom React hooks (6 hooks)
│   ├── stores/                   # Zustand state stores (4 stores)
│   └── lib/                      # Types, constants, utils, Tauri command wrappers
│
├── src-tauri/                    # Rust backend (Tauri)
│   ├── Cargo.toml                # Rust dependencies
│   ├── tauri.conf.json           # Tauri app configuration
│   ├── capabilities/             # Permission declarations
│   ├── icons/                    # App icons (32x32, 128x128, 256x256)
│   ├── binaries/                 # Python sidecar binary (PyInstaller output)
│   └── src/
│       ├── main.rs               # Rust entry point
│       ├── lib.rs                # Module exports + Tauri builder
│       ├── commands/             # Tauri invoke handlers (trading, config, license, etc.)
│       ├── license/              # AES-256 encryption, HMAC validation, HW fingerprint
│       ├── sidecar/              # Python process manager, JSON-RPC protocol, health
│       ├── state/                # App state, trading state, config state
│       ├── events/               # Event emitter (Rust → React)
│       └── utils/                # Crypto helpers, path utilities
│
├── trading-engine/               # Python sidecar (trading logic)
│   ├── main.py                   # Entry point (JSON-RPC over stdio)
│   ├── build.py                  # PyInstaller build script
│   ├── requirements.txt          # Python dependencies
│   ├── engine/
│   │   ├── trading_engine.py     # TradingEngine class (wraps BOT.py logic)
│   │   └── models.py             # JSON-serializable data models
│   ├── protocol/
│   │   ├── handler.py            # stdin message handler
│   │   ├── emitter.py            # stdout event emitter
│   │   └── messages.py           # Message type constants
│   └── strategies/
│       └── base.py               # Abstract strategy interface
│
├── *.py                          # Legacy Python modules (preserved)
│   ├── BOT.py                    # Original trading engine (~2400 lines)
│   ├── GUI.py                    # Original PyQt5 GUI (~2000 lines)
│   ├── common.py                 # Shared data models (OptionOrder, Tick, etc.)
│   ├── tws_api_client.py         # IB TWS API wrapper
│   ├── order_manager.py          # Order lifecycle management
│   ├── data_access.py            # SQLite database layer
│   ├── Indicators.py             # Technical indicators (SuperTrend, RSI, etc.)
│   └── logger.py                 # Rotating file logger
│
├── config.json                   # Trading configuration
├── expiryStrike.json             # Pre-fetched strike prices
├── package.json                  # Node.js / React dependencies
├── tsconfig.json                 # TypeScript configuration
├── vite.config.ts                # Vite build configuration
├── tailwind.config.js            # Tailwind CSS configuration
├── postcss.config.js             # PostCSS configuration
└── index.html                    # HTML entry point
```

---

## Configuration

### Trading Configuration (`config.json`)

The main trading parameters. Editable via the dashboard UI or directly in the file.

| Category | Parameters |
|----------|-----------|
| **Connection** | IP, PORT, CLIENTID, ACCOUNT_ID |
| **Signal detection** | candleTime, CALL_DELTA_CHECK, PUT_DELTA_CHECK, ATR_VALUE, BODY, VWAP_ON_OFF |
| **Risk management** | profit_amount_day, loss_amount_day, perDayTrades, MAX_CONTRACT_AMOUNT |
| **Order settings** | QUANTITY, ORDER_TRANSMIT, ORDER_EXPIRY_TIMER, profit_increment |
| **Timing** | scriptStartTime, scriptEndTime, distance_between_trade |
| **Watchlist** | stockListToTrade, stockData (per-symbol max amounts) |

### Expiry Options

| Value | Meaning |
|-------|---------|
| `0DTE` | Same-day expiry (day trading) |
| `1DTE` | Next trading day expiry |
| `current` | Current week Friday expiry |
| `next` | Next week Friday expiry |

---

## Features

### Dashboard
- **Live stats:** Daily P&L, realized/unrealized, trade count, win rate
- **Trading controls:** Start/Stop/Emergency stop with confirmation dialogs
- **Trade parameters:** Expiry, candle timeframe, delta thresholds, quantity
- **Risk management:** Profit target, loss limit, max trades, trailing profit
- **Connection config:** TWS IP/Port/ClientID with live connection status
- **Stock watchlist:** Add/remove symbols with per-symbol amount caps
- **Activity log:** Real-time scrolling log of trading events

### Analytics
- **Performance metrics:** Total trades, win rate, avg win/loss, profit factor
- **Win/Loss distribution:** Interactive donut chart
- **P&L distribution:** Per-trade bar chart (green=profit, red=loss)
- **Equity curve:** Cumulative P&L area chart

### Positions
- **Active positions:** Live table with symbol, type, strike, qty, P&L, close button
- **Position history:** Closed trades with entry/exit prices and realized P&L
- **Bulk actions:** Close all positions with confirmation

### Logs
- **Full log viewer:** Scrollable, monospaced log output
- **Filters:** By level (INFO, WARN, ERROR, DEBUG) and category (trading, system, orders, signals)
- **Auto-scroll:** Toggle auto-scroll to latest entries

### Settings
- **Appearance:** Dark/Light theme toggle with smooth transitions
- **Trading mode:** Demo/Live switch with visual indicator
- **Notifications:** Enable/disable trade alerts
- **License management:** View status, activate/deactivate keys

---

## Licensing System

The licensing system is implemented entirely in Rust for tamper resistance.

### How it works

1. **Hardware fingerprinting:** Generates a SHA-256 hash of CPU, hostname, memory, and OS info
2. **License activation:** User enters `XXXX-XXXX-XXXX-XXXX` key + email
3. **Signature creation:** HMAC-SHA256 signs all license fields
4. **Encrypted storage:** AES-256-GCM encrypts the license, keyed to the hardware fingerprint
5. **Validation:** On startup, decrypts and validates signature + expiry + hardware match
6. **License gate:** If invalid/expired, the app shows a license input screen instead of the main UI

### License tiers

| Tier | Features |
|------|----------|
| **Basic** | Demo trading only, 5 symbols, 10 trades/day |
| **Pro** | Live trading, 20 symbols, 50 trades/day, all strategies |
| **Enterprise** | Everything + multi-account support |

### Security properties

- **Hardware-bound:** License file cannot be copied to another machine
- **Encrypted on disk:** AES-256-GCM with hardware-derived key
- **Tamper-proof:** HMAC-SHA256 signature detects any modification
- **Compiled binary:** License logic is in compiled Rust (not reversible like Python)

---

## Troubleshooting

### Common issues

**"TWS not connected"**
- Ensure IB TWS or Gateway is running
- Verify the port matches your config (`7497` for TWS paper trading)
- Check that "Enable ActiveX and Socket Clients" is enabled in TWS API settings
- Add `127.0.0.1` to the trusted IP list

**"License file not found"**
- The license is stored in the system application data directory
- macOS: `~/Library/Application Support/com.quantdrift.optbot/`
- Windows: `%APPDATA%\quantdrift\optbot\`
- Linux: `~/.local/share/quantdrift/optbot/`

**Sidecar binary not found during `cargo check`**
- Run the placeholder creation step from [Local Development Setup](#4-create-placeholder-sidecar-binary-required-for-dev-mode)
- The binary name must match your platform's target triple (e.g., `trading-engine-aarch64-apple-darwin`)

**`npm run tauri:dev` fails on first run**
- Rust compilation can take 2-5 minutes on first build (downloading + compiling ~500 crates)
- Subsequent builds are incremental and much faster (~5 seconds)

**Python trading engine errors**
- Ensure `ibapi` is installed: `pip install ibapi`
- Check Python version: `python3 --version` (3.10+ required)
- Verify all dependencies: `cd trading-engine && pip install -r requirements.txt`

**Large bundle size warning during Vite build**
- This is expected due to Recharts. The warning can be safely ignored
- For optimization, code splitting can be added later via `React.lazy()` and dynamic imports

### Useful commands

```bash
# Check all builds at once
npx tsc --noEmit && npx vite build && cd src-tauri && cargo check

# Watch mode for frontend changes
npm run dev

# Run Rust tests
cd src-tauri && cargo test

# Check Rust for warnings
cd src-tauri && cargo clippy

# Find your platform's target triple
rustc -vV | grep host
```

---

## Legacy Application

The original PyQt5 application is preserved alongside the new Tauri app. To run the legacy version:

```bash
# Start the original PyQt5 GUI
python3 GUI.py

# Or on Windows
RUN_GUI.bat
```

The legacy files (`BOT.py`, `GUI.py`, `common.py`, `tws_api_client.py`, `order_manager.py`, `data_access.py`, `Indicators.py`) remain in the project root and are also imported by the new Python sidecar to preserve proven trading logic.

---

## License

Proprietary software. All rights reserved.
Contact: support@quantdrift.com

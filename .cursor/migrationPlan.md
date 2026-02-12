# Migration Plan: Tauri + React + TypeScript

## Executive Summary

Migrate OPT_BOT from PyQt5 to **Tauri 2.0 + React + TypeScript** with a **hybrid backend** — Rust for the application shell, licensing, state management, and IPC; Python sidecar (via PyInstaller) for the trading engine (ibapi, indicators, order management). This gives the best balance of modern UI, secure licensing, and minimal risk to proven trading logic.

---

## Backend Analysis: Python vs Rust

### Option A: Pure Rust Backend

| Factor | Assessment |
|---|---|
| **IB API** | `ibapi` Rust crate exists (v2.5.0, Jan 2026, MIT, 254 GitHub stars, async+sync). Covers market data, orders, positions, account info. |
| **Indicators** | No pandas/numpy equivalent. Would need to rewrite SuperTrend, ATR, EMA, engulfing detection in Rust from scratch. |
| **Performance** | Excellent — native speed, zero GC pauses, sub-microsecond latency. |
| **Licensing** | Excellent — compiled binary is very hard to reverse-engineer. |
| **Risk** | HIGH — Rust ibapi crate is newer, may have edge cases. Complete rewrite of ~3000 lines of trading logic. |
| **Timeline** | 4-6 months minimum |
| **Bundle size** | ~2-5 MB total |

### Option B: Python Sidecar Only

| Factor | Assessment |
|---|---|
| **IB API** | Keep existing `ibapi` Python — zero risk, proven. |
| **Indicators** | Keep existing pandas/numpy/yfinance code — zero changes. |
| **Performance** | Adequate — same as current PyQt5 app. IPC overhead for UI updates (~1-5ms). |
| **Licensing** | WEAK — PyInstaller binaries can be decompiled. Python source recoverable. |
| **Risk** | LOW — only GUI changes, trading logic untouched. |
| **Timeline** | 2-3 months |
| **Bundle size** | ~80-150 MB (PyInstaller + Python + libraries) |

### Option C: Hybrid — Rust Core + Python Sidecar (RECOMMENDED)

| Factor | Assessment |
|---|---|
| **IB API** | Python sidecar runs existing ibapi code. |
| **Indicators** | Python sidecar runs existing indicator code. |
| **Performance** | Rust handles UI state, event routing, licensing. Python handles trading. Best of both worlds. |
| **Licensing** | STRONG — license validation in Rust (compiled, tamper-proof). Python sidecar only starts if Rust validates license. |
| **Risk** | MEDIUM — new IPC layer between Rust ↔ Python, but trading logic unchanged. |
| **Timeline** | 3-4 months |
| **Bundle size** | ~80-150 MB (includes Python sidecar) |
| **Migration path** | Can gradually move trading logic to Rust over time using `ibapi` Rust crate. |

### Recommendation: Option C (Hybrid)

**Why:**
1. Trading logic is the highest-risk code — keep it in proven Python
2. Licensing MUST be in Rust (compiled binary = tamper-proof)
3. React frontend gives modern UI with hot-reload development
4. Gradual migration path to pure Rust if desired later
5. Rust handles all the things Python is weak at (licensing, IPC, file security)

---

## Target Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Tauri 2.0 Application Shell                    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              React + TypeScript Frontend                     │ │
│  │                                                              │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │ │
│  │  │Dashboard │ │Analytics │ │Positions │ │  Settings     │  │ │
│  │  │  Tab     │ │  Tab     │ │  Tab     │ │  Tab          │  │ │
│  │  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │              Shared State (Zustand)                   │   │ │
│  │  │  tradingState | positions | pnl | logs | config      │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  └──────────────────────────┬──────────────────────────────────┘ │
│                              │ Tauri invoke() / listen()          │
│  ┌──────────────────────────┴──────────────────────────────────┐ │
│  │                 Rust Backend (src-tauri/)                     │ │
│  │                                                               │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │ │
│  │  │  License     │  │  Config      │  │  IPC Bridge          │ │ │
│  │  │  Manager     │  │  Manager     │  │  (Rust ↔ Python)     │ │ │
│  │  │  (tamper-    │  │  (encrypted  │  │  (JSON over stdio)   │ │ │
│  │  │   proof)     │  │   storage)   │  │                      │ │ │
│  │  └─────────────┘  └─────────────┘  └──────────┬───────────┘ │ │
│  │  ┌─────────────┐  ┌─────────────┐             │             │ │
│  │  │  State       │  │  Event       │             │             │ │
│  │  │  Aggregator  │  │  Router      │             │             │ │
│  │  │  (positions, │  │  (ticks →    │             │             │ │
│  │  │   P&L, logs) │  │   frontend)  │             │             │ │
│  │  └─────────────┘  └─────────────┘             │             │ │
│  └───────────────────────────────────────────────┼─────────────┘ │
│                                                   │               │
│  ┌───────────────────────────────────────────────┴─────────────┐ │
│  │              Python Sidecar (PyInstaller binary)             │ │
│  │                                                              │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐              │ │
│  │  │ Trading    │ │ TWS API    │ │ Indicators │              │ │
│  │  │ Engine     │ │ Client     │ │ Library    │              │ │
│  │  │ (BOT.py)   │ │ (ibapi)    │ │ (pandas)   │              │ │
│  │  └────────────┘ └────────────┘ └────────────┘              │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐              │ │
│  │  │ Order      │ │ Data       │ │ Strategy   │              │ │
│  │  │ Manager    │ │ Access     │ │ Engine     │              │ │
│  │  └────────────┘ └────────────┘ └────────────┘              │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  IB TWS/Gateway  │
                    │  (TCP Socket)    │
                    └──────────────────┘
```

---

## Module Breakdown

### Frontend (React + TypeScript)

```
src/
├── App.tsx                          # Root app with router
├── main.tsx                         # Tauri entry point
├── components/
│   ├── layout/
│   │   ├── AppShell.tsx             # Main layout (sidebar + content)
│   │   ├── Header.tsx               # Logo, clock, connection status, theme toggle
│   │   └── Sidebar.tsx              # Navigation menu
│   ├── dashboard/
│   │   ├── DashboardPage.tsx        # Main trading dashboard
│   │   ├── TradingControls.tsx      # Start/Stop/Emergency buttons
│   │   ├── RiskManagement.tsx       # Profit/Loss/Risk inputs
│   │   ├── TradeParameters.tsx      # Expiry, delta, candle time
│   │   ├── StockList.tsx            # Stock selection editor
│   │   ├── ConnectionConfig.tsx     # TWS IP/Port/ClientID
│   │   ├── LiveStats.tsx            # Real-time P&L, trades, win rate
│   │   └── ActivityLog.tsx          # Scrolling trade log
│   ├── analytics/
│   │   ├── AnalyticsPage.tsx        # Analytics dashboard
│   │   ├── PerformanceMetrics.tsx   # Stats cards grid
│   │   ├── WinLossChart.tsx         # Pie/donut chart
│   │   ├── PnLChart.tsx             # Bar chart of trade P&L
│   │   └── EquityCurve.tsx          # Cumulative P&L line chart
│   ├── positions/
│   │   ├── PositionsPage.tsx        # Active positions table
│   │   ├── PositionRow.tsx          # Individual position with close button
│   │   └── PositionHistory.tsx      # Closed positions history
│   ├── logs/
│   │   ├── LogsPage.tsx             # System logs viewer
│   │   └── LogFilter.tsx            # Log type/level filters
│   ├── settings/
│   │   ├── SettingsPage.tsx         # All settings in one place
│   │   ├── GeneralSettings.tsx      # Theme, font, language
│   │   ├── TradingSettings.tsx      # Strategy params, risk
│   │   ├── BrokerSettings.tsx       # TWS connection config
│   │   └── LicenseSettings.tsx      # License management
│   ├── license/
│   │   ├── LicenseGate.tsx          # Full-screen license validation
│   │   ├── LicenseInput.tsx         # Key input form
│   │   └── LicenseStatus.tsx        # Expiry, days remaining
│   └── common/
│       ├── StatusBadge.tsx          # Connected/Disconnected badge
│       ├── ThemeToggle.tsx          # Dark/Light switch
│       ├── ModeToggle.tsx           # Demo/Live toggle
│       ├── StatCard.tsx             # Metric display card
│       └── ConfirmDialog.tsx        # Confirmation modals
├── hooks/
│   ├── useTauri.ts                  # Tauri invoke/listen wrappers
│   ├── useTradingEngine.ts          # Start/stop/status
│   ├── usePositions.ts              # Position data + refresh
│   ├── usePnL.ts                    # Real-time P&L
│   ├── useLicense.ts                # License validation
│   └── useTheme.ts                  # Theme management
├── stores/
│   ├── tradingStore.ts              # Zustand: trading state
│   ├── positionStore.ts             # Zustand: positions
│   ├── configStore.ts               # Zustand: configuration
│   └── logStore.ts                  # Zustand: log messages
├── lib/
│   ├── tauri-commands.ts            # Type-safe Tauri command wrappers
│   ├── types.ts                     # Shared TypeScript types
│   └── constants.ts                 # App constants
└── styles/
    ├── globals.css                  # Tailwind base + custom vars
    └── themes.css                   # Dark/light theme tokens
```

### Rust Backend (src-tauri/)

```
src-tauri/
├── Cargo.toml
├── tauri.conf.json
├── src/
│   ├── main.rs                      # Tauri app entry
│   ├── lib.rs                       # Module exports
│   ├── commands/
│   │   ├── mod.rs
│   │   ├── trading.rs               # start_trading, stop_trading, emergency_stop
│   │   ├── config.rs                # get_config, save_config, get_settings
│   │   ├── license.rs               # validate_license, get_license_status, revoke
│   │   ├── positions.rs             # get_positions, close_position, close_all
│   │   └── logs.rs                  # get_logs, clear_logs
│   ├── license/
│   │   ├── mod.rs
│   │   ├── validator.rs             # License key validation (SHA-256 + HMAC)
│   │   ├── hardware_id.rs           # Machine fingerprinting
│   │   ├── encrypted_store.rs       # AES-256 encrypted license storage
│   │   └── online_validator.rs      # Optional: server-side validation
│   ├── sidecar/
│   │   ├── mod.rs
│   │   ├── manager.rs               # Spawn/kill Python sidecar process
│   │   ├── protocol.rs              # JSON message protocol (Rust ↔ Python)
│   │   └── health.rs                # Sidecar health monitoring
│   ├── state/
│   │   ├── mod.rs
│   │   ├── app_state.rs             # Global app state (Mutex-wrapped)
│   │   ├── trading_state.rs         # Trading status, positions, P&L
│   │   └── config_state.rs          # Runtime configuration
│   ├── events/
│   │   ├── mod.rs
│   │   └── emitter.rs               # Emit events to React frontend
│   └── utils/
│       ├── mod.rs
│       ├── crypto.rs                # Encryption utilities
│       └── paths.rs                 # Cross-platform path handling
├── binaries/                        # Python sidecar (PyInstaller output)
│   └── trading-engine-{target-triple}
└── icons/                           # App icons
```

### Python Sidecar (trading-engine/)

```
trading-engine/
├── main.py                          # Entry point — JSON-RPC over stdio
├── engine/
│   ├── __init__.py
│   ├── trading_engine.py            # Refactored BOT.py (class-based)
│   ├── tws_client.py                # TwsApiClient (from tws_api_client.py)
│   ├── order_manager.py             # OrderManager (from order_manager.py)
│   ├── data_access.py               # DAL (from data_access.py)
│   └── models.py                    # Dataclasses (from common.py)
├── indicators/
│   ├── __init__.py
│   ├── supertrend.py                # BOTSingal extracted
│   ├── engulfing.py                 # Engulfing pattern detection
│   ├── atr.py                       # ATR calculation
│   ├── ema.py                       # EMA calculations
│   └── vwap.py                      # VWAP calculation
├── strategies/
│   ├── __init__.py
│   ├── base.py                      # Abstract strategy interface
│   ├── engulfing_atr.py             # Engulfing + ATR strategy
│   └── supertrend.py                # SuperTrend strategy
├── protocol/
│   ├── __init__.py
│   ├── handler.py                   # JSON-RPC message handler
│   ├── messages.py                  # Message type definitions
│   └── emitter.py                   # Send events back to Rust
├── config.json                      # Trading configuration
└── build.py                         # PyInstaller build script
```

---

## Rust ↔ Python IPC Protocol

Communication between Rust and Python sidecar uses **JSON messages over stdio** (stdin/stdout).

### Message Format

```typescript
// Request (Rust → Python)
{
  "id": "uuid-v4",
  "method": "start_trading",
  "params": {
    "config": { /* full config object */ }
  }
}

// Response (Python → Rust)
{
  "id": "uuid-v4",          // matches request
  "result": { "status": "ok" }
}

// Event (Python → Rust, unsolicited)
{
  "event": "tick_update",
  "data": {
    "symbol": "SPY",
    "last": 585.42,
    "bid": 585.40,
    "ask": 585.44
  }
}

// Event types:
// "tick_update"       - real-time price
// "position_update"   - position changed
// "order_update"      - order status change
// "pnl_update"        - P&L changed
// "signal_detected"   - trading signal found
// "trade_executed"    - trade placed
// "trade_closed"      - position closed
// "log_message"       - log entry
// "error"             - error occurred
// "engine_status"     - engine health/state
```

### Rust Side (sidecar/protocol.rs)

```rust
// Spawn sidecar and communicate
let sidecar = app.shell().sidecar("trading-engine")?;
let (mut rx, child) = sidecar.spawn()?;

// Send command
child.write(serde_json::to_string(&command)?.as_bytes())?;

// Receive events
while let Some(event) = rx.recv().await {
    match event {
        CommandEvent::Stdout(line) => {
            let msg: SidecarMessage = serde_json::from_str(&line)?;
            // Route to frontend via Tauri events
            app.emit("trading-event", &msg)?;
        }
        _ => {}
    }
}
```

### Python Side (protocol/handler.py)

```python
import sys, json

def send_event(event_type: str, data: dict):
    msg = json.dumps({"event": event_type, "data": data})
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()

def main_loop():
    for line in sys.stdin:
        request = json.loads(line.strip())
        method = request["method"]
        params = request.get("params", {})
        
        if method == "start_trading":
            result = engine.start(params["config"])
            respond(request["id"], result)
        elif method == "stop_trading":
            result = engine.stop()
            respond(request["id"], result)
        # ... etc
```

---

## Licensing System (Rust — Tamper-Proof)

### Architecture

```
┌─────────────────────────────────────────────┐
│           License Validation Flow            │
│                                              │
│  App Start                                   │
│      │                                       │
│      ▼                                       │
│  Read encrypted license file                 │
│  (AES-256-GCM encrypted, machine-bound)      │
│      │                                       │
│      ▼                                       │
│  Decrypt with hardware-derived key           │
│  (CPU ID + disk serial + MAC address hash)   │
│      │                                       │
│      ▼                                       │
│  Validate license fields:                    │
│  ├── HMAC signature (SHA-256)                │
│  ├── Expiry date check                       │
│  ├── Hardware ID match                       │
│  ├── Feature flags                           │
│  └── Tamper detection (file hash)            │
│      │                                       │
│      ├── VALID → Start app, load sidecar     │
│      └── INVALID → Show license gate UI      │
│                                              │
│  Optional: Online validation                 │
│  ├── POST to license server                  │
│  ├── Validate against server records         │
│  └── Cache result for offline use            │
└─────────────────────────────────────────────┘
```

### License Features

| Feature | Implementation |
|---|---|
| **Hardware binding** | Machine fingerprint from CPU/disk/MAC → prevents key sharing |
| **Encrypted storage** | AES-256-GCM with hardware-derived key → can't copy license file |
| **Tamper detection** | HMAC-SHA256 signature on license data → detects modifications |
| **Expiry enforcement** | Date check in compiled Rust binary → can't bypass with Python |
| **Feature flags** | License tiers: Basic (demo only), Pro (live trading), Enterprise (multi-account) |
| **Offline support** | Cached validation, grace period (e.g., 7 days offline) |
| **Online validation** | Optional server check for revocation, usage tracking |
| **Obfuscation** | Rust binary is compiled → much harder to reverse than Python |

### License File Format (encrypted)

```json
{
  "license_key": "XXXX-XXXX-XXXX-XXXX",
  "customer_email": "user@example.com",
  "hardware_id": "sha256_of_machine_fingerprint",
  "issued_at": "2026-02-07T00:00:00Z",
  "expires_at": "2026-08-07T00:00:00Z",
  "tier": "pro",
  "features": {
    "live_trading": true,
    "max_symbols": 20,
    "max_daily_trades": 50,
    "strategies": ["supertrend", "engulfing_atr"]
  },
  "signature": "hmac_sha256_of_all_fields"
}
```

---

## React Frontend — UI Design

### Design System

- **Framework:** React 18+ with TypeScript
- **Styling:** Tailwind CSS v4 + shadcn/ui components
- **Charts:** Recharts (React-native) or Lightweight Charts (TradingView)
- **State:** Zustand (lightweight, TypeScript-native)
- **Icons:** Lucide React
- **Animations:** Framer Motion
- **Theme:** CSS variables for dark/light with smooth transitions

### Page Layouts

#### License Gate (shown when unlicensed)

```
┌──────────────────────────────────────────┐
│                                          │
│            [Brand Logo]                  │
│                                          │
│     ┌──────────────────────────────┐     │
│     │  Enter License Key           │     │
│     │  ┌────────────────────────┐  │     │
│     │  │ XXXX-XXXX-XXXX-XXXX   │  │     │
│     │  └────────────────────────┘  │     │
│     │                              │     │
│     │  [Activate License]          │     │
│     │                              │     │
│     │  Status: ● Not activated     │     │
│     │  Contact: support@...        │     │
│     └──────────────────────────────┘     │
│                                          │
└──────────────────────────────────────────┘
```

#### Dashboard (main trading view)

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]     ● Connected    10:35:42 AM    [Demo] [🌙]       │
├────────┬────────────────────────────────────────────────────┤
│        │                                                     │
│  📊    │  ┌─────────────────┐ ┌──────────────────────────┐  │
│ Dash   │  │ Daily P&L       │ │ Trades Today    │ Win %  │  │
│        │  │ +$245.50        │ │     12          │ 66.7%  │  │
│  📈    │  └─────────────────┘ └──────────────────────────┘  │
│ Anlytx │                                                     │
│        │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  💼    │  │ Trade Params│ │ Risk Mgmt   │ │ Controls    │  │
│ Posns  │  │ Expiry: 0DTE│ │ Profit: $500│ │ [▶ Start]   │  │
│        │  │ Delta: 0.35 │ │ Loss: -$300 │ │ [⏹ Stop]    │  │
│  📋    │  │ Candle: 5m  │ │ Risk: 2%    │ │ [🚨 Emerg]  │  │
│ Logs   │  └─────────────┘ └─────────────┘ └─────────────┘  │
│        │                                                     │
│  ⚙️    │  ┌──────────────────────────────────────────────┐  │
│ Settngs│  │ Trading Activity Log                         │  │
│        │  │ [10:35:12] Signal: CALL SPY at $585.42       │  │
│        │  │ [10:35:13] Order placed: SPY 585C 0DTE x2    │  │
│        │  │ [10:35:14] Order filled at $1.52              │  │
│        │  │ [10:37:22] TP triggered: $1.52 → $1.68       │  │
│        │  └──────────────────────────────────────────────┘  │
└────────┴────────────────────────────────────────────────────┘
```

#### Analytics

```
┌────────┬────────────────────────────────────────────────────┐
│        │  Performance Metrics                                │
│ Sidebar│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │
│        │  │Trades│ │Win % │ │Avg W │ │Avg L │ │Net PL│    │
│        │  │  142 │ │61.9% │ │$85.20│ │-$42  │ │$2.4k │    │
│        │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │
│        │                                                     │
│        │  ┌─────────────────────┐ ┌────────────────────────┐│
│        │  │  Win/Loss Donut     │ │  Equity Curve          ││
│        │  │      ████           │ │  ╱──╲   ╱──────        ││
│        │  │    ██ 62% ██        │ │ ╱    ╲─╱               ││
│        │  │      ████           │ │╱                        ││
│        │  └─────────────────────┘ └────────────────────────┘│
│        │                                                     │
│        │  ┌──────────────────────────────────────────────┐  │
│        │  │  Trade P&L Distribution (bar chart)          │  │
│        │  │  ▓▓▓ ▓▓ ▓▓▓▓▓  ▓ ▓▓▓  ▓▓▓▓ ▓▓             │  │
│        │  │  ▒▒▒    ▒▒         ▒▒▒                       │  │
│        │  └──────────────────────────────────────────────┘  │
└────────┴────────────────────────────────────────────────────┘
```

---

## Tech Stack Summary

| Layer | Technology | Why |
|---|---|---|
| **Desktop shell** | Tauri 2.0 | Cross-platform, tiny bundle, native performance, Rust security |
| **Frontend** | React 18 + TypeScript | Component ecosystem, type safety, developer experience |
| **UI components** | shadcn/ui + Tailwind CSS | Modern, accessible, customizable, dark/light themes |
| **Charts** | Recharts or TradingView Lightweight Charts | Real-time capable, React-native |
| **State** | Zustand | Lightweight, TypeScript-first, no boilerplate |
| **Backend (shell)** | Rust | Licensing, IPC, config encryption, event routing |
| **Backend (trading)** | Python sidecar (PyInstaller) | Keep proven ibapi/pandas/numpy trading logic |
| **IPC** | JSON over stdio | Simple, debuggable, language-agnostic |
| **Database** | SQLite (via rusqlite) | Single file, embedded, cross-platform |
| **Licensing** | Rust (AES-256 + HMAC-SHA256 + hardware binding) | Tamper-proof compiled binary |

---

## Migration Phases

### Phase 1: Foundation (Weeks 1-3)

- Set up Tauri 2.0 + React + TypeScript project
- Implement Rust licensing module (validator, encrypted store, hardware ID)
- Create license gate UI in React
- Set up Tailwind + shadcn/ui + theme system
- Build app shell layout (sidebar, header, routing)

### Phase 2: Python Sidecar (Weeks 3-5)

- Refactor BOT.py into class-based `TradingEngine`
- Implement JSON-RPC stdio protocol in Python
- Build PyInstaller packaging script
- Implement Rust sidecar manager (spawn, monitor, kill)
- Wire up Rust ↔ Python communication

### Phase 3: Dashboard & Trading (Weeks 5-8)

- Build Dashboard page (trade params, risk, controls, activity log)
- Implement Tauri commands: start_trading, stop_trading, emergency_stop
- Wire real-time events: ticks, orders, P&L → React via Tauri events
- Build Positions page (active positions table, close actions)

### Phase 4: Analytics & Settings (Weeks 8-10)

- Build Analytics page (metrics, charts, equity curve)
- Build Settings page (general, trading, broker, license)
- Implement config persistence (encrypted in Rust)
- Build Logs page with filtering

### Phase 5: Polish & Release (Weeks 10-12)

- Cross-platform testing (Windows, macOS, Linux)
- Performance optimization (event throttling, virtual scrolling)
- Installer/updater setup (Tauri bundler)
- Documentation and user guide

### Phase 6: Future — Gradual Rust Migration (Optional)

- Port indicators to Rust (SuperTrend, ATR, EMA)
- Switch from Python ibapi to Rust `ibapi` crate
- Remove Python sidecar dependency
- Result: single ~5MB binary with no Python requirement

---

## Key Dependencies

### Frontend (package.json)

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "@tauri-apps/api": "^2.0.0",
    "@tauri-apps/plugin-shell": "^2.0.0",
    "zustand": "^5.0.0",
    "react-router-dom": "^7.0.0",
    "recharts": "^2.15.0",
    "framer-motion": "^11.0.0",
    "lucide-react": "^0.400.0",
    "date-fns": "^4.0.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0"
  },
  "devDependencies": {
    "@tauri-apps/cli": "^2.0.0",
    "typescript": "^5.6.0",
    "tailwindcss": "^4.0.0",
    "@types/react": "^18.3.0",
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^4.3.0"
  }
}
```

### Rust Backend (Cargo.toml)

```toml
[dependencies]
tauri = { version = "2", features = ["shell-sidecar"] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
rusqlite = { version = "0.32", features = ["bundled"] }
aes-gcm = "0.10"           # AES-256 encryption
sha2 = "0.10"               # SHA-256 hashing
hmac = "0.12"                # HMAC signatures
uuid = { version = "1", features = ["v4"] }
chrono = { version = "0.4", features = ["serde"] }
machine-uid = "0.5"         # Hardware fingerprinting
ring = "0.17"                # Cryptographic primitives
```

### Python Sidecar (requirements.txt)

```
ibapi>=10.19
pandas>=2.2
numpy>=2.0
yfinance>=0.2
pytz>=2024.1
```

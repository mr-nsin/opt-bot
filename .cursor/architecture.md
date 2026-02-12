# Architecture — OPT_BOT

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GUI Layer (PyQt5)                        │
│  GUI.py ─ MainApp, TradingThread, License Validation            │
│  Tabs: Trading | Analytics | Positions | Logs                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ calls BOT.start_trading(config)
                             │ reads BOT.stop_trading()
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Trading Engine (BOT.py)                        │
│  main_call() → init_api_client() → subscribe data               │
│  event_processor() loop ← Queue ← tick events                   │
│  getCallPutEngulfCheck() → checkConditionsAndTrade() → takeTrade │
│  pnl_watchdog_thread() monitors daily P&L                       │
│  monitor_positions_loop() checks TP/SL                          │
└─────────┬───────────────────┬──────────────────┬────────────────┘
          │                   │                  │
          ▼                   ▼                  ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│ TwsApiClient    │ │ OrderManager    │ │ Indicators.py           │
│ (tws_api_client │ │ (order_manager  │ │ SuperTrend (BOTSingal)  │
│  .py)           │ │  .py)           │ │ Engulfing patterns      │
│                 │ │                 │ │ RSI, MACD, ATR, EMA     │
│ EWrapper+EClient│ │ Entry/Exit mgmt │ │ Ichimoku, Williams %R   │
│ Market data sub │ │ TP/SL trailing  │ │ Fibonacci               │
│ Order placement │ │ Cooldown track  │ │ Uses yfinance + pandas  │
│ Position track  │ │ Thread-safe     │ │                         │
│ P&L monitoring  │ │ (Lock-based)    │ │                         │
│ Auto-reconnect  │ │                 │ │                         │
└─────────────────┘ └────────┬────────┘ └─────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  DAL            │
                    │  (data_access   │
                    │   .py)          │
                    │                 │
                    │ SQLite queue-   │
                    │ based writes    │
                    │ option_orders   │
                    │ table           │
                    └─────────────────┘
```

## Component Relationships

### 1. GUI → BOT (Loose Coupling)

`GUI.py` imports `BOT` module and calls:
- `BOT.start_trading(config_dict)` — starts the trading engine in a subprocess
- `BOT.stop_trading()` — signals the engine to stop

The GUI reads config from `config/settings.json` and writes updated parameters to `config.json` before starting.

### 2. BOT → TwsApiClient (Direct Dependency)

`BOT.py` holds a global `client` (TwsApiClient instance) initialized via `init_api_client()`. The client:
- Connects to IB TWS on `IP:PORT` with `CLIENTID`
- Runs its own message loop in a daemon thread
- Pushes tick events into a shared `Queue` (event_queue)
- Handles order callbacks → routes to `OrderManager.process_trade()`

### 3. BOT → OrderManager → DAL (Chain)

- `BOT.py` creates `OrderManager(db)` with a `DAL` instance
- `OrderManager` receives trade callbacks from `TwsApiClient`
- On fill events, it updates the DAL (SQLite) and manages TP/SL logic
- `OrderManager.close_position()` places exit (market) orders via `TwsApiClient`

### 4. Event Queue Architecture

```
TwsApiClient.tickPrice() ──┐
TwsApiClient.tickSize()  ──┤──→ event_queue (Queue) ──→ event_processor() in BOT.py
                            │                              │
                            │                              ├── Stock tick → getCallPutEngulfCheck()
                            │                              └── Option tick → check_and_close_position()
```

The event queue decouples the IB API callback thread from the trading logic thread.

### 5. Threading Model

| Thread | Owner | Purpose |
|---|---|---|
| Main thread | GUI.py | PyQt5 event loop |
| IB message thread | TwsApiClient | `EClient.run()` — processes IB messages |
| Heartbeat thread | TwsApiClient | Checks connection every 60s, attempts reconnect |
| Orders queue thread | DAL | Processes DB write queue (insert/update/delete) |
| Event processor | BOT.py | Processes tick events from event_queue |
| PnL watchdog | BOT.py | Monitors daily P&L limits every ~60s |
| Position monitor | BOT.py | Checks TP/SL on active orders every ~2s |

### 6. Two Database Layers

**Layer 1 — `data_access.py` (DAL)**
- Used by the core trading engine (`BOT.py` → `OrderManager`)
- Single table: `option_orders`
- Queue-based async writes, thread-safe with `Lock`
- Database path: `db/orders.db`

**Layer 2 — `utils/database_manager.py` (DatabaseManager)**
- Used by newer `strategies/` and `clients/` modules
- Tables: `trades`, `signals`, `performance_metrics`, `sessions`, `candle_data`
- Context-manager based connections
- Database path: `database/trades.db`

### 7. Configuration Flow

```
config.json (trading params)  ──┐
config/settings.json (UI/strategy) ──┤──→ BOT.py globals
expiryStrike.json (strike data) ──┘    GUI.py config
                                        strategies/ config
```

GUI reads `config/settings.json`, writes updated values, then passes merged config dict to `BOT.start_trading()`.

### 8. License System

Two license mechanisms coexist:
1. **GUI-level** (`GUI.py`): SHA-256 hash of `{ip, email, key, start_date, days}` → validates against hardcoded values
2. **BOT-level** (`BOT.py`): Base64-encoded issue date in `license.json`, valid for 90 days

### 9. Newer Architecture Layer (strategies/, clients/, utils/)

The `strategies/`, `clients/`, and `utils/` directories represent a **config-driven, class-based** architecture designed for:
- Multiple strategy support (pluggable via `config/settings.json`)
- Multiple broker support (Tradovate, Databento alongside IB)
- Enhanced database schema with session/performance tracking
- Categorized logging (trading, trades, errors, system)

This layer is **partially integrated** — the strategies generate signals but the main `BOT.py` still drives execution.

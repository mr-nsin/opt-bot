# System Patterns: QuantDrift Options Trading Bot

## System Architecture

```
┌──────────────────────────────────────────────┐
│            Tauri Frontend React UI           │
│  [Zustand Stores] ◄─── (Tauri Events)        │
│          │                                   │
│    (tauri::invoke)                           │
│          ▼                                   │
┌──────────────────────────────────────────────┐
│                 Rust Backend                 │
│  [License Handler] [ConfigState Management]  │
│  [Sidecar Thread Manager]                    │
│          │                                   │
│    (stdio JSON-RPC)                          │
│          ▼                                   │
┌──────────────────────────────────────────────┐
│           Python Trading Engine              │
│  [trading_engine.py] ◄─── (SQLite DB)        │
│  [tws_api_client.py] ───► (IB TWS API)       │
└──────────────────────────────────────────────┘
```

## Key Technical Decisions & Patterns

### 1. Engine Threading & API Isolation
The Python Engine (`trading_engine.py`) separates responsibilities strictly across threads:
* **JSON-RPC Stdio:** The main thread acts as an IPC server, reading `stdin` and emitting events to `stdout` to communicate with Rust.
* **Engine Thread:** `_engine_thread` runs asynchronously, polling for signals and managing state changes.
* **TWS API Thread:** `tws_api_client.py` spawns a background daemon thread to process asynchronous `EWrapper` callbacks coming from the Interactive Brokers API without blocking execution logic.

### 2. TWS Communication and Data Caching
`tws_api_client.py` uses `EWrapper` and `EClient` to connect to TWS. It relies heavily on local memory caching (`tick_cache`, `ticker_contract_cache`, `positions`, `history_cache`) to prevent hammering the IBKR API limit thresholds.
* **Snapshot Upgrades:** Tickers can be subscribed to strictly as snapshots, or upgraded seamlessly into streaming ticks. 
* **Fallback Mechanisms:** If real-time option P&L is unavailable or duplicate positions are fetched, it implements a deduplication layer based on `(symbol, strike, right, expiry)` and defaults to Order Manager tick lookups.

### 3. Double Event Emission for Real-Time UI Updates
* **Active Positions:** Python fetches options tick data, computes Bid/Ask and P&L, and emits `position_update` events via stdout. Rust intercepts and emits `trading:position_update` to the frontend.
* **Trade Blotter:** Displays executed orders and cross-references them against active positions using `positionKey(symbol, strike, right, expiry)` for real-time price updates.

### 4. JSON-RPC Communication over Stdio
The Rust backend communicates with the Python sidecar using raw standard input/output pipes. Events are serialized as JSON-RPC messages. This isolates errors: if the Python engine crashes, the Rust layer can detect the exit code, emit an alarm to the UI, and restart the process safely.

### 5. Zustand State Stores
Lightweight React stores (`positionStore`, `configStore`, `tradingStore`) decouple component states. UI elements subscribe to these stores to handle asynchronous WebSocket/IPC updates smoothly.

### 6. Hardware-Locked License Validation
Compiled Rust utilizes hardware properties (`hostname|cpu_brand|total_memory|os_name|os_version|mac|quantdrift-salt-v1`) to derive a unique SHA-256 fingerprint. Signature checking happens at app initialization, tightly binding the executable to a single machine preventing license sharing.

### 7. Config Mirroring
Tauri handles configuration load and save operations. Saves are mirrored to the source file location from which they were read so that the Python sidecar and Rust loader stay fully in sync at runtime.

### 8. Sidecar Process Management (Rust/Tauri)
The Rust Backend (`src-tauri/src/sidecar/manager.rs`) handles the Python engine lifecycle:
* **Spawn Hierarchy:** Tries `QUANTDRIFT_PYTHON` env var first -> then workspace `.venv/bin/python` -> finally falls back to a standalone embedded `trading-engine` binary.
* **Process Cleanup (Windows):** Uses Windows Job Objects (`win32job`). If the parent Tauri app crashes or is killed by Task Manager, the OS immediately force-kills the Python sidecar, preventing orphaned zombie trading processes.
* **Smart AppState Routing:** Rust intercepts JSON lines from Python `stdout`. Instead of just passing them blindly to React, it updates its own memory state (e.g., merging `trade_closed` P&L into the active `trades_today` array) before emitting sanitized `trading:*` events to the frontend.

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
1. **JSON-RPC Communication over Stdio:** The Rust backend communicates with the Python sidecar using raw standard input/output pipes. Events are serialized as JSON-RPC messages. This isolates errors: if the Python engine crashes, the Rust layer can detect the exit code, emit an alarm to the UI, and restart the process safely.
2. **Double Event Emission for Real-Time UI Updates:**
   * **Active Positions:** Python fetches options tick data, computes Bid/Ask and P&L, and emits `position_update` events via stdout. Rust intercepts and emits `trading:position_update` to the frontend.
   * **Trade Blotter:** Displays executed orders and cross-references them against active positions using `positionKey(symbol, strike, right, expiry)` for real-time price updates.
3. **Zustand State Stores:** Lightweight React stores (`positionStore`, `configStore`, `tradingStore`) decouple component states. UI elements subscribe to these stores to handle asynchronous WebSocket/IPC updates smoothly.
4. **License Validation:** Compiled Rust utilizes hardware properties (CPU ID, hostname, RAM size) to derive a unique key. Signature checking happens at app initialization, gating access to trading controls.
5. **Config Mirroring:** Tauri handles configuration load and save operations. Saves are mirrored to the source file location from which they were read so that the Python sidecar and Rust loader stay fully in sync at runtime.

# OPT_BOT — Complete Architecture Reference

**Last updated:** April 2026  
**Purpose:** Single reference for stack layout, data flow, **database and logging behavior**, **position monitoring concurrency**, and prioritized follow-ups. Supersedes scattered notes in older architecture drafts where they conflict with the current repo.

---

## 1. Stack overview

| Layer | Technology | Role |
|-------|------------|------|
| UI | React + TypeScript + Vite + Tailwind | Dashboard, positions, settings, analytics |
| Shell | Tauri (Rust) | Window, licensing, **sidecar lifecycle**, **IPC to webview** |
| Trading engine | Python 3.12 (`trading-engine/`, project-root `BOT.py`, `order_manager.py`, …) | IBKR TWS API, strategies, TP/SL, DB persistence |
| Broker | Interactive Brokers TWS / Gateway | Market data and orders |

**Bridge:** Python sidecar speaks **JSON-RPC over stdio** to Rust; Rust **pushes** events to the frontend with `app.emit` (no WebSocket).

---

## 2. End-to-end data flow

```
IBKR TWS
    │ callbacks (ticks, positions, orders, PnL…)
    ▼
TwsApiClient (Python) — tick_cache, positions, pnl_cache, …
    │
    ├─► Event queue (OPT/STK ticks) ─► BOT.event_processor × N threads ─► signals / TP&SL (OPT)
    ├─► monitor_positions_loop (Thread) ─► ThreadPoolExecutor ─► TP&SL per TWS position (parallel)
    └─► TradingEngine main loop ─► get_positions() ─► emit_positions_snapshot ─► stdout JSON
            │
            ▼
Rust sidecar (reads stdout, parses JSON events)
            │
            ▼
Tauri emit("trading:…") ─► React (useTradingEvents, Zustand stores)
```

**Important:** UI refresh cadence (e.g. positions every ~0.5s, P&L emit throttled to ~1s) is **for display and IPC volume**. **TP/SL execution** uses live `Tick` objects and the monitor loop (see §6), not the React store.

---

## 3. Database layer — async or not?

### 3.1 Primary app DB: `data_access.py` (`DAL`) — `db/orders.db`

| Aspect | Behavior |
|--------|----------|
| API style | **Synchronous** `sqlite3` (stdlib). **Not** `asyncio` / `aiosqlite`. |
| Concurrency model | **Single writer thread** + `Queue`: `put` / `update` / `delete` enqueue work; `handle_orders_queue` runs `insert_order`, `update_option_order`, `delete_option_order` on **one** long-lived `self.conn`. |
| Callers | `OrderManager.save_order` → `db.put`; status updates → `db.update`; deletes on close → `db.delete`. These return quickly (queue only). |
| Reads | `get_all_option_orders()` runs on the **DB thread** at startup; in-memory `self.orders` is updated when inserts/deletes complete. |

**Performance takeaway:** Order path does **not** block the trading thread on disk I/O for every write — it blocks only on `queue.put` (cheap). SQLite writes still happen **sequentially** on the worker thread (good for SQLite; avoids lock contention from multiple writers).

**Not “async” in the asyncio sense:** there is no event-loop integration. The design is **background-thread + queue** (classic fire-and-forget persistence).

**SQL safety:** `update_option_order` uses **parameterized** `UPDATE … WHERE id = ?` (no f-string SQL) so `order_status` and numeric fields cannot break quoting or inject SQL.

### 3.2 Analytics / secondary: `utils/database_manager.py`

Uses **synchronous** `sqlite3` with `with sqlite3.connect(...)` per operation (or long-lived connection in some paths). Suitable for analytics volume; not on the hot order path.

### 3.3 Possible improvements

1. **`aiosqlite` + asyncio** — Only worth it if the whole engine becomes async-aware; today the stack is threaded/sync. **Low priority** unless you unify on asyncio.
2. **WAL mode + `PRAGMA`** — Can reduce writer stalls under burst updates (`journal_mode=WAL`, `synchronous=NORMAL`) — validate against durability needs.
3. **Parameterized queries everywhere** — `update_option_order` still builds raw SQL strings in places; prefer `?` placeholders for safety and plan cache stability.

---

## 4. Logging — async or not?

### 4.1 Python → Rust (`trading-engine/protocol/emitter.py`)

| Mechanism | Behavior |
|-----------|----------|
| `send_event` / `_send` | **Synchronous** `os.write()` to stdout **fd** under `_write_lock` — thread-safe, one JSON line per event. |
| `emit_log` | **Batched**: appends to `_LOG_BUFFER` (under lock), schedules a **threading.Timer(150ms)** to flush many log lines as **one** `log_message` event. Reduces IPC vs per-line emit. |
| `emit_error` | **Immediate** single event (not batched the same way as `emit_log`). |

**Not async:** no asyncio; batching is **timer + buffer**.

### 4.2 JSON-RPC handler (`protocol/handler.py`)

Each stdin request is dispatched to a **bounded `ThreadPoolExecutor`** (default **8** workers, override with env **`QUANTDRIFT_RPC_MAX_WORKERS`**, clamped 1–32) so the stdin read loop never blocks but thread count cannot explode under rapid UI/RPC load. `handler.stop()` shuts the pool down on process signals (`main.py`).

### 4.3 Rust (`src-tauri/src/commands/logs.rs`)

| API | Behavior |
|-----|------------|
| `push_log` | `tokio::sync::Mutex` + `VecDeque` — **async** Rust side when called from async Tauri handlers. |
| `get_logs` | Async read from the same buffer. |

Frontend log panel receives **pushed** events from the sidecar; hydration uses `invoke` when needed.

### 4.4 React (`useTradingEvents.ts`)

Log lines from Python are further **batched** (`LOG_BATCH_MS = 150`) before hitting the log store.

**Performance takeaway:** Logging is **decoupled from tight loops** via Python-side batching + lock; still **CPU-bound** for huge log volume — keep TP/SL paths on `logger.debug` where possible.

---

## 5. Position monitoring — parallel or sequential?

There are **three** relevant paths:

### 5.1 Poll-based monitor (`BOT.monitor_positions_loop`)

- **Loop interval:** `time.sleep(0.1)` (~10 Hz).
- **Concurrency:** For each cycle, open TWS positions are checked with **`ThreadPoolExecutor`**:
  - `max_workers = min(16, max(1, pos_count))`
  - One task per position: `order_mgr.check_exit_conditions(pos)` → `check_and_close_position(tick)`.
- **Conclusion:** **Different positions are checked in parallel** (up to 16 workers). **Each position** uses one shared `Tick` object; `tick.busy` prevents re-entrant TP/SL on the **same** tick from overlapping.

### 5.2 Event-driven path (`BOT.event_processor`)

- **Threads:** `PROCESSORS_COUNT = 4` (four worker threads pull from the **same** `Queue`).
- **Per tick:** One OPT tick with `active_order` runs `check_and_close_position` **on that thread** — sequential **per event**, but **multiple** threads process **different** ticks concurrently.
- **Conclusion:** **Parallel across symbols/ticks**, not a single global queue processed one-at-a-time.

### 5.3 Interaction between paths

The same `Tick` can be touched by the **event** thread and the **monitor** thread. **`tick.busy`** is the serialization guard for TP/SL logic on that object.

### 5.4 UI snapshot (`TradingEngine.get_positions` → `emit_positions_snapshot`)

- Builds the positions list for the UI **once per ~0.5s** (not the TP/SL decision path).
- **Implementation note:** Prefer iterating TWS positions via **`TwsApiClient.get_all_positions()`**, which copies under `positions` lock, instead of iterating `client.positions` without a snapshot — avoids rare dict mutation errors during iteration.

---

## 6. IPC and batching (current behavior)

| Event | Typical pattern |
|-------|-----------------|
| Positions | **`positions_snapshot`** — batched list (`emit_positions_snapshot`), not N × `position_update` per tick from the engine loop. |
| P&L | Throttled in engine (`_pnl_throttle_sec`, ~1s) — reduces noise; **not** used for TP/SL. |
| Logs | Batched 150ms Python + 150ms React. |
| Position store updates | React batches **~250ms** (`POSITION_BATCH_MS`) in `useTradingEvents`. |

---

## 7. Prioritized improvements (consolidated)

### P0 — Stability / correctness

- Extend **thread-safe access** to remaining `TwsApiClient` caches (`trades_cache` **done:** `_trades_lock` + `has_order_in_trades_cache`; order lists, `history_cache`) where callbacks and readers overlap.
- **`handler.py`:** ~~replace unbounded threads~~ **done:** bounded `ThreadPoolExecutor` + `QUANTDRIFT_RPC_MAX_WORKERS`.
- **`BOT.py` emergency / bulk close:** ensure **short** positions close with **BUY**, longs with **SELL** (do not assume SELL everywhere).

### P1 — Architecture maintainability

- Introduce **`TradingSession`** (or equivalent) to replace **BOT.py globals**; inject session into engine and `OrderManager`.
- Split **`OrderManager`** into persistence + execution + **exit strategy** modules.
- **`TradingEngine.get_positions` docstring** mentions fallback to `entry_orders_cache` — implement or align doc with code.

### P2 — UX / polish

- Persist **`signal_data` / `data_status`** in Rust `AppState` if navigation should not lose last payload.
- Rust: structured **`AppError`** instead of `String` everywhere; optional split `AppState` mutexes.

### P3 — Performance (optional)

- `aiosqlite` only if the Python runtime moves to asyncio end-to-end.
- Chart components (e.g. PnL sparkline): throttle redraws to **≤2 Hz** if profiling shows layout cost.

---

## 8. Related documents

| File | Contents |
|------|----------|
| `docs/ARCHITECTURE_DEEP_DIVE.md` | Original audit (some tables outdated — prefer this doc for “current” facts). |
| `docs/ARCHITECTURE_IMPROVEMENTS.md` | Historical “fixes applied” + ADRs; refresh paths may reference old `emit_position` naming. |
| `docs/OPTION_SL_TP_LOGIC.md` | SL/TP rules and trailing behavior. |

---

## 9. Verification checklist (for future PRs)

- [ ] TP/SL uses **live** `Tick` / monitor, not UI snapshot timing.
- [ ] DB writes go through **`DAL` queue** for order rows (no new synchronous SQLite hot paths without review).
- [ ] New **high-frequency** logs use **`logger.debug`** or omit `emit_log`.
- [ ] Position iteration uses **`get_all_positions()`** when available.
- [ ] Multi-position monitoring remains **parallel** (`ThreadPoolExecutor`) unless a deliberate serialization requirement exists.

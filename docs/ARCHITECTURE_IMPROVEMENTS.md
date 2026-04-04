# Architecture Improvements — QuantDrift OPT_BOT

**Date:** April 2026  
**Status:** Critical items fixed. Remaining items prioritized for follow-up.

---

## 1. Data Flow Architecture

### Current Architecture (Correct — No WebSocket Needed)

```
┌──────────────┐    JSON-RPC/stdio    ┌──────────────┐    Tauri IPC (push)    ┌──────────────┐
│  Python       │ ──── events ──────► │  Rust         │ ──── emit() ────────► │  React        │
│  Trading      │ ◄── commands ────── │  Sidecar      │ ◄── invoke() ──────── │  Frontend     │
│  Engine       │                     │  Manager      │                       │              │
└──────────────┘                     └──────────────┘                       └──────────────┘
```

**Tauri's native IPC is already push-capable.** The Rust process can push events to the webview at any time via `app_handle.emit("event_name", payload)`. The frontend listens via `useTauriEvent`. This is a zero-latency push channel — no WebSocket, HTTP server, or polling is needed.

### Data Flow Verification

| Data Type | Push Event | Frequency | Polling Required? |
|-----------|-----------|-----------|-------------------|
| Position updates | `trading:position_update` | Every 0.5s/position | **No** |
| P&L (daily/unrealized/realized) | `trading:pnl_update` | Every 1s (throttled) | **No** |
| Engine status | `trading:engine_status` | On change | **No** |
| TWS connection | `trading:connection_status` | On change | **No** |
| Account metrics | `trading:account_metrics` | Every 5s (dedup'd) | **No** |
| Data feed status | `trading:data_status` | Every 5s | **No** |
| Trade fills | `trading:trade_executed` | On demand | **No** |
| Trade closes | `trading:trade_closed` | On demand | **No** |
| Signals | `trading:signal_detected` | On demand | **No** |
| Signal data | `trading:signal_data` | On demand | **No** |
| Log messages | `trading:log_message` | Batched 150ms | **No** |

**All real-time data is push-based.** The only `invoke()` calls are:
- **One-time hydration** on app mount (positions, trading status, account metrics)
- **Manual user actions** (start/stop trading, close position, activate license)

---

## 2. Critical Fixes Applied (This Session)

### 2.1 Close Position Passed Incomplete Identity
**Severity:** CRITICAL  
**Files:** `PositionRow.tsx`, `usePositions.ts`  
**Before:** Close button sent `(symbol, strike, right)` — missing `expiry`. Two positions with different expiries on the same contract would be ambiguous.  
**After:** Now sends `(symbol, strike, right, expiry)`.

### 2.2 TWS Reconnect Logic Was Dead Code
**Severity:** CRITICAL  
**File:** `tws_api_client.py`  
**Before:** `connectionClosed()` was defined twice. Python uses the last definition, so the reconnect logic (in the first definition) was completely unreachable. When TWS disconnected, the engine never reconnected.  
**After:** Removed the duplicate, preserved the reconnect handler, added `self.connection_closed = True` flag.

### 2.3 License Silently Deleted by Network Failures
**Severity:** CRITICAL  
**Files:** `useLicense.ts`, `license.rs` (Rust)  
**Before:** A transient network failure when fetching the license registry caused the error `"Registry check failed: ... License may be revoked or expired."` The frontend matched `"expired"` and `"registry check failed"` in `isRevocationError()`, triggering `invalidateLicenseState()` which deleted `license.enc`.  
**After:**
- `isRevocationError()` only matches `"not found in registry"` or `"revoked"`
- ALL `invalidateLicenseState()` calls removed from automated paths
- Rust `validate_license` falls back to local validation when network fails

---

## 3. High-Priority Fixes Applied (This Session)

### 3.1 Active Positions Sorted by P&L Instead of Time
**File:** `PositionsPage.tsx`  
Default sort changed from `"pnl"` descending to `"time"` descending (newest first). Added sortable "Time" column.

### 3.2 `nextOrderId()` Not Thread-Safe
**File:** `tws_api_client.py`  
Added `self._lock` protection. Without it, two concurrent order placements could get the same order ID, causing TWS to reject one.

### 3.3 Exit Fill Crashed on Missing Tick Lookup
**File:** `order_manager.py`  
`process_fill` for exit orders accessed `option_tick.last_trade_time` without null check. Externally-placed orders or orders where the tick lookup was evicted would crash the fill handler, leaving positions stuck.

### 3.4 PositionRow Re-Render Storm
**File:** `PositionRow.tsx`  
Each `PositionRow` called `usePositions()` which subscribed to the entire position store. Any single tick update caused ALL position rows to re-render. Fixed by removing the store subscription — close button now calls `positionsApi.close()` directly.

### 3.5 PENDING_RESPONSES Not Drained on Sidecar Crash
**File:** `manager.rs`  
When the Python sidecar crashed, all pending `send_request_and_wait` callers (e.g., `get_positions`) hung for 10s each. Now immediately unblocked with "Sidecar terminated" error.

### 3.6 Close Position Silent Fail
**File:** `order_manager.py`  
If no managed entry order existed (position opened before engine started, or opened externally), `close_position_by_symbol` did nothing. Added `_close_position_direct()` fallback that scans TWS positions and places a MKT order.

### 3.7 Redundant AccountSummary Polling Retries
**File:** `AccountSummary.tsx`  
Removed 600ms/1600ms retry timeouts. The `trading:account_metrics` push event arrives every 5s — retrying an imperative fetch creates a race that can overwrite fresher event data.

---

## 4. Remaining Architecture Improvements (Prioritized)

### P0 — Thread Safety in Python Engine

**Impact:** Can crash the engine during live trading  
**Files:** `tws_api_client.py`, `trading_engine.py`

| Issue | Risk |
|-------|------|
| `positions` dict has no lock — `position()` callback writes, `get_positions()` reads | `RuntimeError: dictionary changed size during iteration` |
| `tick_cache` reads in `get_positions()` are outside `_lock` — partial tick data | Incorrect bid/ask/last displayed for 1 tick cycle |
| `handler.py` spawns unbounded threads per RPC request | Thread exhaustion under load |

**Recommended fix:**
1. Add a `positions_lock = threading.Lock()` to `TwsApiClient`
2. Use `with self.positions_lock:` in `position()` callback and all readers
3. Use `with self._lock:` in `get_data()`, `get_options_data()` readers
4. Replace thread-per-request in `handler.py` with `ThreadPoolExecutor(max_workers=4)`

### P1 — Heartbeat Thread Exits Permanently on Disconnect

**Impact:** After reconnect, no heartbeat — next disconnection may not be detected  
**File:** `tws_api_client.py`

The heartbeat loop (`while not self.connection_closed`) exits when `connection_closed = True`. After the engine reconnects and resets `connection_closed = False`, **no new heartbeat is started**.

**Recommended fix:** In `_try_reconnect_tws_if_needed()`, after successful reconnect, call `self._client.start_heartbeat()` to restart the heartbeat thread.

### P2 — Window Close Can Kill Engine Mid-Trade

**Impact:** Data loss if user closes window while trading  
**File:** `lib.rs`

```rust
let is_trading = state_arc.try_lock().map(|app| { ... }).unwrap_or(false);
```

If the Tokio mutex is held (e.g., processing a position_update), `try_lock()` fails, `unwrap_or(false)` treats it as "not trading", and the window closes — killing the sidecar mid-trade.

**Recommended fix:** Use an `AtomicBool` for `is_trading` that's updated whenever status changes, so `on_window_event` never needs the mutex.

### P3 — Batch Position Updates

**Impact:** Performance — reduces IPC calls by 90%  
**Files:** `trading_engine.py`, `emitter.py`

Currently `_emit_positions()` sends N individual `position_update` events (one per position) every 0.5s. For 10 positions = 20 IPC calls/second. `emit_positions_snapshot()` exists but is never called from the engine loop.

**Recommended fix:** Replace individual `emit_position()` calls in `_emit_positions()` with a single `emit_positions_snapshot(positions)` call. The frontend handler already exists at `useTradingEvents.ts:345`.

### P4 — Store signal_data and data_status in Rust AppState

**Impact:** Data loss on page navigation  
**File:** `manager.rs`

Neither `signal_data` nor `data_status` events are stored in AppState. They're forwarded to the frontend but if the user navigates away and back, the data is lost until the engine re-emits.

**Recommended fix:** Add match cases in `handle_sidecar_message` to store these in AppState, similar to how `account_metrics` is stored.

### P5 — Emergency Close Always SELLs (Breaks Short Positions)

**Impact:** Would increase a short position instead of closing it  
**File:** `BOT.py`

```python
action = "SELL"  # Always — never checks if position is long or short
```

**Recommended fix:** Check `pos.position > 0` → SELL, `pos.position < 0` → BUY.

---

## 5. SL/TP Architecture (Verified Correct)

The SL/TP system is ATR-based:

```
1. getATR(df, n=21)           → Wilder's 21-period ATR on 5-min IBKR bars
2. resolve_atr_for_sl_tp()    → Prefers option ATR, falls back to stock ATR  
3. compute_sl_tp_from_price_and_atr():
   - If ATR > 30% of price → offset = 30% of price (cap)
   - Else → offset = ATR
   - LONG:  TP = entry + offset, SL = entry - offset
   - SHORT: TP = entry - offset, SL = entry + offset
4. Trailing TP: profit_increment = $0.03 per step (config)
5. ATR_CHECKS = 0.047 minimum to allow trade entry
```

**Known edge case:** When ATR ≤ 0.01, TP is set $0.02 above entry but `profit_increment` ($0.03) is larger, so the trailing mechanism can never activate. Fix: set `profit_increment = min(profit_increment, initial_tp_distance * 0.8)`.

---

## 6. Refresh Button Architecture (Resolved)

**Current state after fixes:**
- The Refresh button is **manual only** — no automatic polling
- `refreshPositions()` on mount only fires if the store is empty (hydration)
- All real-time data comes via Tauri push events (`emit`)
- The 10-second `setInterval` polling loop was removed in a previous session

**The Refresh button is now a manual escape hatch only.** In normal operation, position data flows:

```
Python (0.5s) → emit_position() → stdout JSON → Rust manager.rs → emit("trading:position_update") → React useTradingEvents → positionStore.updatePosition()
```

No fetch, no poll, no WebSocket. Pure push via Tauri's native IPC.

---

## 7. Architecture Decision: Tauri IPC vs WebSocket

| Criterion | Tauri IPC (current) | WebSocket |
|-----------|-------------------|-----------|
| Latency | ~0ms (same process) | ~1-10ms (localhost TCP) |
| Push support | Native (`emit`) | Native |
| Reliability | Guaranteed delivery | Can drop on reconnect |
| Complexity | Zero setup | Needs WS server + client |
| Security | Sandboxed IPC | Localhost port exposure |
| Binary support | Via serde | Via MessagePack/Protocol Buffers |

**Verdict: Tauri IPC is the correct choice.** A WebSocket would add complexity with no benefit. The Python → Rust → React event chain via stdio + Tauri emit is already lower-latency than any WebSocket implementation could be.

---

## 8. Files Modified in This Session

| File | Changes |
|------|---------|
| `src/hooks/useLicense.ts` | Tightened `isRevocationError`, removed all automated `invalidateLicenseState()` calls |
| `src-tauri/src/commands/license.rs` | Network-resilient `validate_license` with local fallback |
| `src/components/positions/PositionRow.tsx` | Pass expiry to close, remove store subscription, add time column |
| `src/hooks/usePositions.ts` | Accept expiry in `closePosition` |
| `src/components/positions/PositionsPage.tsx` | Default sort by time, add Time sortable column |
| `tws_api_client.py` | Fix duplicate connectionClosed, thread-safe nextOrderId, safe openOrdersSymbol.remove |
| `order_manager.py` | Null guard on process_fill, fix options_tick typo, add _close_position_direct fallback |
| `src-tauri/src/sidecar/manager.rs` | Drain PENDING_RESPONSES on sidecar termination |
| `src/components/dashboard/AccountSummary.tsx` | Remove redundant polling retries |
| `trading-engine/engine/trading_engine.py` | Improved demo simulation |

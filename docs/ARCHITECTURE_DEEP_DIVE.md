# Architecture Deep Dive — QuantDrift OPT_BOT

**Date:** April 2026  
**Scope:** Complete codebase audit — Python engine, Rust backend, React frontend  
**Methodology:** Static analysis, data flow tracing, performance profiling

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Data Flow Architecture](#2-data-flow-architecture)
3. [Python Engine — Critical Issues](#3-python-engine)
4. [Rust Backend — Assessment](#4-rust-backend)
5. [React Frontend — Performance](#5-react-frontend)
6. [Performance Hotspots](#6-performance-hotspots)
7. [Improvement Roadmap](#7-improvement-roadmap)

---

## 1. Executive Summary

| Category | Critical | High | Medium | Fixed (this session) |
|----------|----------|------|--------|---------------------|
| Python Engine | 2 | 5 | 6 | 4 |
| Rust Backend | 0 | 2 | 4 | 3 |
| React Frontend | 1 | 3 | 4 | 4 |
| **Total** | **3** | **10** | **14** | **11** |

**Top 3 actions that would have the highest impact:**

1. **Wrap BOT.py's 35 globals into `TradingSession` class** — unlocks testability, thread safety, multi-instance
2. **Batch position updates** — Python→Rust (10 IPC→1) and React (20 re-renders/sec→2)
3. **Thread-safe caches in tws_api_client.py** — prevents RuntimeError crashes during live trading

---

## 2. Data Flow Architecture

### Current Architecture (Correct — No WebSocket Needed)

```
┌──────────────┐    JSON-RPC/stdio    ┌──────────────┐    Tauri IPC (push)    ┌──────────────┐
│  Python       │ ──── events ──────► │  Rust         │ ──── emit() ────────► │  React        │
│  Trading      │ ◄── commands ────── │  Sidecar      │ ◄── invoke() ──────── │  Frontend     │
│  Engine       │                     │  Manager      │                       │              │
└──────────────┘                     └──────────────┘                       └──────────────┘
     │                                      │                                      │
     │ TWS API                              │ AppState (Mutex)                     │ Zustand stores
     │ tick_cache, positions                │ positions, pnl, trades               │ positionStore
     │ pnl_cache, orders_cache             │ license, sidecar_running             │ tradingStore
     ▼                                      ▼                                      ▼
  IBKR TWS                            Single process                        WebView (Vite)
```

**Tauri IPC is native push — zero latency, no polling needed.**

| Data Type | Push Event | Frequency | Polling? |
|-----------|-----------|-----------|----------|
| Position updates | `trading:position_update` | 0.5s per position | **No** |
| P&L | `trading:pnl_update` | 1s (throttled) | **No** |
| Engine status | `trading:engine_status` | On change | **No** |
| TWS connection | `trading:connection_status` | On change | **No** |
| Account metrics | `trading:account_metrics` | 5s (dedup'd) | **No** |
| Trade fills/closes | `trading:trade_executed/closed` | On demand | **No** |
| Signals | `trading:signal_detected` | On demand | **No** |
| Log messages | `trading:log_message` | Batched 150ms | **No** |

**All 11 event types are push-based.** The only `invoke()` calls are one-time hydration on mount and manual user actions.

### Why Not WebSocket?

| Criterion | Tauri IPC (current) | WebSocket |
|-----------|-------------------|-----------|
| Latency | ~0ms (same process) | ~1-10ms (TCP) |
| Push support | Native (`emit`) | Native |
| Reliability | Guaranteed | Can drop on reconnect |
| Complexity | Zero setup | WS server + client + reconnect logic |
| Security | Sandboxed | Localhost port exposure |

**Verdict: Tauri IPC is correct. WebSocket would add complexity with no benefit.**

---

## 3. Python Engine

### 3.1 BOT.py — The God File

**Size:** 2,484 lines | **Classes:** 0 | **Global variables:** 35+ | **Functions >100 lines:** 8

This is the single biggest architectural problem in the codebase.

#### 35+ Global Variables

Connection config, trading state, data caches, flags, timers — all as module-level globals. Every function mutates shared state. The code is:
- **Untestable** — can't instantiate isolated trading sessions
- **Thread-unsafe** — concurrent access to globals with no locks
- **Non-composable** — can't run multiple instances

```python
# Current: 35+ globals scattered across the file
global IP, PORT, CLIENTID, SUB_ACCOUNT_ID, fetchValue, candleTime, stockListDict, 
       stockList, dataInFile, EXPIRY, useAmount, MARKET_START_TIME, startTime, endTime,
       VWAP_ON_OFF, TRANSMIT, ORDER_EXPIRY_TIMER, USE_TIMER_IN_ORDER, CALL_DELTA_CHECK,
       PUT_DELTA_CHECK, VOLUME_CHECK, ATR_CHECKS, ACTIVE_VOLUME, MAX_CONTRACT_AMOUNT,
       ATR_VALUE, SHARE_VOLUME, BODY, perDayTrades, PROFIT_INCREMENT, 
       TRADE_COOLDOWN_SECONDS, profit_amount_day, loss_amount_day ...
```

**Recommended fix — `TradingSession` class:**

```python
class TradingSession:
    def __init__(self, config: TradingConfig):
        self.config = config
        self.client: TwsApiClient = None
        self.order_mgr: OrderManager = None
        self.event_queue = Queue()
        self.signal_dict: dict = {}
        self.trade_time_dict: dict = {}
        self.stop_trading = False
        # ... all state centralized here
```

#### 50-Line Global Injection in trading_engine.py

`_start_data_feed_and_strategies` (234 lines) sets BOT globals one by one:

```python
BOT.client = self._client
BOT.order_mgr = self._order_mgr
BOT.event_queue = self._event_queue
BOT.stockList = stock_list
BOT.TRADE_COOLDOWN_SECONDS = int(...)
BOT.PROFIT_INCREMENT = float(...)
# ... 40 more lines
```

Every new config parameter requires editing **4 files**: config.json, TradingConfig.from_dict, to_bot_config_dict, and this injection block.

#### Functions That Should Be Extracted

| New Module | Functions to Move | Lines |
|-----------|------------------|-------|
| `signal_detector.py` | `getCallPutEngulfCheck` | ~233 |
| `trade_executor.py` | `takeTrade`, `checkConditionsAndTrade`, `placeOrder` | ~410 |
| `risk_manager.py` | `pnl_watchdog_thread`, `getAndBuyAfterMarketEnd`, `squareOffAll`, `_zero_dte_entry_gate` | ~200 |
| `market_data.py` | `init_data_feed`, `get10StrikesNearUnderlying`, `getStockNearStrikes` | ~200 |
| `config_manager.py` | Config parsing from `main_call` | ~100 |
| `indicators.py` (merge) | `getATR`, `checkVWAPValue`, `resolve_atr_for_sl_tp`, `compute_sl_tp_from_price_and_atr` | ~150 |

#### Dead Code

| Code | Location | Type |
|------|----------|------|
| `checkVWAPValue_OLD` | L773-832 | Entire dead function |
| `account_pnl_monitor` | L2194-2215 | Dead function with triple `sys.exit` |
| `DAILY_LIMIT_HIT` | L64 | Declared, never read |
| Commented `__main__` block | L2436-2484 | 48 lines |
| 7 × dead candle variables | L565-607 | `candle_0_*` series |
| ~15 commented-out blocks | Various | Old logic, test code |

### 3.2 Thread Safety (CRITICAL)

**tws_api_client.py** has 13 caches. Only 2 are thread-safe:

| Cache | Lock? | Written By | Read By |
|-------|-------|-----------|---------|
| `nextValidOrderId` | ✅ `_lock` | `nextValidId` callback | `nextOrderId()` |
| `account_summary_cache` | ✅ `_lock` | `accountSummary` callback | `_emit_account_metrics` |
| `tick_cache` | ⚠️ Partial | `tickPrice` (locked) | `get_positions` (**no lock**) |
| `positions` | ❌ | `position` callback | `get_positions`, `_emit_positions` |
| `trades_cache` | ❌ | `orderStatus` callback | `process_trade` |
| `ticker_id` | ❌ | `nextTickerId` | Multiple |
| `history_cache` | ❌ | `historicalData` callback | `get_bars` |
| `allOrders`, `allOpenOrders` | ❌ | Multiple | Multiple |
| `openOrdersSymbol` | ❌ | `openOrder`, `orderStatus` | `checkConditionsAndTrade` |
| `ticker_id_contract_cache` | ❌ | `subscribe` | Multiple |
| `pnl_cache` | ❌ | `pnl` callback | `_emit_pnl_update` |

**Risk:** `RuntimeError: dictionary changed size during iteration` on the `positions` dict when `get_positions` iterates while `position()` callback modifies it.

### 3.3 OrderManager — God Class (915 lines)

Mixes 6 concerns in one class:
1. Order cache CRUD
2. Trade execution (placeOrder → TWS)
3. TP/SL evaluation logic
4. Database persistence
5. Position monitoring
6. UI event emission

Also has **circular imports**: `import BOT` inside methods to access globals (`trade_time_dict`, `SUB_ACCOUNT_ID`).

### 3.4 TWS Reconnection — Broken (FIXED this session)

`connectionClosed()` was defined twice. Python uses the last definition, so the reconnect handler was dead code. Fixed by removing the duplicate.

Remaining issue: heartbeat thread exits permanently on disconnect. After reconnect, no new heartbeat is started.

---

## 4. Rust Backend

### Assessment: Structurally Sound, Needs Polish

The Rust code is the best-organized layer. Tauri commands are clean, sidecar management works, IPC is correct.

### 4.1 Coarse AppState Mutex

Single `Arc<Mutex<AppState>>` for everything — trading, license, sidecar. ~28 lock acquisitions/sec during active trading. Not a problem today (no contention), but prevents future parallelism.

**Fix:** Split into `TradingState`, `LicenseState`, `SidecarState` with separate mutexes.

### 4.2 Error Handling — `Result<T, String>` Everywhere

All Tauri commands return `String` errors. No structured error types, no error codes.

**Fix:** Define `AppError` enum with `thiserror`. Frontend can then distinguish user errors from system errors.

### 4.3 Window Close Mid-Trade Bug

```rust
let is_trading = state_arc.try_lock().map(|app| { ... }).unwrap_or(false);
```

If the lock is held during a position_update, `try_lock()` fails → `unwrap_or(false)` → "not trading" → window closes → sidecar killed mid-trade.

**Fix:** Use `AtomicBool` for `is_trading`.

### 4.4 Log Buffer O(n) Removal

`Vec::remove(0)` shifts all 999 elements when buffer is full. ~7000 shifts/sec.

**Fix:** Use `VecDeque` for O(1) pop_front.

### 4.5 Position Matching — Float Comparison

```rust
(p.strike - pos.strike).abs() < 0.01
```

Works for standard options but could collide for micro options. Also allocates 2 new Strings per comparison (`norm_opt_right`, `norm_exp`).

---

## 5. React Frontend

### 5.1 The Re-Render Storm (CRITICAL Performance Issue)

Every `position_update` event (20/sec with 10 positions) calls `positionStore.updatePosition()` which creates a **new array** via `.map()`. This triggers re-renders of:

- `PositionsPage` (subscribes to `positions`)
- `TradeBlotter` (subscribes to `positions` for live enrichment)
- Every `PositionRow` (receives new object from the new array)

**Impact:** 20 full React reconciliations/sec across 3+ components, each running `useMemo` chains.

**Fixes applied this session:**
- PositionRow no longer calls `usePositions()` (eliminated store subscription)
- Close button calls `positionsApi.close()` directly

**Remaining fix needed:** Batch/throttle `updatePosition` to max 2-4/sec.

### 5.2 TradeBlotter — Subscribes to Full Positions Array

```typescript
const positions = usePositionStore((s) => s.positions);
```

Rebuilds Map + enriches trades + sorts on every tick. Should throttle to 1-2 Hz.

### 5.3 PnLSparkline — Recharts 10×/sec

PnL throttle is 100ms, so Recharts does 10 full SVG re-layouts per second. Should throttle chart renders to 0.5 Hz (the `useEffect` already gates history recording to 2s).

### 5.4 What's Working Well

- `useTradingEvents.ts` handles all 14 event types cleanly at app root
- No event listener leaks
- Zero polling — all data is push-based
- PnL throttling (100ms) is effective
- Log batching (150ms) reduces IPC volume
- Store caps (100 trades, 200 closed positions) prevent unbounded growth

---

## 6. Performance Hotspots

### Ranked by Impact (10 Active Positions)

| # | Layer | Issue | Current Cost | Fix | Improvement |
|---|-------|-------|-------------|-----|-------------|
| 1 | React | `updatePosition` → 20 re-renders/sec | 20 reconciliations/sec | Batch per frame or throttle to 2/sec | **90% fewer renders** |
| 2 | Python | 10 individual `emit_position` calls/0.5s | 20 JSON serialize + IPC/sec | Use `emit_positions_snapshot()` (exists, unused) | **80% fewer IPC** |
| 3 | React | Recharts re-renders 10×/sec | 10 SVG layouts/sec | Throttle to 0.5 Hz | **95% fewer charts** |
| 4 | Python | `get_positions` O(n²) per 0.5s | n² entry_order lookups/sec | Index by (symbol, strike, right, expiry) tuple | **O(n²) → O(n)** |
| 5 | React | TradeBlotter subscribes to positions (20×/sec) | 20 Map+sort+enrich/sec | Throttle subscription to 1-2 Hz | **90% less work** |
| 6 | Rust | `Vec::remove(0)` in log buffer | 7000 shifts/sec | Use `VecDeque` | **O(n) → O(1)** |
| 7 | Rust | Position matching: O(n) scan + String allocs | 400 allocs/sec | Use HashMap<PositionKey, Position> | **O(n) → O(1)** |
| 8 | Python | 50ms engine loop (18/20 iterations idle) | 20 iterations/sec | Increase to 200ms | **75% fewer iterations** |
| 9 | Python | 50-line log dump per TP/SL check | ~100 KB/sec I/O | Move to `logger.debug()` | **90% less log I/O** |

### Quick Win Calculation

Fixing #1, #2, and #3 alone would:
- Reduce React re-renders from ~40/sec → ~4/sec
- Reduce Python→Rust IPC from ~25/sec → ~5/sec
- Reduce chart renders from 10/sec → 0.5/sec
- **Total: ~85% reduction in wasted computation across the entire stack**

---

## 7. Improvement Roadmap

### Phase 1: Stability & Performance (1-2 weeks)

| ID | Priority | Task | Files |
|----|----------|------|-------|
| 1.1 | **P0** | Thread-safe caches in tws_api_client.py | `tws_api_client.py` |
| 1.2 | **P0** | Restart heartbeat thread after reconnect | `tws_api_client.py`, `trading_engine.py` |
| 1.3 | **P1** | Batch React position updates (throttle to 2/sec) | `positionStore.ts`, `useTradingEvents.ts` |
| 1.4 | **P1** | Switch `_emit_positions` to `emit_positions_snapshot` | `trading_engine.py` |
| 1.5 | **P1** | Throttle PnLSparkline to 0.5 Hz | `PnLSparkline.tsx` |
| 1.6 | **P1** | Throttle TradeBlotter position subscription | `TradeBlotter.tsx` |

### Phase 2: Code Quality & Refactoring (2-4 weeks)

| ID | Priority | Task | Files |
|----|----------|------|-------|
| 2.1 | **P0** | Create `TradingSession` class — move 35 globals | `BOT.py` |
| 2.2 | **P0** | Split BOT.py into 5 focused modules | `BOT.py` → 5 new files |
| 2.3 | **P0** | Replace 50-line global injection with session passing | `trading_engine.py`, `BOT.py` |
| 2.4 | **P1** | Remove circular `import BOT` from OrderManager | `order_manager.py` |
| 2.5 | **P1** | Extract exit strategy from OrderManager | `order_manager.py` → `exit_strategy.py` |
| 2.6 | **P1** | Replace blocking poll with Event/Future | `tws_api_client.py` |

### Phase 3: Polish (Ongoing)

| ID | Priority | Task | Files |
|----|----------|------|-------|
| 3.1 | **P2** | Rust: `AppError` enum instead of `String` errors | `src-tauri/src/commands/*.rs` |
| 3.2 | **P2** | Rust: Split `AppState` into sub-states | `src-tauri/src/state/` |
| 3.3 | **P2** | Rust: `AtomicBool` for `is_trading` | `lib.rs` |
| 3.4 | **P2** | Rust: `VecDeque` for log buffer | `commands/logs.rs` |
| 3.5 | **P2** | Clean up dead code (BOT.py, order_manager.py) | Multiple |
| 3.6 | **P2** | Fix `Tick` model (remove active_order, busy, locked) | `common.py` |
| 3.7 | **P2** | Unify duplicate model definitions | `common.py`, `engine/models.py` |
| 3.8 | **P3** | Add DB transaction boundaries in process_fill | `order_manager.py` |
| 3.9 | **P3** | Emergency close: check long/short before SELL | `BOT.py` |

---

## Appendix: Files Modified This Session

| File | Changes |
|------|---------|
| `src/hooks/useLicense.ts` | Tightened `isRevocationError`, removed all automated `invalidateLicenseState()` calls, removed expiry-based file deletion |
| `src-tauri/src/commands/license.rs` | Network-resilient `validate_license` with local fallback |
| `src/components/positions/PositionRow.tsx` | Pass expiry to close, remove store subscription (perf), add time column |
| `src/hooks/usePositions.ts` | Accept expiry in `closePosition` |
| `src/components/positions/PositionsPage.tsx` | Default sort by time, add Time sortable column |
| `tws_api_client.py` | Fix duplicate connectionClosed (reconnect was dead code), thread-safe nextOrderId, safe openOrdersSymbol.remove |
| `order_manager.py` | Null guard on process_fill, fix options_tick typo, add _close_position_direct fallback |
| `src-tauri/src/sidecar/manager.rs` | Drain PENDING_RESPONSES on sidecar termination |
| `src/components/dashboard/AccountSummary.tsx` | Remove redundant polling retries |
| `trading-engine/engine/trading_engine.py` | Improved demo simulation |
| `src/components/settings/SettingsPage.tsx` | Updated demo description and timeout |
| `src/components/dashboard/TradingControls.tsx` | Updated demo timeout |

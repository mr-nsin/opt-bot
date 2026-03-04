# Task Plans

---

# Emergency Stop UI Sync — Fix Plan

## Problem Summary

When the emergency stop button is clicked:

1. **Positions on TWS are closed** (via `getAndBuyAfterMarketEnd()` → MKT orders)
2. **App UI becomes stale**:
   - Positions page still shows open positions
   - Trades card still shows open trades
   - Realized/unrealized P&L and other metrics are not updated

## Root Cause Analysis

### Data Flow (Normal Operation)

| Data | Source | Consumer |
|------|--------|----------|
| Positions | Sidecar `position_update` + `trade_closed` | Rust `app.trading.positions`, React `positionStore` |
| Trades (today) | Sidecar `trade_executed` + `trade_closed` | React `tradingStore.todayTrades` |
| P&L (realized/unrealized) | Sidecar `pnl_update` | Rust `app.trading.daily_pnl`, React `tradingStore.dailyPnl` |
| Account metrics | Sidecar `account_metrics` | Rust + React stores |

### What Happens on Emergency Stop

1. **Engine**: `emergency_stop()` → `_close_all_orders_and_positions()` → `BOT.getAndBuyAfterMarketEnd()`
   - Places MKT orders to close each position
   - **Does not wait for fills** — immediately disconnects TWS and tears down

2. **Engine**: Destroys `_client`, `_order_mgr`, `_db` before fill callbacks can run

3. **Rust**: Waits 15s, kills sidecar, emits `sidecar-terminated`
   - `app.trading.positions` is **never cleared** (Rust expects `trade_closed` events to remove them)
   - `app.trading.daily_pnl`, `account_metrics` stay at last values

4. **React `sidecar-terminated` handler** (`useTradingEvents.ts`):
   - Resets: status, sidecarRunning, connectedToTws, signalScanning
   - **Does NOT**: clear positions, clear/stale trades, reset P&L, reset account metrics

5. **`getAndBuyAfterMarketEnd()`** places orders via `placeOrder()`; `trade_closed` is emitted only when the **exit order fills** in `order_manager`'s status callback. With TWS disconnected and order_mgr destroyed, those callbacks never run.

## Improvement Plan

### 1. Rust: Clear positions and reset state on emergency/stop

**File**: `src-tauri/src/commands/trading.rs`

- In `emergency_stop` (and optionally `stop_trading` when sidecar is killed):
  - After `kill_sidecar()`, before emitting `sidecar-terminated`:
  - Clear `app.trading.positions`
  - Optionally zero `app.trading.daily_pnl.unrealized` (positions gone), keep `realized` if desired
  - Optionally clear or null `app.trading.account_metrics`
- Ensures `get_positions` returns `[]` after emergency stop

### 2. Frontend: Clear stores on `sidecar-terminated`

**File**: `src/hooks/useTradingEvents.ts`

- In `sidecar-terminated` handler:
  - Call `usePositionStore.getState().clearAll()` — clears positions and closedPositions
  - Call `useTradingStore.getState().reset()` — or a new `resetOnTermination()` that:
    - Keeps todayTrades history but marks all open trades as closed (status: "closed", pnl: null?) OR clears todayTrades
    - Resets dailyPnl (at least unrealized → 0, or full reset)
  - Optionally clear accountMetrics

**File**: `src/stores/positionStore.ts`

- Ensure `clearAll()` exists (it does) and is invoked from the event handler.

### 3. Trades card behavior on emergency stop

**Options**:

- **A) Mark open trades as closed (unknown P&L)**: Preserve history, show "CLOSED" with "—" for P&L
- **B) Clear session trades**: Simpler, but loses visibility of what was open
- **C) Move open trades to closed with `pnl: null`**: Keep in blotter, user knows they were force-closed

**Recommendation**: Option C — add `updateTradePnl` overload or new action `markTradesClosedOnEmergency(matchAllOpen: true)` that sets `status: "closed"` and `pnl: null` for all open trades. TradeBlotter already handles missing P&L gracefully.

### 4. P&L and metrics

- **Unrealized P&L**: Must go to 0 (no positions)
- **Realized P&L**: Could keep last value or reset — keeping is more accurate if user had realized gains before emergency stop
- **Account metrics**: Stale after disconnect; either clear (show "—") or keep last value with a "stale" indicator. **Recommendation**: Keep last value, add subtle "as of stop" tooltip if needed.

### 5. Engine (optional enhancement)

**File**: `trading-engine/engine/trading_engine.py`

- Before disconnecting in `emergency_stop`, optionally:
  - Emit a bulk `positions_closed` or multiple `trade_closed` events for each position being closed (with `pnl: null` or best-effort estimate)
  - This requires the engine to know which positions were open at emergency time
- **Downside**: Engine tears down quickly; adding logic may delay disconnect. Simpler to fix in Rust/Frontend.

### 6. Stop Trading vs Emergency Stop

- **Stop Trading**: Leaves positions open; same `sidecar-terminated` is emitted. Positions should remain (user didn’t close them). Only clear if we decide stop_trading also kills sidecar without closing — current behavior leaves positions open.
- **Emergency Stop**: Closes all positions. Must clear UI state.

**Differentiation**: Pass payload `{ reason: "emergency_stop" | "stop_trading" }` on `sidecar-terminated`; frontend clears only when `reason === "emergency_stop"` (normal stop leaves positions open in UI).

## Checklist

- [x] **Rust**: In `emergency_stop`, clear positions, reset `daily_pnl.unrealized`; emit `sidecar-terminated` with `{ reason: "emergency_stop" }`
- [x] **Rust**: In `stop_trading`, emit `sidecar-terminated` with `{ reason: "stop_trading" }`
- [x] **Frontend**: In `sidecar-terminated`, when `reason === "emergency_stop"`: call `positionStore.clearAll()`
- [x] **Frontend**: When `reason === "emergency_stop"`: mark all open trades as closed (pnl: undefined) or clear todayTrades
- [x] **Frontend**: When `reason === "emergency_stop"`: set `dailyPnl.unrealized = 0`; optionally reset total/realized
- [x] **Trading store**: Add `markOpenTradesClosedOnEmergency()` for sidecar-terminated
- [ ] **Verification**: Click emergency stop with open positions → Positions page empty, Trades show closed, P&L unrealized = 0

## P&L / Positions Live Update (separate fix)

**Issue**: Position P&L and current price not updating continuously in Positions/Trades views.

**Root cause**:
1. Engine emits `position_update` every 5s; frontend polls `get_positions` every 5s
2. `get_positions` gets `current_price` from `order_id_tick_lookup` only; if tick missing (no matching entry order), PnL stays 0

**Fixes applied**:
- [x] Reduce engine `_positions_interval_sec` from 5 to 2 seconds
- [x] Add fallback: use `client.get_options_data()` (tick_cache) when `order_id_tick_lookup` has no tick
- [x] Reduce frontend poll interval from 5s to 2s in PositionsPage

**Note**: If P&L still shows 0, the option may not be subscribed for ticks (illiquid, or subscription gap). Consider reqPnLSingle for per-position PnL from TWS as future enhancement.

## Files to Modify

| File | Change |
|------|--------|
| `src-tauri/src/commands/trading.rs` | Clear positions, reset P&L state in emergency_stop |
| `src/hooks/useTradingEvents.ts` | Clear positionStore, update tradingStore on sidecar-terminated |
| `src/stores/tradingStore.ts` | Add `markOpenTradesClosedOnEmergency()` or extend reset |
| `src-tauri/src/state/trading_state.rs` | No struct change; ensure positions can be cleared |

---

# Monitor Positions & Exit Conditions — Fix Plan

## 1. Flow Summary

### Start Trading → Signal Detection → Orders
- **engine.start()** → connects TWS → ** _start_data_feed_and_strategies()**
- **init_order_requests()** → reqPositions, reqAllOpenOrders, reqPnL
- **init_data_feed()** → subscribes STK + OPT (near-ATM strikes)
- **synchronize_orders()** → syncs filled orders to entry_orders_cache, subscribes OPT for active trades
- **event_processor threads** (4) → consume event_queue: STK ticks → getCallPutEngulfCheck → checkConditionsAndTrade → takeTrade → placeOrder
- **monitor_positions_loop** → get_all_positions() → for each pos: check_exit_conditions(pos)
- **pnl_watchdog_thread** → checks daily P&L limits

### Exit Paths (two)
1. **Event path**: OPT tick arrives with `active_order` → event_processor → check_and_close_position(tick)
2. **Monitor path**: monitor_positions_loop → get positions → check_exit_conditions(pos) → find order+tick → check_and_close_position(tick)

### Root Causes (Positions Not Closing)
- **option_tick is None**: No matching entry order for position (expiry mismatch, symbol/strike/right mismatch, or order not in cache)
- **Expiry format mismatch**: order.expiration "2026-03-06" vs pos.expiry "20260306" — need normalize
- **Sequential loop**: 10–20 positions checked one-by-one every 0.1s — can parallelize
- **Insufficient logging**: Hard to debug when/why exit checks fail

## 2. Implementation Checklist

- [x] Fix expiry normalization in check_exit_conditions (order_manager._norm_expiry)
- [x] Add float strike tolerance (0.01) for matching
- [x] Add diagnostic logs when option_tick is None (logger.debug with position + cache sizes)
- [x] Add synchronize_positions to engine startup (was commented in main_call)
- [x] Fix synchronize_positions: normalize expiry/right when matching, use exp_for_contract for subscribe
- [x] Parallelize monitor_positions_loop with ThreadPoolExecutor (max 8 workers)
- [x] Add periodic heartbeat log every 30s when positions > 0
- [x] Reduce log noise: EXIT already placed / Order not filled → DEBUG
- [x] Improve "No valid price" log with actual values

## 3. Verification

- Run engine with open positions; check logs for "Position monitor", "Position synchronized", "TAKE PROFIT CHECK", "HIT TakeProfit"
- Set log level to DEBUG to see "no matching entry order" when positions lack managed orders

## 4. 10+ Positions — How It Works

### Parallel execution (not one-by-one)
- `monitor_positions_loop` uses `ThreadPoolExecutor` with `max_workers = min(16, pos_count)`
- 10 positions → 10 workers, all checked in parallel (one batch)
- 20 positions → 16 workers, two batches (~20ms total vs 2000ms sequential)
- Loop runs every 0.1s; all positions checked each iteration

### Changes for scale
- `log_order_status` throttled to once per 30s per order (was every 0.1s → 100 logs/sec with 10 positions)
- `log_order_status` switched to DEBUG level (enable when troubleshooting)
- `max_workers` raised from 8 to 16 for 10–20 positions

### Dual path (redundancy is intentional)
1. **Event path**: OPT tick arrives → `event_processor` → `check_and_close_position` (reactive)
2. **Monitor path**: Every 0.1s → each position → `check_exit_conditions` → `check_and_close_position` (proactive)
- `tick.busy` prevents concurrent execution; both paths can trigger closes
- Illiquid options with few ticks still get monitored via the loop

## 5. Additional Improvements (Latest)

- [x] close_position: Revert order.exit_placed=False when placeOrder fails (allows retry)
- [x] close_position: Validate executed_qty > 0 before placing close order
- [x] close_position: Normalize expiry when rebuilding contract from DB
- [x] _find_entry_order: Use 0.01 strike tolerance (was exact float match)
- [x] placeAndVerifyOrder: Guard against options_tick is None
- [x] del_entry_order: Clean up _log_status_last when order removed

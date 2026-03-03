# Issues Roadmap — Sidecar vs Standalone Parity & UI

## Summary Tables

### P0 Critical Issues (Implement First)

| # | Issue | File | Status | Effort |
|---|-------|------|--------|--------|
| P0-1 | Duplicate event processors on TWS reconnect | trading_engine.py | ✅ Done | Medium |
| P0-2 | config.json not overwritten when exists | trading_engine.py | ✅ Done | Low |
| P0-3 | entry_orders_cache key collision (multi-position same symbol) | order_manager.py | ✅ Done | High |
| P0-4 | Close position API — symbol only (needs strike/right) | Multiple | ✅ Done | Medium |

### Signal Grid UI — Current vs Required

| Field | Backend Sends | UI Shows | Status |
|-------|---------------|----------|--------|
| Symbol | ✓ | ✓ | ✓ |
| Direction (CALL/PUT) | signal_type | ✓ | ✓ Fixed (was UNKNOWN) |
| Price | ✓ | ✓ | ✓ |
| Strike | ✓ | ✓ | ✓ Done |
| Timestamp | ✓ | ✓ (full date+time) | ✓ Done |
| Strength/Reason | reason | ✓ as badge | ✓ |
| Indicator | — | "SuperTrend" | ✓ |
| Expiry | ✓ | ✓ when available | ✓ Done |

### Stop vs Emergency Stop

| Action | Orders | Positions | Status |
|--------|--------|-----------|--------|
| Stop Trading | Cancel | Leave open | ✅ Done |
| Emergency Stop | Cancel | Close all at market | ✅ Done |

### P1/P2/P3 Issues

| Priority | Issue | File | Status |
|----------|-------|------|--------|
| P1 | timeCheckAndCloseProgram not in sidecar loop | trading_engine.py | 🔴 Open |
| P1 | Expiry format mismatch in check_exit_conditions | order_manager.py | 🔴 Open |
| P2 | updateTradePnl format verification | tradingStore, useTradingEvents | ⚠️ Verify |
| P3 | Dead _process_event, docstrings, etc. | Various | 🔴 Open |

---

## 1. UNKNOWN Issue — **FIXED**

**Fix applied:** useTradingEvents sets `direction: signalType`; SignalActivity uses `resolveDirection()`.

---

## 2. Signal Grid — **DONE**

**Current:** Grid shows Symbol, Direction, Strike, Price, Expiry, Strength, Indicator, full Date/Time.

**Implemented:** All session signals and executed trades display in a grid with timestamp, signal info, price, strike, expiry (when available), and every detail.

---

## 3. P0 Fix Details

### P0-1: Duplicate Event Processors on Reconnect
- On disconnect: stop event processor threads.
- On reconnect: re-run init + data feed only; do NOT start new processor threads.

### P0-2: config.json Not Overwritten
- Always overwrite config.json with `self.config.to_bot_config_dict()` before importing BOT.

### P0-3: entry_orders_cache Collision
- Key by `option_symbol` or `(symbol, strike, right, expiry)`.
- Update add_entry_order, del_entry_order, get_entry_order, close_position_by_symbol, check_exit_conditions.

### P0-4: Close API Needs strike/right
- Extend `close_position(symbol, strike?, right?)`.
- Update order_manager, Rust command, UI PositionRow.

---

## 4. Stop vs Emergency Stop — **DONE**

**Stop Trading:** Cancels all open orders. Positions **remain open** — user can close manually via Positions UI or Close All.

**Emergency Stop:** Cancels all orders and **closes all positions** at market price, then disconnects.

**Implementation:** `_cancel_orders_only()` for stop; `_close_all_orders_and_positions()` for emergency stop (trading_engine.py).

---

## 5. Positions & Analytics Status

| Component | Status |
|-----------|--------|
| Positions (open) | ✓ position_update + get_positions |
| Positions (closed) | ✓ trade_closed |
| Analytics (todayTrades) | ✓ trade_executed + updateTradePnl |
| Trade Blotter | ✓ Same flow |

---

## 6. Verification Checklist

- [x] Signals show CALL/PUT with price, strike, timestamp, expiry in grid
- [ ] TWS reconnect → no duplicate processing (P0-1 implemented)
- [ ] Config change → Start uses new config (P0-2 implemented)
- [ ] Multiple SPY positions → Close targets correct one (P0-3, P0-4 implemented)
- [ ] Trade executed/closed → Positions + Analytics update
- [x] Stop Trading → positions left open; Emergency Stop → closes all

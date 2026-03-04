# Deep Analysis: Logs, Signals, P&L, Notifications, Session Metrics

**Date:** Mar 4, 2026

## 1. Signals Generated When Market is Closed

### Root Cause
**No market-hours check before signal emission.**

- **Flow:** `event_processor` receives STK tick → `getCallPutEngulfCheck(stock)` → fetches 21 bars via `client.get_bars()` → runs SuperTrend → if signal flips (last_signal ≠ current_signal), emits signal via `_emit_signal()`.
- **Market check:** `timeCheckAndCloseProgram()` is only called inside `checkAlgoAndTrade()` and `checkConditionsAndTrade()` — i.e. **before placing a trade**, not before scanning or emitting signals.
- **When market closed:** IB can still provide:
  - Stale tick data (last known prices)
  - Historical bars from `get_bars` (previous session's closed candles)
  - SuperTrend can flip on that data → signal emitted
- **Result:** Signals are emitted and shown in Activity/Signals tab even when the market is closed. The user sees many signals (13 in <2 min) because each tick triggers a full SuperTrend recompute; when bars don't change, repeated ticks can still cause apparent "flips" if using slightly different candle sets or edge cases.

### Fix
Add a market-hours gate **before** running signal logic in `event_processor` (STK branch). Use the same `endTime` / `startTime` from config as `timeCheckAndCloseProgram`. If outside hours, skip `getCallPutEngulfCheck` and do not emit signals.

---

## 2. Unrealized P&L Discrepancy (395.16 vs -395.2)

### Analysis
- **TWS:** Sends `pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)` → `pnl_cache` in tws_api_client.
- **Engine:** `_emit_pnl_update()` reads `cache["unrealized"]` and emits via `emit_pnl(unrealized=...)`.
- **Frontend:** `trading:pnl_update` → `dailyPnl.unrealized` → `formatCurrency()` displays.
- **Sign:** `formatCurrency(-395.16)` produces `-$395.16` (Intl.NumberFormat preserves sign). Both app and TWS show negative — no sign bug.
- **Difference 0.04:** Likely rounding (we round to 2 decimals) or timing (different moments). Minor and acceptable.

---

## 3. Log Issues (from Logs Page)

| Issue | Cause | Severity |
|-------|-------|----------|
| Signal volume when market closed | No market-hours gate before signal scan | High |
| TWS disconnected vs Data Feed Connected | Sidebar shows engine/TWS status; Data Feed shows tick subscription status — can diverge during reconnect | Medium |
| Same symbol+direction signal spam | 60s throttle exists per `_sig_key`; multiple symbols still emit | Low |

---

## 4. Notification Pop-up: Orders Only, Not Signals

### Current Behavior
- `signal_detected` → `addToast` when `settings.show_notifications`
- `trade_executed` → `addToast` when `settings.show_notifications`
- `trade_closed` → `addToast` when `settings.show_notifications`

### Desired
- **Orders only:** trade_executed, trade_closed → toast
- **Signals:** no toast (signals still show in Activity/Signals tab)

### Fix
Remove `addToast` from `trading:signal_detected` handler in `useTradingEvents.ts`. Keep toasts for `trade_executed` and `trade_closed`.

---

## 5. Session P&L vs Manual Trades (Deep Analysis)

### Current State
- **Source:** TWS `reqPnL` → account-level `daily`, `unrealized`, `realized`.
- **No separation:** TWS does not distinguish bot vs manual trades. All P&L is mixed.

### Options to Separate

| Approach | Pros | Cons |
|----------|------|------|
| **A. Session delta** | Store `session_start_pnl` when engine starts; show `current - session_start` as "Session P&L" | Manual trades during session still included |
| **B. Bot-only trades** | Track only trades from `trade_executed`/`trade_closed`; sum their PnL | Ignores manual trades; realized from TWS includes manual |
| **C. Hybrid** | Session start snapshot + only count bot-originated closed trades for "Session Realized" | Complex; unrealized still includes manual positions |

### Recommendation
Implement **A** as phase 1: add `sessionPnlDelta = current_total - session_start_total` when engine starts. Add a "Session P&L" card. Later, add option to show "Bot Trades" PnL derived from `todayTrades` (only trades we placed/closed).

---

## 6. Position Closure in DB (Monitor Loop / Emergency)

### Current Flow

**Monitor loop / TP-SL hit:**
1. `order_mgr.check_and_close_position(tick)` or `check_exit_conditions(pos)` → places MKT close order.
2. On fill → `orderStatus` callback → `process_fill()` → `_emit_trade_closed()` → `db.delete(entry_order)`, `db.delete(exit_order)`.
3. **DB:** Entry and exit orders removed from `option_orders` table.

**Emergency stop:**
1. User clicks Emergency Stop → Rust kills sidecar.
2. `sidecar-terminated` with `reason: "emergency_stop"` → frontend: `clearAll()` positions, `markOpenTradesClosedOnEmergency()`.
3. **DB:** No close orders placed. Entry orders remain in DB. Positions may still exist on TWS.
4. **Gap:** If user had open positions, they are not closed on TWS. DB still has entry orders. On next start, TWS will show positions; we'd need to reconcile.

**`getAndBuyAfterMarketEnd` / `check_and_close_all_open_positions`:**
- Places MKT orders to close all positions.
- When those fill → same `process_fill` path → DB deletes.

### Verdict
- **Monitor loop / EOD close:** Positions closed correctly; DB orders deleted on fill.
- **Emergency stop:** Positions NOT closed on TWS; DB entry orders remain. UI marks trades "closed" for display only. Document this behavior.

---

## Summary of Fixes to Implement

1. **Market-hours gate** before signal scan (BOT.py event_processor)
2. **Remove signal toast** — keep only order toasts (useTradingEvents.ts)
3. **Session P&L** — phase 1: store session start PnL, add Session card (future)
4. **Document** emergency stop behavior (positions not closed on TWS)

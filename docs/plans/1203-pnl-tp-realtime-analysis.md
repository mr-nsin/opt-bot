# P&L Discrepancy, TP Not Closing, and Real-Time Data — Analysis

**Date:** 2026-03-12  
**Status:** Analysis only (no code changes; system is running)

---

## 1. TSLA P&L Discrepancy: -37 vs -35

### Observed Behavior
- **TWS/IBKR (or external source):** Shows -$37 for TSLA Mar13'26 397.5 CALL
- **Our app (CLOSED table):** Shows -$35.00 for the same closed trade

### Root Cause Analysis

**Our app's P&L calculation** (`order_manager.py` lines 386–410):

```python
# In process_fill() when exit order fills:
entry_avg = entry_order.average_price if entry_order else 0
exit_avg = order.average_price if order.average_price else 0
trade_pnl = (exit_avg - entry_avg) * order.executed_qty * 100 if entry_avg > 0 else 0

_emit_trade_closed({
    ...
    "pnl": float(trade_pnl),
    "entry_price": float(entry_avg),
    "exit_price": float(exit_avg),
    ...
})
```

**Formula:** `(exit_price - entry_price) × quantity × 100`  
- No rounding before emission  
- No commissions or fees included  
- Uses `order.average_price` from the fill (may differ from limit price due to slippage)

**TWS/IBKR P&L** (from `pnl()` callback, `pnl_cache`):
- Includes commissions and fees
- Uses IBKR’s own cost basis and realized P&L logic
- Per-contract and per-trade calculations can differ from a simple (exit − entry) × 100

### Likely Explanation
The ~$2 gap (-35 vs -37) is consistent with:
- Option commissions (e.g. ~$0.65–$1 per contract per leg)
- Fees (regulatory, exchange, etc.)
- Slight differences in fill price vs. our stored `average_price`

### Recommendation
- **Option A:** Use TWS/IBKR realized P&L when available (e.g. from `pnlSingle` or execution report) instead of our formula.
- **Option B:** Keep our formula but document that it excludes commissions; add a note in the UI.
- **Option C:** Add commission/fee fields to the close flow if IBKR provides them, and include them in our P&L.

---

## 2. SPY TP Not Closing When Current ($1.87) > TP ($1.86)

### Observed Behavior
- SPY CALL $669.0: Current $1.87, TP $1.86, position still open
- User expects: close when current ≥ TP

### Root Cause: Trailing Take-Profit Logic

The system uses **trailing take-profit**, not a simple “hit TP and close” rule.

**Logic** (`order_manager.py` `check_take_profit`, lines 716–744):

1. **First time price ≥ target:**  
   - Set `profit_trigger = True`  
   - Raise target: `current_profit_price = exit_price + profit_increment`  
   - Do **not** close; return

2. **Close only on pullback:**  
   - Close when `profit_trigger` AND `exit_price < (current_profit_price - profit_increment)`

**Example (SPY):**
- Initial TP: $1.86  
- Current/bid: $1.87 → price ≥ $1.86  
- Trailing activates: new target = $1.87 + increment (e.g. $0.03) = $1.90  
- Position stays open until price drops below $1.90 − $0.03 = $1.87

So when current is $1.87 and TP shows $1.86, the **displayed TP** is the **initial** target. The **effective** target has already been raised by trailing.

### UI vs. Backend

**Backend** (`trading_engine.py` lines 325–327, 390–391, 1144–1147):

```python
pos_data["profit_price"] = round(float(entry_order.current_profit_price or entry_order.profit_price or 0), 2)
if getattr(entry_order, "profit_trigger", False):
    pos_data["trailing_active"] = True
```

- `profit_price` in the payload is `current_profit_price` (trailing target) when available.
- `trailing_active` is set when trailing has been triggered.

**Frontend** (`PositionRow.tsx` lines 97–101, 175–179):

- Shows `TP $X.XX` with `↺` when `trailing_active` is true.
- Label: "Take Profit (trailing)" in details.

### Possible Issues

1. **Stale `profit_price` in UI**  
   - `position_update` runs every 1s (`_positions_interval_sec`).  
   - If `current_profit_price` is updated in the DB but not yet reflected in `get_positions()` or the event, the UI can show an outdated TP.

2. **DB update timing**  
   - `order_manager.py` line 734: `self.db.update(order=order)` after raising the trailing target.  
   - `get_positions()` reads from `entry_orders_cache` (in-memory), which is updated in the same process.  
   - So the engine should have the latest `current_profit_price` when it emits `position_update`.

3. **Event vs. display**  
   - If `trailing_active` is true but `profit_price` still shows the old value, the UI may be using cached or stale data.

### Recommendation
- Confirm that `position_update` events carry the latest `current_profit_price` after each trailing update.
- Add logging when `profit_price` / `current_profit_price` changes so we can verify the UI receives updates.
- Consider a “Simple TP” mode: close on first hit of initial TP, without trailing (as noted in `tasks/LOGS_ORDER_PLACE_TP_SL_analysis.md`).

---

## 3. P&L and Other Data Showing Delayed

### Current Intervals

| Data              | Source                    | Interval      | Location                                      |
|-------------------|---------------------------|---------------|-----------------------------------------------|
| Position updates  | `_emit_positions()`       | 1.0 s         | `trading_engine.py` line 58, 1031              |
| P&L (daily, etc.) | `_emit_pnl_update()`     | 1.0 s throttle| `trading_engine.py` line 62, 1104              |
| P&L frontend      | `pnl_update` handler     | 1.0 s throttle| `useTradingEvents.ts` line 9, 76–89            |
| Account metrics   | `_emit_account_metrics()` | 5.0 s         | `trading_engine.py` line 54                    |
| Data status       | `_emit_data_status()`     | 5.0 s         | `trading_engine.py` line 53                    |

### Why It Feels Delayed

1. **1 s for positions and P&L**  
   - In fast markets, 1 s can feel laggy.  
   - Throttling was added to cut IPC volume (~95% fewer emissions).

2. **TWS as source of truth**  
   - `pnl_update` comes from TWS `pnl()` callback.  
   - TWS updates asynchronously; we only forward what we receive.

3. **Position prices**  
   - `current_price` comes from `order_id_tick_lookup` or `get_options_data()`.  
   - No real-time tick stream to the UI; we rely on periodic snapshots.

4. **Frontend P&L throttle**  
   - `PNL_THROTTLE_MS = 1000` batches updates.  
   - First update flushes immediately; later ones are delayed up to 1 s.

### Options for More Real-Time Behavior

| Option                         | Effort | Effect                                      |
|--------------------------------|--------|---------------------------------------------|
| Reduce `_positions_interval_sec` to 0.5 s | Low    | Faster position/price updates               |
| Reduce `_pnl_throttle_sec` to 0.5 s      | Low    | More frequent P&L updates                   |
| Reduce `PNL_THROTTLE_MS` to 500 ms        | Low    | Faster P&L display                          |
| Add `tick_update` stream to UI            | High   | True real-time prices (needs new pipeline)  |
| Use WebSocket for TWS data                 | High   | Depends on TWS/IBKR API support              |

### Recommendation
- Start with lowering intervals to 0.5 s for positions and P&L.  
- Monitor IPC and CPU impact before going lower.  
- Real-time tick streaming would require a larger design change.

---

## 4. SPY Stop Loss Not Hit (Current $0.61 < SL $0.94)

### Observed Behavior
- SPY CALL $671.0, exp 20260312: Entry $1.52, Current $0.61, SL $0.94
- Current ($0.61) is **below** Stop Loss ($0.94) — SL should have triggered for a long call
- Position remains open; P&L -$182 (-59.9%)

### Root Cause Analysis

**SL logic** (`order_manager.py` `check_stop_loss`, lines 774–834):

- **Long:** `exit_price = option_tick.bid` (or `last` if bid ≤ 0); close when `exit_price <= order.stoploss_price`
- If bid = $0.61 and SL = $0.94 → $0.61 ≤ $0.94 is TRUE → SL should fire

**SL is only evaluated when `check_and_close_position` runs.** That happens via two paths:

| Path | Trigger | Requirement |
|------|---------|-------------|
| **1. event_processor** | IBKR sends tick (bid/last) for OPT | `tick.active_order` must be set |
| **2. monitor_positions_loop** | Every 0.1 s | Entry in `entry_orders_cache` and tick in `order_id_tick_lookup` |

### Likely Causes (Why SL Didn’t Fire)

1. **No matching entry order**  
   - `check_exit_conditions` (monitor path) returns early with "Position X: no matching entry order".  
   - Happens when: position opened manually in TWS, before app restart without sync, or from another app.  
   - `synchronize_positions` is commented out in standalone BOT (line 2627); only trading engine runs it.

2. **No tick in `order_id_tick_lookup`**  
   - `check_exit_conditions` returns early with "matched order but NO TICK".  
   - Tick is added in `add_entry_order` when placing order. If option was never subscribed or subscription failed, `order_id_tick_lookup[order.id]` is empty.  
   - `get_options_data()` fallback is used for UI display, but TP/SL logic uses `order_id_tick_lookup` only.

3. **Invalid price data**  
   - `check_and_close_position` returns early if `tick.last <= 0 and tick.bid <= 0`.  
   - If tick has stale -1 values (no recent `tickPrice` from IBKR), TP/SL is skipped.  
   - Illiquid options or snapshot-only subscriptions can leave bid/last at -1.

4. **Order not filled**  
   - Early return if `order.order_status != "filled"`.  
   - Unlikely if position is open in TWS.

5. **Exit already placed**  
   - Early return if `order.exit_placed == True`.  
   - If a prior close attempt failed (e.g. TWS reject) but `exit_placed` was set, we would skip further checks.

6. **Event path: `tick.active_order` not set**  
   - Event path only runs when OPT tick arrives with `tick.active_order` set.  
   - Set in `placeOrder`, `synchronize_positions`, or `check_exit_conditions` (monitor path).  
   - If position never went through those flows, event path never runs for it.

### Data Flow Summary

```
monitor_positions_loop (every 0.1s)
  → get_all_positions() [TWS]
  → for each pos: check_exit_conditions(pos)
       → _find_entry_order(symbol, strike, right, expiry)
       → if no match: "no matching entry order" → return
       → option_tick = order_id_tick_lookup.get(entry_order.id)
       → if None: "matched order but NO TICK" → return
       → option_tick.active_order = entry_order
       → check_and_close_position(tick=option_tick)
            → check_take_profit() [runs first]
            → if not order.exit_placed: check_stop_loss()
```

### Recommendation

1. **Check logs** for this position (SPY 671C 20260312):  
   - "Position SPY 671 ...: no matching entry order"  
   - "Position SPY 671 ...: matched order but NO TICK"  
   - "STOPLOSS CHECK - Order(...) SPY... Exit: $X.XX ... StopLoss: $0.94"

2. **If "no matching entry order":**  
   - Ensure `synchronize_positions` runs on connect (trading engine does; standalone BOT has it commented out).  
   - Consider syncing pre-existing TWS positions into `entry_orders_cache` and subscribing to options so TP/SL can run.

3. **If "NO TICK":**  
   - Verify option is subscribed (not snapshot-only).  
   - Ensure `add_entry_order` receives a valid tick when the order is placed/synced.

4. **If tick has invalid prices:**  
   - Add fallback: when `order_id_tick_lookup` has a tick with bid/last ≤ 0, call `get_options_data()` for a fresh quote before skipping TP/SL.

5. **Add heartbeat logging** when positions exist but TP/SL checks are skipped (e.g. log reason: no match, no tick, invalid prices).

---

## 5. Log Analysis: SPY 671 SL Not Hit (2026-03-12)

**Log file:** `C:\Users\cloudbase-admin\AppData\Roaming\quantdrift\logs\bot_2026-03-12.log`

### Timeline

| Time | Event |
|------|-------|
| 16:42:57 | Order 22236 created: SPY 671C, Entry ~$1.52, TP $1.78, SL $0.94 |
| 16:43:52 | Order filled: avg $1.52, TP/SL checks start |
| 16:43:52–16:46:40 | TP/SL checks run continuously; bid ranges $1.46 → $1.17 |
| 16:46:40 | **Last STOPLOSS CHECK:** Exit $1.17, Bid $1.17, SL $0.94 → $1.17 > $0.94, no close |
| 16:46:48 | **Square off** (getAndBuyAfterMarketEnd): 4 positions closed, including SPY 671 (order 22241) |
| 16:46:52 | Position 671 → 0; order 22241 filled |

### Root Cause

1. **SL never triggered:** The bid never reached or went below $0.94 in the tick stream. The lowest bid seen was **$1.17** at 16:46:40. The condition `exit_price <= $0.94` was never true.

2. **Position closed by Square off:** The position was closed by **getAndBuyAfterMarketEnd()** (Square off) at 16:46:48, not by SL. That flow is triggered when:
   - Daily PnL limit is hit (`pnlData <= loss_amount_day` or `pnlData >= profit_amount_day`), or
   - Market end time, or
   - Square off button.

3. **Price vs. UI:** If the UI showed Current $0.61, that might have come from:
   - A different source (e.g. TWS position update or another feed) after the last tick we used for TP/SL
   - A drop to $0.61 after 16:46:40 but before Square off, with no tick received before the Square off at 16:46:48

### Evidence from Logs

- No `"HIT STOPLOSS"` for order 22236.
- No `"no matching entry order"` or `"matched order but NO TICK"` — monitoring was active.
- Lowest bid for SPY 671: **$1.17** (16:46:40).
- Square off: `"Square off [1st][4/4]: SPY20260312C671.0 — orderId=22241 PLACED"`.

### Conclusion

The SL was not hit because the bid price in our tick stream never reached $0.94. The position was closed by the Square off flow instead of by SL. If the market traded below $0.94, we either did not receive those ticks or the Square off closed the position before the next SL check could run.

---

## 6. Fixes Applied (2026-03-12)

### Fix 1: get_options_data fallback when NO TICK

**Problem:** When `order_id_tick_lookup` has no tick for an entry order (e.g. after restart, tick never stored), `check_exit_conditions` returns early with "matched order but NO TICK" and TP/SL never runs. The UI can still show the position (using `get_options_data` fallback) but the bot does not close it.

**Fix:** In `check_exit_conditions`, when `option_tick is None`, call `api_client.get_options_data(symbol, expiry, right, strike)` to obtain a tick. If found, use it for TP/SL and store it in `order_id_tick_lookup` for future checks.

**File:** `order_manager.py`

### Fix 2: Enable synchronize_positions in standalone BOT

**Problem:** In standalone BOT `main_call`, `synchronize_positions()` was commented out. TWS positions from before restart (or from DB) were never synced into `entry_orders_cache` and `order_id_tick_lookup`. Result: "no matching entry order" for monitor path; TP/SL never runs.

**Fix:** Uncomment `synchronize_positions()` so TWS positions are synced to managed orders and ticks on startup.

**File:** `BOT.py`

### Remaining consideration: Stale tick when IBKR stops sending updates

When an option becomes illiquid (e.g. 0DTE near expiry), IBKR may stop sending `tickPrice` updates. The tick in `order_id_tick_lookup` then holds the last received price. If the real market drops below SL but we never receive that tick, SL will not trigger. A future enhancement could request a periodic `reqMktData` snapshot when the tick has not been updated for N seconds.

---

## Summary Table

| Issue                    | Root Cause                                      | Suggested Fix                                      |
|--------------------------|-------------------------------------------------|----------------------------------------------------|
| TSLA -37 vs -35          | Our P&L excludes commissions; TWS includes them | Use TWS P&L or add commission handling             |
| SPY TP not closing      | Trailing TP raises target; close on pullback     | Verify UI gets latest `current_profit_price`       |
| SPY SL not hit           | TP/SL never runs: no entry, no tick, or bad prices | Sync positions; ensure tick; add price fallback   |
| Delayed P&L/data         | 1 s throttles on engine and frontend            | Reduce to 0.5 s; consider tick stream long-term    |

---

## Files Referenced

- `order_manager.py` — P&L calc, `check_take_profit`, `check_stop_loss`, `process_fill`, `_emit_trade_closed`, `check_exit_conditions`
- `trading_engine.py` — `_emit_positions`, `_emit_pnl_update`, intervals
- `BOT.py` — `event_processor`, `monitor_positions_loop`, `synchronize_positions`
- `docs/POSITION_MONITORING_FLOW.md` — TP/SL paths and requirements
- `useTradingEvents.ts` — `pnl_update` throttle
- `PositionRow.tsx` — TP display, `trailing_active`
- `tws_api_client.py` — `pnl()` callback, `pnl_cache`

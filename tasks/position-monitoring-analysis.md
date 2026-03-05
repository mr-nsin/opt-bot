# Position Monitoring & TP/SL Analysis

## 1. When Does `monitor_positions_loop` Start?

**Not at app start.** The position monitor starts only when:

1. User clicks **"Start Trading"**
2. Sidecar (trading engine) spawns and connects to TWS
3. `_start_data_feed_and_strategies()` runs when `self.connected and not self._data_feed_started`
4. After `init_order_requests()`, `init_data_feed()`, `synchronize_positions()`, `synchronize_orders()`
5. Then starts: event processors, pnl_watchdog, **monitor_positions_loop**

**Flow:** Start Trading → TWS connected → data feed init → `monitor_positions_loop` thread starts.

---

## 2. Logs Printed

| Log | Level | When |
|-----|-------|------|
| `"Position monitor thread started"` | INFO (logger) | When thread starts |
| `"Position monitor thread started — checking TP/SL on open positions"` | INFO | Same, via _emit_log |
| `"Position monitor: N open position(s) — checking TP/SL"` | INFO (logger) | Every 30s when pos_count > 0 |
| `"Monitor: N position(s) under TP/SL check"` | **DEBUG** | Same — **NOT sent to UI** (DEBUG skipped) |
| `"TAKE PROFIT CHECK - Order(...)"` | INFO | Every TP check (every ~100ms when position exists) |
| `"Position X: no matching entry order or tick"` | **DEBUG** | When check_exit_conditions fails to match — **NOT visible in UI** |

**Problem:** Critical diagnostic logs (no match, no tick) are DEBUG and do not appear in the UI. Only INFO/WARN/ERROR do.

---

## 3. TP/SL Flow

```
monitor_positions_loop (every 0.1s)
  → client.get_all_positions()
  → for each position: order_mgr.check_exit_conditions(pos)
       → Find order in entry_orders_cache (symbol, strike, right, expiry match)
       → Get tick from order_id_tick_lookup[order.id]
       → If both found: check_and_close_position(tick)
         → Requires: tick.active_order, !order.exit_placed, order.order_status == "filled"
         → Requires: tick.last > 0 or tick.bid > 0
         → check_take_profit() then check_stop_loss()
```

**Alternative path:** event_processor — when OPT tick arrives with `tick.active_order` set → `check_and_close_position(tick)`.

---

## 4. Root Causes for TP/SL Not Firing

### A. No matching order in `entry_orders_cache`

**When:** `check_exit_conditions` iterates `entry_orders_cache` but no order matches the position.

- **Position** from TWS: `symbol`, `expiry` (e.g. `20260306`), `right` (C/P), `strike`
- **Order** has: `symbol`, `expiration` (e.g. `2026-03-06`), `right` (CALL/PUT), `strike`
- Matching uses `_norm_expiry()` — should handle both formats.

**Possible causes:**
- Order was never added (e.g. add_entry_order not called or failed)
- Expiry/symbol/strike/right mismatch
- Order was removed (e.g. `del_entry_order` called incorrectly)

**Current symptom:** Logged at DEBUG only:  
`"Position X no matching entry order or tick (entry_orders=N, tick_lookup=M)"`

---

### B. No tick in `order_id_tick_lookup`

**When:** Order is found but `order_id_tick_lookup.get(order.id)` is `None`.

- Tick is set in `add_entry_order(order, option_tick)`.
- If `add_entry_order` ran without a tick, or tick was never subscribed, lookup is empty.

**Current symptom:** Same DEBUG log as above.

---

### C. Invalid tick prices (`last` and `bid` are -1 or 0)

**When:** `check_and_close_position` exits early:

```python
if tick.last <= 0 and tick.bid <= 0:
    logger.warning(f"No valid price (last={tick.last} bid={tick.bid}) — skipping TP/SL check")
    return
```

And in `check_take_profit`:

```python
if option_tick.last == -1 or option_tick.bid == -1:
    return  # Silent return, no log
```

**Possible causes:**
- Options contract not subscribed for live data
- TWS not sending ticks for that contract (e.g. illiquid)
- Wrong tick object (e.g. underlying instead of option)

---

### D. Order not filled yet

**When:** `order.order_status != "filled"`.

- `check_and_close_position` returns early: `"Order status=submitted — waiting for fill"` (DEBUG).
- Fill is driven by TWS `orderStatus` → `process_trade` → `process_fill`.
- If `process_trades_callback` is not wired, or Trade not in `trades_cache`, fills are never processed.

---

### E. `synchronize_positions` not linking positions

**When:** Positions exist before Start Trading (e.g. from previous run).

- `synchronize_positions` uses `order_mgr.get_filled_orders(order_side='BUY')`.
- `get_filled_orders` returns `self.db.orders` filtered by filled + BUY.
- **Bug:** `db.orders` is loaded once at DAL startup and is **not updated** when new orders are inserted/updated. New orders from this session are missing from `db.orders`, so pre-existing positions may not get a matching order and are never added for TP/SL.

---

## 5. Recommended Fixes

1. **Upgrade critical DEBUG logs to WARN:**
   - `"Position X: no matching entry order or tick"` when `check_exit_conditions` fails.
   - Makes it visible in the UI when positions are not monitored.

2. **Add INFO log when TP/SL check is skipped due to invalid prices:**
   - Replace or supplement the silent return in `check_take_profit` when `last == -1 or bid == -1`.

3. **Fix DAL `db.orders` staleness:**
   - When `insert_order` or `update_option_order` runs, also update `self.orders` so `get_filled_orders` sees new/filled orders.

4. **Ensure options contract is subscribed for live ticks:**
   - Confirm `get_options_data` subscribes before returning.
   - Confirm the returned tick is the same object that receives TWS tick updates.

5. **Add periodic INFO heartbeat in `monitor_positions_loop`:**
   - e.g. every 30s: `"Position monitor: N positions, M with TP/SL active"` so users see that monitoring is running.

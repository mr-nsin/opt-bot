# Position Monitoring & Closure Flow

Positions are monitored and closed (TP/SL) through **two parallel paths** that both converge to `order_mgr.check_and_close_position(tick=...)`.

---

## Path 1: event_processor (tick-driven)

**Location:** `BOT.py` ~2107–2200

**Trigger:** When IBKR sends a price update (bid or last) for an option contract.

**Flow:**
1. `tws_api_client.tickPrice()` (tws_api_client.py ~590–601) receives bid (tickType=1) or last (tickType=4)
2. Updates `tick.bid` or `tick.last` in `tick_cache`
3. Puts `{"tick": tick}` into `event_queue`
4. `event_processor` threads (4 workers) consume from `event_queue`
5. If `tick.contract.secType == "OPT"` **and** `tick.active_order is not None`:
   - Calls `order_mgr.check_and_close_position(tick=tick)`

**Requirement:** `tick.active_order` must be set. This happens when:
- **placeOrder** (BOT.py ~388): `options_tick.active_order = option_order` before `add_entry_order`
- **synchronize_positions** (BOT.py ~2377): For TWS positions matching DB filled BUY orders
- **synchronize_orders** (BOT.py ~2418): For pending orders in `client.trades_cache`

**Limitation:** TP/SL is checked only when IBKR sends a price update. If the market is quiet (no bid/last change), no TP/SL check runs for that contract.

---

## Path 2: monitor_positions_loop (position-driven)

**Location:** `BOT.py` ~2451–2488

**Trigger:** Every 0.1 seconds (loop).

**Flow:**
1. `client.get_all_positions()` → list of TWS `Position` objects (symbol, strike, right, expiry, position)
2. For each position with `position != 0`:
   - `order_mgr.check_exit_conditions(pos)`
3. `check_exit_conditions` (order_manager.py ~151–174):
   - Extracts symbol, strike, right, expiry from `pos`
   - `_find_entry_order(symbol, strike, right, expiry)` → matches against `entry_orders_cache`
   - `order_id_tick_lookup.get(entry_order.id)` → gets tick
   - `option_tick.active_order = entry_order`
   - `check_and_close_position(tick=option_tick)`

**Requirement:** Entry order must be in `entry_orders_cache` and tick in `order_id_tick_lookup`. If no match: logs "no matching entry order" or "matched order but NO TICK" and skips.

**Limitation:** If tick is missing (e.g. never subscribed), TP/SL cannot run. `check_exit_conditions` returns early with "matched order but NO TICK".

---

## When a position enters the monitoring system

| Scenario | entry_orders_cache | order_id_tick_lookup | tick.active_order | event_processor | monitor_positions_loop |
|---------|--------------------|----------------------|-------------------|-----------------|------------------------|
| **New order placed** (placeOrder) | ✓ add_entry_order | ✓ | ✓ set before add | ✓ | ✓ |
| **synchronize_positions** (TWS pos → DB match) | ✓ add_entry_order | ✓ | ✓ | ✓ | ✓ |
| **synchronize_orders** (pending order in trades_cache) | ✓ add_entry_order | ✓ | ✓ | ✓ | ✓ |
| **Pre-existing position, no sync** | ✗ | ✗ | ✗ | ✗ | ✗ (no match) |

---

## Convergence: check_and_close_position

**Location:** `order_manager.py` ~483–554

Both paths call:
```python
order_mgr.check_and_close_position(tick=option_tick)
```

`check_and_close_position`:
1. Uses `tick.active_order` (set by placeOrder/sync, or by `check_exit_conditions`)
2. Skips if `tick.busy` or `order.exit_placed` or `order.order_status != "filled"`
3. Runs `check_take_profit(tick, order, option_tick)` and `check_stop_loss(last_price, order, option_tick)`
4. If TP or SL hit → `close_position(order, option_tick)`

---

## Startup: synchronize_positions vs synchronize_orders

| Entry point | synchronize_positions | synchronize_orders |
|-------------|----------------------|--------------------|
| **main_call** (standalone BOT) | ❌ COMMENTED OUT (line 2627) | ✓ |
| **Trading engine** (trading_engine.py) | ✓ (lines 711, 720) | ✓ |

**Impact:** In standalone BOT, pre-existing TWS positions (e.g. from before restart) are **not** synced. Only positions opened in this session (via placeOrder) or matched by `synchronize_orders` (pending orders) get TP/SL monitoring.

---

## Summary

| Path | Trigger | Frequency | Depends on |
|------|---------|-----------|------------|
| **event_processor** | IBKR tick (bid/last) | On price change | tick in tick_cache, tick.active_order set |
| **monitor_positions_loop** | Loop | Every 0.1s | entry in entry_orders_cache, tick in order_id_tick_lookup |

Both paths are complementary:
- **event_processor:** Fast reaction when prices move (tick-driven).
- **monitor_positions_loop:** Backup when ticks are sparse; ensures TP/SL is checked even if no recent price update.

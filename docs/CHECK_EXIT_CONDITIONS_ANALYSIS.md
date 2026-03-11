# check_exit_conditions Removal Analysis

## How It Was Removed

### Commit 5d22ec7 (Mar 10, 2026)
**Message:** "Multi-account routing, 10% profit target, strike filter (<.25), config/UI updates"  
**Made-with: Cursor**

### What Cursor Did

Cursor was asked to implement multi-account routing, 10% profit target, strike filter (<.25), and config/UI updates. As part of that refactor, it **simplified** `order_manager.py`:

1. **Changed `entry_orders_cache` key** from composite `option_symbol` (symbol+expiry+right+strike) to **symbol-only**:
   - Before: `key = getattr(order, "option_symbol", None) or f"{order.symbol}{order.expiration}{order.right}{order.strike}"`
   - After: `self.entry_orders_cache[order.symbol] = order`

2. **Removed `_find_entry_order`** – replaced `close_position_by_symbol` with simple `entry_orders_cache.get(symbol)`.

3. **Simplified `close_position_by_symbol`** – removed `strike`, `right`, `reason` parameters; now only accepts `symbol`.

4. **`check_exit_conditions`** – was never in the 5d22ec7 parent. It was added later in commit **499553f** on the `improvment_changes` branch. The `opt-bot` branch (HEAD=5d22ec7) never had it; `BOT.py` was written to call it (likely from code that expected the improvment_changes branch to be merged).

### Why Cursor Removed It

- The refactor assumed **one position per underlying symbol**.
- The simplification reduced code and made `close_position_by_symbol` a simple symbol lookup.
- `check_exit_conditions` was not in scope for that commit; it lived on another branch.

---

## Current State After Restoration

`check_exit_conditions`, `_find_entry_order`, `_norm_expiry`, and `_norm_right` have been restored in `order_manager.py`.

### Position Object Format (TWS)

From `tws_api_client.py` line 770:
```python
Position(account=account, symbol=contract.symbol, position=position, strike=contract.strike, right=contract.right, expiry=contract.lastTradeDateOrContractMonth, avg_cost=avgCost)
```

So positions have: `symbol`, `strike`, `right`, `expiry`, `position`, `account`, `avg_cost`.  
`check_exit_conditions` correctly reads these via `getattr(pos, ...)`.

---

## Critical Bug: entry_orders_cache Key

**Problem:** `entry_orders_cache` is still keyed by `order.symbol` only (line 188):

```python
self.entry_orders_cache[order.symbol] = order
```

If you have **multiple option positions** for the same underlying (e.g. AAPL 150C and AAPL 150P), the second `add_entry_order` **overwrites** the first. Only one entry per symbol is stored.

**Impact:**
- **Single position per symbol:** Works. `_find_entry_order` finds the one order and matches by strike/right/expiry.
- **Multiple positions per symbol:** Broken. Only the last-added order is in the cache; earlier ones are lost. `monitor_positions_loop` will fail to match and run TP/SL for overwritten positions.

**Fix:** Use `option_symbol` (or equivalent composite key) for `entry_orders_cache` instead of `order.symbol`.

---

## Call Chain Verification

1. `monitor_positions_loop()` (BOT.py ~2477) → `client.get_all_positions()` → list of `Position` objects
2. For each `pos` with `position != 0` → `order_mgr.check_exit_conditions(pos)`
3. `check_exit_conditions` → extracts symbol, strike, right, expiry from `pos`
4. `_find_entry_order(symbol, strike, right, expiry)` → iterates `entry_orders_cache.values()`, matches by symbol+strike+right+expiry
5. `order_id_tick_lookup.get(entry_order.id)` → gets `Tick` for price data
6. `check_and_close_position(tick=option_tick)` → runs TP/SL logic

---

## Other Mismatches (from 5d22ec7 simplification)

| Caller | Expects | order_manager provides |
|--------|---------|-------------------------|
| BOT.py:311 | `get_entry_order(symbol, right)` | `get_entry_order(symbol)` – `right` ignored |
| BOT.py:1088 | `get_entry_order(stockName, right=...)` | `right` ignored |
| trading_engine:456 | `close_position_by_symbol(symbol, strike, right)` | `close_position_by_symbol(symbol)` – strike/right ignored |

These work only when there is at most one position per symbol.

---

## Fixes Applied (Post-Analysis)

1. **Restored `check_exit_conditions`** and helpers (`_find_entry_order`, `_norm_expiry`, `_norm_right`).

2. **Fixed `entry_orders_cache` key** – now uses `option_symbol` (symbol+expiry+right+strike) via `_option_key(order)` so multiple positions per underlying are supported.

3. **Restored `close_position_by_symbol(symbol, strike, right, expiry, reason)`** – uses `_find_entry_order` for lookup; trading_engine and UI can pass strike/right.

4. **Restored `get_entry_order(symbol, right, strike, expiry)`** – uses `_find_entry_order`; BOT.py calls with `right` for "order already present" checks.

5. **Fixed `close_all_positions`** – iterates over `entry_orders_cache.values()` and closes each order directly (no longer relies on symbol-only keys).

Position monitoring should now work correctly for single and multiple positions per symbol.

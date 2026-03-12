# Duplicate Positions — Root Cause Analysis

## Summary

**Are multiple trades actually opening?** No. The `entry_orders_cache` is keyed by `_option_key(order)` = symbol+expiration+right+strike. Multiple orders for the same option **overwrite** each other — we only track one. TWS aggregates positions by contract, so we get one position per option.

**Why do duplicates appear in the UI?** Duplicates come from **display/aggregation bugs**, not from multiple real trades:

1. **Key format inconsistency** — Different code paths use different formats for expiry ("20260313" vs "2026-03-13") and right ("C" vs "CALL"), causing the same logical position to be treated as distinct.
2. **Missing expiry in match logic** — React and Rust matched by symbol+strike+right only; expiry was ignored.
3. **No deduplication** — Raw data flowed through without merging duplicates.

---

## 1. Trade Flow (No Duplicate Trades)

### Order placement
- `placeOrder` / `placeAndVerifyOrder` → `add_entry_order(order, tick)`
- `entry_orders_cache[key] = order` where `key = _option_key(order) = symbol+expiration+right+strike`
- **If we place 3 orders for MSFT CALL 487.5 20260313:** Each `add_entry_order` overwrites the previous. We end up with **1 entry** in the cache.

### Order fills
- Each fill → `process_fill` → `_emit_trade_executed`
- **3 fills → 3 `trade_executed` events** (same symbol, strike, right, expiry)
- React: First adds position. Second and third should match `alreadyExists` and skip — **if** expiry is in the check.

### TWS positions
- `position(account, contract, position, avgCost)` callback
- Ticker key: `symbol+lastTradeDateOrContractMonth+right+strike`
- **3 fills → 3 callbacks**, each updating the same ticker (position=1, then 2, then 3). We end up with **1 entry** in `client.positions`.

**Conclusion:** We do **not** open multiple separate positions for the same option. TWS and our cache both aggregate.

---

## 2. Root Causes of UI Duplicates

### A. `_option_key` uses raw expiration (no normalization)

```python
# order_manager.py
def _option_key(self, order: OptionOrder) -> str:
    return f"{order.symbol}{order.expiration}{order.right}{order.strike}"
```

- Order A: expiration `"2026-03-13"` → key `"MSFT2026-03-13C487.5"`
- Order B: expiration `"20260313"` → key `"MSFT20260313C487.5"`
- **Same option, different keys** → 2 entries in `entry_orders_cache`.

**When:** Fallback path in `get_positions` (when TWS positions empty) iterates `entry_orders_cache.values()`. Different expiration formats → multiple position rows for the same option.

### B. TWS position callback ticker

```python
# tws_api_client.py
ticker = f"{contract.symbol}{contract.lastTradeDateOrContractMonth}{contract.right}{contract.strike}"
```

- If TWS ever sends `lastTradeDateOrContractMonth` as `"2026-03-13"` in one callback and `"20260313"` in another, we get 2 entries for the same option.
- IB typically uses YYYYMMDD, but format can vary by source.

### C. React `position_update` / `trade_executed` — expiry not in match

- Before fix: matched by `symbol`, `strike`, `right` only.
- Same option with different expiry formats could match the wrong row or fail to match, leading to duplicate adds.

### D. Rust `position_update` — right not normalized

- `p.right == pos.right` fails when one is `"C"` and the other `"CALL"`.
- Result: Rust pushes a new position instead of updating → duplicate rows.

---

## 3. Why Deduplication Is Needed

Even with fixes, deduplication is a **defense-in-depth** measure because:

1. **External data** — TWS/IB can send inconsistent formats.
2. **Multiple sources** — Orders from DB, TWS positions, sync logic can use different formats.
3. **Race conditions** — Rapid events can produce overlapping updates before state settles.

Deduplication at the backend (`get_positions`) and frontend (`setPositions`) ensures we never show duplicate rows regardless of upstream quirks.

---

## 4. Recommended Fixes (Beyond Current Deduplication)

### Fix 1: Normalize `_option_key` in order_manager ✅ DONE

`_option_key` now uses `_norm_expiry` and `_norm_right` so cache keys are consistent. This prevents the fallback path from ever creating multiple entries for the same option when expiration/right formats differ.

### Fix 2: Normalize TWS position ticker (optional)

In `tws_api_client.position()`, normalize `lastTradeDateOrContractMonth` before building the ticker so the same option always maps to the same key. (Lower priority if backend deduplication is robust.)

---

## 5. Verification

- Run with logging: Check `entry_orders_cache` size vs number of unique options.
- After `_option_key` normalization: Same option should never produce multiple cache entries.
- UI: Each (symbol, strike, right, expiry) should appear at most once in Active Positions.

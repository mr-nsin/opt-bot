# TAKE PROFIT CHECK – Order 374 Analysis

## Root Cause: No Streaming Price Updates (bid, last constant)

### Critical bug: init_data_feed uses snapshot-only, blocks streaming

**Flow:**
1. `init_data_feed()` subscribes to options with `subscribe(contract, snapshot=True)` — gets ONE snapshot of bid/last.
2. After 10s, it calls `subscribe(contract)` (no snapshot) to establish streaming.
3. In `subscribe()`: when `ticker_id` is already in cache (from step 1), it **returns early** with "already subscribed, skipping".
4. **Result:** Options never get streaming. `tickPrice()` is only called once per contract. bid/last never update.

**Fix applied:** Track `_snapshot_only_tickers`. When `subscribe(contract, snapshot=False)` is called for a ticker that was snapshot-only, cancel the snapshot and re-subscribe for streaming.

---

## Why Values Don't Change (bid, last, current_profit_price)

### 1. Tick data is only updated when IBKR sends updates

**Source:** `tws_api_client.py` tickPrice() – tickType 1 (bid), 2 (ask), 4 (last)

- `tick.bid`, `tick.last`, `tick.ask` are updated **only** when IBKR sends `tickPrice()`.
- If the market is quiet (no trades, no quote changes), IBKR does not send updates.
- **monitor_positions_loop** runs every **0.1 seconds** and uses the same tick from `order_id_tick_lookup`.
- That tick is the same object as in `tick_cache` – it is only modified when `tickPrice()` runs.
- **Result:** If no `tickPrice()` for 5 seconds, you see the same bid/last 50 times in a row.

### 2. order.current_profit_price only changes when TP logic runs

- `current_profit_price` is stored on the order and persisted via `db.update(order)`.
- It is updated only when: `exit_price >= order.current_profit_price` → we raise the target.
- If `exit_price` never reaches `current_profit_price` (e.g. target $3.00, exit_price stuck at $2.87), it never changes.
- **Result:** Same `current_profit_price` on every check until the condition is met.

### 3. Ask is not used in TP/SL logic

- `tick.ask` is updated by tickType 2, but **ask updates do not put events in event_queue**.
- TP/SL uses `tick.bid` and `tick.last` only.
- Ask is logged in `log_order_status` but not used for exit decisions.

---

## Are we getting "current" values?

**Yes, but only as current as IBKR’s last update.**

- We read `tick.bid` and `tick.last` from the tick object.
- That tick is updated in place by `tickPrice()` when IBKR pushes new data.
- There is no explicit request for a fresh quote; we rely on IBKR’s streaming updates.
- **"Current"** = last value received from IBKR. If no update for 10 seconds, values are 10 seconds old.

---

## Critical bug: exit_price uses bid (can lag last)

**Current logic (order_manager.py ~579–584):**
```python
if tick.bid > 0 and tick.bid <= tick.last:
    exit_price = tick.bid   # Use BID when bid <= last
else:
    exit_price = tick.last
```

**Previous logic (before 5d22ec7):**
```python
# For TP trigger: use max(bid, last) so we recognize when price reaches target
# (bid can lag last; using bid-only missed TP when last hit target but bid hadn't)
exit_price = max(bid_val, last_val)
```

**Impact for Order 374 (AMZN PUT):**
- Log: Exit $2.87, Bid $2.87, Last $2.89
- Current code: `exit_price = bid = $2.87` (because bid <= last).
- If `current_profit_price` is $2.90, we never hit `exit_price >= current_profit_price`.
- But **last** is $2.89 – closer to target. If last later reaches $2.95 while bid stays at $2.90, we would miss TP because we use bid ($2.90) instead of max(bid, last) = $2.95.

**Recommendation:** Use `max(bid, last)` for TP checks so we recognize when price reaches target even if bid lags.

---

## Flow summary

| Component | When updated | Used for |
|-----------|-------------|----------|
| tick.bid | tickPrice() tickType 1 | exit_price (current: when bid ≤ last) |
| tick.last | tickPrice() tickType 4 | exit_price (current: else branch) |
| tick.ask | tickPrice() tickType 2 | Logging only |
| order.current_profit_price | When exit_price ≥ target | Trailing TP target |

---

## Recommendations

1. **Restore max(bid, last) for TP exit_price** – avoids missing TP when bid lags last.
2. **Throttle TAKE PROFIT CHECK logs** – e.g. log at most every 30s per order when values unchanged, to reduce log noise.
3. **Optional: request snapshot** – if needed, add an explicit `reqMktData` snapshot to refresh prices when monitor runs, at the cost of extra API calls.

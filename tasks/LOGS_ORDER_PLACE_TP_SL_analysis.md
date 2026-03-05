# Deep Analysis: LOGS:ORDER_PLACE Positions — Why They Weren't Closed by TP/SL

**Log source:** `bot_2026-03-04.log`  
**Scope:** All orders logged via `LOGS:ORDER_PLACE` and their TP/SL outcomes

---

## 1. Summary of All LOGS:ORDER_PLACE Events

| # | Time     | Stock | Order IDs   | Outcome                          |
|---|----------|-------|-------------|----------------------------------|
| 1 | 19:25:05 | TSLA  | 67, 68      | **Both CANCELLED** (67 @ 19:25:07, 68 @ 19:25:11) |
| 2 | 19:26:36 | MSFT  | 69          | **CANCELLED** (69 @ 19:26:58)    |
| 3 | 19:27:31 | TSLA  | 70          | **CANCELLED** (70 @ 19:28:32)    |
| 4 | 19:29:01 | NVDA  | 71          | **FILLED** (MKT order) — monitored |
| 5 | 19:30:24 | TSLA  | 73          | **CANCELLED** (73 @ 19:30:25)   |
| 6 | 19:31:49 | MSFT  | 74          | **CANCELLED** (74 @ 19:32:49)   |
| 7 | 19:34:01 | AMD   | 75          | **CANCELLED** (75 @ 19:35:00)   |
| 8 | 19:35:37 | TSLA  | 76          | **FILLED** (LMT) — monitored     |
| 9 | 19:37:00 | MSFT  | 77          | **CANCELLED** (77 @ 19:38:00)   |

**Key finding:** Only **2 orders filled** (71 NVDA, 76 TSLA). All **7 LMT orders** were cancelled (GTD/timer).

---

## 2. Orders That Filled and Were Monitored

### Order 71 — NVDA20260306CALL185.0
- **Placed:** 19:29:01 (MKT)
- **Filled:** 19:29:04
- **TP:** $1.92 | **SL:** $1.40
- **Monitoring:** Yes (TAKE PROFIT CHECK / STOPLOSS CHECK present)
- **Last observed (19:38:31):** Bid between SL and TP
- **Closed by TP/SL?** No

### Order 76 — TSLA20260306PUT405.0
- **Placed:** 19:35:37 (LMT $5.55)
- **Filled:** 19:35:37 (same second)
- **TP:** $5.88 | **SL:** $5.16
- **Monitoring:** Yes
- **Last observed (19:38:31):** Exit $5.55, Bid $5.55, TP $5.88, SL $5.16
- **Closed by TP/SL?** No

---

## 3. All 7 Positions Monitored at End of Session (19:38:31)

| Order | Contract            | Exit (Bid) | TP   | SL   | TP Hit?  | SL Hit? | Distance to TP | Distance to SL |
|-------|---------------------|------------|------|------|----------|---------|----------------|----------------|
| 4     | NVDA PUT 182.5      | $2.51      | $2.80| $2.24| No       | No      | $0.29 below    | $0.27 above    |
| 9     | AMD PUT 200         | $3.35      | $3.63| $3.02| No       | No      | $0.28 below    | $0.33 above    |
| 10    | BABA CALL 134       | $2.42      | $2.56| $2.25| No       | No      | $0.14 below    | $0.17 above    |
| 30    | AMZN PUT 215        | $2.08      | $2.38| $1.82| No       | No      | $0.30 below    | $0.26 above    |
| 36    | BABA PUT 133        | $2.14      | $2.27| $1.99| No       | No      | $0.13 below    | $0.15 above    |
| 49    | AMZN CALL 217.5     | $1.75      | $2.02| $1.50| No       | No      | $0.27 below    | $0.25 above    |
| 71    | NVDA CALL 185       | (in list)  | $1.92| $1.40| No       | No      | —              | —              |
| 76    | TSLA PUT 405        | $5.55      | $5.88| $5.16| No       | No      | $0.33 below    | $0.39 above    |

**Conclusion:** For every position, market price (bid) stayed **between** TP and SL. Neither condition was ever met.

---

## 4. Why TP/SL Did Not Close Any Position

### A. TP Logic (Trailing)

The logic in `check_take_profit`:

1. **Activate trailing:** When `exit_price >= current_profit_price` → set `profit_trigger`, raise target, return (no close).
2. **Close on pullback:** When `profit_trigger` AND `exit_price < (current_profit_price - profit_increment)` → close.

So TP only closes after:
- Price first reaches the target (activates trigger),
- Then pulls back by at least `profit_increment` (e.g. $0.03).

In this session, no position ever reached its TP target, so the trigger never activated and no TP close occurred.

### B. SL Logic

SL closes when `exit_price <= stoploss_price`.

In all cases, bid remained above SL. No SL close occurred.

### C. Price vs. TP/SL — Numeric Check

| Order | Bid  | TP   | SL   | bid >= TP? | bid <= SL? |
|-------|------|------|------|------------|------------|
| 4     | 2.51 | 2.80 | 2.24 | No         | No         |
| 9     | 3.35 | 3.63 | 3.02 | No         | No         |
| 10    | 2.42 | 2.56 | 2.25 | No         | No         |
| 30    | 2.08 | 2.38 | 1.82 | No         | No         |
| 36    | 2.14 | 2.27 | 1.99 | No         | No         |
| 49    | 1.75 | 2.02 | 1.50 | No         | No         |
| 76    | 5.55 | 5.88 | 5.16 | No         | No         |

So TP and SL conditions were never satisfied.

---

## 5. Why Many LOGS:ORDER_PLACE Positions Never Became Positions

**Root cause:** GTD (Good-Till-Date) on LMT orders with `ORDER_EXPIRY_TIMER`.

| Order | Type | Placed      | Cancelled  | Time to cancel |
|-------|------|-------------|------------|----------------|
| 67    | LMT  | 19:25:05    | 19:25:07   | ~2 sec         |
| 68    | LMT  | 19:25:05    | 19:25:11   | ~6 sec         |
| 69    | LMT  | 19:26:36    | 19:26:58   | ~22 sec        |
| 70    | LMT  | 19:27:31    | 19:28:32   | ~61 sec        |
| 73    | LMT  | 19:30:24    | 19:30:25   | ~1 sec         |
| 74    | LMT  | 19:31:49    | 19:32:49   | ~60 sec        |
| 75    | LMT  | 19:34:01    | 19:35:00   | ~59 sec        |
| 77    | LMT  | 19:37:00    | 19:38:00   | ~60 sec        |

Cancellations occur within ~60 seconds (or much less for 67, 68, 73), consistent with `ORDER_EXPIRY_TIMER`. Those orders never filled, so they never became positions and were never eligible for TP/SL.

---

## 6. Potential Logic Bug: `exit_price` When `bid > last`

In `check_take_profit`:

```python
if tick.bid > 0 and tick.bid <= tick.last:
    exit_price = tick.bid
else:
    exit_price = tick.last
```

When `bid > last`, `exit_price = last` (stale or lower price). That can:

- Make TP harder to hit (we need `last >= TP` instead of `bid >= TP`).
- Make SL easier to hit (we need `last <= SL` instead of `bid <= SL`).

For a long options position, the actionable sell price is the bid. Prefer `exit_price = tick.bid` when `tick.bid > 0`, unless there is a deliberate reason to use `last` in edge cases.

---

## 7. How Positions Were Ultimately Closed

Exit orders 78–84 filled around 19:38:33–19:38:46:

- 78: AMZN CALL 217.5
- 79: AMD PUT 200
- 80: NVDA PUT 182.5
- 81: BABA CALL 134
- 82: BABA PUT 133
- 83: AMZN PUT 215
- 84: TSLA PUT 405

These are MKT SELL (exit) orders, consistent with **Close All** or similar EOD/square-off logic, not with TP/SL.

---

## 8. Recommendations

| Priority | Issue | Recommendation |
|----------|-------|----------------|
| **P0** | LMT orders cancelled by GTD | Increase `ORDER_EXPIRY_TIMER` or turn off GTD when not needed. LMT orders are being cancelled before fill. |
| **P1** | `exit_price` when `bid > last` | Use `bid` for `exit_price` when closing longs, unless there is a clear rationale for using `last`. |
| **P2** | Optional: non-trailing TP | Add a mode to close on first TP hit (e.g. `exit_price >= current_profit_price` and `not order.profit_trigger`) instead of only trailing. |
| **P2** | Logging | Log `ORDER_EXPIRY_TIMER` on order placement and when GTD causes cancellation. |

---

## 9. Conclusion

- **Monitoring:** All filled positions (and synced ones) were monitored correctly; TP/SL checks ran regularly.
- **No TP/SL closes:** Market bid stayed between TP and SL for every position; TP/SL conditions were never met.
- **Orders not becoming positions:** Most `LOGS:ORDER_PLACE` LMT orders were cancelled by GTD within about 60 seconds (or less), so they never filled and were never monitored.

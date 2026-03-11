# Log Analysis: Trade Placement, Position Monitoring & Trade Closure
**Dates:** 2026-03-09, 2026-03-10  
**Logs analyzed:** bot_2026-03-09, bot_2026-03-10, and rotated session logs  
**Last updated:** Fixes applied per recommendations below

---

## Executive Summary

| Area | Status | Key Findings |
|------|--------|--------------|
| **Trade placement** | ✅ Working | Entry orders placed; some cancelled (cooldown, optionsTickLocked) |
| **Position monitoring (TP/SL)** | ✅ Working | TP/SL checks run every ~30s; all 6–7 positions monitored |
| **Trade closure (EOD/Day limit)** | ✅ Fixed | getAndBuyAfterMarketEnd bug fixed — positions close on EOD/day limit |
| **Event processor** | ✅ Fixed | Logging now includes exception message |
| **getAndBuyAfterMarketEnd** | ✅ Fixed | `fileData` dict handling corrected |

---

## 1. Trade Placement

### 1.1 Entry Orders
- **bot_2026-03-10_17-02-16:** Session started with 6 existing TWS positions (AMD, AMZN, TSLA, BABA, etc.)
- New entry orders placed: MSFT 407.5 CALL (488, 490), NVDA 185 PUT (489, 491, 492, 493, 495), NVDA 187.5 CALL (494)
- Order 494 (NVDA CALL) **filled** at 17:10:48
- Others **cancelled** due to: `cooldownPeriodHit`, `optionsTickLocked`, `orderAlreadyPresent`

### 1.2 Order Flow
```
Created option_order → submitted/presubmitted → filled (494) or cancelled (others)
```

### 1.3 Issues
- **Cooldown:** NVDA_PUT_20260313 cooldown (120s) blocked repeated entries
- **optionsTickLocked:** Some orders cancelled before fill (tick lock)
- **orderAlreadyPresent:** Correctly skips when position already exists

---

## 2. Position Monitoring (TP/SL)

### 2.1 Monitoring Active
- **Position monitor thread** started and runs every ~30 seconds
- **TP/SL processors** (3 dedicated threads) run for position monitoring
- Log pattern: `Position monitor: N TWS pos | M entry_orders, K ticks`

### 2.2 TP/SL Check Pattern
```
TAKE PROFIT CHECK - Order(X) SYMBOL: Exit Price, Bid, Last, Initial Profit, Current Profit, Trigger Active
STOPLOSS CHECK - Order(X) SYMBOL: Exit Price, Bid, Last, StopLoss
```

### 2.3 Example (bot_2026-03-10_17-02-16)
| Order | Contract | Exit | Bid | Last | StopLoss | Status |
|-------|----------|------|-----|------|----------|--------|
| 373 | AMD20260313PUT202.5 | $4.50 | $4.50 | $4.55 | $4.08 | OK |
| 374 | AMZN20260313PUT212.5 | $2.87 | $2.87 | $2.89 | $2.54 | OK |
| 377 | TSLA20260313PUT397.5 | $4.80 | $4.80 | $4.70 | $4.37 | OK |
| 379 | AMZN20260313CALL215.0 | $2.24 | $2.24 | $2.27 | $2.01 | OK |
| 416 | TSLA20260313CALL407.5 | $4.80 | $4.80 | $4.99 | $4.42 | OK |
| 461 | BABA20260313CALL140.0 | $1.52 | $1.46–1.52 | $1.52 | $1.40 | **Close to SL** (Bid $1.46 vs SL $1.40) |
| 494 | NVDA20260313CALL187.5 | $1.92 | $1.90 | $1.92 | $1.63 | OK |

### 2.4 TP/SL Logic
- **SL:** Exit when `Bid <= StopLoss` (for long positions)
- **TP:** Exit when `Last >= Current Profit` and `Trigger Active` becomes True (trailing)
- During the session, **no TP or SL was hit** under normal monitoring — all positions were above SL and below TP

### 2.5 Position Monitor vs TP/SL Processors
- **Position monitor:** Legacy loop; logs "N TWS pos | M entry_orders"
- **TP/SL processors:** Dedicated threads consuming from `_opt_event_queue`; perform actual TP/SL checks and place exit orders
- Both run; TP/SL processors are the primary exit logic

---

## 3. Trade Closure (EOD / Day Limit)

### 3.1 Trigger Flow
When **timeCheckAndCloseProgram** returns True (EOD or PnL limit):
1. `cancel_all_orders()` — cancels pending entry orders
2. `getAndBuyAfterMarketEnd()` — places MKT close for each TWS position

### 3.2 Observed Triggers
- **bot_2026-03-10:** 20:52:03, 21:04:17, 21:11:52 — "Cancel All Placed Order/s And Square Off..."
- **bot_2026-03-09:** 20:46:00, 23:47:09, 23:47:50, 23:48:26, 23:49:02

### 3.3 Critical Bug: getAndBuyAfterMarketEnd — FIXED
```
ERROR - Error in getAndBuyAfterMarketEnd: int() argument must be a string, a bytes-like object or a real number, not 'dict'
```
- **Cause:** `buf = int(globals().get("fileData") or {}).get(...)` — `fileData` is a dict; `int(dict)` fails
- **Impact:** **Positions were NOT closed** when EOD/day limit triggered — the function crashed before placing MKT orders
- **Fix applied:** `file_data = globals().get("fileData") or {}`; `buf = file_data.get("emergency_close_buffer_seconds", 5) if isinstance(file_data, dict) else 5`

### 3.4 Successful Closure (bot_2026-03-10_17-02-16)
- At **17:11:09** — timeCheckAndCloseProgram triggered (likely EOD; PnL was -$120.73, loss limit -$250)
- **Routing exit order** and **EXIT Order (496–502) ... was filled** for all 6 positions
- This session used a **different code path** (cancel_all + order_manager close_all or similar) — exits were placed and filled
- The **getAndBuyAfterMarketEnd** bug affects sessions where that function is called (e.g. from timeCheckAndCloseProgram in checkAlgoAndTrade flow)

---

## 4. Event Processor Errors

### 4.1 Pattern
```
2026-03-10 17:46:55 - ERROR - Error occurred:
```
- Hundreds of occurrences in bot_2026-03-10.log at startup (17:46:55)
- Source: `BOT.py` line ~2200 — `event_processor` except block

### 4.2 Likely Cause
- Possible causes: `Empty` (queue timeout), TWS disconnect, or exception in `checkAlgoAndTrade` / `checkConditionsAndTrade`

### 4.3 Fix Applied
- Changed to: `logger.error(f"Event processor error: {ex}", exc_info=True)` so the exception message is visible

---

## 5. Other Observations

### 5.1 Delta/Volume Mismatch — FIXED
```
Delta/Volume values not matched. received Delta is = -5.47e-05 and Volume is = 557 ** Expected Delta is = -0.35 and Volume is = 100
```
- QQQ strike 561.0 PUT has near-zero delta (weekly) — fails delta check
- SPY: `received Delta is = -1 and Volume is = -1` — indicates missing/invalid options data
- **Fix applied:** `get_delta_volume` now treats delta=-1 or volume=-1 as invalid — returns "NoDataPresent" instead of noisy mismatch

### 5.2 Position Sync
- `synchronize_positions: 0 TWS positions (qty≠0), 0 filled BUY orders in DB` — after restart, DB is empty
- When positions exist from prior session, sync matches TWS positions to filled BUY orders for TP/SL

### 5.3 bot_2026-03-04 (Older Log)
- `AMZN20260306P207.5 position: no matching filled BUY order in DB — cannot monitor TP/SL`
- Positions carried from before app start cannot be monitored if not in DB

---

## 6. Recommendations

| Priority | Action | Status |
|----------|--------|--------|
| **P0** | Fix `getAndBuyAfterMarketEnd` — ensures positions close on EOD/day limit | ✅ Done |
| **P1** | Improve "Error occurred" logging — include exception message in log line | ✅ Done |
| **P2** | Add explicit "SL HIT" / "TP HIT" log when exit is placed due to TP/SL | ✅ Done (HIT STOPLOSS, HIT TAKE PROFIT) |
| **P3** | Handle `-1` delta/volume from options data — treat as "no data" and skip | ✅ Done |
| **P4** | Document timezone: timeCheckAndCloseProgram uses NY_TZ; ensure endTime matches intended market close | Pending |
| **P5** | Fix `pos_right` parsing — use `position.right` instead of parsing `__str__` (was returning expiry) | ✅ Done |
| **P6** | Fix `checkAlgoAndTrade` returning `"DayLocked"` string — causes "too many values to unpack" | ✅ Done |
| **P7** | Fix typos: Öptions→Options, or→for, priceConditonNotMatched→priceConditionNotMatched | ✅ Done |
| **P8** | Fix ticker key mismatch: `get_options_contract` used full right (CALL) vs `get_options_data` used right[0] (C) | ✅ Done |

---

## 7. Conclusion

- **Position monitoring (TP/SL)** is functioning: checks run, prices compared correctly, no false triggers.
- **Trade closure** was broken by the `getAndBuyAfterMarketEnd` bug when EOD/day limit fired; **fix applied**.
- **Event processor** logging improved; exception message now visible.
- **Delta/volume -1** now treated as invalid data; returns "NoDataPresent" instead of noisy mismatch.
- **pos_right parsing** fixed — now uses `position.right` directly; previously parsed `__str__` and got expiry instead of C/P.
- **checkAlgoAndTrade DayLocked** — now returns `(False, 0.0, ([0],[0],[0]))` instead of `"DayLocked"` string to avoid unpack error.
- **Typos** fixed: Öptions→Options, or→for, priceConditonNotMatched→priceConditionNotMatched.
- **Ticker key** — `get_options_contract` now uses `right[0]` (C/P) for cache key to match `get_options_data`.
- **P4** (timezone documentation) remains pending.

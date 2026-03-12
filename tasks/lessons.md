# Lessons Learned

## Bug Fix Workflow (2026-03-12)

### Rule: Test Every Fix

When fixing any issue:
1. **Create a test case** for every fix — test should fail before fix, pass after
2. **Run tests first** — do not mark done until tests pass locally
3. **Verify no regressions** — run broader test suite; manually check related functionality if no tests exist

See `.cursor/rules/fix-and-test.mdc` for the full rule.

---

## Stop Trading / Sidecar Not Stopping (2026-03-12)

### Problem
- Stop Trading button clicked but sidecar kept running
- Signals continued to be generated and printed in logs after stop

### Root Cause
1. **event_processor never checked STOP_TRADING** — The loop only exited when `client.connection_closed` was True (in the Empty branch). It never read `BOT.STOP_TRADING`.
2. **checkConditionsAndTrade did not gate on STOP_TRADING** — Trade logic ran even when stopping.

### Fix
1. Add `STOP_TRADING` check at start of each event_processor loop iteration; set `keep_running = False` when True.
2. Add `STOP_TRADING` check in Empty except block.
3. Add early return in `checkConditionsAndTrade` when `STOP_TRADING` is True.
4. Handler already calls `os._exit(0)` after `engine.stop()` — process exits.

### Pattern
- **Background loops must check stop flags** — Any long-running loop (event_processor, watchdog) must periodically check a stop flag. Relying only on "connection closed" or similar is fragile.
- **Gate entry points** — Functions that trigger side effects (checkConditionsAndTrade, takeTrade) should check STOP_TRADING at entry to avoid work during shutdown.

---

## Signal Scan & Stop Trading Log Noise (2026-03-12)

### Issues
1. **Signal scan failed: name 'BOT' is not defined** — Engine loop used `BOT.scan_all_stocks_signals()` without importing BOT first (sidecar process).
2. **Order 22217 not found / Code 202** — During reqGlobalCancel, TWS sends error 202 for orders already filled/cancelled; untracked orders log as ERROR.
3. **TWS disconnected — waiting for engine reconnect** (x4) — Event processors could log during shutdown race.

### Fixes
1. Add `import BOT` before signal scan in trading_engine engine loop.
2. Add IB error code 202 to `warning_codes` (tws_api_client) so it logs as WARN.
3. Downgrade "Order not found" to WARNING in tws_api_client and order_manager (expected during cancel).
4. Re-check STOP_TRADING in event_processor Empty branch before logging "TWS disconnected" to avoid shutdown race.

---

## Cooldown Key Mismatch — Cooldown Never Enforced (2026-03-12)

### Problem
When the same symbol+right+expiry signal fires again after an exit, the cooldown period is ignored and a new trade is placed immediately.

### Root Cause
**Key format mismatch between SET and CHECK:**
- **SET** (order_manager.py `process_fill`): Uses `order.right` from exit order which is IB format `"C"` / `"P"` (via `contract.right`). Key: `"SPY_C_20260312"`.
- **CHECK** (BOT.py `checkConditionsAndTrade`): Uses `rightMatch` = `"CALL"` / `"PUT"`. Key: `"SPY_CALL_20260312"`.
- These keys **never match**, so `trade_time_dict.get(key)` always returns `None` and cooldown is never enforced.

### Fix
1. **Normalize right in `_cooldown_key`**: `CALL/C → C`, `PUT/P → P` (first letter, uppercased). Both sides now produce the same key.
2. **Use `BOT._cooldown_key`** in order_manager instead of manual key construction.

### Tests
- 23 tests in `tests/test_cooldown.py` covering key normalization, cooldown enforcement, boundary conditions, and cross-format matching.

### Pattern
- **Canonical keys** — When data flows through different systems (IB API uses C/P, app logic uses CALL/PUT), normalize to one format at the key-construction boundary.

---

## Position Monitoring & UI Issues (2026-03-12)

### Issues Found
1. **Trade appears in Positions before Trade Blotter** — `position_update` (every 2s) populated positionStore, but `trade_executed` only populated tradingStore. Blotter appeared delayed.
2. **Active Positions tab continuously re-rendered** — 2s polling interval PLUS 2s event-driven updates = double-update causing flicker.
3. **Current price / bid / ask not updating live** — Prices only sent via `position_update` snapshots every 2s. `emit_tick` existed but was never called. No frontend tick subscription.
4. **position_update and trade_closed listeners page-scoped** — Only ran when Positions page was active; positionStore went stale on other pages.

### Fixes
1. On `trade_executed`, immediately add a position to `positionStore` so Blotter and Active Positions show simultaneously.
2. Removed 2s polling interval from PositionsPage; rely on event-driven `position_update` (now 1s) + manual Refresh button.
3. Reduced `_positions_interval_sec` from 2s to 1s for faster price updates.
4. Moved `position_update` and `trade_closed` listeners from `usePositions` (page-level) to `useTradingEvents` (app-level).

### Pattern
- **App-level event listeners** — Position and trade events must be handled at the app root, not in page-specific hooks that unmount when navigating away.

---

## Duplicate Positions in Active Positions Tab (2026-03-12)

### Problem
Multiple rows for the same trade (same symbol, strike, right, expiry) appeared in the Active Positions tab — e.g. 3x MSFT CALL 487.5 20260313, 3x AMZN CALL 212.5, 5x SPY CALL 671.

### Root Causes
1. **Missing expiry in match logic** — React `position_update` and `trade_executed` handlers matched by symbol+strike+right only; expiry was ignored, causing wrong matches and duplicate adds.
2. **Backend could return duplicates** — TWS/fallback paths could produce duplicate entries when expiry format differed (e.g. `20260313` vs `2026-03-13`) or when multiple orders existed for the same option.
3. **Rust `right` string mismatch** — `p.right == pos.right` failed when Python sent "C" and existing had "CALL", so Rust pushed instead of updating.
4. **No safety deduplication** — `setPositions` did not deduplicate when replacing positions.

### Fixes
1. **Python `get_positions`** — Added `_deduplicate_positions()` to merge duplicates by (symbol, strike, right, expiry); prefer entry with `current_price > 0`.
2. **React handlers** — Added `normExp` and include expiry in `alreadyExists` (trade_executed) and `existing` find (position_update).
3. **Rust `position_update`** — Added `norm_right` to match C/CALL and P/PUT consistently.
4. **positionStore** — Added `dedupePositions()` in `setPositions` as a safety net.
5. **PositionRow key** — Include expiry in React key to avoid duplicate-key warnings.

### Tests
- 8 tests in `tests/test_position_deduplication.py` covering empty, single, duplicates, expiry/right normalization, and distinct positions.

### Pattern
- **Match on full identity** — For options, always match by (symbol, strike, right, expiry). Normalize expiry (strip dashes/spaces) and right (C/CALL, P/PUT) across the pipeline.
- **Defense in depth** — Deduplicate at source (backend) and at sink (store) to handle edge cases.

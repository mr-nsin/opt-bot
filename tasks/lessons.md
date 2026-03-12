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

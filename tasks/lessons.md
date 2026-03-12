# Lessons Learned

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

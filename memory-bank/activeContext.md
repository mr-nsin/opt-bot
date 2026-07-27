# Active Context: QuantDrift Options Trading Bot

## Current Focus of Work
* We completed a comprehensive architecture review and **Ponytail Review** (code cleanup) to optimize performance and ensure the bot operates reliably end-to-end.
* **The Decision:** Aligned on the **Class-Based BOT Wrapper Architecture** (`trading-engine` wrapping `BOT.py`/`tws_api_client.py`) as the primary production engine. The alternative `ib_insync` rewrite was found to be incomplete (missing option chains, strikes, and order placements) and was fully cleaned up.
* **Code Cleanup:** Deleted obsolete Tkinter/PyQt files (`TK_GUI.py`, `new_change.py`, `image_load.py`), the unused `clients/` folder (Databento/Tradovate connectors), and the incomplete `ib_insync` sidecar rewrite files.

## Recent Decisions
* **Performance Optimizations:** 
  1. Throttled stock scans to 2.0s and option risk checks to 0.25s per symbol.
  2. Implemented a 90-contract streaming limit in `tws_api_client.py` to prevent IBKR API cutoffs.
  3. Added virtualized scrolling in the `TradeBlotter` UI (TanStack Virtualizer) to render hundreds of transactions lag-free.
  4. Expanded log display limits to 500 lines for comprehensive signal monitoring.

## Next Steps
* Run regression tests on the full Tauri app workspace.
* Monitor live trade execution and TWS reconnect stability during market hours.
* Ensure all developers follow the unified rules defined in `antigravity-rules.md`.

